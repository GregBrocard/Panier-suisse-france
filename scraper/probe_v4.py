"""Sonde v4 : codes COICOP disponibles en 2026 (Eurostat), produits Open Prices les plus relevés par marque."""
import requests
UA = {"User-Agent": "panier-suisse-france/2.0 (https://github.com/GregBrocard/Panier-suisse-france)"}
ES = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
for unit in ["I25", "I15"]:
    r = requests.get(ES + "prc_hicp_midx", params={"geo": "FR", "unit": unit, "sinceTimePeriod": "2026-01",
                     "format": "JSON", "lang": "fr"}, headers=UA, timeout=300)
    j = r.json(); print("== midx", unit, r.status_code, "valeurs", len(j.get("value", {})))
    if not j.get("value"):
        continue
    dims, size = j["id"], j["size"]
    cats = {d: {v: k for k, v in j["dimension"][d]["category"]["index"].items()} for d in dims}
    lab = j["dimension"]["coicop"]["category"]["label"]
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * size[i + 1]
    seen = {}
    for k, v in j["value"].items():
        k = int(k); idx = {d: cats[d][(k // st) % sz] for d, st, sz in zip(dims, strides, size)}
        c = idx["coicop"]
        if any(w in lab.get(c, "").lower() for w in ["lait", "beurre", "fromage", "yaourt", "huile", "œuf", "oeuf"]) or c in ("CP0114", "CP0115"):
            seen.setdefault(c, {})[idx["time"]] = v
    for c, s in sorted(seen.items()):
        print(f"   {c:10s} {lab.get(c,'')[:70]:70s} {min(s)}={s[min(s)]} {max(s)}={s[max(s)]}")
    # même poste sur l'historique long ?
    for c in list(seen)[:3]:
        r2 = requests.get(ES + "prc_hicp_midx", params={"geo": "FR", "unit": unit, "coicop": c, "sinceTimePeriod": "2019-11",
                          "format": "JSON"}, headers=UA, timeout=120).json()
        t = {v: k for k, v in r2["dimension"]["time"]["category"]["index"].items()}
        vals = {t[int(k)]: v for k, v in r2.get("value", {}).items()}
        print("   historique", c, len(vals), min(vals) if vals else None, max(vals) if vals else None)

for b in ["barilla", "evian", "nescafe", "heinz", "kellogg", "oreo", "haribo", "kiri", "babybel", "toblerone",
          "lavazza", "philadelphia", "president", "volvic", "cristaline", "panzani", "lu", "danone", "milka", "bonne maman"]:
    try:
        r = requests.get("https://prices.openfoodfacts.org/api/v1/products", headers=UA, timeout=60,
                         params={"brands__like": b, "order_by": "-price_count", "size": 6})
        items = r.json().get("items", [])
        print("==", b, r.status_code, len(items))
        for p in items:
            print(f"   {p.get('code')} | {(p.get('product_name') or '')[:55]} | {p.get('product_quantity')}{p.get('product_quantity_unit') or ''} | prix: {p.get('price_count')} | {p.get('brands')}")
    except Exception as e:  # noqa: BLE001
        print("==", b, "ERR", e, getattr(r, "status_code", ""), getattr(r, "text", "")[:200])
