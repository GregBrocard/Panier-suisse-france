"""Génère le site public complet (version 2) dans un dossier prêt à publier.

  python -m scraper.site                 -> dist/
  python -m scraper.site --out _site     -> _site/ (publication GitHub Pages)

Pages : calculateur, essence, zones (une page par ville), baromètre (mois courant + archives), douane,
méthodologie, données ouvertes, widget, à propos, mentions légales, confidentialité, 404.
Fichiers : style, scripts, polices, images, images de partage, icônes, manifeste, plan du site, données JSON.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import html
import json
import math
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from .common import ROOT
from .synthese import MIX, calcul, synthese

SITE = ROOT / "site"
DATA = ROOT / "data"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
NAV = [("", "Calculateur", "index"), ("essence/", "Essence", "essence"), ("zones/", "Villes", "zones"),
       ("douane/", "Douane", "douane"), ("barometre/", "Baromètre", "barometre"),
       ("methodologie/", "Méthode", "methodologie")]


# ------------------------------------------------------------------ formats

def nf(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    s = f"{v:,.{d}f}".replace(",", " ").replace(".", ",")
    return s


def pc(v, signe=True):
    if v is None:
        return "—"
    r = round(v)
    return (("+" if r > 0 else "−" if r < 0 else "") if signe else "") + f"{abs(r)} %"


def mois_long(m: str | None) -> str:
    if not m:
        return "—"
    y, mm = m.split("-")[:2]
    return f"{MOIS[int(mm) - 1]} {y}"


def date_longue(d: str) -> str:
    y, m, j = d[:10].split("-")
    return f"{int(j)} {MOIS[int(m) - 1]} {y}"


def e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def pts(v):
    if v is None:
        return ""
    r = round(v, 1)
    return f"{'+' if r > 0 else '−' if r < 0 else '±'}{nf(abs(r), 1)} point{'s' if abs(r) >= 2 else ''}"


# ------------------------------------------------------------------ données

def charger():
    latest = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    series = json.loads((DATA / "series.json").read_text(encoding="utf-8"))
    extra = {}
    for key, path in (("carte", DATA / "carte.json"), ("credits", SITE / "img/credits.json"),
                      ("essence", DATA / "essence.json")):
        if path.exists():
            extra[key] = json.loads(path.read_text(encoding="utf-8"))
    site = yaml.safe_load((ROOT / "config/site.yaml").read_text(encoding="utf-8"))
    site["base_url"] = site["base_url"].rstrip("/")
    return latest, series, extra, site


def essence_effective(latest, extra):
    """Prix des stations françaises : relevé quotidien s'il existe, sinon relevé mensuel."""
    ess = extra.get("essence") or {}
    zones = copy.deepcopy((latest.get("carburant") or {}).get("destinations") or {})
    for zid, z in (ess.get("zones") or {}).items():
        if z and z.get("n"):
            zones[zid] = z
    ch = copy.deepcopy((latest.get("carburant") or {}).get("ch") or {})
    if ess.get("ofdf") and ess["ofdf"].get("sp95") and ess["ofdf"].get("diesel"):
        ch.update({k: ess["ofdf"][k] for k in ("sp95", "diesel", "date_texte", "zones") if k in ess["ofdf"]})
    return zones, ch, ess.get("genere_le")


def public_latest(latest, zones_ess, ch_ess):
    pub = copy.deepcopy(latest)
    for k in ("journal", "origines"):
        pub.pop(k, None)
    carb = pub.get("carburant") or {}
    carb.pop("historique_fr", None)
    carb["destinations"] = {k: ({kk: vv for kk, vv in v.items() if kk != "stations"} if v else v)
                            for k, v in zones_ess.items()}
    carb["ch"] = ch_ess
    if not (pub.get("magasins") or {}).get("publier"):
        pub["magasins"] = None
    return pub


# ------------------------------------------------------------------ images (partage, icônes)

def _font(size, weight="Regular"):
    from PIL import ImageFont
    return ImageFont.truetype(str(ROOT / "scraper/fonts" / f"IBMPlexSans-{weight}.ttf"), size)


def croix(draw, x, y, s):
    draw.rectangle([x, y, x + s, y + s], fill=(218, 41, 28))
    b, l = s * 0.18, s * 0.6
    c = s / 2
    draw.rectangle([x + c - l / 2, y + c - b / 2, x + c + l / 2, y + c + b / 2], fill="white")
    draw.rectangle([x + c - b / 2, y + c - l / 2, x + c + b / 2, y + c + l / 2], fill="white")


def image_partage(path: Path, titre: str, sous_titre: str, chiffres: list[tuple[str, str]]):
    from PIL import Image, ImageDraw
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    croix(d, 64, 60, 56)
    d.text((140, 66), "Panier Suisse France", font=_font(34, "SemiBold"), fill=(23, 23, 23))
    d.text((64, 160), titre, font=_font(58, "Bold"), fill=(23, 23, 23))
    d.text((64, 238), sous_titre, font=_font(30), fill=(79, 79, 79))
    d.line([64, 312, W - 64, 312], fill=(23, 23, 23), width=3)
    n = max(1, len(chiffres))
    col = (W - 128) / n
    for i, (val, lab) in enumerate(chiffres):
        x = 64 + i * col
        d.text((x, 340), val, font=_font(84, "Bold"), fill=(218, 41, 28))
        for j, ligne in enumerate(lab.split("\n")):
            d.text((x, 452 + j * 36), ligne, font=_font(28, "SemiBold" if j == 0 else "Regular"), fill=(23, 23, 23))
    d.text((64, H - 62), "Données publiques, mises à jour chaque mois · gregbrocard.github.io/Panier-suisse-france",
           font=_font(24), fill=(107, 107, 107))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True)


def icones(out: Path):
    from PIL import Image, ImageDraw
    (out / "icon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" '
                                  'fill="#da291c"/><rect x="13" y="6" width="6" height="20" fill="#fff"/><rect x="6" y="13" '
                                  'width="20" height="6" fill="#fff"/></svg>', encoding="utf-8")
    for s in (180, 192, 512):
        im = Image.new("RGB", (s, s), (218, 41, 28))
        croix(ImageDraw.Draw(im), 0, 0, s)
        im.save(out / f"icon-{s}.png", "PNG", optimize=True)


# ------------------------------------------------------------------ contenus des pages

