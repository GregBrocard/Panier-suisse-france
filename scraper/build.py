"""Construit les données du site à partir de toutes les sources.

Sorties :
  data/series.json           historique mensuel (panier officiel, change, carburant)
  data/latest.json           photo du mois : détail par produit, viande, marques, carburant par zone
  data/releves/AAAA-MM.json  archive des relevés automatiques (Migros, Open Prices, stations)

Lancement : python -m scraper.build
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
import traceback

import yaml

from . import sources as S
from .common import ROOT, Candidate, Session, matches, finalize
from .migros import Scraper as Migros

DATA = ROOT / "data"
LOG: list[str] = []


def log(msg: str):
    print(msg, flush=True)
    LOG.append(msg)


def safe(fn, *a, default=None, label=""):
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        log(f"!! {label or fn.__name__} : {e.__class__.__name__}: {str(e)[:200]}")
        if __import__('os').environ.get('SCRAPER_DEBUG') == '2':
            traceback.print_exc()
        return default


def mean_series(series_list: list[dict]) -> dict:
    months = sorted({m for s in series_list for m in s})
    out = {}
    for m in months:
        v = [s[m] for s in series_list if m in s]
        if v:
            out[m] = round(statistics.mean(v), 4)
    return out


def ffill(series: dict, months: list[str], limit: int) -> dict:
    out, last, age = {}, None, 0
    for m in months:
        if m in series:
            last, age = series[m], 0
            out[m] = last
        elif last is not None and age < limit:
            age += 1
            out[m] = last
    return out


def month_range(start: str, end: str) -> list[str]:
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


# ------------------------------------------------------------------ couche 1 : officiel

def build_officiel(cfg, fx):
    items = {}
    for it in cfg["officiel"]:
        ch = mean_series([safe(S.ofag_series, it["ofag"]["cube"], p, default={}, label=f"OFAG {p}")
                          for p in it["ofag"]["products"]])
        fr_list, titles = [], []
        for idb in it["insee"]:
            res = safe(S.insee_series, idb, default=None, label=f"INSEE {idb}")
            if res:
                titles.append(res[0])
                fr_list.append(res[1])
        fr = mean_series(fr_list)
        if it.get("fill_months") and ch:
            ch = ffill(ch, month_range(min(ch), max(max(ch), max(fr) if fr else max(ch))), it["fill_months"])
        log(f"   {it['id']:12s} OFAG {len(ch):4d} mois ({min(ch) if ch else '-'}→{max(ch) if ch else '-'})"
            f" | INSEE {len(fr):4d} mois ({min(fr) if fr else '-'}→{max(fr) if fr else '-'})")
        items[it["id"]] = {"meta": {**{k: it[k] for k in ("id", "label", "cat", "unit", "qty")},
                                    "in_total": it.get("in_total", True)},
                           "sources": {"ofag": it["ofag"]["products"], "insee": it["insee"], "insee_titres": titles},
                           "ch": ch, "fr": fr}

    # série mensuelle du panier : uniquement les mois où CH, FR et change existent
    months = sorted({m for v in items.values() for m in v["ch"]} & {m for v in items.values() for m in v["fr"]} & set(fx))
    n_total = len(items)
    series = []
    for m in months:
        common = [k for k, v in items.items() if m in v["ch"] and m in v["fr"] and v["meta"]["in_total"]]
        if len(common) < max(3, int(0.6 * n_total)):
            continue
        ch_t = sum(items[k]["ch"][m] * items[k]["meta"]["qty"] for k in common)
        fr_t = sum(items[k]["fr"][m] * fx[m] * items[k]["meta"]["qty"] for k in common)
        cats = {}
        for c in sorted({items[k]["meta"]["cat"] for k in common}):
            ks = [k for k in common if items[k]["meta"]["cat"] == c]
            a = sum(items[k]["ch"][m] * items[k]["meta"]["qty"] for k in ks)
            b = sum(items[k]["fr"][m] * fx[m] * items[k]["meta"]["qty"] for k in ks)
            cats[c] = round((a / b - 1) * 100, 1)
        series.append({"m": m, "fx": fx[m], "n": len(common), "ch": round(ch_t, 2), "fr": round(fr_t, 2),
                       "ecart": round((ch_t / fr_t - 1) * 100, 1), "cats": cats})

    # photo : dernier mois commun pour chaque produit
    photo = []
    for k, v in items.items():
        common = sorted(set(v["ch"]) & set(v["fr"]) & set(fx))
        if not common:
            photo.append({**v["meta"], "status": "indisponible"})
            continue
        m = common[-1]
        fr_chf = v["fr"][m] * fx[m]
        photo.append({**v["meta"], "mois": m, "ch": round(v["ch"][m], 2), "fr_eur": round(v["fr"][m], 2),
                      "fr_chf": round(fr_chf, 2), "ecart": round((v["ch"][m] / fr_chf - 1) * 100, 1),
                      "sources": v["sources"]})
    # historique par produit (allégé : 1 point / mois commun)
    per_item = {k: [[m, round(v["ch"][m], 3), round(v["fr"][m], 3)]
                    for m in sorted(set(v["ch"]) & set(v["fr"]))] for k, v in items.items()}
    return series, photo, per_item


# ------------------------------------------------------------------ Migros (viande, marques)

def migros_candidates(mig: Migros, query: str) -> list[Candidate]:
    return mig.search({"id": query.replace(" ", "_"), "query": query})


def build_viande(cfg, fx, s):
    mig = Migros(s, {})
    out = []
    for it in cfg["viande"]:
        rule = {"match": {k: it["migros"].get(k, []) for k in ("include", "any", "exclude")},
                "unit": it["unit"], "size": {"min": 0.05, "max": 5}}
        cands = safe(migros_candidates, mig, it["migros"]["query"], default=[], label=f"Migros {it['id']}")
        valid = []
        for c in cands:
            if matches(rule, c) and not c.promo:
                c2 = finalize(rule, c)
                if c2:
                    valid.append(c2)
        ch = round(statistics.median([c.unit_price for c in valid]), 2) if valid else None
        res = safe(S.insee_series, it["insee"][0], default=None, label=f"INSEE {it['id']}")
        fr_m, fr = (max(res[1]), res[1][max(res[1])]) if res and res[1] else (None, None)
        rate = fx.get(fr_m) if fr_m else None
        row = {"id": it["id"], "label": it["label"], "unit": it["unit"], "qty": it["qty"],
               "ch": ch, "ch_n": len(valid), "ch_produits": [f"{c.name} — {c.unit_price:.2f}/kg" for c in
                                                              sorted(valid, key=lambda c: c.unit_price)][:8],
               "fr_eur": fr, "fr_mois": fr_m, "fr_chf": round(fr * rate, 2) if fr and rate else None,
               "insee": it["insee"][0]}
        if row["ch"] and row["fr_chf"]:
            row["ecart"] = round((row["ch"] / row["fr_chf"] - 1) * 100, 1)
        log(f"   viande {it['id']:10s} CH {ch} ({len(valid)} produits) | FR {fr} € ({fr_m})")
        out.append(row)
    return out


def build_marques(cfg, fx_today, s):
    """Même marque des deux côtés, comparée au prix unitaire (CHF/kg ou CHF/L)."""
    mig = Migros(s, {})
    out = []
    for it in cfg["marques"]:
        lo, hi = it["migros"]["size"]
        rule = {"match": {k: it["migros"].get(k, []) for k in ("include", "any", "exclude")},
                "unit": it["unit"], "size": {"min": lo * 0.98, "max": hi * 1.02}}
        cands = safe(migros_candidates, mig, it["migros"]["query"], default=[], label=f"Migros {it['id']}")
        valid = [c for c in (finalize(rule, c) for c in cands if matches(rule, c)) if c]
        regular = [c for c in valid if not c.promo] or valid
        best = min(regular, key=lambda c: c.unit_price) if regular else None
        op = safe(S.openprices_fr, it["ean_fr"], default=None, label=f"Open Prices {it['id']}")
        row = {"id": it["id"], "label": it["label"], "unit": it["unit"], "qty": it["qty"],
               "ch_unit": best.unit_price if best else None,
               "ch_produit": f"{best.name} ({best.size:g} {best.unit}) à {best.price:.2f}" if best else None,
               "ch_url": best.url if best else None,
               "fr_unit_eur": round(op["median"] / it["size_fr"], 3) if op else None, "fr_n": op["n"] if op else 0,
               "fr_produit": (op["products"][0] if op and op["products"] else None),
               "fr_prix_eur": op["median"] if op else None, "fr_depuis": op["since"] if op else None,
               "ean_fr": it["ean_fr"]}
        if row["fr_unit_eur"]:
            row["fr_unit_chf"] = round(row["fr_unit_eur"] * fx_today, 3)
        if row["ch_unit"] and row.get("fr_unit_chf"):
            row["ecart"] = round((row["ch_unit"] / row["fr_unit_chf"] - 1) * 100, 1)
        log(f"   marque {it['id']:8s} CH {row['ch_unit']}/{it['unit']} ({row['ch_produit']}) | "
            f"FR {row['fr_unit_eur']} €/{it['unit']} (n={row['fr_n']})")
        out.append(row)
    return out


# ------------------------------------------------------------------ carburant

def build_carburant(cfg, fx, fx_today, dests, rayon):
    """Prix des stations françaises autour de chaque destination + prix suisse (OFDF) + historique INSEE."""
    out = {}
    for d in dests:
        res = safe(S.fuel_fr_near, d["lat"], d["lon"], rayon + 1, default=None, label=f"stations {d['id']}")
        if res:
            res.pop("stations", None)
            res["moyenne_chf"] = {k: (round(v * fx_today, 3) if v else None) for k, v in res["moyenne"].items()}
            res["min_chf"] = {k: (round(v * fx_today, 3) if v else None) for k, v in res["min"].items()}
            log(f"   carburant {d['id']:11s} {res['n']} stations, moyenne {res['moyenne']}")
        out[d["id"]] = res
    ch = safe(S.fuel_ch_ofdf, default=None, label="OFDF T4.4")
    if ch:
        log(f"   carburant CH (OFDF) diesel {ch.get('diesel')} sp95 {ch.get('sp95')} ({ch.get('date_texte')})")
        ch.pop("raw", None)
    hist = {}
    for t in cfg["carburant"]["types"]:
        res = safe(S.insee_series, t["insee"][0], default=None, label=f"INSEE {t['id']}")
        if res:
            hist[t["id"]] = [[m, v, round(v * fx[m], 3)] for m, v in sorted(res[1].items()) if m in fx]
    return {"destinations": out, "ch": ch, "historique_fr": hist}


# ------------------------------------------------------------------ magasins (Que Choisir) et trajets

def _km(a, b):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def build_magasins(cfg, dcfg):
    from . import quechoisir as QC
    from . import routes as R
    qc = cfg.get("quechoisir") or {}
    dests = dcfg["destinations"]
    rayon = dcfg["rayon_km"]
    panel = safe(QC.national_panel, qc["panel"]["n"], qc["panel"]["seed"], 22000, DATA / "qc_panel.json",
                 default=None, label="Que Choisir panel")
    if not panel or not panel["mediane"]:
        return None
    log(f"   panel national : {panel['n']} magasins, médiane {panel['mediane']} €")

    ids = []
    for dep in dcfg["departements"]:
        got = safe(QC.department_store_ids, dep, default=[], label=f"Que Choisir dép. {dep}") or []
        log(f"   département {dep} : {len(got)} magasins listés")
        ids += got
    geo_path = DATA / "geo_magasins.json"
    geo = json.loads(geo_path.read_text()) if geo_path.exists() else {}
    per_dest = {d["id"]: [] for d in dests}
    n_ok = 0
    for dm in sorted(set(ids)):
        st = safe(QC.store, dm, default=None, label=f"magasin {dm}")
        if not st:
            continue
        n_ok += 1
        key = str(dm)
        if key not in geo:
            c = R.geocode([st.get("adresse"), f"{st['nom']} {st.get('cp') or ''}", f"{st.get('cp') or ''} France"])
            if c:
                geo[key] = c
        if key not in geo:
            continue
        dkm = lambda d: min(_km(geo[key], tuple(p)) for p in [(d["lat"], d["lon"])] + (d.get("points") or []))
        near = min(dests, key=dkm)
        dist = dkm(near)
        if dist > rayon:
            continue
        g = st["paniers"]["global"]
        per_dest[near["id"]].append({"dm": dm, "nom": st["nom"], "cp": st["cp"], "adresse": st.get("adresse"),
                                     "url": st["url"], "panier": g, "paniers": st["paniers"],
                                     "appreciation": st["appreciation"], "indice": round(g / panel["mediane"], 4),
                                     "km_centre": round(dist, 1), "coord": geo[key]})
    geo_path.write_text(json.dumps(geo, separators=(",", ":")), encoding="utf-8")
    log(f"   {n_ok} fiches magasin lues, {len(geo)} adresses géocodées")

    out_dests = []
    for d in dests:
        ms = sorted(per_dest[d["id"]], key=lambda r: r["panier"])
        idx = [m["indice"] for m in ms]
        out_dests.append({**{k: v for k, v in d.items() if k != "points"}, "magasins": ms,
                          "indice_median": round(statistics.median(idx), 4) if idx else None,
                          "panier_median": round(statistics.median([m["panier"] for m in ms]), 2) if ms else None})
        log(f"   {d['id']:11s} {len(ms)} magasins, indice médian {out_dests[-1]['indice_median']}")
    return {"source": "UFC-Que Choisir, comparateur des supermarchés", "publier": qc.get("publier", False),
            "panel": panel, "destinations": out_dests}


def build_origines(dests):
    """Toutes les localités de Suisse et leur distance routière vers chaque destination."""
    from . import origines as O
    from . import routes as R
    locs = O.localites()
    log(f"   {len(locs)} localités suisses (swisstopo)")
    cache = R.matrix(locs, dests, DATA / "distances.json", log=log)
    liste, dist, coords = [], [], []
    for o in locs:
        row = cache.get(f"{o['nom']}|{o['canton']}", {})
        if not row:
            continue
        liste.append([o["nom"], o["canton"], o["npa"]])
        coords.append([round(o["lat"], 3), round(o["lon"], 3)])
        flat = []
        for d in dests:
            v = row.get(d["id"])
            flat += v if v else [None, None]
        dist.append(flat)
    log(f"   trajets disponibles pour {len(liste)} localités")
    return {"liste": liste, "dist": dist, "coords": coords, "destinations": [d["id"] for d in dests],
            "source": "swisstopo (répertoire officiel des localités) ; OSRM et OpenStreetMap (itinéraires)"}


# ------------------------------------------------------------------ main

def main():
    cfg = yaml.safe_load((ROOT / "config/panier.yaml").read_text(encoding="utf-8"))
    s = Session(delay=1.0)
    today = dt.date.today()

    log("== Change BCE")
    fx = S.ecb_eur_chf_monthly()
    fx_day = safe(S.ecb_eur_chf_daily_last, default=None, label="BCE jour") or \
        {"date": max(fx), "eur_chf": fx[max(fx)]}
    log(f"   {len(fx)} mois, dernier jour {fx_day}")

    log("== Panier officiel (OFAG / INSEE)")
    series, photo, per_item = build_officiel(cfg, fx)
    log(f"   {len(series)} mois de série, dernier : {series[-1] if series else '-'}")

    log("== Viande (Migros / INSEE)")
    viande = build_viande(cfg, fx, s)
    log("== Marques (Migros / Open Prices)")
    marques = build_marques(cfg, fx_day["eur_chf"], s)
    dcfg = yaml.safe_load((ROOT / "config/destinations.yaml").read_text(encoding="utf-8"))
    log("== Carburant")
    carb = build_carburant(cfg, fx, fx_day["eur_chf"], dcfg["destinations"], dcfg["rayon_km"])
    log("== Magasins (Que Choisir)")
    magasins = build_magasins(cfg, dcfg)
    log("== Trajets")
    origines = safe(build_origines, dcfg["destinations"], default=None, label="trajets")

    latest = {
        "genere_le": today.isoformat(), "basket_version": cfg["basket_version"],
        "fx": {"jour": fx_day, "source": "BCE, taux de référence EUR/CHF"},
        "officiel": {"mois": series[-1]["m"] if series else None, "produits": photo,
                     "dernier": series[-1] if series else None},
        "viande": viande, "marques": marques, "carburant": carb,
        "magasins": magasins, "origines": origines,
        "destinations": [{k: d[k] for k in ("id", "nom", "lat", "lon", "passage")} for d in dcfg["destinations"]],
        "journal": LOG,
    }
    hist = {
        "genere_le": today.isoformat(), "basket_version": cfg["basket_version"],
        "panier": series,
        "produits": per_item,
        "fx": [[m, v] for m, v in sorted(fx.items())],
        "carburant_fr": carb["historique_fr"],
    }
    DATA.mkdir(exist_ok=True)
    (DATA / "releves").mkdir(exist_ok=True)
    (DATA / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "series.json").write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    snap = {"date": today.isoformat(), "fx": fx_day, "viande": viande, "marques": marques,
            "carburant": {"destinations": {z: (v and {k: v[k] for k in ("n", "moyenne", "min")}) for z, v in carb["destinations"].items()},
                          "ch": carb["ch"]}}
    (DATA / "releves" / f"{today:%Y-%m}.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    log("== Terminé")


if __name__ == "__main__":
    main()
