"""Contrôles de cohérence du relevé mensuel et valeurs de secours.

Principe : un chiffre manquant ou douteux n'est jamais publié en silence.
  - valeur manquante ou échantillon trop petit : on reprend la valeur du mois précédent, marquée « reprise » ;
  - saut anormal d'un mois à l'autre : publié, mais signalé (alerte) ;
  - incohérence entre deux sources : corrigée si la correction est évidente, sinon signalée.
Le rapport est écrit dans data/controles.json ; le robot ouvre un ticket GitHub s'il contient une alerte.
"""
from __future__ import annotations

import copy

SAUT_POINTS = 15          # variation d'écart (en points) jugée anormale d'un mois à l'autre
MIN_PRODUITS_VIANDE = 5   # nombre minimal de produits Migros pour un morceau de viande
TOLERANCE_OFDF = 0.10     # écart maximal entre le prix français du tableau OFDF et le flux officiel français


def _by_id(rows):
    return {r["id"]: r for r in rows or [] if isinstance(r, dict) and "id" in r}


def controler(latest: dict, prev: dict | None) -> dict:
    """Modifie `latest` en place (reprises) et renvoie le rapport."""
    prev = prev or {}
    rep = {"date": latest.get("genere_le"), "alertes": [], "reprises": []}
    pdate = prev.get("genere_le")

    # ---- viande
    pv = _by_id(prev.get("viande"))
    for v in latest.get("viande") or []:
        old = pv.get(v["id"])
        faible = v.get("ch") is None or (v.get("ch_n") or 0) < MIN_PRODUITS_VIANDE
        if faible and old and old.get("ch"):
            raison = "aucun produit" if v.get("ch") is None else f"{v.get('ch_n')} produits seulement"
            for k in ("ch", "ch_migros", "ch_n", "ch_produits"):
                if k in old:
                    v[k] = old[k]
            v["reprise"] = old.get("reprise") or pdate
            rep["reprises"].append(f"Viande {v['id']} : prix suisse du {v['reprise']} repris ({raison}).")
        elif faible:
            rep["alertes"].append(f"Viande {v['id']} : échantillon Migros insuffisant et pas de valeur précédente.")
        if v.get("ch") and v.get("fr_chf"):
            v["ecart"] = round((v["ch"] / v["fr_chf"] - 1) * 100, 1)
        if old and old.get("ecart") is not None and v.get("ecart") is not None \
                and abs(v["ecart"] - old["ecart"]) > SAUT_POINTS:
            rep["alertes"].append(f"Viande {v['id']} : écart passé de {old['ecart']} % à {v['ecart']} % en un mois.")

    # ---- marques
    pm = _by_id(prev.get("marques"))
    for m in latest.get("marques") or []:
        old = pm.get(m["id"]) or {}
        if m.get("ch_unit") is None and old.get("ch_unit"):
            for k in ("ch_unit", "ch_produit", "ch_url"):
                m[k] = old.get(k)
            m["reprise_ch"] = old.get("reprise_ch") or pdate
            rep["reprises"].append(f"Marque {m['id']} : prix Migros du {m['reprise_ch']} repris.")
        if m.get("fr_unit_eur") is None and old.get("fr_unit_eur"):
            for k in ("fr_unit_eur", "fr_n", "fr_produit", "fr_prix_eur", "fr_depuis", "fenetre_mois"):
                m[k] = old.get(k)
            fx = ((latest.get("fx") or {}).get("jour") or {}).get("eur_chf")
            if fx:
                m["fr_unit_chf"] = round(m["fr_unit_eur"] * fx, 3)
            m["reprise_fr"] = old.get("reprise_fr") or pdate
            rep["reprises"].append(f"Marque {m['id']} : prix Open Prices du {m['reprise_fr']} repris.")
        if m.get("ch_unit") and m.get("fr_unit_chf"):
            m["ecart"] = round((m["ch_unit"] / m["fr_unit_chf"] - 1) * 100, 1)
        if old.get("ecart") is not None and m.get("ecart") is not None and abs(m["ecart"] - old["ecart"]) > SAUT_POINTS:
            rep["alertes"].append(f"Marque {m['id']} : écart passé de {old['ecart']} % à {m['ecart']} % en un mois.")

    # ---- carburant
    carb = latest.get("carburant") or {}
    pcarb = prev.get("carburant") or {}
    if not carb.get("ch") or not (carb["ch"].get("sp95") and carb["ch"].get("diesel")):
        if pcarb.get("ch"):
            carb["ch"] = copy.deepcopy(pcarb["ch"])
            carb["ch"]["reprise"] = pcarb["ch"].get("reprise") or pdate
            rep["reprises"].append("Essence suisse (OFDF) : valeur précédente reprise, tableau illisible.")
        else:
            rep["alertes"].append("Essence suisse (OFDF) : tableau illisible et pas de valeur précédente.")
    zones = carb.get("destinations") or {}
    for zid, z in list(zones.items()):
        if not z or not z.get("n"):
            old = (pcarb.get("destinations") or {}).get(zid)
            if old:
                zones[zid] = copy.deepcopy(old)
                zones[zid]["reprise"] = old.get("reprise") or pdate
                rep["reprises"].append(f"Essence {zid} : stations françaises du {zones[zid]['reprise']} reprises.")
    verifier_ofdf(carb, rep)

    # ---- magasins Que Choisir
    mag, pmag = latest.get("magasins"), prev.get("magasins")
    if not mag and pmag:
        latest["magasins"] = copy.deepcopy(pmag)
        latest["magasins"]["reprise"] = pmag.get("reprise") or pdate
        rep["reprises"].append("Magasins Que Choisir : relevé précédent repris (source inaccessible).")
    elif mag and pmag:
        pn = {d["id"]: len(d.get("magasins") or []) for d in pmag.get("destinations") or []}
        for d in mag.get("destinations") or []:
            n, n0 = len(d.get("magasins") or []), pn.get(d["id"], 0)
            if n0 >= 2 and n < n0 / 2:
                rep["alertes"].append(f"Magasins {d['id']} : {n} magasins au lieu de {n0} le mois précédent.")
        m0 = (pmag.get("panel") or {}).get("mediane")
        m1 = (mag.get("panel") or {}).get("mediane")
        if m0 and m1 and abs(m1 / m0 - 1) > 0.10:
            rep["alertes"].append(f"Que Choisir : médiane du panel passée de {m0} à {m1} € (plus de 10 %).")

    # ---- trajets
    if not latest.get("origines") and prev.get("origines"):
        latest["origines"] = prev["origines"]
        rep["reprises"].append("Trajets : table précédente reprise (calcul d'itinéraires indisponible).")

    # ---- fraîcheur des séries officielles
    mois = (latest.get("officiel") or {}).get("mois")
    if mois and latest.get("genere_le"):
        y, m = map(int, latest["genere_le"][:7].split("-"))
        y0, m0 = map(int, mois.split("-"))
        if (y - y0) * 12 + (m - m0) > 3:
            rep["alertes"].append(f"Fruits et légumes : dernier mois commun OFAG/INSEE = {mois}, plus de 3 mois de retard.")
    return rep


