"""Comparateur des supermarchés de l'UFC-Que Choisir : prix d'un panier de ~100 produits, magasin par magasin.

Utilisation dans ce projet (voir METHODOLOGIE.md, § 3.5) :
  - pour chaque zone frontalière, tous les magasins situés à moins de 15 km d'un magasin « graine » ;
  - un panel national de magasins tirés au hasard sert de référence (médiane) ;
  - indice d'un magasin = panier global du magasin / médiane du panel national.

Données propriété de l'UFC-Que Choisir : usage privé de test, publication soumise à leur accord.
"""
from __future__ import annotations

import random
import re
import statistics
import time

import requests

BASE = "https://www.quechoisir.org/carte-interactive-drives-n21243/drive-magasin-dm{}/"
UA = {"User-Agent": "panier-suisse-france (projet de recherche HES-SO ; contact via GitHub GregBrocard)"}
DELAY = 2.0


def _get(url: str) -> str | None:
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=60, allow_redirects=True)
            time.sleep(DELAY)
            if r.status_code == 200 and "drive-magasin-dm" in r.url:
                return r.text
            return None  # magasin inexistant -> redirection vers la carte
        except requests.RequestException:
            time.sleep(5 * (i + 1))
    return None


def _num(s: str) -> float:
    return float(s.replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", "."))


def store(dm: int) -> dict | None:
    html = _get(BASE.format(dm))
    if not html:
        return None
    title = re.search(r"<title>\s*(.*?)\s*(?:-\s*Que Choisir.*?|Comparateur des supermarch.s)?\s*</title>", html, re.S)
    name = re.sub(r"\s+", " ", title.group(1)).strip() if title else f"dm{dm}"
    cp = re.search(r"\((\d{5})\)", name)
    baskets = {}
    for label, val in re.findall(r"<td>\s*(Global|Famille|Couple|C.libataire)\s*</td>\s*<td>\s*([\d\s \xa0.,]+?)\s*(?:\xa0|&nbsp;)?€", html):
        key = {"Global": "global", "Famille": "famille", "Couple": "couple"}.get(label, "celibataire")
        baskets[key] = _num(val)
    rating = None
    i = html.find("<td>Global</td>")
    if i > 0:
        m = re.search(r'aria-label="Appréciation : ([^"]+)"', html[i:i + 3000])
        rating = m.group(1) if m else None
    neighbors = []
    for href, ens, addr in re.findall(
            r'<a class="qc-compare-map-drive_drive-card[^"]*"[^>]*?(?:href="/carte-interactive-drives-n21243/drive-magasin-dm(\d+)/")?\s*>'
            r'.*?drive-enseigne[^>]*>([^<]+)</span>.*?<address>(.*?)</address>', html, re.S):
        if href:
            neighbors.append({"dm": int(href), "enseigne": ens.strip(),
                              "adresse": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", addr)).strip()})
    if "global" not in baskets:
        return None
    return {"dm": dm, "nom": name.split(" (")[0], "cp": cp.group(1) if cp else None,
            "url": BASE.format(dm), "paniers": baskets, "appreciation": rating, "voisins": neighbors}


def zone_stores(seeds: list[int], postcodes_prefix: list[str] | None = None) -> list[dict]:
    """Magasins graines + leurs voisins (rayon 15 km publié par Que Choisir)."""
    seen, out = set(), []
    queue = list(seeds)
    voisins = []
    for dm in queue:
        if dm in seen:
            continue
        seen.add(dm)
        s = store(dm)
        if s:
            out.append(s)
            voisins += [v["dm"] for v in s["voisins"]]
    for dm in voisins:
        if dm in seen:
            continue
        seen.add(dm)
        s = store(dm)
        if s and (not postcodes_prefix or (s["cp"] or "")[:2] in postcodes_prefix):
            out.append(s)
    return out


def national_panel(n: int = 600, seed: int = 2026, max_id: int = 22000, cache=None) -> dict:
    """Médiane du panier global sur un échantillon fixe de magasins tirés au hasard (même tirage chaque mois).

    Beaucoup d'identifiants tirés ne correspondent à aucun magasin : au premier passage, on garde la liste
    des identifiants valides dans le fichier `cache` (JSON) et les mois suivants on ne relit que ceux-là.
    """
    import json
    ids = None
    if cache is not None and cache.exists():
        meta = json.loads(cache.read_text())
        if meta.get("seed") == seed and meta.get("n") == n:
            ids = meta["valides"]
    fresh = ids is None
    if fresh:
        ids = random.Random(seed).sample(range(1, max_id), n)
    vals, valid = [], []
    for dm in ids:
        s = store(dm)
        if s:
            vals.append(s["paniers"]["global"])
            valid.append(dm)
    if cache is not None and (fresh or len(valid) < len(ids)):
        cache.write_text(json.dumps({"seed": seed, "n": n, "valides": valid}))
    return {"n": len(vals), "tires": n, "mediane": round(statistics.median(vals), 2) if vals else None,
            "moyenne": round(statistics.mean(vals), 2) if vals else None,
            "p10": round(sorted(vals)[len(vals) // 10], 2) if vals else None,
            "p90": round(sorted(vals)[len(vals) * 9 // 10], 2) if vals else None}
