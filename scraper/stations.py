"""Stations-service pour le mode « Où faire le plein ».

- Suisse et France frontalière : liste des stations d'OpenStreetMap (nom, marque, position), via l'API Overpass.
  Relevé mensuel, résultat dans data/stations_osm.json (© contributeurs OpenStreetMap, licence ODbL).
- France : prix officiels du jour, station par station (flux du ministère de l'Économie), dans une bande
  frontalière ; appelé par scraper/essence.py chaque jour.

python -m scraper.stations      -> data/stations_osm.json
"""
from __future__ import annotations

import json
import time

import requests

from .common import ROOT

DATA = ROOT / "data"
UA = {"User-Agent": "panier-suisse-france/2.0 (https://github.com/GregBrocard/Panier-suisse-france)"}
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
# Bande française couverte : départements frontaliers de la Suisse (et un peu au-delà)
BBOX_FR = (45.75, 5.55, 47.95, 7.65)  # lat min, lon min, lat max, lon max


def _overpass(q: str) -> dict:
    last = None
    for url in OVERPASS:
        for _ in range(2):
            try:
                r = requests.post(url, data={"data": q}, headers=UA, timeout=300)
                r.raise_for_status()
                return r.json()
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(10)
    raise RuntimeError(last)


def _parse(j, pays):
    out = []
    for el in j.get("elements", []):
        t = el.get("tags", {})
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        nom = t.get("name") or t.get("brand") or t.get("operator") or ""
        out.append([f"{el['type'][0]}{el['id']}", round(lat, 5), round(lon, 5), nom, t.get("brand") or "",
                    t.get("addr:city") or "", pays])
    return out


def osm_stations() -> list[list]:
    """[id, lat, lon, nom, marque, localité, pays] : toutes les stations de Suisse, et celles de la bande française."""
    s, w, n, e = BBOX_FR
    ch = _overpass("""[out:json][timeout:240];
area["ISO3166-1"="CH"][admin_level=2]->.ch;
nwr["amenity"="fuel"](area.ch);
out center tags;""")
    time.sleep(5)
    fr = _overpass(f"""[out:json][timeout:240];
area["ISO3166-1"="FR"][admin_level=2]->.fr;
nwr["amenity"="fuel"]({s},{w},{n},{e})(area.fr);
out center tags;""")
    return _parse(ch, "CH") + _parse(fr, "FR")


def fr_stations_bande() -> list[dict]:
    """Prix du jour de toutes les stations françaises de la bande frontalière (flux officiel)."""
    s, w, n, e = BBOX_FR
    url = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
           "prix-des-carburants-en-france-flux-instantane-v2/exports/json")
    where = f"in_bbox(geom, {s}, {w}, {n}, {e})"
    r = requests.get(url, params={"where": where}, headers=UA, timeout=180)
    r.raise_for_status()
    out = []
    for x in r.json():
        g = x.get("geom") or {}
        lat, lon = g.get("lat"), g.get("lon")
        if lat is None:
            continue

        def f(k):
            try:
                return float(x.get(k)) if x.get(k) not in (None, "") else None
            except (TypeError, ValueError):
                return None
        maj = {k: x.get(f"{k}_maj") for k in ("sp95", "e10", "gazole")}
        out.append({"id": str(x.get("id")), "lat": round(lat, 5), "lon": round(lon, 5),
                    "adresse": x.get("adresse"), "ville": x.get("ville"),
                    "sp95": f("sp95_prix") or f("e10_prix"), "sp95_maj": maj["sp95"] or maj["e10"],
                    "diesel": f("gazole_prix"), "diesel_maj": maj["gazole"]})
    return out


def main():
    st = osm_stations()
    ch = sum(1 for x in st if x[6] == "CH")
    (DATA / "stations_osm.json").write_text(json.dumps({"source": "© contributeurs OpenStreetMap (ODbL), via Overpass",
                                                          "genere_le": __import__("datetime").date.today().isoformat(),
                                                          "stations": st}, ensure_ascii=False, separators=(",", ":")),
                                             encoding="utf-8")
    print(f"stations OpenStreetMap : {len(st)}, dont {ch} en Suisse")


if __name__ == "__main__":
    main()
