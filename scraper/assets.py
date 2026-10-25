"""Prépare les ressources visuelles du site (à lancer à la main, résultat versionné) :

  site/img/*.webp     photos libres de Wikimedia Commons, redimensionnées
  site/img/credits.json  auteur, licence et lien de chaque photo (affichés sur le site)
  data/carte.json     contours simplifiés de la Suisse, de la France et du Léman (Natural Earth)

python -m scraper.assets
"""
from __future__ import annotations

import io
import json
import re
import sys

import requests
from PIL import Image

from .common import ROOT

UA = {"User-Agent": "panier-suisse-france (https://github.com/GregBrocard/Panier-suisse-france)"}
OUT = ROOT / "site" / "img"

PHOTOS = {
    "frontiere": "File:Douane-Moillesulaz-10.jpg",
    "jura": "File:Jougne douane.JPG",
    "leman": "File:St-Gingolph (France).jpg",
    "boucherie": "File:La vie chère à Paris (étal de boucherie) - btv1b53004739h.jpg",
    "marchande": "File:Marchande des quatre saisons. PH1033.jpg",
}
SEARCH = ["Agence Rol marché légumes", "marchande des quatre saisons", "Les Halles marché légumes 1910", "étal fruits marché Genève"]


def commons(title: str) -> dict:
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "query", "format": "json", "titles": title, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1800})
    p = next(iter(r.json()["query"]["pages"].values()))
    ii = p["imageinfo"][0]
    m = ii.get("extmetadata", {})
    clean = lambda k: re.sub(r"\s+", " ", re.sub("<[^>]+>", "", m.get(k, {}).get("value", ""))).strip()
    return {"thumb": ii.get("thumburl") or ii["url"], "page": ii["descriptionurl"], "auteur": clean("Artist")[:80],
            "licence": clean("LicenseShortName"), "description": clean("ImageDescription")[:160]}


def photos():
    OUT.mkdir(parents=True, exist_ok=True)
    credits = {}
    for key, title in PHOTOS.items():
        info = commons(title)
        img = Image.open(io.BytesIO(requests.get(info["thumb"], headers=UA, timeout=120).content)).convert("RGB")
        img.thumbnail((1800, 1800))
        img.save(OUT / f"{key}.webp", "WEBP", quality=78, method=6)
        credits[key] = {**{k: info[k] for k in ("page", "auteur", "licence", "description")}, "titre": title}
        print(key, img.size, info["licence"], info["auteur"])
    (OUT / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")


def search():
    for q in SEARCH:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=60, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}",
            "gsrnamespace": 6, "gsrlimit": 8, "prop": "imageinfo", "iiprop": "size|extmetadata"})
        print("==", q)
        for p in (r.json().get("query") or {}).get("pages", {}).values():
            ii = p["imageinfo"][0]
            lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
            print(f"   {p['title'][:90]} | {ii['width']}x{ii['height']} | {lic}")


# ------------------------------------------------------------------ carte

BBOX = (5.6, 45.75, 8.2, 47.85)  # lon min, lat min, lon max, lat max


def _rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** .5 or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / n
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return _rdp(pts[:idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def _rings(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        yield poly[0]


def carte():
    base = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    countries = requests.get(base + "ne_10m_admin_0_countries.geojson", timeout=300).json()
    lakes = requests.get(base + "ne_10m_lakes.geojson", timeout=300).json()
    out = {"bbox": BBOX, "pays": {}, "lacs": [], "source": "Natural Earth (domaine public)"}
    for f in countries["features"]:
        pr = f["properties"]
        iso = pr.get("ADM0_A3") or pr.get("adm0_a3") or pr.get("ISO_A3") or pr.get("iso_a3")
        if iso not in ("CHE", "FRA", "DEU", "ITA", "LIE", "AUT"):
            continue
        rings = []
        for ring in _rings(f["geometry"]):
            if not any(BBOX[0] - 1 <= x <= BBOX[2] + 1 and BBOX[1] - 1 <= y <= BBOX[3] + 1 for x, y in ring):
                continue
            simp = _rdp([[round(x, 4), round(y, 4)] for x, y in ring], 0.004)
            if len(simp) > 3:
                rings.append(simp)
        if rings:
            out["pays"][iso] = rings
    for f in lakes["features"]:
        for ring in _rings(f["geometry"]):
            if all(BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3] for x, y in ring) and len(ring) > 20:
                xs = [p[0] for p in ring]
                if max(xs) - min(xs) > 0.12:
                    out["lacs"].append(_rdp([[round(x, 4), round(y, 4)] for x, y in ring], 0.003))
    (ROOT / "data" / "carte.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("propriétés exemple :", list(countries["features"][0]["properties"])[:15])
    print("carte :", {k: sum(len(r) for r in v) for k, v in out["pays"].items()}, "lacs", len(out["lacs"]))


if __name__ == "__main__":
    what = sys.argv[1:] or ["search", "photos", "carte"]
    if "search" in what:
        search()
    if "photos" in what:
        photos()
    if "carte" in what:
        carte()
