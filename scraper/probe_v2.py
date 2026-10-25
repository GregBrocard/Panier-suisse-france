"""Sonde v2 : catalogues OFAG (crèmerie, œufs, pain, huiles), séries INSEE de prix moyens, marques candidates."""
import json
import re
import sys
import requests

from .common import Session
from .migros import Migros
from . import lindas_explore as LX

UA = {"User-Agent": "panier-suisse-france (https://github.com/GregBrocard/Panier-suisse-france)"}
what = sys.argv[1:] or ["ofag", "insee", "marques"]

if "ofag" in what:
    for c in ["MilkDairyProducts", "Eggs", "BreadCerealsFlourBakedGoods", "Oilseeds", "Meat"]:
        try:
            LX.catalog(f"https://agriculture.ld.admin.ch/foag/cube/{c}/Consumption_Price_Month")
        except Exception as e:  # noqa: BLE001
            print("ERR", c, e)

if "insee" in what:
    r = requests.get("https://bdm.insee.fr/series/sdmx/dataflow", headers=UA, timeout=120)
    flows = re.findall(r'<str:Dataflow[^>]*id="([^"]+)"[^>]*>.*?<com:Name xml:lang="fr">([^<]+)</com:Name>', r.text, re.S)
    print("== dataflows", len(flows))
    for fid, name in flows:
        if re.search(r"prix|PRIX|carbur", name):
            print("  ", fid, "|", name)
    for fid, name in flows:
        if re.search(r"moyen", name, re.I) and re.search(r"prix", name, re.I):
            print("== séries de", fid, name)
            d = requests.get(f"https://bdm.insee.fr/series/sdmx/data/{fid}", params={"lastNObservations": 1},
                             headers=UA, timeout=300)
            for m in re.finditer(r'<Series ([^>]+)>\s*<Obs ([^>]+)/>', d.text):
                a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
                o = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
                print(f"   {a.get('IDBANK')} | {a.get('TITLE_FR','')[:150]} | {o.get('TIME_PERIOD')} {o.get('OBS_VALUE')}")

if "marques" in what:
    QUERIES = ["barilla spaghetti", "lavazza qualita rossa", "evian", "nescafe gold", "philadelphia original",
               "heinz ketchup", "kellogg's corn flakes", "oreo", "haribo", "toblerone", "ovomaltine", "nivea creme",
               "colgate", "pampers", "president", "lu petit beurre", "nespresso", "volvic", "san pellegrino",
               "knorr", "maggi", "milka", "ricore", "kiri", "babybel", "danone", "activia", "head & shoulders"]
    mig = Migros(Session(), {})
    for q in QUERIES:
        print("==", q)
        try:
            for c in mig.search({"id": q.replace(" ", "_"), "query": q})[:6]:
                print(f"   MIGROS {c.name[:70]} | {c.price} | {c.raw_size} | promo={c.promo} | ean={c.ean}")
        except Exception as e:  # noqa: BLE001
            print("   MIGROS ERR", e)
        try:
            off = requests.get("https://world.openfoodfacts.org/cgi/search.pl", headers=UA, timeout=60, params={
                "search_terms": q, "json": 1, "page_size": 6, "countries_tags_en": "france",
                "fields": "code,product_name,quantity,brands", "sort_by": "unique_scans_n"}).json()
            for p in off.get("products", []):
                n = requests.get("https://prices.openfoodfacts.org/api/v1/prices", headers=UA, timeout=60, params={
                    "product_code": p["code"], "currency": "EUR", "date__gte": "2026-04-25", "size": 1}).json().get("total")
                print(f"   OFF {p['code']} | {p.get('brands','')[:20]} {p.get('product_name','')[:50]} | {p.get('quantity')} | prix 6 mois: {n}")
        except Exception as e:  # noqa: BLE001
            print("   OFF ERR", e)
