"""Chiffres de synthèse partagés par toutes les pages, le calculateur et les images de partage.

Une seule source de vérité : le calculateur (site/calc.js) reçoit ces valeurs telles quelles.
"""
from __future__ import annotations

# Poids des catégories dans « Un peu de tout » : structure des dépenses alimentaires des ménages suisses,
# pondérations de l'indice des prix harmonisé (Eurostat prc_hicp_inw, Suisse, 2025, en pour mille).
#   viande         = viande (CP0112)                                              17,93
#   fruits/légumes = fruits (CP0116) + légumes (CP0117)                           20,57
#   crèmerie       = lait, fromage, œufs (CP0114) + huiles et graisses (CP0115)   18,30
#   épicerie       = pain et céréales, sucre et chocolat, autres, boissons
#                    sans alcool, poisson (CP0111, CP0118, CP0119, CP012, CP0113)  42,92
POIDS_IPCH_CH_2025 = {"m": 17.93, "f": 20.57, "c": 18.30, "b": 42.92}
_tot = sum(POIDS_IPCH_CH_2025.values())
MIX = [
    {"id": "mixte", "label": "Un peu de tout", "w": {k: round(v / _tot, 3) for k, v in POIDS_IPCH_CH_2025.items()}},
    {"id": "viande", "label": "Viande", "w": {"m": .55, "f": .15, "c": .15, "b": .15}},
    {"id": "fl", "label": "Fruits et légumes", "w": {"m": .10, "f": .60, "c": .15, "b": .15}},
    {"id": "cremerie", "label": "Produits laitiers", "w": {"m": .10, "f": .15, "c": .60, "b": .15}},
    {"id": "marques", "label": "Épicerie et marques", "w": {"m": .10, "f": .15, "c": .15, "b": .60}},
]

# Règles et coûts (sources dans METHODOLOGIE.md, section 4 et 5)
REGLES = {
    "franchise_chf": 150,            # OFDF, par personne et par jour
    "tva_alimentaire": 0.026,        # TVA suisse, taux réduit
    "viande_franchise_kg": 1,        # OFDF, par personne et par jour
    "viande_droits": [[10, 17], [None, 23]],   # CHF/kg sur l'excédent : 17 jusqu'à 10 kg, 23 au-delà
    "beurre_franchise_kg": 1, "beurre_droits": 16,
    "huile_franchise_kg": 5, "huile_droits": 2,
    "alcool_bas_franchise_l": 5, "alcool_bas_droits": 2,
    "alcool_haut_franchise_l": 1, "alcool_haut_droits": 15,
    "cigarettes_franchise": 250, "cigarettes_droits": 0.25,
    "usure_chf_km": 0.19,            # TCS 2026 : frais variables 4135 CHF/an pour 15 000 km, moins l'essence (5 L × 1,71 CHF)
    "electricite_chf_kwh": 0.28,     # TCS 2026
    "conso_ev_kwh": 18,              # TCS 2026, kWh/100 km
    "douane_minutes": 15,            # forfait passage de douane et parking, affiché à part
    "frais_carte": 0.015,            # ordre de grandeur des frais de change d'une carte suisse classique
    "tva_fr_alimentaire": 0.055,     # TVA française, taux réduit (détaxe)
    "detaxe_min_eur": 100,           # douane française : plus de 100 € TTC le même jour dans le même magasin
}


def _w(rows, a, b):
    num = sum(r[a] * r["qty"] for r in rows)
    den = sum(r[b] * r["qty"] for r in rows)
    return (num / den - 1) * 100 if den else None


def rolling12(series: list[dict], key: str = "ecart") -> list[float | None]:
    out = []
    for i in range(len(series)):
        w = series[max(0, i - 11): i + 1]
        out.append(round(sum(p[key] for p in w) / 12, 2) if len(w) == 12 else None)
    return out