def verifier_ofdf(carb: dict, rep: dict) -> None:
    """Le prix français du tableau OFDF doit être proche de la moyenne du flux officiel français.
    Si l'essence et le diesel semblent inversés, on les remet dans le bon ordre et on le signale."""
    ch = carb.get("ch") or {}
    zones = [z for z in (carb.get("destinations") or {}).values() if z and z.get("moyenne")]
    if not (ch.get("sp95") and ch.get("diesel") and zones):
        return
    feed = {k: [z["moyenne"][k] for z in zones if z["moyenne"].get(k)] for k in ("sp95", "diesel")}
    if not (feed["sp95"] and feed["diesel"]):
        return
    f = {k: sum(v) / len(v) for k, v in feed.items()}
    o = {k: ch[k].get("fr_eur") for k in ("sp95", "diesel")}
    if not (o["sp95"] and o["diesel"]):
        return
    ok = abs(o["sp95"] / f["sp95"] - 1) + abs(o["diesel"] / f["diesel"] - 1)
    swapped = abs(o["diesel"] / f["sp95"] - 1) + abs(o["sp95"] / f["diesel"] - 1)
    if swapped + 0.02 < ok:
        ch["sp95"], ch["diesel"] = ch["diesel"], ch["sp95"]
        ch["inversion_corrigee"] = True
        rep["alertes"].append("OFDF : essence et diesel semblaient inversés dans le tableau ; ordre corrigé automatiquement. "
                              "Vérifier scraper/sources.py (parse_ofdf).")
        o = {k: ch[k].get("fr_eur") for k in ("sp95", "diesel")}
    for k in ("sp95", "diesel"):
        if abs(o[k] / f[k] - 1) > TOLERANCE_OFDF:
            rep["alertes"].append(f"OFDF : prix français {k} du tableau ({o[k]} €) éloigné du flux officiel ({f[k]:.3f} €).")