def tableau(entetes, lignes, caption=None):
    h = "<div class=\"tbl\"><table>"
    if caption:
        h += f"<caption>{caption}</caption>"
    h += "<thead><tr>" + "".join(f"<th>{x}</th>" for x in entetes) + "</tr></thead><tbody>"
    h += "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in lignes)
    return h + "</tbody></table></div>"


def kpis(items):
    return "<div class=\"kpis\">" + "".join(
        f"<div class=\"kpi\"><span>{a}</span><b>{b}</b><small>{c}</small></div>" for a, b, c in items) + "</div>"


def textes_synthese(sy, series):
    g = sy["gaps"]
    roll = [r for r in sy["fl_roll"] if r is not None]
    delta = (roll[-1] - roll[-13]) if len(roll) >= 13 else None
    if delta is None:
        titre_fl = "Fruits et légumes : l'écart avec la France"
    elif delta < -1:
        titre_fl = f"Fruits et légumes : l'écart a baissé de {nf(abs(delta), 0)} points en un an"
    elif delta > 1:
        titre_fl = f"Fruits et légumes : l'écart a augmenté de {nf(delta, 0)} points en un an"
    else:
        titre_fl = "Fruits et légumes : l'écart est stable sur un an"
    titre_viande = (f"Viande : {nf(g['m'], 0)} % plus chère en Suisse" if g["m"] is not None and g["m"] > 0
                    else "Viande : l'écart avec la France")
    pan = series.get("panier") or []
    if pan:
        mx = max(pan, key=lambda p: p["ecart"])
        mn = min(pan, key=lambda p: p["ecart"])
        r12 = roll[-1] if roll else None
        resume_fl = ((f"En résumé : sur 12 mois, la Suisse est {nf(abs(r12), 0)} % {'plus' if r12 >= 0 else 'moins'} chère. " if r12 is not None else "")
                     + f"Écart mensuel le plus haut : {pc(mx['ecart'])} en {mois_long(mx['m'])} ; "
                     f"le plus bas : {pc(mn['ecart'])} en {mois_long(mn['m'])}.")
    else:
        resume_fl = ""
    fx = series.get("fx") or []
    if fx:
        hi = max(fx, key=lambda f: f[1])
        resume_fx = (f"En résumé : 1 euro valait {nf(fx[-1][1], 3)} CHF en {mois_long(fx[-1][0])}, "
                     f"contre {nf(hi[1], 3)} CHF au plus haut ({mois_long(hi[0])}). Un franc fort rend la France moins chère.")
    else:
        resume_fx = ""
    return titre_fl, titre_viande, resume_fl, resume_fx


def page_essence(sy, zones, ch, maj, dests, fx):
    ess = sy["essence"]
    rows = []
    for d in dests:
        z = zones.get(d["id"])
        if not z or not z.get("moyenne_chf"):
            continue
        mc = z.get("moins_chers", {}).get("sp95") or []
        best = (f"{e(mc[0].get('adresse'))}, {e(mc[0].get('ville'))}<small>{nf(mc[0]['prix'], 3)} EUR"
                f"{', soit ' + nf(mc[0]['prix'] * fx, 2) + ' CHF' if fx else ''}</small>") if mc else "—"
        gain = (ess["sp95_ch"] - z["moyenne_chf"]["sp95"]) * 50 if ess.get("sp95_ch") and z["moyenne_chf"].get("sp95") else None
        rows.append((f"<a href=\"../zones/{d['id']}/\">{e(d['nom'])}</a>{' <span class=flag>valeur reprise</span>' if z.get('reprise') else ''}<small>{z.get('n', '')} stations</small>",
                     f"{nf(z['moyenne_chf'].get('sp95'))} CHF<small>{nf((z.get('moyenne') or {}).get('sp95'), 3)} EUR</small>",
                     f"{nf(z['moyenne_chf'].get('diesel'))} CHF<small>{nf((z.get('moyenne') or {}).get('diesel'), 3)} EUR</small>",
                     (f"{nf(gain, 0)} CHF" if gain is not None and gain >= 0 else f"−{nf(-gain, 0)} CHF" if gain is not None else "—"),
                     best))
    autres = []
    noms = {"bale": "Bâle / Weil am Rhein (Allemagne)", "kreuzlingen": "Kreuzlingen / Constance (Allemagne)",
            "tessin": "Tessin / Italie", "geneve": "Genève / France", "liechtenstein": "Liechtenstein / Autriche"}
    for zid, z in (ch.get("zones") or {}).items():
        def cell(k):
            v = z.get(k)
            if not v:
                return "—", "—"
            etr_chf = v["etranger_eur"] * fx if fx else None
            diff = (v["ch_chf"] - etr_chf) * 50 if etr_chf else None
            return (f"{nf(v['ch_chf'])} CHF", f"{nf(v['etranger_eur'], 3)} EUR<small>{'soit ' + nf(etr_chf) + ' CHF' if etr_chf else ''}"
                    f"{(', plein de 50 L : ' + nf(diff, 0) + ' CHF de moins') if diff and diff > 0 else ''}</small>")
        a, b = cell("sp95")
        c, d_ = cell("diesel")
        autres.append((noms.get(zid, zid), a, b, c, d_))
    h = f"""<h1>Faire le plein à l'étranger : les prix du jour</h1>
<p class="lede">Prix moyens des stations françaises autour de chaque ville frontalière, relevés chaque jour sur le flux officiel du ministère de l'Économie, convertis au taux de change du jour. Dernière mise à jour : {e(date_longue(maj)) + ' à ' + maj[11:16] + ' (UTC)' if maj else 'mensuelle'}.</p>
{kpis([("Sans plomb 95 en Suisse", nf(ess.get('sp95_ch')) + " CHF", "zone frontière genevoise, OFDF, " + e(ch.get('date_texte') or '')),
       ("Sans plomb 95 en France", nf(ess.get('sp95_fr')) + " CHF", "moyenne des zones frontalières"),
       ("Plein de 50 L", (nf((ess['sp95_ch'] - ess['sp95_fr']) * 50, 0) + " CHF") if ess.get('sp95_ch') and ess.get('sp95_fr') else "—", "économisés en moyenne en France"),
       ("Diesel", pc(ess.get('diesel_ecart')), "Suisse comparée à la France")])}
<h2>Par ville frontalière</h2>
{tableau(["Ville", "Sans plomb 95", "Diesel", "Plein de 50 L (SP95)", "La moins chère (SP95)"], rows)}
<p class="muted">Plein de 50 L : économie par rapport au prix suisse de la zone frontière genevoise, sans compter le trajet. Pour savoir si le détour vaut la peine, utilisez le <a href="../">calculateur</a>.</p>
<h2>Les autres frontières suisses</h2>
<p>Prix à la colonne publiés une fois par mois par l'Office fédéral de la douane et de la sécurité des frontières (OFDF), tableau T 4.4, état du {e(ch.get('date_texte') or '—')}.</p>
{tableau(["Frontière", "SP95 Suisse", "SP95 à l'étranger", "Diesel Suisse", "Diesel à l'étranger"], autres)}
<h2>Bon à savoir</h2>
<ul><li>Le carburant contenu dans le réservoir passe la douane sans formalité. Pour un bidon de réserve, renseignez-vous auprès de l'<a href="https://www.bazg.admin.ch/fr/franchises-quantitatives-denrees-alimentaires-alcool-et-tabac" rel="noopener">OFDF</a>.</li>
<li>Le prix en francs suppose le taux de change officiel de la BCE ; avec une carte suisse classique, comptez environ 1 à 2 % de plus.</li>
<li>Sources : <a href="https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2/" rel="noopener">flux officiel des prix des carburants</a> (France), <a href="https://www.bazg.admin.ch" rel="noopener">OFDF</a> (Suisse et frontières), BCE (change).</li></ul>"""
    return h