def synthese(latest: dict, series: dict) -> dict:
    """Écarts Suisse / France (en %) par catégorie, au niveau national, et autres chiffres clés."""
    pan = series.get("panier") or []
    roll = rolling12(pan)
    g_fl = roll[-1] if roll else None
    g_fl_prev = roll[-13] if len(roll) >= 13 else None
    meat = [v for v in latest.get("viande") or [] if v.get("ch") and v.get("fr_chf")]
    g_meat = _w(meat, "ch", "fr_chf") if meat else None
    brands = [v for v in latest.get("marques") or [] if v.get("ch_unit") and v.get("fr_unit_chf")]
    g_brand = _w(brands, "ch_unit", "fr_unit_chf") if brands else None
    crem = series.get("cremerie") or []
    g_crem = crem[-1]["ecart"] if crem else None
    carb = latest.get("carburant") or {}
    ch = carb.get("ch") or {}
    zones = carb.get("destinations") or {}
    fr_sp95 = [z["moyenne_chf"]["sp95"] for z in zones.values() if z and z.get("moyenne_chf", {}).get("sp95")]
    fr_dsl = [z["moyenne_chf"]["diesel"] for z in zones.values() if z and z.get("moyenne_chf", {}).get("diesel")]
    ess = {
        "sp95_ch": (ch.get("sp95") or {}).get("ch_chf"), "diesel_ch": (ch.get("diesel") or {}).get("ch_chf"),
        "sp95_fr": round(sum(fr_sp95) / len(fr_sp95), 3) if fr_sp95 else None,
        "diesel_fr": round(sum(fr_dsl) / len(fr_dsl), 3) if fr_dsl else None,
    }
    for k in ("sp95", "diesel"):
        a, b = ess[f"{k}_ch"], ess[f"{k}_fr"]
        ess[f"{k}_ecart"] = round((a / b - 1) * 100, 1) if a and b else None
    meat_fr_kg = (sum(v["fr_chf"] * v["qty"] for v in meat) / sum(v["qty"] for v in meat)) if meat else 30.0
    return {
        "gaps": {"m": _r(g_meat), "f": _r(g_fl), "c": _r(g_crem), "b": _r(g_brand)},
        "fl_12m_il_y_a_un_an": _r(g_fl_prev), "fl_roll": roll,
        "essence": ess, "viande_fr_chf_kg": round(meat_fr_kg, 2),
        "mix": MIX, "regles": REGLES,
        "fx": (latest.get("fx") or {}).get("jour", {}).get("eur_chf"),
        "mois": latest.get("genere_le"),
    }


def _r(v):
    return None if v is None else round(v, 1)


def taux_economie(gaps: dict, w: dict, idx: float = 1.0) -> float:
    """Part de la dépense suisse économisée en France (même formule que site/calc.js)."""
    tot = sw = 0.0
    for k, wk in w.items():
        g = gaps.get(k)
        if g is None:
            continue
        g_adj = (1 + g / 100) / idx - 1
        tot += wk * (1 - 1 / (1 + g_adj))
        sw += wk
    return tot / sw if sw else 0.0


def calcul(p: dict, S: dict) -> dict:
    """Portage Python de PSF.compute (site/calc.js), pour les pages générées (zones, baromètre).
    Les deux versions sont comparées par les tests (tests/test_calc.py)."""
    R = S["regles"]
    spend, km = max(0.0, p.get("spend", 0)), max(0.0, p.get("km", 0))
    persons = max(1, round(p.get("persons", 1)))
    rate = taux_economie(S["gaps"], p["w"], p.get("idx", 1.0))
    fr = spend * (1 - rate)
    gross = spend - fr
    mode = p.get("mode", "essence")
    car = mode != "tp"
    fuel_ch = S["essence"]["diesel_ch"] if mode == "diesel" else S["essence"]["sp95_ch"]
    if mode == "tp":
        energy = max(0.0, p.get("tpCost", 0))
    elif mode == "ev":
        energy = 2 * km * (p.get("conso") or R["conso_ev_kwh"]) / 100 * R["electricite_chf_kwh"]
    else:
        energy = 2 * km * p.get("conso", 0) / 100 * (fuel_ch or 2.2)
    wear = 2 * km * R["usure_chf_km"] if car and p.get("wear") else 0.0
    lim = R["franchise_chf"] * persons
    vat = fr * R["tva_alimentaire"] if fr > lim else 0.0
    card = fr * R["frais_carte"] if p.get("card") else 0.0
    meat_kg = p["w"].get("m", 0) * fr / S["viande_fr_chf_kg"] if S.get("viande_fr_chf_kg") else 0.0
    excess = max(0.0, meat_kg - R["viande_franchise_kg"] * persons)
    duty, done, rest = 0.0, 0.0, excess
    for up_to, r in R["viande_droits"]:
        cap = float("inf") if up_to is None else up_to - done
        q = min(rest, cap)
        duty += q * r
        rest -= q
        done += q
        if rest <= 0:
            break
    net = gross - energy - wear - vat - card - duty
    return {"rate": rate, "fr": fr, "gross": gross, "road": energy + wear, "vat": vat, "duty": duty, "net": net}
