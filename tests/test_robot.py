"""Tests des calculs clés (lancés par le robot avant chaque relevé, et à chaque modification du code)."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

from scraper.controles import controler, verifier_ofdf
from scraper.sources import parse_ofdf
from scraper.synthese import MAGASINS_CH, MIX, REGLES, calcul, ecarts_officiels, synthese, taux_economie

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- tableau OFDF

def test_ofdf_ordre_essence_diesel():
    o = parse_ofdf((ROOT / "tests/ofdf_2026-10.txt").read_text(encoding="utf-8"))
    assert o["date_texte"] == "20 octobre 2026"
    assert o["sp95"] == {"ch_chf": 2.19, "fr_eur": 2.2}
    assert o["diesel"] == {"ch_chf": 2.48, "fr_eur": 2.4}
    assert set(o["zones"]) == {"bale", "kreuzlingen", "tessin", "geneve", "liechtenstein"}
    # en Suisse, le diesel est plus cher que l'essence dans toutes les zones (octobre 2026)
    assert all(z["diesel"]["ch_chf"] > z["sp95"]["ch_chf"] for z in o["zones"].values())


def test_ofdf_inversion_detectee():
    carb = {"ch": {"sp95": {"ch_chf": 2.48, "fr_eur": 2.40}, "diesel": {"ch_chf": 2.19, "fr_eur": 2.20}},
            "destinations": {"a": {"n": 5, "moyenne": {"sp95": 2.14, "diesel": 2.39}}}}
    rep = {"alertes": [], "reprises": []}
    verifier_ofdf(carb, rep)
    assert carb["ch"]["sp95"]["ch_chf"] == 2.19 and carb["ch"]["inversion_corrigee"]
    assert rep["alertes"]


# ---------------------------------------------------------------- contrôles

def _latest(**kw):
    base = {"genere_le": "2026-11-20", "fx": {"jour": {"eur_chf": 0.93}},
            "viande": [{"id": "veau", "ch": 50.0, "ch_n": 2, "fr_chf": 28.0, "qty": 0.2}],
            "marques": [{"id": "coca", "ch_unit": None, "fr_unit_eur": 1.7, "fr_unit_chf": 1.58, "qty": 1.5}],
            "carburant": {"ch": None, "destinations": {"annemasse": None}},
            "officiel": {"mois": "2026-10"}, "magasins": None, "origines": None}
    base.update(kw)
    return base


def test_reprises_et_alertes():
    prev = {"genere_le": "2026-10-20",
            "viande": [{"id": "veau", "ch": 54.0, "ch_n": 8, "fr_chf": 28.0, "ecart": 92.9}],
            "marques": [{"id": "coca", "ch_unit": 1.6, "ecart": 0}],
            "carburant": {"ch": {"sp95": {"ch_chf": 2.19, "fr_eur": 2.2}, "diesel": {"ch_chf": 2.48, "fr_eur": 2.4}},
                          "destinations": {"annemasse": {"n": 11, "moyenne": {"sp95": 2.14, "diesel": 2.39}}}},
            "magasins": {"panel": {"mediane": 300}, "destinations": []}, "origines": {"liste": []}}
    lat = _latest()
    rep = controler(lat, prev)
    assert lat["viande"][0]["ch"] == 54.0 and lat["viande"][0]["reprise"] == "2026-10-20"
    assert lat["marques"][0]["ch_unit"] == 1.6
    assert lat["carburant"]["ch"]["sp95"]["ch_chf"] == 2.19
    assert lat["carburant"]["destinations"]["annemasse"]["n"] == 11
    assert lat["magasins"]["reprise"] == "2026-10-20" and lat["origines"] == {"liste": []}
    assert len(rep["reprises"]) >= 5


def test_saut_signale():
    prev = {"genere_le": "2026-10-20", "viande": [{"id": "veau", "ch": 50.0, "ch_n": 8, "fr_chf": 28.0, "ecart": 78.6}]}
    lat = _latest(viande=[{"id": "veau", "ch": 70.0, "ch_n": 9, "fr_chf": 28.0, "qty": 0.2}])
    rep = controler(lat, prev)
    assert any("Viande veau" in a for a in rep["alertes"])


# ---------------------------------------------------------------- calcul des économies

S = {"gaps": {"m": 100.0, "f": 20.0, "c": 50.0, "p": 40.0, "b": 30.0}, "regles": REGLES, "fx": 0.93,
     "essence": {"sp95_ch": 2.19, "diesel_ch": 2.48, "sp95_fr": 1.98, "diesel_fr": 2.21}, "viande_fr_chf_kg": 25.0}


def test_taux_economie():
    # écart de +100 % : on économise la moitié ; magasin 10 % moins cher : écart ajusté (2 / 0,9 - 1)
    assert taux_economie({"m": 100}, {"m": 1}) == pytest.approx(0.5)
    assert taux_economie({"m": 100}, {"m": 1}, 0.9) == pytest.approx(1 - 0.9 / 2)
    # catégorie manquante : les poids restants sont renormalisés
    assert taux_economie({"m": 100, "c": None}, {"m": .5, "c": .5}) == pytest.approx(0.5)
    # supermarché suisse moins cher (facteur 0,9) : prix suisse × 0,9, sauf épicerie et boissons
    assert taux_economie({"m": 100}, {"m": 1}, 1.0, 0.9) == pytest.approx(1 - 1 / 1.8)
    assert taux_economie({"b": 100}, {"b": 1}, 1.0, 0.9) == pytest.approx(0.5)


def test_achat_suisse_exclu_du_trajet():
    w = {"m": .5, "b": .5}
    tout = calcul({"spend": 200, "km": 0, "w": w, "idx": 1, "persons": 1, "mode": "essence", "conso": 0}, S)
    malin = calcul({"spend": 200, "km": 0, "w": w, "suisse": ["m"], "idx": 1, "persons": 1, "mode": "essence", "conso": 0}, S)
    assert malin["kept"] == pytest.approx(100) and malin["spend_fr"] == pytest.approx(100)
    assert malin["gross"] < tout["gross"] and malin["duty"] == 0
    rien = calcul({"spend": 200, "km": 10, "w": w, "suisse": ["m", "b"], "idx": 1, "persons": 1, "mode": "essence", "conso": 7}, S)
    assert rien["gross"] == 0 and rien["net"] < 0


def test_facteurs_k_tipp():
    f = {m["id"]: m["f"] for m in MAGASINS_CH}
    assert f["migros"] == 1.0 and f["discount"] == pytest.approx(231.885 / 243.54, abs=1e-3)
    assert f["coop"] == pytest.approx(250.70 / 243.54, abs=1e-3)


def test_ecarts_officiels_change_et_evolution():
    pli = {"annee": "2024", "categories": {c: {"CH": 150.0, "FR": 100.0} for c in
           ("A01010101", "A01010102", "A01010103", "A01010104", "A01010105", "A01010106", "A01010199", "A010102")}}
    # taux moyen 2024 = 0,95 ; aujourd'hui 0,95 ; relevés identiques en 2024 et récemment -> écart officiel inchangé
    rows = [{"m": f"2024-{i:02d}", "ch": 3.0, "fr": 2.0, "fx": 0.95} for i in range(1, 13)]
    series = {"fx": [[r["m"], 0.95] for r in rows], "panier": rows, "cremerie": rows}
    o = ecarts_officiels(pli, series, 0.95)
    assert all(v == pytest.approx(50.0) for v in o["gaps"].values())
    # franc plus fort de 5 % : l'écart augmente d'autant
    o = ecarts_officiels(pli, series, 0.95 / 1.05)
    assert o["gaps"]["m"] == pytest.approx((1.5 * 1.05 - 1) * 100, abs=0.1)
    # prix suisses des fruits et légumes +10 % dans les 12 derniers mois relevés
    rows2 = rows + [{"m": f"2025-{i:02d}", "ch": 3.3, "fr": 2.0, "fx": 0.95} for i in range(1, 13)]
    o = ecarts_officiels(pli, {**series, "panier": rows2}, 0.95)
    assert o["gaps"]["f"] == pytest.approx(65.0, abs=0.1) and o["gaps"]["m"] == pytest.approx(50.0)


def test_calcul_cas_simple():
    p = {"spend": 100, "km": 10, "w": {"m": 1}, "idx": 1, "persons": 1, "mode": "essence", "conso": 10, "wear": False}
    r = calcul(p, S)
    assert r["fr"] == pytest.approx(50)
    assert r["road"] == pytest.approx(2 * 10 * 0.10 * 2.19)
    assert r["vat"] == 0  # 50 CHF < franchise
    assert r["duty"] == pytest.approx(max(0, 50 / 25 - 1) * 17)


def test_tva_au_dela_franchise():
    p = {"spend": 400, "km": 0, "w": {"f": 1}, "idx": 1, "persons": 1, "mode": "essence", "conso": 0}
    r = calcul(p, S)
    assert r["fr"] > 150 and r["vat"] == pytest.approx(r["fr"] * 0.026)
    p["persons"] = 3
    assert calcul(p, S)["vat"] == 0


def test_js_et_python_donnent_le_meme_resultat():
    cas = [{"spend": 200, "km": 42, "minutes": 37, "w": MIX[0]["w"], "idx": 0.96, "persons": 1, "mode": "essence",
            "conso": 7, "wear": True, "fill": False, "card": True},
           {"spend": 350, "km": 80, "w": MIX[0]["w"], "suisse": ["m", "c", "f"], "idx": 1.05, "persons": 2, "mode": "diesel", "conso": 6, "wear": False},
           {"spend": 120, "km": 30, "w": MIX[0]["w"], "suisse": ["m"], "idx": 1.0, "persons": 1, "mode": "ev", "conso": 18, "wear": True, "fch": 0.952},
           {"spend": 260, "km": 25, "w": MIX[0]["w"], "idx": 0.93, "persons": 1, "mode": "essence", "conso": 7, "fch": 1.029},
           {"spend": 90, "km": 12, "w": MIX[0]["w"], "suisse": ["m", "c", "f", "p", "b"], "idx": 0.9, "persons": 1, "mode": "tp", "tpCost": 8}]
    js = ("const P=require('./site/calc.js');const S=" + json.dumps(S) + ";const C=" + json.dumps(cas) +
          ";console.log(JSON.stringify(C.map(c=>P.compute(c,S).net)))")
    out = json.loads(subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    for c, net_js in zip(cas, out):
        assert calcul(c, S)["net"] == pytest.approx(net_js, abs=1e-6)


def test_synthese_sur_les_donnees_publiees():
    latest = json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))
    series = json.loads((ROOT / "data/series.json").read_text(encoding="utf-8"))
    sy = synthese(latest, series)
    assert sy["gaps"]["m"] is not None and sy["gaps"]["m"] > 0
    pli = json.loads((ROOT / "data/pli.json").read_text(encoding="utf-8"))
    sy = synthese(latest, series, pli)
    assert sy["officiel"] and 0 < sy["total"]["economie"] < 60
    assert all(-20 < v < 120 for v in sy["gaps"].values())
    assert abs(sum(MIX[0]["w"].values()) - 1) < 0.01


# ---------------------------------------------------------------- mode « Où faire le plein »

def test_gain_essence_js():
    js = ("const P=require('./site/calc.js');"
          "console.log(JSON.stringify(P.fuelGain({litres:50,conso:7,pref:2.19,wear:true,usure:0.19},{km:5,prix:2.05})))")
    g = json.loads(subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    assert g["fuel"] == pytest.approx(50 * 0.14)
    assert g["drive"] == pytest.approx(2 * 5 * 0.07 * 2.19)
    assert g["wear"] == pytest.approx(2 * 5 * 0.19)
    assert g["net"] == pytest.approx(g["fuel"] - g["drive"] - g["wear"])


def test_stations_prix_perimes_et_releves(tmp_path, monkeypatch):
    import scraper.site as SI
    monkeypatch.setattr(SI, "DATA", tmp_path)
    (tmp_path / "prix_ch.yaml").write_text(
        "releves:\n"
        "  - { station: A, localite: Morges, lat: 46.5, lon: 6.5, sp95: 1.9, date: '2026-10-20', source: test }\n"
        "  - { station: B, localite: Nyon, lat: 46.4, lon: 6.2, sp95: 1.9, date: '2026-01-01', source: test }\n", encoding="utf-8")
    extra = {"essence": {"genere_le": "2026-10-25T05:00+00:00", "stations_fr": [
        {"id": "1", "lat": 46.2, "lon": 6.2, "adresse": "x", "ville": "ANNEMASSE", "sp95": 2.0, "sp95_maj": "2026-10-24T10:00", "diesel": 2.3, "diesel_maj": "2026-09-01T10:00"}]}}
    dests = [{"id": "annemasse", "lat": 46.19, "lon": 6.23}]
    import datetime as _dt
    class D(_dt.date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 25)
    monkeypatch.setattr(SI.dt, "date", D)
    st, zones = SI.donnees_stations(extra, dests, {"zones": {}}, 0.93)
    assert len(st["fr"]) == 1 and st["fr"][0][5] == pytest.approx(1.86) and st["fr"][0][6] is None  # diesel périmé
    assert [x[2] for x in st["ch"]] == ["A"]  # relevé de plus de 45 jours écarté
    assert st["fr"][0][9] == "annemasse"
