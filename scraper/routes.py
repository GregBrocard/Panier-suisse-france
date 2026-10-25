"""Distances routières entre les localités suisses et les villes françaises de destination.

OSRM (calcul d'itinéraire sur OpenStreetMap), en matrices de 80 départs × toutes les destinations.
Cache : data/distances.json ({"Nom|Canton": {destination: [km, minutes]}}) ; seules les paires manquantes
sont recalculées.
"""
from __future__ import annotations

import json
import time

import requests

UA = {"User-Agent": "panier-suisse-france (projet de recherche ; https://github.com/GregBrocard/Panier-suisse-france)"}
CHUNK = 80


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def geocode(queries: list[str]) -> list[float] | None:
    """Nominatim (OpenStreetMap), 1 requête par seconde ; essaie les requêtes dans l'ordre."""
    for q in [x for x in queries if x]:
        try:
            r = requests.get("https://nominatim.openstreetmap.org/search", headers=UA, timeout=30,
                             params={"q": q, "format": "json", "limit": 1, "countrycodes": "fr"})
            time.sleep(1.1)
            js = r.json()
            if js:
                return [round(float(js[0]["lat"]), 5), round(float(js[0]["lon"]), 5)]
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return None


def matrix(origins: list[dict], dests: list[dict], cache_path, log=print) -> dict:
    cache = _load(cache_path)
    dids = [d["id"] for d in dests]
    todo = [o for o in origins if any(d not in cache.get(f"{o['nom']}|{o['canton']}", {}) for d in dids)]
    log(f"   trajets : {len(todo)} localités à calculer sur {len(origins)}")
    for i in range(0, len(todo), CHUNK):
        part = todo[i:i + CHUNK]
        pts = [f"{o['lon']},{o['lat']}" for o in part] + [f"{d['lon']},{d['lat']}" for d in dests]
        url = "https://router.project-osrm.org/table/v1/driving/" + ";".join(pts)
        params = {"sources": ";".join(str(k) for k in range(len(part))),
                  "destinations": ";".join(str(len(part) + k) for k in range(len(dests))),
                  "annotations": "distance,duration"}
        for attempt in range(4):
            try:
                js = requests.get(url, params=params, headers=UA, timeout=120).json()
                if js.get("code") == "Ok":
                    for a, o in enumerate(part):
                        row = cache.setdefault(f"{o['nom']}|{o['canton']}", {})
                        for b, did in enumerate(dids):
                            dist, dur = js["distances"][a][b], js["durations"][a][b]
                            if dist is not None:
                                row[did] = [round(dist / 1000), round(dur / 60)]
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5 * (attempt + 1))
        time.sleep(1.0)
        if i % (CHUNK * 10) == 0:
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return cache