def villes_proches(ori, dest_id, n=8):
    from .common import ROOT as _r  # noqa: F401
    big = ["Genève", "Lausanne", "Nyon", "Morges", "Vevey", "Montreux", "Yverdon-les-Bains", "Neuchâtel",
           "La Chaux-de-Fonds", "Le Locle", "Delémont", "Porrentruy", "Basel", "Fribourg", "Bulle", "Sion",
           "Monthey", "Aigle", "Gland", "Rolle", "Carouge", "Vernier", "Meyrin", "Lancy", "Thônex", "Versoix",
           "Vallorbe", "Orbe", "Le Sentier", "Sainte-Croix", "Bern", "Biel/Bienne", "Martigny", "Riehen", "Allschwil"]
    if not ori:
        return []
    k = ori["destinations"].index(dest_id) if dest_id in ori["destinations"] else None
    if k is None:
        return []
    out = []
    for i, (nom, ct, npa) in enumerate(ori["liste"]):
        if nom in big:
            r = ori["dist"][i]
            if r[2 * k] is not None:
                out.append((nom, ct, r[2 * k], r[2 * k + 1]))
    out.sort(key=lambda x: x[3])
    seen, res = set(), []
    for x in out:
        if x[0] in seen:
            continue
        seen.add(x[0])
        res.append(x)
    return res[:n]


def page_zone(d, sy, mag, zone_fuel, ori, magasins_publies):
    idx = (mag or {}).get("indice_median") or 1.0
    w = MIX[0]["w"]
    proches = villes_proches(ori, d["id"])
    lignes = []
    for nom, ct, km, mn in proches:
        r1 = calcul({"spend": 150, "km": km, "w": w, "idx": idx, "persons": 1, "mode": "essence", "conso": 7, "wear": True}, sy)
        r2 = calcul({"spend": 300, "km": km, "w": w, "idx": idx, "persons": 2, "mode": "essence", "conso": 7, "wear": True}, sy)
        f = lambda v: (f"{nf(v, 0)} CHF" if v >= 0 else f"<span class=up>−{nf(-v, 0)} CHF</span>")
        lignes.append((f"{e(nom)} <small>{e(ct)}</small>", f"{km} km<small>{mn} min</small>", f(r1["net"]), f(r2["net"])))
    ms = (mag or {}).get("magasins") or []
    niveau = (lambda i: "dans la moyenne française" if abs(i - 1) < .01 else
              f"{round(abs(i - 1) * 100)} % {'moins cher' if i < 1 else 'plus cher'} qu'un supermarché français moyen")
    pas = d.get('passage') or ''
    lede = f"{e(pas[:1].upper() + pas[1:])}."
    if magasins_publies and ms:
        lede += f" {len(ms)} supermarché{'s' if len(ms) > 1 else ''} référencé{'s' if len(ms) > 1 else ''} : au milieu du classement, {niveau(idx)}."
    h = f"""<h1>Faire ses courses à {e(d['nom'])} depuis la Suisse</h1>
<p class="lede">{lede}</p>
<p><a class="btn" href="../../?a={e(d['id'])}">Calculer depuis ma ville</a></p>
<h2>Combien on économise, depuis les villes proches</h2>
<p>Pour des courses « un peu de tout », en voiture à essence (7 L/100 km), usure comprise, au niveau de prix du magasin du milieu. Le temps de trajet n'est pas déduit.</p>
{tableau(["Départ", "Trajet", "150 CHF, 1 adulte", "300 CHF, 2 adultes"], lignes) if lignes else '<p class="muted">Distances indisponibles.</p>'}"""
    if magasins_publies and ms:
        h += "<h2>Les supermarchés</h2>" + tableau(
            ["Magasin", "Niveau de prix"],
            [(f"<a href=\"{e(m.get('url'))}\" rel=\"noopener\">{e(m['nom'])}</a><small>{e(m.get('adresse') or m.get('cp') or '')}</small>", niveau(m["indice"]))
             for m in ms])
        h += ("<p class=\"muted\">Niveau de prix : panier d'une centaine de produits relevé par l'UFC-Que Choisir, comparé au "
              "supermarché français du milieu d'un échantillon national. <a href=\"../../methodologie/\">Méthode</a>.</p>")
    if zone_fuel and zone_fuel.get("moyenne_chf"):
        mc = (zone_fuel.get("moins_chers") or {}).get("sp95") or []
        h += f"""<h2>Essence</h2>
<p>Sans plomb 95 : {nf(zone_fuel['moyenne_chf'].get('sp95'))} CHF le litre en moyenne ({zone_fuel.get('n')} stations), diesel : {nf(zone_fuel['moyenne_chf'].get('diesel'))} CHF. En Suisse (zone frontière genevoise) : {nf(sy['essence'].get('sp95_ch'))} CHF.</p>"""
        if mc:
            h += "<ul>" + "".join(f"<li>{e(s.get('adresse'))}, {e(s.get('ville'))} : {nf(s['prix'], 3)} EUR</li>" for s in mc) + "</ul>"
        h += "<p><a href=\"../../essence/\">Toutes les villes</a></p>"
    return h


