"""Distances routières entre les localités de départ (Suisse) et les magasins français.

1. Géocodage de l'adresse de chaque magasin (Nominatim / OpenStreetMap, 1 requête par seconde),
   gardé en cache dans data/geo_magasins.json.
2. Distance et durée routières (OSRM, service de calcul d'itinéraire sur OpenStreetMap),
   gardées en cache dans data/distances.json. Seules les paires manquantes sont recalculées.
"""
from __future__ import annotations

import json
import time

import requests

UA = {"User-Agent": "panier-suisse-france (projet de recherche ; https://github.com/GregBrocard/Panier-suisse-france)"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def geocode_stores(stores: list[dict], cache_path) -> dict:
    """{dm: [lat, lon]} pour chaque magasin (adresse Que Choisir)."""
    cache = _load(cache_path)
    for s in stores:
        key = str(s["dm"])
        if key in cache:
            continue
        queries = [s.get("adresse"), f"{s['nom']} {s.get('cp') or ''}", f"{s.get('cp') or ''} France"]
        for q in [x for x in queries if x]:
            try:
                r = requests.get("https://nominatim.openstreetmap.org/search", headers=UA, timeout=30,
                                 params={"q": q, "format": "json", "limit": 1, "countrycodes": "fr"})
                time.sleep(1.1)
                js = r.json()
                if js:
                    cache[key] = [round(float(js[0]["lat"]), 5), round(float(js[0]["lon"]), 5)]
                    break
            except Exception:  # noqa: BLE001
                time.sleep(2)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    return cache


def road_matrix(origins: list[list], coords: dict, cache_path) -> dict:
    """{origine: {dm: [km aller, minutes]}} via OSRM ; ne recalcule que les paires absentes du cache."""
    cache = _load(cache_path)
    dms = sorted(coords)
    for name, lat, lon in origins:
        have = cache.get(name, {})
        missing = [d for d in dms if d not in have]
        if not missing:
            continue
        pts = [f"{lon},{lat}"] + [f"{coords[d][1]},{coords[d][0]}" for d in missing]
        url = "https://router.project-osrm.org/table/v1/driving/" + ";".join(pts)
        for i in range(3):
            try:
                r = requests.get(url, headers=UA, timeout=60,
                                 params={"sources": "0", "annotations": "distance,duration"})
                js = r.json()
                if js.get("code") == "Ok":
                    for j, d in enumerate(missing, start=1):
                        dist, dur = js["distances"][0][j], js["durations"][0][j]
                        if dist is not None:
                            have[d] = [round(dist / 1000, 1), round(dur / 60)]
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(3 * (i + 1))
        cache[name] = have
        time.sleep(1.0)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return cache
