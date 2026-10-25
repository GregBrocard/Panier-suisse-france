"""Relevé quotidien des prix de l'essence (page « Faire le plein »).

France : flux officiel des prix des stations (data.economie.gouv.fr), autour de chaque zone de
destination ; Suisse et autres frontières : tableau OFDF T 4.4 (mensuel) ; change : BCE (quotidien).

Sortie : data/essence.json. Lancement : python -m scraper.essence
"""
from __future__ import annotations

import datetime as dt
import json

import yaml

from . import sources as S
from .common import ROOT

DATA = ROOT / "data"


def _safe(fn, *a, default=None):
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        print(f"!! {fn.__name__}: {e.__class__.__name__}: {str(e)[:200]}", flush=True)
        return default


def moins_chers(stations: list[dict], kind: str, n: int = 3) -> list[dict]:
    key = "sp95_ou_e10" if kind == "sp95" else "diesel"
    rows = [s for s in stations if s.get(key)]
    rows.sort(key=lambda s: s[key])
    return [{"adresse": s.get("adresse"), "ville": s.get("ville"), "prix": s[key], "maj": s.get("maj")} for s in rows[:n]]


def main():
    dcfg = yaml.safe_load((ROOT / "config/destinations.yaml").read_text(encoding="utf-8"))
    prev = {}
    path = DATA / "essence.json"
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
    fx = _safe(S.ecb_eur_chf_daily_last) or prev.get("fx") or {}
    rate = fx.get("eur_chf")
    zones = {}
    for d in dcfg["destinations"]:
        res = _safe(S.fuel_fr_near, d["lat"], d["lon"], dcfg["rayon_km"] + 1)
        if not res or not res.get("n"):
            old = (prev.get("zones") or {}).get(d["id"])
            if old:
                old["reprise"] = True
            zones[d["id"]] = old
            print(f"   {d['id']:12s} pas de données, valeur précédente reprise", flush=True)
            continue
        z = {"nom": d["nom"], "n": res["n"], "moyenne": res["moyenne"], "min": res["min"],
             "moins_chers": {k: moins_chers(res["stations"], k) for k in ("sp95", "diesel")}}
        if rate:
            z["moyenne_chf"] = {k: (round(v * rate, 3) if v else None) for k, v in res["moyenne"].items()}
            z["min_chf"] = {k: (round(v * rate, 3) if v else None) for k, v in res["min"].items()}
        zones[d["id"]] = z
        print(f"   {d['id']:12s} {res['n']} stations, moyenne {res['moyenne']}", flush=True)
    ofdf = _safe(S.fuel_ch_ofdf) or prev.get("ofdf")
    # stations françaises de la bande frontalière, prix du jour (mode « Où faire le plein »)
    from . import stations as ST
    bande = _safe(ST.fr_stations_bande)
    if bande:
        print(f"   bande frontalière : {len(bande)} stations françaises", flush=True)
    else:
        bande = prev.get("stations_fr") or []
        print("   bande frontalière : flux indisponible, liste précédente reprise", flush=True)
    # liste OpenStreetMap des stations : rafraîchie si absente ou plus vieille que 30 jours
    osm = DATA / "stations_osm.json"
    age = 999
    if osm.exists():
        try:
            age = (dt.date.today() - dt.date.fromisoformat(json.loads(osm.read_text(encoding="utf-8"))["genere_le"])).days
        except Exception:  # noqa: BLE001
            age = 999
    if age > 30:
        _safe(ST.main)
    out = {"genere_le": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "fx": fx,
           "zones": zones, "ofdf": ofdf, "stations_fr": bande,
           "sources": {"france": "Flux officiel des prix des carburants, data.economie.gouv.fr",
                       "suisse": "OFDF, tableau T 4.4 (prix à la colonne en zone frontière)", "change": "BCE"}}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("== essence.json écrit", flush=True)


if __name__ == "__main__":
    main()
