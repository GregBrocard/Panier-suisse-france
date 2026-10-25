"""Sonde v3 : indices de prix (Eurostat HICP, INSEE IPC) pour la crèmerie, pondérations HICP Suisse,
codes-barres français des marques candidates (Open Food Facts + nombre de prix Open Prices)."""
import re
import sys
import time
import requests

UA = {"User-Agent": "panier-suisse-france/2.0 (https://github.com/GregBrocard/Panier-suisse-france)"}
what = sys.argv[1:] or ["eurostat", "insee", "off"]
ES = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

if "eurostat" in what:
    for ds, params in [("prc_hicp_inw", {"geo": ["CH", "FR"], "sinceTimePeriod": "2025"}),
                       ("prc_hicp_minr", {"geo": "FR", "unit": "I15", "sinceTimePeriod": "2019-12"}),
                       ("prc_hicp_midx", {"geo": "FR", "unit": "I15", "sinceTimePeriod": "2019-12"}),
                       ("prc_hicp_minr", {"geo": "FR", "unit": "I25", "sinceTimePeriod": "2019-12"})]:
        r = requests.get(ES + ds, params={**params, "format": "JSON", "lang": "en"}, headers=UA, timeout=180)
        print("==", ds, params, r.status_code, len(r.content))
        if r.status_code != 200:
            print(r.text[:500]); continue
        j = r.json()
        dims = j["id"]; size = j["size"]
        cats = {d: {v: k for k, v in j["dimension"][d]["category"]["index"].items()} for d in dims}
        labels = j["dimension"]["coicop"]["category"].get("label", {}) if "coicop" in dims else {}
        # imprime les coicop alimentaires et la dernière valeur
        vals = j["value"]
        strides = [1] * len(dims)
        for i in range(len(dims) - 2, -1, -1):
            strides[i] = strides[i + 1] * size[i + 1]
        last = {}
        for k, v in vals.items():
            k = int(k); idx = {}
            for d, st, sz in zip(dims, strides, size):
                idx[d] = cats[d][(k // st) % sz]
            c = idx.get("coicop", "")
            if c.startswith("CP01") and len(c) <= 7:
                key = (idx.get("geo"), c)
                t = idx.get("time")
                last.setdefault(key, {})[t] = v
        for (geo, c), series in sorted(last.items()):
            ts = sorted(series)
            pick = [t for t in ts if t in ("2019-12", "2025", "2026", "2025-12")] + ts[-1:]
            print(f"   {geo} {c:8s} {labels.get(c,'')[:60]:60s} " + " ".join(f"{t}={series[t]}" for t in dict.fromkeys(pick)))

if "eurostat2" in what:
    r = requests.get(ES + "prc_hicp_midx", params={"geo": "FR", "unit": "I25", "coicop": ["CP01142", "CP01151", "CP01145", "CP01144", "CP01154"],
                     "sinceTimePeriod": "2019-11", "format": "JSON", "lang": "en"}, headers=UA, timeout=180)
    print("== midx I25", r.status_code)
    j = r.json(); t = j["dimension"]["time"]["category"]["index"]; inv = {v: k for k, v in t.items()}
    print("   périodes", min(t), max(t), len(t), "valeurs", len(j.get("value", {})))
    print("   ", {inv[int(k) % len(t)]: v for k, v in list(j["value"].items())[:3]}, {inv[int(k) % len(t)]: v for k, v in list(j["value"].items())[-3:]})

if "insee" in what:
    for fid in ["IPC-2015", "IPC-2025"]:
        r = requests.get(f"https://bdm.insee.fr/series/sdmx/data/{fid}", params={"lastNObservations": 1},
                         headers=UA, timeout=600)
        print("==", fid, r.status_code, len(r.content))
        for m in re.finditer(r'<Series ([^>]+)>\s*<Obs ([^>]+)/>', r.text):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            o = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
            t = a.get("TITLE_FR", "")
            if re.search(r"Ensemble des ménages - France", t) and re.search(
                    r"[Ll]ait|[Bb]eurre|[Ff]romage|[Yy]a?ourt|[Hh]uile|[Œœ]ufs|[Pp]âtes|[Ss]ucre|[Cc]afé|[Ff]arine|[Ee]aux min", t) \
                    and "mensuel" in t.lower():
                print(f"   {a.get('IDBANK')} | {t[:170]} | {o.get('TIME_PERIOD')} {o.get('OBS_VALUE')}")

if "off" in what:
    Q = [("barilla", "spaghetti"), ("evian", "eaux-minerales"), ("nescafe", "cafes-solubles"), ("heinz", "ketchup"),
         ("kellogg-s", "corn-flakes"), ("oreo", "biscuits"), ("haribo", "bonbons"), ("president", "camemberts"),
         ("kiri", ""), ("babybel", ""), ("toblerone", ""), ("head-shoulders", ""), ("lavazza", "cafes-moulus"),
         ("pampers", ""), ("philadelphia", "")]
    for brand, cat in Q:
        time.sleep(8)
        params = {"brands_tags": brand, "countries_tags": "en:france", "page_size": 8,
                  "fields": "code,product_name,quantity,brands", "sort_by": "unique_scans_n"}
        if cat:
            params["categories_tags"] = cat
        try:
            r = requests.get("https://world.openfoodfacts.org/api/v2/search", params=params, headers=UA, timeout=90)
            prods = r.json().get("products", [])
        except Exception as e:  # noqa: BLE001
            print("==", brand, "ERR", e, r.status_code if 'r' in dir() else ""); continue
        print("==", brand, cat, len(prods))
        for p in prods:
            n = requests.get("https://prices.openfoodfacts.org/api/v1/prices", headers=UA, timeout=60, params={
                "product_code": p["code"], "currency": "EUR", "date__gte": "2025-10-25", "size": 1}).json().get("total")
            print(f"   {p['code']} | {p.get('product_name','')[:55]} | {p.get('quantity')} | prix 12 mois: {n}")
