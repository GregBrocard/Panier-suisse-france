"""Où acheter suisse en direct : magasins à la ferme, distributeurs de lait et d'œufs, boucheries, fromageries,
marchés et caves en Suisse, d'après OpenStreetMap (© contributeurs OpenStreetMap, licence ODbL), via Overpass.

Relevé mensuel (appelé par scraper/essence.py quand le fichier a plus de 30 jours) -> data/fermes_osm.json

python -m scraper.fermes
"""
from __future__ import annotations

import datetime as dt
import json
import time

from .common import ROOT
from .stations import _overpass

DATA = ROOT / "data"

# type -> (libellé, sélecteur Overpass)
TYPES = {
    "ferme": ("Magasin à la ferme", 'nwr["shop"="farm"]'),
    "distributeur": ("Distributeur de produits de la ferme",
                     'nwr["amenity"="vending_machine"]["vending"~"milk|eggs|cheese|meat|potatoes|vegetables|fruit|food"]'),
    "boucherie": ("Boucherie", 'nwr["shop"="butcher"]'),
    "fromagerie": ("Fromagerie", 'nwr["shop"="cheese"]'),
    "marche": ("Marché", 'nwr["amenity"="marketplace"]'),
    "cave": ("Cave, vigneron", 'nwr["craft"="winery"]'),
}
PRODUITS = {"milk": "lait", "eggs": "œufs", "cheese": "fromage", "meat": "viande", "potatoes": "pommes de terre",
            "vegetables": "légumes", "fruit": "fruits", "fruits": "fruits", "honey": "miel", "bread": "pain",
            "wine": "vin", "apples": "pommes", "flowers": "fleurs", "sausages": "saucisses", "butter": "beurre",
            "yoghurt": "yogourt", "juice": "jus", "jam": "confiture"}


def _produits(t: dict) -> str:
    vals = []
    for k in ("produce", "vending", "product"):
        vals += [v.strip().lower() for v in (t.get(k) or "").split(";") if v.strip()]
    out = []
    for v in vals:
        fr = PRODUITS.get(v)
        if fr and fr not in out:
            out.append(fr)
    return ", ".join(out[:6])


def fermes() -> list[list]:
    """[type, lat, lon, nom, localité, produits, horaires, site web, id OSM]"""
    out, vus = [], set()
    for typ, (_, sel) in TYPES.items():
        j = _overpass(f'[out:json][timeout:240];area["ISO3166-1"="CH"][admin_level=2]->.a;({sel}(area.a););out center tags;')
        for el in j.get("elements", []):
            t = el.get("tags", {})
            if t.get("access") in ("private", "no") or t.get("disused") == "yes":
                continue
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            oid = f"{el['type'][0]}{el['id']}"
            if lat is None or oid in vus:
                continue
            vus.add(oid)
            web = t.get("website") or t.get("contact:website") or ""
            out.append([typ, round(lat, 5), round(lon, 5), t.get("name") or "", t.get("addr:city") or t.get("addr:place") or "",
                        _produits(t), t.get("opening_hours") or "", web if web.startswith("http") else "", oid])
        time.sleep(3)
    return out


def main():
    pts = fermes()
    par_type = {k: sum(1 for p in pts if p[0] == k) for k in TYPES}
    (DATA / "fermes_osm.json").write_text(json.dumps({
        "source": "© contributeurs OpenStreetMap (ODbL), via Overpass", "genere_le": dt.date.today().isoformat(),
        "types": {k: v[0] for k, v in TYPES.items()}, "par_type": par_type, "points": pts},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"points de vente directe OpenStreetMap : {len(pts)} ({par_type})")


if __name__ == "__main__":
    main()
