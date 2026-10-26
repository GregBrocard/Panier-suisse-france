"""Sonde ponctuelle : données pour le volet « acheter suisse » (OFAG LINDAS, OpenStreetMap)."""
from __future__ import annotations

import json
from collections import Counter

from scraper.lindas_explore import GRAPH, catalog, q, show
from scraper.stations import _overpass

print("== tous les cubes OFAG")
cubes = [b["cube"]["value"] for b in q(f"""SELECT DISTINCT ?cube WHERE {{ GRAPH <{GRAPH}> {{ ?cube a <https://cube.link/Cube> }} }}""")]
for c in sorted(cubes):
    print("   ", c)

for c in sorted(cubes):
    if "Producer" in c or "Production_Price" in c or "Meat" in c:
        try:
            catalog(c)
        except Exception as e:  # noqa: BLE001
            print("ERR", c, e)
            try:
                show(q(f"""SELECT ?p ?o WHERE {{ GRAPH <{GRAPH}> {{
                    <{c}> <https://cube.link/observationSet> ?set . ?set <https://cube.link/observation> ?obs .
                    ?obs ?p ?o }} }} LIMIT 30"""))
            except Exception as e2:  # noqa: BLE001
                print("ERR2", e2)

print("== OpenStreetMap, Suisse")
TAGS = {
    "ferme": 'nwr["shop"="farm"]',
    "boucherie": 'nwr["shop"="butcher"]',
    "distributeur_lait": 'nwr["amenity"="vending_machine"]["vending"~"milk"]',
    "distributeur_oeufs": 'nwr["amenity"="vending_machine"]["vending"~"eggs"]',
    "distributeur_autre_ferme": 'nwr["amenity"="vending_machine"]["vending"~"food|meat|cheese|potatoes|vegetables"]',
    "marche": 'nwr["amenity"="marketplace"]',
    "cave": 'nwr["craft"="winery"]',
    "vin_shop": 'nwr["shop"="wine"]',
    "fromagerie": 'nwr["shop"="cheese"]',
}
out = {}
for k, sel in TAGS.items():
    try:
        r = _overpass(f'[out:json][timeout:240];area["ISO3166-1"="CH"][admin_level=2]->.a;({sel}(area.a););out center tags;')
        els = r.get("elements", [])
        romandie = [e for e in els if 45.8 < (e.get("lat") or e.get("center", {}).get("lat", 0)) < 47.5
                    and 5.9 < (e.get("lon") or e.get("center", {}).get("lon", 0)) < 7.4]
        names = sum(1 for e in els if e.get("tags", {}).get("name"))
        hours = sum(1 for e in els if e.get("tags", {}).get("opening_hours"))
        prod = Counter(p.strip() for e in els for p in e.get("tags", {}).get("produce", "").split(";") if p.strip())
        out[k] = {"suisse": len(els), "ouest_approx": len(romandie), "avec_nom": names, "avec_horaires": hours,
                  "produits": prod.most_common(12)}
        print(k, out[k])
    except Exception as e:  # noqa: BLE001
        print("ERR", k, e)
json.dump(out, open("debug/osm_suisse.json", "w"), ensure_ascii=False, indent=1)