def page_zones_index(dests, mags, zones_fuel, magasins_publies):
    rows = []
    for d in dests:
        m = mags.get(d["id"]) or {}
        z = zones_fuel.get(d["id"]) or {}
        rows.append((f"<a href=\"{d['id']}/\">{e(d['nom'])}</a>", e(d.get("passage") or ""),
                     str(len(m.get("magasins") or [])) if magasins_publies else "—",
                     (pc((m.get("indice_median") - 1) * 100) if m.get("indice_median") and magasins_publies else "—"),
                     f"{nf((z.get('moyenne_chf') or {}).get('sp95'))} CHF"))
    return ("<h1>Les villes françaises où les Suisses font leurs courses</h1>"
            "<p class=\"lede\">Douze zones frontalières, de Saint-Louis à Évian. Pour chacune : les supermarchés et leur niveau de prix, l'essence du jour et l'économie depuis les villes suisses proches.</p>"
            + tableau(["Ville", "Passage", "Supermarchés", "Niveau de prix (vs moyenne française)", "SP95 du jour"], rows))


def snapshot_barometre(sy, latest):
    return {"mois": latest["genere_le"][:7], "date": latest["genere_le"], "gaps": sy["gaps"],
            "essence": sy["essence"], "fx": sy["fx"], "fl_12m_il_y_a_un_an": sy["fl_12m_il_y_a_un_an"]}


def page_barometre(snap, prev, archives, base_url, courant=True):
    g, p = snap["gaps"], (prev or {}).get("gaps") or {}
    var = lambda k: (f"{pts(g[k] - p[k])} sur un mois" if g.get(k) is not None and p.get(k) is not None else "")
    ess = snap["essence"]
    mois = mois_long(snap["mois"])
    plein = (ess["sp95_ch"] - ess["sp95_fr"]) * 50 if ess.get("sp95_ch") and ess.get("sp95_fr") else None
    k = kpis([("Viande", pc(g.get("m")), "plus cher en Suisse " + var("m")),
              ("Fruits et légumes", pc(g.get("f")), "moyenne sur 12 mois " + var("f")),
              ("Produits laitiers", pc(g.get("c")), "estimation " + var("c")),
              ("Mêmes marques", pc(g.get("b")), "prix unitaires " + var("b")),
              ("Plein de 50 L", nf(plein, 0) + " CHF" if plein else "—", "économisés en France (SP95)"),
              ("1 euro", nf(snap.get("fx"), 4) + " CHF", "taux BCE")])
    fl_an = snap.get("fl_12m_il_y_a_un_an")
    pm = lambda v, mot="chère": f"{nf(abs(v), 0)} % {'plus' if v >= 0 else 'moins'} {mot}"
    phrases = []
    if g.get("m") is not None:
        phrases.append(f"La viande reste le poste où l'écart est le plus fort : {pm(g['m'])} en Suisse qu'en France, pour les mêmes morceaux.")
    if g.get("f") is not None:
        s = (f"Pour les fruits et légumes, la Suisse est en moyenne {pm(g['f'])} que la France sur les douze derniers mois"
             if abs(g["f"]) >= 0.5 else "Pour les fruits et légumes, les prix sont presque au même niveau des deux côtés sur les douze derniers mois")
        if fl_an is not None:
            s += f", contre {'+' if fl_an > 0 else '−' if fl_an < 0 else ''}{nf(abs(fl_an), 0)} % un an plus tôt"
        phrases.append(s + ".")
    if g.get("c") is not None:
        phrases.append(f"Les produits laitiers sont environ {pm(g['c'], 'chers')} en Suisse (estimation).")
    if g.get("b") is not None:
        phrases.append(f"Pour des produits de marque strictement identiques, la Suisse est en moyenne {pm(g['b'])}.")
    if plein:
        phrases.append(f"À la pompe, un plein de 50 litres de sans plomb coûte environ {nf(plein, 0)} francs de moins côté français.")
    texte = " ".join(phrases)
    cite = (f"Panier Suisse France, baromètre de {mois}, d'après les données de l'OFAG, de l'INSEE, d'Open Prices, "
            f"de l'OFDF et de la BCE. {base_url}/barometre/{snap['mois']}/")
    h = f"""<h1>Baromètre des prix Suisse – France : {mois}</h1>
<p class="lede">Chaque mois, les mêmes courses comparées des deux côtés de la frontière, tout en francs suisses. Publié le {date_longue(snap['date'])}.</p>
{k}
<h2>Ce qu'il faut retenir</h2>
<p>{e(texte)}</p>
<h2>Texte prêt à reprendre</h2>
<div class="note"><p id="txt">{e(texte)} Source : {e(cite)}</p><p style="margin-top:10px"><button type="button" class="btn ghost" id="copy">Copier le texte</button> <span class="muted" id="copied" aria-live="polite"></span></p></div>
<h2>Citer</h2>
<p class="quote">{e(cite)}</p>
<p><a href="../{'' if courant else '../'}og/barometre-{snap['mois']}.png" download>Télécharger l'image du mois</a> · <a href="../{'' if courant else '../'}donnees/">Données ouvertes</a> · <a href="../{'' if courant else '../'}methodologie/">Méthodologie</a></p>
<h2>Les mois précédents</h2>
<ul>{''.join(f'<li><a href="../{"" if courant else "../"}barometre/{m}/">{mois_long(m)}</a></li>' for m in archives) or '<li>Premier baromètre.</li>'}</ul>"""
    return h


SCRIPT_COPY = """document.getElementById('copy')&&document.getElementById('copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(document.getElementById('txt').textContent);document.getElementById('copied').textContent='Texte copié.';}catch(e){document.getElementById('copied').textContent='Sélectionnez le texte pour le copier.';}});"""


