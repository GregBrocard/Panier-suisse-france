"""Exploration : densité Open Prices près de la frontière, robots.txt Que Choisir, magasins Auchan."""
import math

import requests

H = {"User-Agent": "panier-suisse-france (recherche)"}
SPOTS = {"Annemasse": (46.193, 6.236), "Divonne/Gex": (46.36, 6.12), "Les Rousses": (46.485, 6.063),
         "Jougne/Pontarlier": (46.85, 6.37)}


def dist(a, b):
    return 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(b[0] - a[0]) / 2) ** 2 + math.cos(math.radians(a[0]))
                                          * math.cos(math.radians(b[0])) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2))


print("== Open Prices : lieux à moins de 20 km")
locs = []
for page in range(1, 60):
    r = requests.get("https://prices.openfoodfacts.org/api/v1/locations",
                     params={"osm_address_country": "France", "size": 100, "page": page, "order_by": "-price_count"},
                     headers=H, timeout=60)
    items = r.json().get("items", [])
    if not items:
        break
    locs += items
    if items[-1].get("price_count", 0) < 3:
        break
print("lieux FR parcourus:", len(locs))
for name, c in SPOTS.items():
    near = [l for l in locs if l.get("osm_lat") and dist(c, (float(l["osm_lat"]), float(l["osm_lon"]))) < 20]
    print(f"-- {name}: {len(near)} lieux")
    for l in sorted(near, key=lambda x: -x.get("price_count", 0))[:10]:
        print(f"   {l.get('osm_name')} | {l.get('osm_address_city')} | prix={l.get('price_count')} | id={l.get('id')}")

print("== robots.txt Que Choisir")
r = requests.get("https://www.quechoisir.org/robots.txt", headers=H, timeout=30)
print(r.status_code)
print("\n".join(l for l in r.text.splitlines() if "drive" in l.lower() or l.lower().startswith("user-agent") or "disallow: /" == l.lower().strip())[:1500])

print("== Auchan magasins")
for u in ["https://www.auchan.fr/nos-magasins?types=HYPER,SUPER,PROXI",
          "https://www.auchan.fr/magasins/haute-savoie",
          "https://www.auchan.fr/store-locator/api/stores?lat=46.19&lng=6.23&radius=40"]:
    try:
        r = requests.get(u, headers={**H, "User-Agent": "Mozilla/5.0"}, timeout=30)
        import re
        print(u, r.status_code, len(r.text), sorted(set(re.findall(r"(?i)auchan[^<\"]{0,40}(?:annemasse|thonon|gex|pontarlier|saint-genis|thoiry|cluses|bonneville|annecy|morez|jura)", r.text)))[:15])
    except Exception as e:  # noqa: BLE001
        print(u, "ERR", e)
