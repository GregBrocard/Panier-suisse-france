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
    {"id": "marques", "label": "Épicerie et boissons", "w": {"m": .10, "f": .15, "c": .15, "b": .60}},
]

# Où l'on fait ses courses en Suisse : niveau de prix par rapport à la moyenne suisse.
# Test K-Tipp d'août 2025, même panier de 100 produits : Aldi 230,94 CHF, Lidl 232,83, Migros 243,54, Coop 250,70.
# Hypothèse documentée : la moyenne suisse (indice officiel) correspond au niveau Migros.
# S'applique à la viande, aux fruits et légumes et aux produits laitiers ; pas aux produits de marque,
# vendus pratiquement au même prix partout (relevé bonus.ch, août 2025).
MAGASINS_CH = [
    {"id": "discount", "label": "Aldi ou Lidl", "f": round(((230.94 + 232.83) / 2) / 243.54, 3)},
    {"id": "migros", "label": "Migros ou Denner", "f": 1.0},
    {"id": "coop", "label": "Coop", "f": round(250.70 / 243.54, 3)},
]

# Catégories du calculateur et postes de la comparaison officielle des niveaux de prix (Eurostat)
PLI_MAP = {"m": {"A01010102": 17.93},
           "f": {"A01010106": 20.57},
           "c": {"A01010104": 15.80, "A01010105": 2.50},
           "b": {"A01010101": 16.71, "A01010103": 2.81, "A01010199": 14.05, "A010102": 9.35}}

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


def _mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def ecarts_officiels(pli: dict, series: dict, fx_now: float) -> dict:
    """Écart Suisse / France par catégorie (en %), ancré sur la comparaison officielle Eurostat de l'année de
    référence, puis mis à jour : (1) taux de change du jour, (2) évolution relative des prix mesurée par nos relevés
    (fruits et légumes, produits laitiers) depuis l'année de référence. Les autres catégories ne suivent que le change."""
    y = str(pli["annee"])
    fxs = dict(series.get("fx") or [])
    fx_y = _mean([v for m, v in fxs.items() if m.startswith(y)])
    fx_adj = (fx_y / fx_now) if fx_y and fx_now else 1.0

    def ratio_local(rows):  # prix suisse en CHF / prix français en EUR, par mois
        return {r["m"]: r["ch"] * r["fx"] / r["fr"] for r in rows if r.get("fr")}

    def evol(rows, recent_n):
        rl = ratio_local(rows)
        base = _mean([v for m, v in rl.items() if m.startswith(y)])
        recent = [rl[m] for m in sorted(rl)[-recent_n:]]
        now = _mean(recent)
        return (now / base) if base and now and len(recent) == recent_n else 1.0
    ev = {"m": 1.0, "f": evol(series.get("panier") or [], 12), "c": evol(series.get("cremerie") or [], 3), "b": 1.0}
    out, detail = {}, {}
    cats = pli["categories"]
    for k, comp in PLI_MAP.items():
        ch = sum(w * cats[c]["CH"] for c, w in comp.items())
        fr = sum(w * cats[c]["FR"] for c, w in comp.items())
        base = ch / fr - 1
        g = (1 + base) * fx_adj * ev[k] - 1
        out[k] = round(g * 100, 1)
        detail[k] = {"officiel": round(base * 100, 1), "change": round((fx_adj - 1) * 100, 2),
                     "evolution": round((ev[k] - 1) * 100, 1)}
    return {"gaps": out, "detail": detail, "annee": y, "fx_annee": round(fx_y, 4) if fx_y else None}


def synthese(latest: dict, series: dict, pli: dict | None = None) -> dict:
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
    releves = {"m": _r(g_meat), "f": _r(g_fl), "c": _r(g_crem), "b": _r(g_brand)}
    fx_now = (latest.get("fx") or {}).get("jour", {}).get("eur_chf")
    off = ecarts_officiels(pli, series, fx_now) if pli else None
    gaps = off["gaps"] if off else releves
    w = MIX[0]["w"]
    part_fr = sum(w[k] / (1 + gaps[k] / 100) for k in w if gaps.get(k) is not None) / sum(w[k] for k in w if gaps.get(k) is not None)
    return {
        "gaps": gaps, "releves": releves, "officiel": off,
        "total": {"ecart": round((1 / part_fr - 1) * 100, 1), "economie": round((1 - part_fr) * 100, 1)},
        "magasins_ch": MAGASINS_CH,
        "fl_12m_il_y_a_un_an": _r(g_fl_prev), "fl_roll": roll,
        "essence": ess, "viande_fr_chf_kg": round(meat_fr_kg, 2),
        "mix": MIX, "regles": REGLES,
        "fx": (latest.get("fx") or {}).get("jour", {}).get("eur_chf"),
        "mois": latest.get("genere_le"),
    }


def _r(v):
    return None if v is None else round(v, 1)


def taux_economie(gaps: dict, w: dict, idx: float = 1.0, f_ch: float = 1.0) -> float:
    """Part de la dépense suisse économisée en France (même formule que site/calc.js).
    f_ch : niveau de prix du magasin suisse habituel (1 = moyenne), appliqué hors produits de marque."""
    tot = sw = 0.0
    for k, wk in w.items():
        g = gaps.get(k)
        if g is None:
            continue
        g_adj = (1 + g / 100) * (f_ch if k != "b" else 1.0) / idx - 1
        tot += wk * (1 - 1 / (1 + g_adj))
        sw += wk
    return tot / sw if sw else 0.0


def calcul(p: dict, S: dict) -> dict:
    """Portage Python de PSF.compute (site/calc.js), pour les pages générées (zones, baromètre).
    Les deux versions sont comparées par les tests (tests/test_calc.py)."""
    R = S["regles"]
    spend, km = max(0.0, p.get("spend", 0)), max(0.0, p.get("km", 0))
    persons = max(1, round(p.get("persons", 1)))
    rate = taux_economie(S["gaps"], p["w"], p.get("idx", 1.0), p.get("fch", 1.0))
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
    net = gross - energy - wear - vat - card  # droits sur la viande : avertissement seulement, non déduits
    return {"rate": rate, "fr": fr, "gross": gross, "road": energy + wear, "vat": vat, "duty": duty, "net": net}