def page_douane(regles):
    R = regles
    h = f"""<h1>Douane : ce que vous pouvez ramener de France</h1>
<p class="lede">Règles de l'Office fédéral de la douane et de la sécurité des frontières (OFDF) pour les achats privés, par personne et par jour. Entrez vos achats : le calcul donne la TVA et les droits à payer.</p>
<div class="grid2"><div class="form" id="dz">
  <div class="row"><label for="dPers">Adultes (17 ans et plus)</label><input id="dPers" type="number" min="1" max="9" value="1"></div>
  <div class="row"><label for="dTot">Montant total des achats<small>en CHF, tout compris</small></label><input id="dTot" type="number" min="0" step="10" value="200"></div>
  <div class="row"><label for="dViande">Viande et préparations de viande<small>en kg, sans le gibier</small></label><input id="dViande" type="number" min="0" step="0.1" value="0"></div>
  <div class="row"><label for="dBeurre">Beurre et crème<small>en kg ou en litres</small></label><input id="dBeurre" type="number" min="0" step="0.1" value="0"></div>
  <div class="row"><label for="dHuile">Huiles, graisses, margarine<small>en kg ou en litres</small></label><input id="dHuile" type="number" min="0" step="0.5" value="0"></div>
  <div class="row"><label for="dAlc1">Boissons alcoolisées jusqu'à 18 % vol.<small>en litres (vin, bière)</small></label><input id="dAlc1" type="number" min="0" step="0.5" value="0"></div>
  <div class="row"><label for="dAlc2">Boissons alcoolisées de plus de 18 % vol.<small>en litres</small></label><input id="dAlc2" type="number" min="0" step="0.1" value="0"></div>
  <div class="row"><label for="dCig">Cigarettes<small>nombre de pièces</small></label><input id="dCig" type="number" min="0" step="20" value="0"></div>
</div>
<div><div class="bill" id="dOut" aria-live="polite"></div></div></div>
<h2>Les règles</h2>
{tableau(["Marchandise", "En franchise, par personne et par jour", "Au-delà"], [
    ("Valeur totale des achats", f"{R['franchise_chf']} CHF", f"TVA suisse sur tout le montant ({nf(R['tva_alimentaire'] * 100, 1)} % pour l'alimentation, 8,1 % pour le reste)"),
    ("Viande et préparations de viande (sans le gibier)", f"{R['viande_franchise_kg']} kg", "17 CHF/kg jusqu'à 10 kg, 23 CHF/kg au-delà"),
    ("Beurre et crème", "1 kg ou 1 L", "16 CHF par kg ou litre"),
    ("Huiles, graisses, margarine", "5 kg ou 5 L", "2 CHF par kg ou litre"),
    ("Boissons jusqu'à 18 % vol.", "5 L", "2 CHF par litre"),
    ("Boissons de plus de 18 % vol.", "1 L", "15 CHF par litre"),
    ("Cigarettes, cigares (ou 250 g d'autres tabacs)", "250 pièces", "0,25 CHF par pièce")])}
<p class="muted">Source : OFDF, <a href="https://www.bazg.admin.ch/dam/fr/sd-web/Mv9dMMMmYzCG/Info-Zoll-Wertfreigrenze-Freimengen_f.pdf" rel="noopener">Info douane, franchises de valeur et quantitatives</a>. Information indicative : en cas de doute, la règle officielle fait foi. Les franchises par personne ne se cumulent pas sur plusieurs jours.</p>
<h2>Déclarer et payer sans attendre</h2>
<p>L'application officielle <b>QuickZoll</b> de l'OFDF permet de déclarer ses achats et de payer la TVA ou les droits sur son téléphone avant de passer la frontière.</p>
<h2>La détaxe : se faire rembourser la TVA française</h2>
<ul><li>Pour les personnes qui habitent hors de l'Union européenne, donc en Suisse, et de passage en France.</li>
<li>Plus de 100 € d'achats TTC le même jour dans le même magasin ; le magasin doit proposer la détaxe et établir un bordereau.</li>
<li>À la sortie de France, faites valider le bordereau à une borne PABLO avant de passer la douane suisse, avec les marchandises.</li>
<li>La TVA française sur l'alimentation est de 5,5 % ; le remboursement est fait par le magasin ou un opérateur, qui garde souvent une partie en frais.</li>
<li>Après la détaxe, les règles suisses ci-dessus s'appliquent normalement.</li></ul>
<p class="muted">Source : <a href="https://www.douane.gouv.fr/articles/a10805-detaxe-presentation-de-pablo" rel="noopener">douane française, la détaxe avec PABLO</a>.</p>"""
    script = """(function(){const R=%s;const $=s=>document.getElementById(s);const nf=(v,d=2)=>v.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).replace(/[\\u202f\\u00a0]/g,'\\u2009');
function tiers(x,t){let r=Math.max(0,x),done=0,s=0;for(const [u,rate] of t){const cap=u==null?Infinity:u-done;const q=Math.min(r,cap);s+=q*rate;r-=q;done+=q;if(r<=0)break;}return s;}
function upd(){const p=Math.max(1,+$('dPers').value||1),tot=+$('dTot').value||0;const rows=[];let sum=0;
const add=(lab,v)=>{if(v>0){rows.push([lab,v]);sum+=v;}};
add('TVA suisse ('+nf(R.tva_alimentaire*100,1)+' %% sur tout, alimentation)', tot>R.franchise_chf*p?tot*R.tva_alimentaire:0);
add('Viande', tiers((+$('dViande').value||0)-R.viande_franchise_kg*p, R.viande_droits));
add('Beurre et crème', Math.max(0,(+$('dBeurre').value||0)-R.beurre_franchise_kg*p)*R.beurre_droits);
add('Huiles et graisses', Math.max(0,(+$('dHuile').value||0)-R.huile_franchise_kg*p)*R.huile_droits);
add('Alcool jusqu\\'à 18 %%', Math.max(0,(+$('dAlc1').value||0)-R.alcool_bas_franchise_l*p)*R.alcool_bas_droits);
add('Alcool de plus de 18 %%', Math.max(0,(+$('dAlc2').value||0)-R.alcool_haut_franchise_l*p)*R.alcool_haut_droits);
add('Cigarettes', Math.max(0,(+$('dCig').value||0)-R.cigarettes_franchise*p)*R.cigarettes_droits);
const r=(a,b,c='')=>`<div class="r ${c}"><span>${a}</span><span>${b}</span></div>`;
$('dOut').innerHTML=(rows.length?rows.map(x=>r(x[0],nf(x[1])+' CHF')).join(''):r('Rien à payer','0 CHF'))+r('Total à payer à la douane',nf(sum)+' CHF','t')+`<p class="muted">Franchise de valeur pour ${p} adulte${p>1?'s':''} : ${nf(R.franchise_chf*p,0)} CHF. Au-delà, déclarez vos achats (passage rouge ou QuickZoll).</p>`;}
document.querySelectorAll('#dz input').forEach(i=>i.addEventListener('input',upd));upd();})();""" % json.dumps(R)
    return h, script


