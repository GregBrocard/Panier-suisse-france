"""Recherche de photos libres (Wikimedia Commons) pour le site."""
import re

import requests

UA = {"User-Agent": "panier-suisse-france (https://github.com/GregBrocard/Panier-suisse-france)"}
Q = ["Moillesulaz douane", "Bardonnex border crossing", "Vallorbe border", "Col de la Givrine La Cure",
     "Lac Léman vignes Lavaux", "Annemasse marché", "marché fruits légumes Haute-Savoie", "étal boucherie France",
     "caddie supermarché", "Thônex Vallard douane", "Saint-Gingolph frontière", "Jura vaudois hiver"]
for q in Q:
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}",
        "gsrnamespace": 6, "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1600})
    pages = (r.json().get("query") or {}).get("pages", {})
    print(f"== {q}")
    for p in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        ii = p["imageinfo"][0]
        m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "")
        art = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", ""))[:40]
        desc = re.sub("<[^>]+>", "", m.get("ImageDescription", {}).get("value", ""))[:80]
        print(f"   {p['title'][:70]} | {ii['width']}x{ii['height']} | {lic} | {art} | {desc}")
        print(f"      {ii.get('thumburl')}")
