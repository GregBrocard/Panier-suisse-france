"""Connecteurs vers les sources officielles et ouvertes.

Toutes renvoient des séries mensuelles sous la forme {"AAAA-MM": valeur}.
"""
from __future__ import annotations

import csv
import io
import re
import statistics
import datetime as dt
from collections import defaultdict

import requests

UA = {"User-Agent": "panier-suisse-france (https://github.com/GregBrocard/Panier-suisse-france)"}


def _get(url, tries: int = 5, **kw):
    """GET avec reprises : certains serveurs publics (INSEE) coupent les connexions en rafale."""
    import time
    headers = {**UA, **kw.pop("headers", {})}
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=90, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code}", response=r)
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            if i == tries - 1:
                raise
            time.sleep(4 * (i + 1))


# ------------------------------------------------------------------ BCE

def ecb_eur_chf_monthly() -> dict[str, float]:
    """Moyenne mensuelle du taux de référence BCE (CHF pour 1 EUR), depuis 1999."""
    r = _get("https://data-api.ecb.europa.eu/service/data/EXR/M.CHF.EUR.SP00.A?format=csvdata")
    out = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        out[row["TIME_PERIOD"]] = round(float(row["OBS_VALUE"]), 5)
    return out


def ecb_eur_chf_daily_last() -> dict:
    r = _get("https://data-api.ecb.europa.eu/service/data/EXR/D.CHF.EUR.SP00.A?format=csvdata&lastNObservations=1")
    row = next(csv.DictReader(io.StringIO(r.text)))
    return {"date": row["TIME_PERIOD"], "eur_chf": float(row["OBS_VALUE"])}


# ------------------------------------------------------------------ INSEE

def insee_series(idbank: str) -> tuple[str, dict[str, float]]:
    """Série BDM INSEE complète. Renvoie (titre, {mois: valeur})."""
    import time
    time.sleep(1.5)  # politesse envers l'API INSEE
    r = _get(f"https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/{idbank}")
    title = re.search(r'TITLE_FR="([^"]+)"', r.text)
    obs = re.findall(r'TIME_PERIOD="(\d{4}-\d{2})" OBS_VALUE="([\d.]+)"', r.text)
    return (title.group(1) if title else idbank), {m: float(v) for m, v in obs}


# ------------------------------------------------------------------ OFAG (LINDAS)

LINDAS = ["https://lindas.admin.ch/query", "https://lindas.cz-aws.net/query"]
GRAPH = "https://lindas.admin.ch/foag/agricultural-market-data"
D = "https://agriculture.ld.admin.ch/foag/dimension/"


def _sparql(query: str) -> list[dict]:
    last = None
    for ep in LINDAS:
        try:
            r = requests.post(ep, data={"query": query}, timeout=120,
                              headers={**UA, "Accept": "application/sparql-results+json"})
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"LINDAS indisponible : {last}")


def ofag_series(cube: str, product: str) -> dict[str, float]:
    """Prix de consommation mensuels OFAG pour un produit (région de vente : Suisse).

    Certains produits ont plusieurs séries le même mois (segments de prix) :
    on retient la moyenne des séries publiées.
    """
    rows = _sparql(f"""PREFIX schema: <http://schema.org/>
SELECT ?d ?price WHERE {{ GRAPH <{GRAPH}> {{
  <https://agriculture.ld.admin.ch/foag/cube/{cube}/Consumption_Price_Month> <https://cube.link/observationSet> ?set .
  ?set <https://cube.link/observation> ?obs .
  ?obs <{D}product> ?p ; <{D}date> ?d ; <https://agriculture.ld.admin.ch/foag/measure/price> ?price ;
       <{D}sales-region> ?sr ; <{D}key-indicator-type> ?k . }}
  ?p schema:name "{product}"@fr .
  ?k schema:name "Prix"@fr .
  ?sr schema:name "Suisse"@fr .
}}""")
    acc = defaultdict(list)
    for b in rows:
        m = b["d"]["value"].rsplit("/", 1)[-1]
        acc[m].append(float(b["price"]["value"]))
    return {m: round(statistics.mean(v), 4) for m, v in sorted(acc.items())}


# ------------------------------------------------------------------ Carburant France (stations)

def fuel_fr_near(lat: float, lon: float, km: float) -> dict:
    """Stations à moins de `km` du point donné."""
    return fuel_fr_stations(None, where=f"within_distance(geom, geom'POINT({lon} {lat})', {km}km)")