def page_widget(base_url):
    code = f'<iframe src="{base_url}/?embed=1" title="Calculateur Panier Suisse France" width="100%" height="1150" style="border:0;max-width:1100px" loading="lazy"></iframe>'
    return f"""<h1>Intégrer le calculateur sur votre site</h1>
<p class="lede">Médias, blogs, associations de frontaliers, communes : vous pouvez afficher le calculateur dans vos pages, gratuitement. Il se met à jour tout seul chaque mois.</p>
<h2>Code à copier</h2>
<pre>{e(code)}</pre>
<p>Le calculateur intégré affiche le formulaire et le résultat, avec un lien vers ce site. Merci de ne pas masquer ce lien.</p>
<h2>Aperçu</h2>
<p><a href="../?embed=1">Voir le calculateur tel qu'il apparaît une fois intégré</a>.</p>
<h2>Reprendre les chiffres</h2>
<p>Les chiffres du <a href="../barometre/">baromètre mensuel</a> peuvent être cités librement avec la mention « Panier Suisse France » et un lien. Les données sont disponibles en <a href="../donnees/">format ouvert</a>.</p>"""


def page_donnees(controles, magasins_publies):
    fichiers = [("data/latest.json", "Photo du mois : tous les prix, écarts, magasins, essence, contrôles"),
                ("data/series.json", "Historique mensuel : écarts fruits et légumes depuis 2006, crèmerie, change, prix par produit"),
                ("data/essence.json", "Essence : prix du jour par zone et stations les moins chères"),
                ("data/origines.json", "Distances et durées de trajet de 4 100 localités suisses vers chaque ville française"),
                ("data/controles.json", "Rapport des contrôles automatiques du dernier relevé")]
    al = controles.get("alertes") or []
    rp = controles.get("reprises") or []
    return f"""<h1>Données ouvertes</h1>
<p class="lede">Tous les chiffres du site sont publiés en fichiers JSON, mis à jour à chaque relevé. Les calculs et l'historique produits par ce projet peuvent être réutilisés librement en citant « Panier Suisse France » (licence Creative Commons BY 4.0).</p>
{tableau(["Fichier", "Contenu"], [(f'<a href="../{f}">{f}</a>', d) for f, d in fichiers])}
<p class="muted">Les données d'origine restent soumises aux conditions de leurs producteurs (OFAG, INSEE, Eurostat, BCE, OFDF : données publiques ; Open Prices et OpenStreetMap : licence ODbL{'; UFC-Que Choisir : droits réservés, reproduction soumise à leur accord' if magasins_publies else ''}). Code source et historique complet sur <a href="https://github.com/GregBrocard/Panier-suisse-france" rel="noopener">GitHub</a>.</p>
<h2>Contrôles du dernier relevé</h2>
<p>À chaque relevé, le robot vérifie les chiffres. Une valeur manquante ou un échantillon trop petit est remplacé par la valeur du mois précédent, signalée sur le site ; un saut anormal est publié mais signalé.</p>
<ul>{''.join(f'<li>{e(x)}</li>' for x in rp) or '<li>Aucune valeur reprise ce mois-ci.</li>'}</ul>
<ul>{''.join(f'<li>Alerte : {e(x)}</li>' for x in al) or '<li>Aucune alerte.</li>'}</ul>"""


def page_apropos():
    return """<h1>À propos</h1>
<p class="lede">Panier Suisse France est un projet indépendant qui répond à une question simple : faire ses courses en France, ça vaut le coup, une fois le trajet, la douane et l'essence comptés ?</p>
<h2>Pourquoi ce site</h2>
<p>Les comparaisons de prix entre la Suisse et la France reviennent souvent, mais elles sont rarement mises à jour et ne disent pas combien il reste une fois le trajet payé. Ce site recalcule tout, chaque mois, à partir de sources publiques, et donne un résultat personnel : depuis votre localité, vers la ville et le magasin de votre choix.</p>
<h2>Indépendance</h2>
<ul><li>Aucun lien commercial avec les enseignes comparées, suisses ou françaises.</li>
<li>Les chiffres viennent de sources publiques et vérifiables ; la méthode est publiée en entier.</li>
<li>Si le site affiche un jour de la publicité ou des liens rémunérés, ils seront signalés comme tels et n'influenceront aucun chiffre.</li></ul>
<h2>Qui</h2>
<p>Le projet est conçu et publié par Greg Brocard, en Suisse romande. Le code et les données sont ouverts.</p>
<h2>Contact</h2>
<p>Une erreur, une ville à ajouter, une question de journaliste : <a href="https://github.com/GregBrocard/Panier-suisse-france/issues" rel="noopener">écrivez-nous</a>.</p>"""


def page_mentions(site):
    contact = (f'<a href="mailto:{e(site["contact_email"])}">{e(site["contact_email"])}</a>' if site.get("contact_email")
               else f'<a href="{e(site["contact_url"])}" rel="noopener">formulaire de contact (GitHub)</a>')
    return f"""<h1>Mentions légales</h1>
<h2>Éditeur</h2>
<p>{e(site['editeur'])}, Suisse. Contact : {contact}.</p>
<h2>Hébergement</h2>
<p>GitHub Pages, GitHub Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p>
<h2>Responsabilité</h2>
<p>Les chiffres sont calculés automatiquement à partir de sources publiques et sont fournis à titre indicatif. Ils ne remplacent ni les prix affichés en magasin ni les règles officielles de la douane. Malgré les contrôles automatiques, des erreurs restent possibles : elles peuvent être signalées via le contact ci-dessus.</p>
<h2>Sources et droits</h2>
<p>Données de l'OFAG, de l'INSEE, d'Eurostat, de la BCE, de l'OFDF et de swisstopo ; Open Prices (Open Food Facts) et OpenStreetMap sous licence ODbL ; comparateur des supermarchés de l'UFC-Que Choisir (droits réservés à l'UFC-Que Choisir) ; photos de Wikimedia Commons (auteurs et licences indiqués sous chaque photo) ; police IBM Plex Sans (licence SIL OFL) ; Chart.js (licence MIT). Les calculs et textes propres au site sont publiés sous licence Creative Commons BY 4.0.</p>"""


