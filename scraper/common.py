"""Outils partagés : HTTP, parsing des tailles, appariement produit <-> besoin."""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEBUG_DIR = ROOT / "debug"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


@dataclass
class Candidate:
    name: str
    price: float                 # prix du conditionnement, en devise locale
    currency: str                # CHF / EUR
    url: str = ""
    size: float | None = None    # quantité dans l'unité de l'article (kg, L, pce)
    unit: str | None = None
    unit_price: float | None = None
    promo: bool = False
    ean: str | None = None
    raw_size: str = ""
    variable_weight: bool = False   # vendu au poids : le prix affiché est un prix unitaire

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Session:
    """Session HTTP polie : un seul client, pause entre requêtes, dump optionnel pour le debug."""
    delay: float = 1.5
    s: requests.Session = field(default_factory=requests.Session)
    debug: bool = bool(os.environ.get("SCRAPER_DEBUG"))

    def __post_init__(self):
        self.s.headers.update({
            "User-Agent": UA,
            "Accept-Language": "fr-CH,fr;q=0.9,de;q=0.6,en;q=0.5",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        })
        self._last = 0.0

    def get(self, url: str, tag: str = "", **kw) -> requests.Response:
        wait = self.delay - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        r = self.s.get(url, timeout=30, **kw)
        self._last = time.time()
        if self.debug and tag:
            DEBUG_DIR.mkdir(exist_ok=True)
            ext = "json" if "json" in r.headers.get("content-type", "") else "html"
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", tag)[:80]
            (DEBUG_DIR / f"{safe}.{ext}").write_text(r.text, encoding="utf-8")
            (DEBUG_DIR / f"{safe}.meta.txt").write_text(
                f"{r.status_code} {r.url}\n{dict(r.headers)}\n", encoding="utf-8")
        return r

    def post(self, url: str, tag: str = "", **kw) -> requests.Response:
        r = self.s.post(url, timeout=30, **kw)
        if self.debug and tag:
            DEBUG_DIR.mkdir(exist_ok=True)
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", tag)[:80]
            (DEBUG_DIR / f"{safe}.txt").write_text(f"{r.status_code} {r.url}\n{r.text}", encoding="utf-8")
        return r


# ---------------------------------------------------------------- texte

def norm(text: str) -> str:
    """minuscules, sans accents, espaces simples."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("œ", "oe").replace("Œ", "oe")
    return re.sub(r"\s+", " ", t.lower()).strip()


def parse_price(text) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"(\d+)(?:[.,'](\d{1,2}))?", str(text).replace("’", "'"))
    if not m:
        return None
    return float(f"{m.group(1)}.{m.group(2) or '0'}")


# ---------------------------------------------------------------- tailles

_NUM = r"(\d+(?:[.,]\d+)?)"
_UNITS = {
    "kg": ("kg", 1.0), "g": ("kg", 0.001), "gr": ("kg", 0.001),
    "l": ("L", 1.0), "lt": ("L", 1.0), "litre": ("L", 1.0), "litres": ("L", 1.0),
    "dl": ("L", 0.1), "cl": ("L", 0.01), "ml": ("L", 0.001),
}
_PIECE_WORDS = r"(?:pcs?|pi[eè]ces?|st(?:ü|u)ck|stk|x\s*oeufs?|oeufs?|œufs?|eier|rouleaux|rouleau|rollen|rolls?)"


def _f(x: str) -> float:
    return float(x.replace(",", "."))


def parse_size(text: str) -> tuple[float, str] | None:
    """Renvoie (quantité, unité) avec unité dans kg / L / pce.

    Gère '750 g', '1,5 l', '6 x 1.5 l', '4x125g', '10 pièces', '8 rouleaux', '0.5kg'.
    """
    t = norm(text).replace("×", "x")
    # multipack : 6 x 1.5 l / 4x125 g
    m = re.search(rf"(\d+)\s*x\s*{_NUM}\s*(kg|gr|g|l|lt|dl|cl|ml)\b", t)
    if m:
        n, q, u = int(m.group(1)), _f(m.group(2)), m.group(3)
        unit, mult = _UNITS[u]
        return n * q * mult, unit
    m = re.search(rf"{_NUM}\s*(kg|gr|g|litres?|lt|l|dl|cl|ml)\b", t)
    if m:
        q, u = _f(m.group(1)), m.group(2)
        unit, mult = _UNITS[u]
        return q * mult, unit
    m = re.search(rf"(\d+)\s*{_PIECE_WORDS}", t)
    if m:
        return float(m.group(1)), "pce"
    m = re.search(rf"{_PIECE_WORDS}\s*x?\s*(\d+)\b", t)
    if m:
        return float(m.group(1)), "pce"
    return None


# ---------------------------------------------------------------- appariement

def matches(item: dict, cand: Candidate) -> bool:
    name = norm(cand.name)
    rule = item.get("match", {})
    for w in rule.get("include", []):
        if norm(w) not in name:
            return False
    any_ = rule.get("any")
    if any_ and not any(norm(w) in name for w in any_):
        return False
    for w in rule.get("exclude", []):
        if norm(w) in name:
            return False
    return True


def finalize(item: dict, cand: Candidate) -> Candidate | None:
    """Calcule taille et prix unitaire ; None si le produit sort des bornes du besoin."""
    if cand.price is None or cand.price <= 0:
        return None
    if cand.size is None or cand.unit is None:
        ps = parse_size(cand.raw_size or "") or parse_size(cand.name)
        if ps:
            cand.size, cand.unit = ps
    # fruits/légumes/viande au kilo : le site affiche souvent "prix / kg" sans poids
    if cand.size is None and cand.unit_price is not None:
        cand.unit = item["unit"]
        cand.size = 1.0
        cand.price = cand.unit_price
    if cand.size is None or cand.unit != item["unit"]:
        return None
    lo, hi = item.get("size", {}).get("min", 0), item.get("size", {}).get("max", 1e9)
    if not cand.variable_weight and not (lo - 1e-9 <= cand.size <= hi + 1e-9):
        return None
    cand.unit_price = round(cand.price / cand.size, 4)
    return cand


def pick(item: dict, cands: list[Candidate]) -> Candidate | None:
    """Règle de sélection documentée dans METHODOLOGIE.md :
    - generic : le produit valide au prix unitaire le plus bas (hors promotion si possible)
    - brand   : le produit de marque exact ; s'il y a plusieurs offres, la moins chère hors promo
    """
    valid = []
    for c in cands:
        if not matches(item, c):
            continue
        c = finalize(item, c)
        if c:
            valid.append(c)
    if not valid:
        return None
    regular = [c for c in valid if not c.promo] or valid
    return min(regular, key=lambda c: c.unit_price)


def jsonld_products(html: str) -> list[dict]:
    """Extrait les blocs schema.org Product des balises JSON-LD."""
    out = []
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                t = d.get("@type")
                if t == "Product" or (isinstance(t, list) and "Product" in t):
                    out.append(d)
                for v in d.values():
                    if isinstance(v, (list, dict)):
                        stack.extend(v if isinstance(v, list) else [v])
            elif isinstance(d, list):
                stack.extend(d)
    return out