def fuel_fr_stations(postcodes: list[str] | None, where: str | None = None) -> dict:
    """Prix instantanés des stations des codes postaux donnés (flux officiel prix-carburants)."""
    where = where or " or ".join(f'cp="{p}"' for p in postcodes)
    r = _get("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
             "prix-des-carburants-en-france-flux-instantane-v2/records",
             params={"where": where, "limit": 100})
    stations = []
    for s in r.json().get("results", []):
        stations.append({
            "id": s.get("id"), "ville": s.get("ville"), "adresse": s.get("adresse"),
            "sp95": _f(s.get("sp95_prix")), "e10": _f(s.get("e10_prix")),
            "sp98": _f(s.get("sp98_prix")), "diesel": _f(s.get("gazole_prix")),
            "maj": max([x for x in [s.get("gazole_maj"), s.get("e10_maj"), s.get("sp95_maj")] if x] or [None]),
        })

    def avg(k):
        v = [s[k] for s in stations if s[k]]
        return round(statistics.mean(v), 3) if v else None

    def mn(k):
        v = [s[k] for s in stations if s[k]]
        return round(min(v), 3) if v else None

    # SP95 pur a quasi disparu : on prend SP95 ou, à défaut, E10 (même usage)
    for s in stations:
        s["sp95_ou_e10"] = s["sp95"] or s["e10"]
    return {"stations": stations, "n": len(stations),
            "moyenne": {"sp95": avg("sp95_ou_e10"), "diesel": avg("diesel")},
            "min": {"sp95": mn("sp95_ou_e10"), "diesel": mn("diesel")}}


def _f(x):
    try:
        return float(x) if x not in (None, "", "None") else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ Carburant Suisse (OFDF)

OFDF_T44 = "https://www.bazg.admin.ch/dam/fr/sd-web/GEosTpUlCewh/Monatstabelle%20T%204.4f.02.pdf"


def fuel_ch_ofdf() -> dict:
    """Tableau OFDF T 4.4 : prix à la colonne en zone frontière genevoise (ct./l)."""
    from pypdf import PdfReader
    r = _get(OFDF_T44)
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    date = re.search(r"[ÉE]tat\s*:\s*([^\n]+)", text)
    out = {"source": OFDF_T44, "date_texte": date.group(1) if date else None, "raw": text[:3000]}
    # lignes "Genève (France) 219,00 220,00 ..." ; la 1re occurrence = diesel, la 2e = essence 95
    lines = [l for l in text.splitlines() if re.search(r"Gen[eè]ve", l)]
    nums = [re.findall(r"\d{3}[.,]\d{2}", l) for l in lines]
    nums = [n for n in nums if len(n) >= 2]
    if len(nums) >= 2:
        out["diesel"] = {"ch_chf": float(nums[0][0].replace(",", ".")) / 100,
                         "fr_eur": float(nums[0][1].replace(",", ".")) / 100}
        out["sp95"] = {"ch_chf": float(nums[1][0].replace(",", ".")) / 100,
                       "fr_eur": float(nums[1][1].replace(",", ".")) / 100}
    return out


# ------------------------------------------------------------------ Open Prices (France)

def openprices_fr(eans: list[str], days: int = 365) -> dict | None:
    """Médiane des prix relevés en France pour ces codes-barres sur les `days` derniers jours."""
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    prices, products = [], set()
    for ean in eans:
        r = _get("https://prices.openfoodfacts.org/api/v1/prices",
                 params={"product_code": ean, "currency": "EUR", "date__gte": since, "size": 100,
                         "order_by": "-date"})
        for it in r.json().get("items", []):
            loc = it.get("location") or {}
            country = (loc.get("osm_address_country") or "").lower()
            if country and country not in ("france", "fr"):
                continue
            if it.get("price_is_discounted"):
                continue
            prices.append(float(it["price"]))
            p = it.get("product") or {}
            if p.get("product_name"):
                products.add(f'{p.get("product_name")} {p.get("product_quantity") or ""}{p.get("product_quantity_unit") or ""}')
    if not prices:
        return None
    return {"median": round(statistics.median(prices), 3), "n": len(prices),
            "min": min(prices), "max": max(prices), "products": sorted(products)[:3], "since": since}