def page_confidentialite(site):
    stats = ("Le site mesure son audience avec GoatCounter, un outil sans cookies qui ne suit pas les visiteurs d'un site à l'autre et ne conserve pas les adresses IP. "
             if site.get("goatcounter") else "Le site ne mesure pas son audience et n'utilise aucun outil de statistiques. ")
    return f"""<h1>Confidentialité</h1>
<p class="lede">Ce site ne demande aucune donnée personnelle et ne dépose aucun cookie.</p>
<h2>Ce qui reste sur votre appareil</h2>
<p>Pour vous éviter de tout ressaisir, vos derniers réglages du calculateur (localité, ville, montant, options) sont gardés dans la mémoire de votre navigateur, sur votre appareil uniquement. Ils ne sont jamais envoyés au site. Vous pouvez les effacer en vidant les données du site dans votre navigateur.</p>
<h2>Mesure d'audience</h2>
<p>{stats}</p>
<h2>Hébergement</h2>
<p>Le site est servi par GitHub Pages, qui enregistre comme tout hébergeur des journaux techniques (adresse IP, date) pour assurer la sécurité du service. Les polices et les scripts sont hébergés sur le site lui-même : aucun service tiers n'est appelé quand vous le consultez.</p>
<h2>Lien de partage</h2>
<p>Le bouton « Partager ce calcul » crée un lien qui contient votre localité, la ville choisie et le montant. Ce lien n'est envoyé à personne sans votre action.</p>
<h2>Contact</h2>
<p>Pour toute question : <a href="{e(site['contact_url'])}" rel="noopener">contact</a>. Cadre légal : loi fédérale sur la protection des données (LPD).</p>"""


def page_methodologie():
    import markdown
    md = (ROOT / "METHODOLOGIE.md").read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["tables"])
    body = body.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    return body + '<p><a href="../METHODOLOGIE.md">Version texte (Markdown)</a> · <a href="../v1/">Version 1 du site (archive)</a></p>'


# ------------------------------------------------------------------ main

