"""Tests des calculs clés (lancés par le robot avant chaque relevé, et à chaque modification du code)."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

from scraper.controles import controler, verifier_ofdf
from scraper.sources import parse_ofdf
from scraper.synthese import MIX, REGLES, calcul, synthese, taux_economie

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

S = {"gaps": {"m": 100.0, "f": 20.0, "c": 50.0, "b": 30.0}, "regles": REGLES, "fx": 0.93,
     "essence": {"sp95_ch": 2.19, "diesel_ch": 2.48, "sp95_fr": 1.98, "diesel_fr": 2.21}, "viande_fr_chf_kg": 25.0}


def test_taux_economie():
    # écart de +100 % : on économise la moitié ; magasin 10 % moins cher : écart ajusté (2 / 0,9 - 1)
    assert taux_economie({"m": 100}, {"m": 1}) == pytest.approx(0.5)
    assert taux_economie({"m": 100}, {"m": 1}, 0.9) == pytest.approx(1 - 0.9 / 2)
    # catégorie manquante : les poids restants sont renormalisés
    assert taux_economie({"m": 100, "c": None}, {"m": .5, "c": .5}) == pytest.approx(0.5)


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
           {"spend": 350, "km": 80, "w": MIX[1]["w"], "idx": 1.05, "persons": 2, "mode": "diesel", "conso": 6, "wear": False},
           {"spend": 120, "km": 30, "w": MIX[3]["w"], "idx": 1.0, "persons": 1, "mode": "ev", "conso": 18, "wear": True},
           {"spend": 90, "km": 12, "w": MIX[2]["w"], "idx": 0.9, "persons": 1, "mode": "tp", "tpCost": 8}]
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
