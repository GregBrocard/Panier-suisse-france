"""Sonde : indices de niveau des prix Eurostat (PPA), Suisse et France, par catégorie alimentaire."""
import requests
UA = {"User-Agent": "panier-suisse-france/2.0"}
r = requests.get("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_ppp_ind",
                 params={"geo": ["CH", "FR"], "na_item": "PLI_EU27_2020", "sinceTimePeriod": "2021", "format": "JSON", "lang": "en"},
                 headers=UA, timeout=300)
j = r.json(); print(r.status_code, j.get("id"), j.get("size"))
dims, size = j["id"], j["size"]
cats = {d: {v: k for k, v in j["dimension"][d]["category"]["index"].items()} for d in dims}
lab = j["dimension"]["ppp_cat"]["category"]["label"]
st = [1] * len(dims)
for i in range(len(dims) - 2, -1, -1):
    st[i] = st[i + 1] * size[i + 1]
vals = {}
for k, v in j["value"].items():
    k = int(k); idx = {d: cats[d][(k // s) % n] for d, s, n in zip(dims, st, size)}
    c = idx["ppp_cat"]
    if c.startswith("A0101") or c.startswith("A0102") or c in ("A01", "GDP", "A0107", "A010722"):
        vals.setdefault(c, {}).setdefault(idx["time"], {})[idx["geo"]] = v
for c in sorted(vals):
    t = max(vals[c]); d = vals[c][t]
    ch, fr = d.get("CH"), d.get("FR")
    print(f"{c:10s} {lab.get(c,'')[:55]:55s} {t} CH={ch} FR={fr} CH/FR={round((ch/fr-1)*100) if ch and fr else '-'} %")