def main(out: Path):
    latest, series, extra, site = charger()
    pcfg = yaml.safe_load((ROOT / "config/panier.yaml").read_text(encoding="utf-8"))
    zones_ess, ch_ess, maj_ess = essence_effective(latest, extra)
    lat2 = copy.deepcopy(latest)
    lat2.setdefault("carburant", {})["destinations"] = zones_ess
    lat2["carburant"]["ch"] = ch_ess
    sy = synthese(lat2, series)
    pub = public_latest(latest, zones_ess, ch_ess)
    publies = bool(pub.get("magasins"))
    version = latest.get("genere_le", "").replace("-", "") + (maj_ess or "")[:10].replace("-", "")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    # fichiers statiques
    shutil.copy(SITE / "base.css", out / "style.css")
    for f in ("calc.js", "app.js"):
        shutil.copy(SITE / f, out / f)
    for d in ("fonts", "img", "vendor", "v1"):
        if (SITE / d).exists():
            shutil.copytree(SITE / d, out / d)
    shutil.copy(ROOT / "METHODOLOGIE.md", out / "METHODOLOGIE.md")
    (out / "data").mkdir()
    (out / "data/latest.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copy(DATA / "series.json", out / "data/series.json")
    if latest.get("origines"):
        (out / "data/origines.json").write_text(json.dumps(latest["origines"], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for f in ("essence.json", "controles.json"):
        if (DATA / f).exists():
            shutil.copy(DATA / f, out / "data" / f)

    # baromètre : archive mensuelle (dans data/, versionnée par le robot)
    bdir = DATA / "barometre"
    bdir.mkdir(exist_ok=True)
    snap = snapshot_barometre(sy, latest)
    (bdir / f"{snap['mois']}.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    snaps = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(bdir.glob("*.json"))}
    mois_list = sorted(snaps)

    env = Environment(loader=FileSystemLoader(SITE / "templates"), autoescape=False)
    common = {"site": site, "nav": NAV, "version": version, "basket_version": pcfg.get("basket_version")}
    pages = []

    def render(tpl, path, depth, title, description, active=None, **kw):
        root = "../" * depth
        h = env.get_template(tpl).render(**common, root=root, path=path, title=title, description=description,
                                          active=active, **kw)
        dest = out / path / "index.html" if path else out / "index.html"
        if path.endswith(".html"):
            dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(h, encoding="utf-8")
        if not path.endswith(".html"):
            pages.append(path)

    # page principale
    gen = latest.get("genere_le")
    nx = dt.date.fromisoformat(gen)
    nxt = (nx.replace(day=20) if nx.day < 20 else (nx.replace(day=1) + dt.timedelta(days=32)).replace(day=20))
    upd = (f"Prix mis à jour automatiquement le 20 de chaque mois, essence chaque jour. Dernière mise à jour : "
           f"{date_longue(gen)}. Prochaine : {nxt.day} {MOIS[nxt.month - 1]}.")
    titre_fl, titre_viande, resume_fl, resume_fx = textes_synthese(sy, series)
    payload = {"latest": pub, "series": series, "carte": extra.get("carte"), "credits": extra.get("credits"),
               "essence": {"zones": zones_ess, "genere_le": maj_ess}, "synth": sy, "root": ""}
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    g = sy["gaps"]
    desc = (f"Combien économisez-vous en faisant vos courses en France ? Calcul personnel depuis votre localité : prix du "
            f"magasin, trajet, douane. Ce mois-ci : viande {pc(g['m'])}, fruits et légumes {pc(g['f'])} plus chers en Suisse.")
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": site["nom"], "url": site["base_url"] + "/",
                         "inLanguage": "fr-CH", "description": desc}, ensure_ascii=False)
    render("index.html", "", 0, "Faire ses courses en France, ça vaut le coup ? | Panier Suisse France", desc, "index",
           data_json=data_json, upd_text=upd, titre_fl=titre_fl, titre_viande=titre_viande, resume_fl=resume_fl,
           resume_fx=resume_fx, regles=sy["regles"], jsonld=jsonld,
           og_title="Faire ses courses en France, ça vaut le coup ?")

    dests = latest.get("destinations") or []
    mags = {d["id"]: d for d in ((pub.get("magasins") or {}).get("destinations") or [])}
    fx_now = sy["fx"]
    render("page.html", "essence/", 1, "Prix de l'essence aux frontières suisses aujourd'hui | Panier Suisse France",
           "Prix du jour du sans plomb et du diesel dans les stations françaises près de la Suisse, et aux autres frontières, comparés au prix suisse.",
           "essence", content=page_essence(sy, zones_ess, ch_ess, maj_ess, dests, fx_now), wide=True)
    render("page.html", "zones/", 1, "Les villes françaises où les Suisses font leurs courses | Panier Suisse France",
           "Annemasse, Saint-Julien, Pontarlier, Saint-Louis… Supermarchés, essence et économie depuis la Suisse, ville par ville.",
           "zones", content=page_zones_index(dests, mags, zones_ess, publies), wide=True)
    for d in dests:
        render("page.html", f"zones/{d['id']}/", 2, f"Faire ses courses à {d['nom']} depuis la Suisse | Panier Suisse France",
               f"Supermarchés de {d['nom']} et leur niveau de prix, essence du jour, économie depuis les villes suisses proches.",
               "zones", content=page_zone(d, sy, mags.get(d["id"]), zones_ess.get(d["id"]), latest.get("origines"), publies), wide=True)
    # baromètre courant + archives
    for i, m in enumerate(mois_list):
        prev = snaps[mois_list[i - 1]] if i > 0 else None
        image_partage(out / "og" / f"barometre-{m}.png", f"Baromètre de {mois_long(m)}", "Les mêmes courses en Suisse et en France",
                      [(pc(snaps[m]["gaps"].get("m")), "Viande\nplus cher en Suisse"),
                       (pc(snaps[m]["gaps"].get("f")), "Fruits et légumes\nsur 12 mois"),
                       (pc(snaps[m]["gaps"].get("b")), "Mêmes marques\nprix unitaires")])
        others = [x for x in reversed(mois_list) if x != m]
        render("page.html", f"barometre/{m}/", 2, f"Baromètre des prix Suisse – France, {mois_long(m)} | Panier Suisse France",
               f"Écarts de prix entre la Suisse et la France en {mois_long(m)} : viande, fruits et légumes, produits laitiers, marques, essence.",
               "barometre", content=page_barometre(snaps[m], prev, others, site["base_url"], courant=False), script=SCRIPT_COPY,
               og_image=f"og/barometre-{m}.png")
    last = mois_list[-1]
    render("page.html", "barometre/", 1, f"Baromètre des prix Suisse – France, {mois_long(last)} | Panier Suisse France",
           f"Chaque mois, les mêmes courses comparées en Suisse et en France. {mois_long(last).capitalize()} : viande {pc(g['m'])}, fruits et légumes {pc(g['f'])}.",
           "barometre", content=page_barometre(snaps[last], snaps[mois_list[-2]] if len(mois_list) > 1 else None,
                                               [x for x in reversed(mois_list) if x != last], site["base_url"]),
           script=SCRIPT_COPY, og_image=f"og/barometre-{last}.png")
    h, sc = page_douane(sy["regles"])
    render("page.html", "douane/", 1, "Douane suisse : franchises, TVA et détaxe pour les achats en France | Panier Suisse France",
           "Combien de viande, d'alcool et de tabac peut-on ramener de France ? Calcul de la TVA et des droits de douane, et mode d'emploi de la détaxe.",
           "douane", content=h, script=sc)
    render("page.html", "methodologie/", 1, "Méthodologie | Panier Suisse France",
           "Sources, calculs et limites du comparateur de prix Suisse – France.", "methodologie", content=page_methodologie())
    render("page.html", "donnees/", 1, "Données ouvertes | Panier Suisse France",
           "Tous les prix et écarts Suisse – France en fichiers JSON, mis à jour chaque mois.", None,
           content=page_donnees(latest.get("controles") or {}, publies),
           jsonld=json.dumps({"@context": "https://schema.org", "@type": "Dataset", "name": "Panier Suisse France",
                              "description": "Écarts de prix alimentaires et de carburant entre la Suisse et la France voisine, mensuels depuis 2006.",
                              "url": site["base_url"] + "/donnees/", "license": "https://creativecommons.org/licenses/by/4.0/",
                              "creator": {"@type": "Person", "name": site["editeur"]},
                              "temporalCoverage": f"2006-01/{gen[:7]}", "spatialCoverage": "Suisse, France"}, ensure_ascii=False))
    render("page.html", "widget/", 1, "Intégrer le calculateur | Panier Suisse France",
           "Affichez gratuitement le calculateur Suisse – France sur votre site.", None, content=page_widget(site["base_url"]))
    render("page.html", "a-propos/", 1, "À propos | Panier Suisse France", "Un projet indépendant, des sources publiques.", None,
           content=page_apropos())
    render("page.html", "mentions-legales/", 1, "Mentions légales | Panier Suisse France", "Éditeur, hébergement, sources.", None,
           content=page_mentions(site))
    render("page.html", "confidentialite/", 1, "Confidentialité | Panier Suisse France", "Aucun cookie, aucune donnée personnelle.", None,
           content=page_confidentialite(site))
    render("page.html", "404.html", 0, "Page introuvable | Panier Suisse France", "Page introuvable.", None,
           content=f'<h1>Page introuvable</h1><p><a href="{site["base_url"]}/">Retour au calculateur</a></p>')

    # images et fichiers techniques
    image_partage(out / "og" / "accueil.png", "Faire ses courses en France,", "ça vaut le coup ? Le calcul depuis votre ville.",
                  [(pc(g["m"]), "Viande\nplus cher en Suisse"), (pc(g["f"]), "Fruits et légumes\nsur 12 mois"),
                   (pc(g["b"]), "Mêmes marques\nprix unitaires")])
    icones(out)
    (out / "manifest.webmanifest").write_text(json.dumps({
        "name": site["nom"], "short_name": "Panier CH-FR", "start_url": "./", "display": "standalone", "lang": "fr-CH",
        "background_color": "#ffffff", "theme_color": "#da291c",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}]}, ensure_ascii=False), encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site['base_url']}/sitemap.xml\n", encoding="utf-8")
    today = dt.date.today().isoformat()
    (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "".join(f"  <url><loc>{site['base_url']}/{p}</loc><lastmod>{today}</lastmod></url>\n" for p in pages)
                                     + "</urlset>\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"site v2 : {len(pages)} pages dans {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist"))
    main(Path(ap.parse_args().out))
