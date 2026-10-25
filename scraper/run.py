"""Relevé complet : prix de chaque besoin dans chaque enseigne + agrégation par zone.

Produit :
  data/latest.json             relevé détaillé du mois (chaque produit retenu, son URL, son prix)
  data/releves/AAAA-MM.json    archive du relevé
  data/history.json            série mensuelle résumée (sert au graphique d'évolution)

Lancement : python -m scraper.run   (SCRAPER_ONLY=ch_coop,fr_leclerc_annemasse pour limiter)
"""
from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import statistics
import traceback

import yaml

from .common import ROOT, Session, pick
from .fx import eur_chf

DATA = ROOT / "data"


def load_cfg():
    basket = yaml.safe_load((ROOT / "config/basket.yaml").read_text(encoding="utf-8"))
    stores = yaml.safe_load((ROOT / "config/stores.yaml").read_text(encoding="utf-8"))
    return basket, stores


def collect(basket: dict, stores: dict, s: Session) -> list[dict]:
    only = [x for x in os.environ.get("SCRAPER_ONLY", "").split(",") if x]
    rows = []
    for st in stores["stores"]:
        if only and st["id"] not in only:
            continue
        try:
            mod = importlib.import_module(f"scraper.{st['scraper']}")
            scraper = mod.Scraper(s, st.get("store") or {})
        except Exception as e:  # noqa: BLE001
            print(f"[{st['id']}] scraper indisponible : {e}")
            continue
        for item in basket["items"]:
            status, chosen, n = "ok", None, 0
            try:
                cands = scraper.search(item)
                n = len(cands)
                chosen = pick(item, cands)
                if not chosen:
                    status = "introuvable" if n else "aucun_resultat"
            except Exception as e:  # noqa: BLE001
                status = f"erreur: {e.__class__.__name__}: {e}"[:200]
                if os.environ.get("SCRAPER_DEBUG"):
                    traceback.print_exc()
            row = {"store": st["id"], "item": item["id"], "status": status, "candidates": n}
            if chosen:
                row.update({
                    "name": chosen.name, "price": chosen.price, "currency": chosen.currency,
                    "size": chosen.size, "unit": chosen.unit, "unit_price": chosen.unit_price,
                    "promo": chosen.promo, "url": chosen.url,
                })
            print(f"[{st['id']:24s}] {item['id']:12s} {status:14s} "
                  f"{(chosen.name[:45] + ' ' + str(chosen.price)) if chosen else ''}")
            rows.append(row)
    return rows


def aggregate(basket: dict, stores: dict, rows: list[dict], fx: float) -> dict:
    """Panier moyen par zone : pour chaque besoin, moyenne des enseignes qui l'ont,
    en CHF (prix France convertis au taux BCE du jour du relevé).
    Seuls les besoins trouvés des deux côtés entrent dans le total de la zone."""
    items = {i["id"]: i for i in basket["items"]}
    store_by_id = {s["id"]: s for s in stores["stores"]}
    found = [r for r in rows if r["status"] == "ok"]

    def line_cost(r):  # coût du besoin en CHF (quantité de référence)
        c = r["unit_price"] * items[r["item"]]["ref_qty"]
        return c * fx if r["currency"] == "EUR" else c

    zones_out = {}
    for z in stores["zones"]:
        zid = z["id"]
        per_item = {}
        for iid, item in items.items():
            side = {"CH": [], "FR": []}
            for r in found:
                st = store_by_id[r["store"]]
                if r["item"] == iid and zid in st["zones"]:
                    side[st["country"]].append({"store": r["store"], "chain": st["chain"],
                                                "chf": round(line_cost(r), 3)})
            if side["CH"] or side["FR"]:
                per_item[iid] = {
                    "ch": side["CH"], "fr": side["FR"],
                    "ch_mean": round(statistics.mean(x["chf"] for x in side["CH"]), 3) if side["CH"] else None,
                    "fr_mean": round(statistics.mean(x["chf"] for x in side["FR"]), 3) if side["FR"] else None,
                    "ch_min": round(min(x["chf"] for x in side["CH"]), 3) if side["CH"] else None,
                    "fr_min": round(min(x["chf"] for x in side["FR"]), 3) if side["FR"] else None,
                }

        def basket_total(kind, stat="mean", category=None):
            ch = fr = 0.0
            n = 0
            for iid, v in per_item.items():
                it = items[iid]
                if (it["type"] != kind) or (category and it["category"] != category):
                    continue
                if v[f"ch_{stat}"] is None or v[f"fr_{stat}"] is None:
                    continue
                ch += v[f"ch_{stat}"]
                fr += v[f"fr_{stat}"]
                n += 1
            if not n:
                return None
            return {"ch": round(ch, 2), "fr": round(fr, 2), "n": n,
                    "diff_pct": round((ch / fr - 1) * 100, 1) if fr else None}

        cats = sorted({i["category"] for i in items.values() if i["type"] == "generic"})
        zones_out[zid] = {
            "premier_prix": basket_total("generic"),
            "premier_prix_moins_cher": basket_total("generic", "min"),
            "marques": basket_total("brand"),
            "categories": {c: basket_total("generic", category=c) for c in cats},
            "items": per_item,
        }
    return zones_out


def main():
    basket, stores = load_cfg()
    s = Session(delay=float(os.environ.get("SCRAPER_DELAY", "1.5")))
    fx = eur_chf(s)
    print(f"Taux EUR/CHF : {fx}")
    rows = collect(basket, stores, s)
    today = dt.date.today()
    zones = aggregate(basket, stores, rows, fx["eur_chf"])

    latest = {
        "date": today.isoformat(),
        "month": today.strftime("%Y-%m"),
        "basket_version": basket["basket_version"],
        "fx": fx,
        "zones_meta": stores["zones"],
        "stores": [{k: v for k, v in s_.items() if k != "store"} for s_ in stores["stores"]],
        "items_meta": [{k: i[k] for k in ("id", "label", "category", "type", "unit", "ref_qty")}
                       for i in basket["items"]],
        "prices": rows,
        "zones": zones,
        "coverage": {
            "ok": sum(r["status"] == "ok" for r in rows),
            "total": len(rows),
        },
    }
    DATA.mkdir(exist_ok=True)
    (DATA / "releves").mkdir(exist_ok=True)
    (DATA / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "releves" / f"{latest['month']}.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")

    hist_path = DATA / "history.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
    hist = [h for h in hist if h["month"] != latest["month"]]
    hist.append({
        "month": latest["month"], "date": latest["date"],
        "basket_version": latest["basket_version"], "eur_chf": fx["eur_chf"],
        "zones": {z: {k: v[k] for k in ("premier_prix", "premier_prix_moins_cher", "marques", "categories")}
                  for z, v in zones.items()},
        "coverage": latest["coverage"],
    })
    hist.sort(key=lambda h: h["month"])
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Couverture : {latest['coverage']['ok']}/{latest['coverage']['total']}")


if __name__ == "__main__":
    main()
