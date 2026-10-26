"""Génère le site public complet (version 3) dans un dossier prêt à publier.

  python -m scraper.site                 -> dist/
  python -m scraper.site --out _site     -> _site/ (publication GitHub Pages)

Pages : calculateur, essence, zones (une page par ville), baromètre (mois courant + archives), douane,
méthodologie, données ouvertes, widget, à propos, mentions légales, confidentialité, 404.
Fichiers : style, scripts, polices, images, images de partage, icônes, manifeste, plan du site, données JSON.
"""
from __future__ import annotations

import re

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
K5 = ("m", "c", "f", "p", "b")
NAV = [("", "Calculateur", "index"), ("acheter-suisse/", "Acheter suisse", "direct"), ("essence/", "Essence", "essence"), ("zones/", "Villes", "zones"),
       ("prix/", "Prix", "prix"), ("douane/", "Douane", "douane"), ("barometre/", "Baromètre", "barometre"),
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
    if (DATA / "pli.json").exists():
        extra["pli"] = json.loads((DATA / "pli.json").read_text(encoding="utf-8"))
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


PIED_IMAGE = "gregbrocard.github.io/Panier-suisse-france"


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
    d.text((64, H - 62), "Données publiques, mises à jour chaque mois · " + PIED_IMAGE,
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



# ------------------------------------------------------------------ petits graphiques SVG (pages générées)

def svg_lignes(series_list, titre, unite="", hauteur=220, largeur=640, zero=False):
    """series_list : [(nom, couleur_css, [(mois, valeur), ...]), ...] -> SVG responsive, sans bibliothèque."""
    pts = [v for _, _, rows in series_list for _, v in rows if v is not None]
    if len(pts) < 2:
        return ""
    allm = sorted({m for _, _, rows in series_list for m, _ in rows})
    lo, hi = min(pts), max(pts)
    if zero:
        lo, hi = min(lo, 0), max(hi, 0)
    if hi == lo:
        hi += 1
    pad_l, pad_b, pad_t = 52, 26, 10
    W, H = largeur, hauteur
    X = lambda m: pad_l + (allm.index(m) / max(1, len(allm) - 1)) * (W - pad_l - 8)
    Y = lambda v: pad_t + (hi - v) / (hi - lo) * (H - pad_t - pad_b)
    out = [f'<svg class="sv" viewBox="0 0 {W} {H}" role="img" aria-label="{e(titre)}">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        out.append(f'<line class="g" x1="{pad_l}" x2="{W - 8}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                   f'<text x="{pad_l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{nf(v, 0 if abs(hi - lo) > 20 else 1)}{unite}</text>')
    if zero and lo < 0 < hi:
        out.append(f'<line class="z" x1="{pad_l}" x2="{W - 8}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>')
    years = sorted({m[:4] for m in allm})
    stepy = max(1, len(years) // 6)
    for y in years[::stepy]:
        m = next(x for x in allm if x.startswith(y))
        out.append(f'<text x="{X(m):.1f}" y="{H - 6}" text-anchor="middle">{y}</text>')
    for nom, col, rows in series_list:
        d = "M" + "L".join(f"{X(m):.1f} {Y(v):.1f}" for m, v in rows if v is not None)
        out.append(f'<path d="{d}" fill="none" stroke="var({col})" stroke-width="2"/>')
    out.append("</svg>")
    leg = "".join(f'<span><span class="sw" style="background:var({col})"></span>{e(n)}</span>' for n, col, _ in series_list)
    return f'<figure class="chart"><div class="cap2"><span>{e(titre)}</span><span class="legend">{leg}</span></div>{"".join(out)}</figure>'

# ------------------------------------------------------------------ contenus des pages

def tableau(entetes, lignes, caption=None):
    h = "<div class=\"tbl\"><table>"
    if caption:
        h += f"<caption>{caption}</caption>"
    h += "<thead><tr>" + "".join(f"<th>{x}</th>" for x in entetes) + "</tr></thead><tbody>"
    import re as _re
    labs = [_re.sub("<[^>]+>", "", str(x)) for x in entetes]
    h += "".join("<tr>" + "".join(f"<td data-label=\"{html.escape(labs[i]) if i < len(labs) else ''}\">{c}</td>"
                                  for i, c in enumerate(l)) + "</tr>" for l in lignes)
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
    titre_viande = "Viande : quelques exemples de prix au kilo"
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
    h = f"""<h2>Les prix du jour, ville par ville</h2>
<p>Prix moyens des stations françaises autour de chaque ville frontalière, relevés chaque jour sur le flux officiel du ministère de l'Économie, convertis au taux de change du jour. Dernière mise à jour : {e(date_longue(maj)) + ' à ' + maj[11:16] + ' (UTC)' if maj else 'mensuelle'}.</p>
{kpis([("Sans plomb 95 en Suisse", nf(ess.get('sp95_ch')) + " CHF", "zone frontière genevoise, OFDF, " + e(ch.get('date_texte') or '')),
       ("Sans plomb 95 en France", nf(ess.get('sp95_fr')) + " CHF", "moyenne des zones frontalières"),
       ("Plein de 50 L", (nf((ess['sp95_ch'] - ess['sp95_fr']) * 50, 0) + " CHF") if ess.get('sp95_ch') and ess.get('sp95_fr') else "—", "économisés en moyenne en France"),
       ("Diesel", pc(ess.get('diesel_ecart')), "Suisse comparée à la France")])}
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
        fch = sy["magasins_ch"][0]["f"]
        base = {"spend": 300, "km": km, "w": w, "idx": idx, "persons": 2, "mode": "essence", "conso": 7, "wear": True, "fch": fch}
        r1 = calcul({**base, "suisse": sy.get("suisse_defaut") or []}, sy)
        r2 = calcul(base, sy)
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
<p>Pour 300 CHF de courses « un peu de tout », 2 adultes, quelqu'un qui fait d'habitude ses courses chez Aldi ou Lidl en Suisse, en voiture à essence (7 L/100 km), usure comprise, au niveau de prix du magasin du milieu. Deux cas : la viande, les laitages et les fruits et légumes restent achetés en Suisse (seuls l'épicerie, le pain et les boissons sont achetés en France), ou tout est acheté en France. Le temps de trajet n'est pas déduit.</p>
{tableau(["Départ", "Trajet", "Épicerie et boissons en France", "Tout en France"], lignes) if lignes else '<p class="muted">Distances indisponibles.</p>'}"""
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


def mags_pub(pub):
    return {d["id"]: d for d in ((pub.get("magasins") or {}).get("destinations") or [])}


def faq_accueil(sy, mags, publies, dests):
    g, R, ess = sy["gaps"], sy["regles"], sy["essence"]
    q = [("Faire ses courses en France, est-ce vraiment moins cher ?",
          f"Oui : en moyenne, les mêmes courses coûtent {nf(sy['total']['economie'], 0)} % de moins en France, d'après la "
          f"comparaison officielle des prix d'Eurostat et de l'Office fédéral de la statistique, mise à jour chaque mois. "
          f"L'écart est le plus fort sur la viande ({pc(g['m'])}) et les produits laitiers ({pc(g['c'])}), plus faible sur "
          f"les fruits et légumes ({pc(g['f'])}). Le trajet, l'usure de la voiture et la douane réduisent l'économie : le "
          f"calculateur fait le compte depuis votre localité."),
         ("Faire ses courses en France, est-ce que ça nuit aux paysans suisses ?",
          f"Cela dépend de ce qu'on achète. Le café, les huiles, les boissons ou les produits de marque sont importés de toute "
          f"façon : les acheter en France ne retire presque rien aux producteurs suisses, et c'est là que l'écart est le plus "
          f"grand ({pc(sy['groupes']['import']['ecart'])} en Suisse). La viande, le lait, le fromage, les œufs et les légumes de "
          f"saison sont surtout produits en Suisse : les acheter en France, c'est autant de ventes en moins pour les paysans "
          f"suisses. Le calculateur les laisse en Suisse par défaut ; vous pouvez changer ce réglage."),
         ("Pourquoi la viande suisse est-elle plus chère ?",
          f"Elle coûte en moyenne {pc(g['m'])} de plus qu'en France. Une partie paie des coûts suisses (salaires, terrain) et la "
          f"protection douanière ; une autre des règles d'élevage plus strictes : élevages plafonnés, transport des animaux limité "
          f"à 6 heures, poules en cage interdites depuis 1991. Le paysan ne touche qu'environ 30 à 40 centimes par franc payé en "
          f"magasin ; en direct (caissettes, magasins à la ferme), il garde l'essentiel."),
         ("Combien peut-on acheter en France sans payer de TVA ?",
          f"{R['franchise_chf']} CHF par personne et par jour. Au-delà, la TVA suisse est due sur la totalité des achats "
          f"({nf(R['tva_alimentaire'] * 100, 1)} % pour l'alimentation), et il faut les déclarer."),
         ("Combien de viande peut-on ramener de France ?",
          f"{R['viande_franchise_kg']} kg par personne et par jour sans droits de douane. Au-delà, 17 CHF par kg jusqu'à "
          f"10 kg, puis 23 CHF par kg. Beurre et crème : 1 kg. Alcool : 5 litres sous 18 % vol., 1 litre au-dessus. "
          f"Rester sous la franchise est aussi le moyen le plus simple de garder ses achats de viande en Suisse."),
         ("Comment déclarer ses achats à la douane ?",
          "En passant par le passage rouge, ou avant la frontière avec l'application officielle QuickZoll de l'OFDF, "
          "qui permet aussi de payer la TVA et les droits.")]
    if publies and mags:
        rows = [(d["nom"], mags[d["id"]]["indice_median"]) for d in dests if mags.get(d["id"], {}).get("indice_median")]
        if rows:
            lo = min(rows, key=lambda x: x[1])
            q.append(("Dans quelle ville française les supermarchés sont-ils les moins chers ?",
                      f"Parmi les villes proches de la Suisse, les supermarchés de {lo[0]} sont les moins chers : "
                      f"{nf(abs(lo[1] - 1) * 100, 0)} % sous la moyenne française (comparateur de l'UFC-Que Choisir). "
                      f"Mais la ville la plus proche de chez vous reste souvent la plus rentable, trajet compris."))
    if ess.get("sp95_ch") and ess.get("sp95_fr"):
        q.append(("Le plein en France vaut-il le coup ?",
                  f"Le sans plomb coûte en moyenne {nf(ess['sp95_fr'])} CHF le litre dans les stations françaises proches, "
                  f"contre {nf(ess['sp95_ch'])} CHF en zone frontière genevoise : environ "
                  f"{nf((ess['sp95_ch'] - ess['sp95_fr']) * 50, 0)} CHF de moins pour 50 litres. Ça ne vaut le détour que si "
                  f"vous habitez près de la frontière ; la page Essence fait le calcul."))
    return q


def og_chiffres(snap):
    grp, g = snap.get("groupes") or {}, snap.get("gaps") or {}
    if (grp.get("import") or {}).get("economie") is not None:
        return [(f"−{nf(grp['import']['economie'], 0)} %", "Ce que la Suisse importe\nen France"),
                (pc(grp["suisse"]["ecart"]), "Ce qu'elle produit\nplus cher en Suisse"), (pc(g.get("m")), "Viande\nplus cher en Suisse")]
    tot = snap.get("total") or {}
    return [(f"−{nf(tot.get('economie'), 0)} %", "Les mêmes courses\nen France"), (pc(g.get("m")), "Viande\nplus cher en Suisse"),
            (pc(g.get("c")), "Produits laitiers\nplus cher en Suisse")]


def snapshot_barometre(sy, latest):
    return {"mois": latest["genere_le"][:7], "date": latest["genere_le"], "gaps": sy["gaps"], "total": sy.get("total"),
            "officiel": sy.get("officiel"), "releves": sy.get("releves"), "mois_releves": (latest.get("officiel") or {}).get("mois"),
            "essence": sy["essence"], "fx": sy["fx"], "fl_12m_il_y_a_un_an": sy["fl_12m_il_y_a_un_an"], "groupes": sy.get("groupes"),
            "version": 4}


def page_barometre(snap, prev, archives, base_url, courant=True, series=None):
    g = snap["gaps"]
    comparable = prev and prev.get("version") == snap.get("version")
    p = (prev or {}).get("gaps") or {} if comparable else {}
    var = lambda k: (f", {pts(g[k] - p[k])} sur un mois" if g.get(k) is not None and p.get(k) is not None else "")
    ess = snap["essence"]
    mois = mois_long(snap["mois"])
    plein = (ess["sp95_ch"] - ess["sp95_fr"]) * 50 if ess.get("sp95_ch") and ess.get("sp95_fr") else None
    tot = snap.get("total") or {}
    grp = snap.get("groupes") or {}
    items = []
    if (grp.get("import") or {}).get("economie") is not None:
        items.append(("Ce que la Suisse importe", f"−{nf(grp['import']['economie'], 0)} %", "en France : épicerie, huiles, boissons"))
        items.append(("Ce que la Suisse produit", pc(grp["suisse"]["ecart"]), "plus cher en Suisse : viande, laitages, fruits et légumes"))
    elif tot.get("economie") is not None:
        items.append(("Les mêmes courses", f"−{nf(tot['economie'], 0)} %", "en France, avant trajet"))
    items += [(RAYON_NOM[k].capitalize(), pc(g.get(k)), "plus cher en Suisse" + var(k)) for k in K5 if g.get(k) is not None]
    items += [
              ("Plein de 50 L", nf(plein, 0) + " CHF" if plein else "—", "économisés en France (SP95)"),
              ("1 euro", nf(snap.get("fx"), 4) + " CHF", "taux BCE")]
    k = kpis(items)
    pm = lambda v, mot="chère": f"{nf(abs(v), 0)} % {'plus' if v >= 0 else 'moins'} {mot}"
    phrases = []
    if (grp.get("import") or {}).get("economie") is not None:
        phrases.append(f"En {mois}, ce que la Suisse importe (épicerie, huiles, boissons) coûte en moyenne {nf(grp['import']['economie'], 0)} % "
                       f"de moins en France, avant les frais de trajet.")
        phrases.append(f"Ce que la Suisse produit elle-même (viande, laitages, fruits et légumes) y est {pm(grp['suisse']['ecart'])} : "
                       f"une partie de cet écart paie des salaires suisses et, pour la viande et les œufs, des règles d'élevage plus strictes.")
    elif tot.get("economie") is not None:
        phrases.append(f"En {mois}, les mêmes courses coûtent en moyenne {nf(tot['economie'], 0)} % de moins en France qu'en Suisse, avant les frais de trajet.")
    if g.get("m") is not None:
        phrases.append(f"La viande reste le rayon où l'écart est le plus fort : {pm(g['m'])} en Suisse.")
    if g.get("f") is not None:
        phrases.append(f"L'écart est plus faible sur les fruits et légumes ({pm(g['f'], 'chers')}).")
    if plein:
        phrases.append(f"À la pompe, un plein de 50 litres de sans plomb coûte environ {nf(plein, 0)} francs de moins côté français.")
    texte = " ".join(phrases)
    cite = (f"Panier Suisse France, baromètre de {mois}, d'après la comparaison des prix d'Eurostat et de l'OFS, les données de "
            f"l'OFAG, de l'INSEE, de l'OFDF et de la BCE. {base_url}/barometre/{snap['mois']}/")
    up = "../" if courant else "../../"
    off = snap.get("officiel") or {}
    det = ""
    if off.get("detail"):
        det = "<h2>D'où vient chaque chiffre</h2>" + tableau(
            ["Rayon", f"Écart officiel {off.get('annee', '')}", "Effet du change depuis", "Évolution de nos relevés", "Écart ce mois-ci"],
            [(RAYON_NOM[c].capitalize(), pc(off['detail'][c]['officiel']), f"{off['detail'][c]['change']:+.1f} %".replace(".", ","),
              (f"{off['detail'][c]['evolution']:+.1f} %".replace(".", ",") if off['detail'][c]['evolution'] else "—"), f"<b>{pc(g[c])}</b>")
             for c in ("m", "c", "f", "p", "b")])
        det += ("<p class=\"muted\">Écart officiel : comparaison des niveaux de prix d'Eurostat et de l'Office fédéral de la statistique "
                "(milliers de produits par pays). Effet du change : le franc s'est renforcé ou affaibli face à l'euro depuis. "
                "Évolution de nos relevés : variation de l'écart mesuré sur nos produits (fruits et légumes, laitages).</p>")
    chart = ""
    if series and series.get("panier"):
        from .synthese import rolling12
        pan = series["panier"]
        roll = rolling12(pan)
        rows = [(x["m"], r) for x, r in zip(pan, roll) if r is not None][-72:]
        chart = svg_lignes([("Fruits et légumes, moyenne sur 12 mois", "--ink", rows)],
                           "Nos relevés : écart Suisse/France sur 14 fruits et légumes, en %", " %", zero=True)
    nb_releves = f" Prix relevés les plus récents : {mois_long(snap['mois_releves'])}." if snap.get("mois_releves") else ""
    h = f"""<h1>Prix Suisse–France : le baromètre de {mois}</h1>
<p class="lede">Chaque mois, les mêmes courses comparées des deux côtés de la frontière, tout en francs suisses. Publié le {date_longue(snap['date'])}.{nb_releves}</p>
{k}
<h2>Ce qu'il faut retenir</h2>
<p>{e(texte)}</p>
{det}
{chart}
<h2>Texte prêt à reprendre</h2>
<div class="note"><p id="txt">{e(texte)} Source : {e(cite)}</p><p style="margin-top:10px"><button type="button" class="btn ghost" id="copy">Copier le texte</button> <span class="muted" id="copied" aria-live="polite"></span></p></div>
<h2>Citer</h2>
<p class="quote">{e(cite)}</p>
<p><a href="{up}og/barometre-{snap['mois']}.png" download>Télécharger l'image du mois</a> · <a href="{up}donnees/">Données ouvertes</a> · <a href="{up}methodologie/">Méthodologie</a></p>
<h2>Les mois précédents</h2>
<ul>{''.join(f'<li><a href="{up}barometre/{m}/">{mois_long(m)}</a></li>' for m in archives) or '<li>Premier baromètre.</li>'}</ul>"""
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
<p class="note"><b>Viande, beurre, vin : les franchises sont basses pour une raison.</b> Elles protègent les produits que la Suisse fabrique elle-même. Rester sous la franchise, c'est aussi garder en Suisse ces achats-là, et réserver la France à ce qui est importé de toute façon (épicerie, huiles, boissons sans alcool). <a href="../acheter-suisse/">Acheter suisse moins cher</a></p>
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
<iframe src="../?embed=1" title="Aperçu du calculateur intégré" style="width:100%;height:1150px;border:1px solid var(--line)" loading="lazy"></iframe>
<h2>Reprendre les chiffres</h2>
<p>Les chiffres du <a href="../barometre/">baromètre mensuel</a> peuvent être cités librement avec la mention « Panier Suisse France » et un lien. Les données sont disponibles en <a href="../donnees/">format ouvert</a>.</p>"""


def page_donnees(controles, magasins_publies):
    fichiers = [("data/ecarts_par_rayon.csv", "Tableur : écart Suisse/France par rayon ce mois-ci, avec sa décomposition"),
                ("data/produits.csv", "Tableur : prix de chaque produit relevé en Suisse et en France"),
                ("data/historique_fruits_legumes.csv", "Tableur : écart mensuel sur 14 fruits et légumes depuis 2006"),
                ("data/pli.json", "Comparaison officielle des niveaux de prix (Eurostat–OFS) utilisée comme base"),
                ("data/latest.json", "Photo du mois : tous les prix, écarts, magasins, essence, contrôles"),
                ("data/series.json", "Historique mensuel : écarts fruits et légumes depuis 2006, crèmerie, change, prix par produit"),
                ("data/essence.json", "Essence : prix du jour par zone et stations les moins chères"),
                ("data/stations.json", "Stations françaises au prix du jour et stations suisses avec un prix relevé (mode « Où faire le plein »)"),
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
<p class="lede">Panier Suisse France est un projet indépendant qui répond à deux questions : faire ses courses en France, ça vaut le coup, une fois le trajet, la douane et l'essence comptés ? Et sur quels produits peut-on économiser sans rien retirer aux paysans suisses ? Le principe : payer moins cher en France ce que la Suisse importe de toute façon, et garder son budget pour ce qu'elle produit.</p>
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
    md = re.sub(r"(?m)^(?!\s*[-*] |\s*\d+\. |\s*$)(.+)\n(?=\s*(?:[-*] |\d+\. ))", r"\1\n\n", md)  # liste sans ligne vide avant
    body = markdown.markdown(md, extensions=["tables"])
    body = body.replace("<table>", '<div class="tscroll"><table>').replace("</table>", "</table></div>")
    return body + '<p><a href="../METHODOLOGIE.md">Version texte (Markdown)</a> · <a href="../v2/">Version 2 (archive)</a> · <a href="../v1/">Version 1 (archive)</a></p>'



# ------------------------------------------------------------------ mode « Où faire le plein »

ZONES_OFDF_GEO = {"geneve": ("zone frontière genevoise", 46.204, 6.143), "bale": ("zone frontière bâloise", 47.559, 7.588),
                  "kreuzlingen": ("zone frontière de Kreuzlingen", 47.650, 9.175), "tessin": ("zone frontière tessinoise", 45.990, 8.950),
                  "liechtenstein": ("zone frontière saint-galloise (Liechtenstein)", 47.168, 9.478)}


def _hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def calibrer_routes(ori, dests):
    """Facteur route / vol d'oiseau et vitesse moyenne, mesurés sur les itinéraires OSRM déjà calculés."""
    import statistics
    pos = {d["id"]: (d["lat"], d["lon"]) for d in dests}
    ratios, speeds = [], []
    for i, row in enumerate(ori["dist"][::7]):
        c = ori["coords"][i * 7]
        for k, did in enumerate(ori["destinations"]):
            km, mn = row[2 * k], row[2 * k + 1]
            if km and mn and did in pos:
                h = _hav(c, pos[did])
                if h > 3:
                    ratios.append(km / h)
                    speeds.append(km / (mn / 60))
    return {"facteur": round(statistics.median(ratios), 3) if ratios else 1.3,
            "kmh": round(statistics.median(speeds), 1) if speeds else 60.0, "paires": len(ratios)}


def donnees_stations(extra, dests, ch_ess, fx):
    """data/stations.json : stations françaises au prix du jour + stations suisses avec un prix relevé."""
    ess = extra.get("essence") or {}
    osm = []
    p = DATA / "stations_osm.json"
    if p.exists():
        osm = json.loads(p.read_text(encoding="utf-8")).get("stations", [])
    osm_fr = [x for x in osm if x[6] == "FR"]
    osm_ch = [x for x in osm if x[6] == "CH"]
    by_id = {x[0]: x for x in osm}
    fr = []
    ref = (ess.get("genere_le") or dt.date.today().isoformat())[:10]

    def frais(prix, maj):  # un prix non mis à jour depuis plus de 15 jours n'est pas utilisé
        if not prix or not maj:
            return None
        try:
            return prix if (dt.date.fromisoformat(ref) - dt.date.fromisoformat(maj[:10])).days <= 15 else None
        except ValueError:
            return None
    for x in ess.get("stations_fr") or []:
        x = dict(x, sp95=frais(x.get("sp95"), x.get("sp95_maj")), diesel=frais(x.get("diesel"), x.get("diesel_maj")))
        if not (x.get("sp95") or x.get("diesel")) or not fx:
            continue
        pt = (x["lat"], x["lon"])
        nom = ""
        best, bd = None, 0.15
        for o in osm_fr:
            if abs(o[1] - pt[0]) < 0.003 and abs(o[2] - pt[1]) < 0.004:
                d = _hav(pt, (o[1], o[2]))
                if d < bd:
                    best, bd = o, d
        if best:
            nom = best[3] or best[4]
        z, zk = None, None
        for d in dests:
            dk = _hav(pt, (d["lat"], d["lon"]))
            if zk is None or dk < zk:
                z, zk = d["id"], round(dk, 2)
        fr.append([x["lat"], x["lon"], nom or f"Station {(x.get('ville') or '').title()}", x.get("adresse") or "",
                   (x.get("ville") or "").title(), round(x["sp95"] * fx, 3) if x.get("sp95") else None,
                   round(x["diesel"] * fx, 3) if x.get("diesel") else None, (x.get("sp95_maj") or "")[:16],
                   (x.get("diesel_maj") or "")[:16], z, zk])
    ch = []
    rp = DATA / "prix_ch.yaml"
    today = dt.date.today()
    if rp.exists():
        for r in (yaml.safe_load(rp.read_text(encoding="utf-8")) or {}).get("releves") or []:
            try:
                age = (today - dt.date.fromisoformat(str(r["date"]))).days
            except Exception:  # noqa: BLE001
                continue
            if age > 45:
                continue
            lat, lon = r.get("lat"), r.get("lon")
            if r.get("osm") and r["osm"] in by_id:
                lat, lon = by_id[r["osm"]][1], by_id[r["osm"]][2]
            if lat is None or lon is None:
                continue
            ch.append([lat, lon, r.get("station", "Station"), r.get("localite", ""), r.get("sp95"), r.get("diesel"),
                       str(r["date"]), r.get("source", "relevé"), age > 14])
    zones = []
    for zid, (nom, lat, lon) in ZONES_OFDF_GEO.items():
        z = (ch_ess.get("zones") or {}).get(zid) or {}
        zones.append({"id": zid, "nom": nom, "lat": lat, "lon": lon,
                      "sp95": (z.get("sp95") or {}).get("ch_chf"), "diesel": (z.get("diesel") or {}).get("ch_chf")})
    bateaux = ("naval", "marina", "port de", "chantier", "bateau", "boat", "hafen", "werft")
    ch_osm = [[x[1], x[2], x[3] or x[4] or "Station", x[5]] for x in osm_ch
              if not any(b in (x[3] or "").lower() for b in bateaux)]
    return {"fr": fr, "ch": ch, "ch_osm": ch_osm, "ch_total": len(osm_ch), "maj_fr": ess.get("genere_le")}, zones



# ------------------------------------------------------------------ pages produit, Suisse, partenaires (v3)

CAT_RAYON = {"Fruits": "f", "Légumes": "f", "Crèmerie": "c", "Pain": "p"}
RAYON_NOM = {"m": "viande", "c": "lait, fromage et œufs", "f": "fruits et légumes", "p": "pain et céréales",
             "b": "épicerie, huiles et boissons"}
# Origine dominante de chaque produit relevé, pour le consommateur suisse (Agristat ; saison : OFAG, calendrier des séries)
ORIGINE = {"bananes": "import", "clementines": "import", "oranges": "import", "huile": "import",
           "pommes": "suisse", "poires": "suisse", "pdt": "suisse", "carottes": "suisse", "oignons": "suisse",
           "poireaux": "suisse", "champignons": "suisse", "lait": "suisse", "beurre": "suisse", "emmental": "suisse",
           "yaourt": "suisse", "pain": "suisse", "entrecote": "suisse", "veau": "suisse", "porc": "suisse", "jambon": "suisse",
           "tomates": "saison", "courgettes": "saison", "endives": "saison", "poivrons": "saison"}
ORIGINE_TXT = {"suisse": "Produit en Suisse", "saison": "Suisse en saison, importé le reste de l'année", "import": "Importé"}


def produits_liste(latest):
    """Tous les produits relevés, sous une forme commune."""
    out = []
    for p in (latest.get("officiel") or {}).get("produits") or []:
        if p.get("ecart") is None:
            continue
        u = "L" if p["unit"] == "L" else p["unit"]
        src = ("OFAG (moyenne du commerce de détail suisse)", "INSEE, prix estimé à partir du dernier prix moyen publié" if p.get("estime")
               else "INSEE (prix moyen de vente au détail)")
        out.append({"id": p["id"], "label": p["label"], "rayon": "b" if p["id"] == "huile" else CAT_RAYON.get(p.get("cat"), "f"), "unite": u,
                    "ch": p["ch"], "fr": p["fr_chf"], "fr_eur": p["fr_eur"], "ecart": p["ecart"], "mois": p.get("mois"),
                    "src_ch": src[0], "src_fr": src[1], "histo": True})
    for v in latest.get("viande") or []:
        ch = v.get("ch_migros") or v.get("ch")
        if not (ch and v.get("fr_chf")):
            continue
        out.append({"id": v["id"], "label": v["label"], "rayon": "m", "unite": "kg", "ch": ch, "fr": v["fr_chf"],
                    "fr_eur": v.get("fr_eur"), "ecart": round((ch / v["fr_chf"] - 1) * 100, 1), "mois": v.get("fr_mois"),
                    "src_ch": f"Migros, médiane de {v.get('ch_n')} produits, hors bio et promotions", "src_fr": "INSEE (prix moyen)",
                    "exemples": v.get("ch_produits") or []})
    for m in latest.get("marques") or []:
        if not (m.get("ch_unit") and m.get("fr_unit_chf")) or (m.get("fr_n") or 0) < 5:
            continue
        u = "L" if m["unit"] == "L" else "kg"
        out.append({"id": m["id"], "label": m["label"], "rayon": "b", "unite": u, "ch": m["ch_unit"], "fr": m["fr_unit_chf"],
                    "fr_eur": m.get("fr_unit_eur"), "ecart": m.get("ecart"), "mois": None,
                    "src_ch": f"Migros : {m.get('ch_produit') or ''}", "src_fr": f"Open Prices, {m.get('fr_n')} tickets de caisse en France",
                    "marque": True})
    for x in out:
        x["origine"] = ORIGINE.get(x["id"], "import" if x.get("marque") else "suisse")
    return out


def page_produit(p, series, sy):
    g = sy["gaps"].get(p["rayon"])
    plus = "plus cher" if p["ecart"] >= 0 else "moins cher"
    h = f"""<h1>Prix {e(p['label'].lower() if not p.get('marque') else p['label'])} : Suisse ou France ?</h1>
<p class="lede">{e(p['label'])} coûte {nf(p['ch'])} CHF par {p['unite']} en Suisse et {nf(p['fr'])} CHF en France ({nf(p['fr_eur'])} EUR), soit {nf(abs(p['ecart']), 0)} % {plus} en Suisse{(' (' + mois_long(p['mois']) + ')') if p.get('mois') else ''}.</p>
{kpis([("En Suisse", nf(p['ch']) + " CHF", "par " + p['unite']), ("En France", nf(p['fr']) + " CHF", "par " + p['unite'] + ", " + nf(p['fr_eur']) + " EUR"), ("Écart", pc(p['ecart']), "Suisse comparée à la France")])}"""
    if p.get("histo"):
        fx = dict(series.get("fx") or [])
        rows = [r for r in (series.get("produits") or {}).get(p["id"], []) if r[0] in fx][-120:]
        if len(rows) > 6:
            h += svg_lignes([("Suisse", "--red", [(r[0], r[1]) for r in rows]), ("France", "--fr", [(r[0], r[2] * fx[r[0]]) for r in rows])],
                            f"Prix en CHF par {p['unite']}, 10 dernières années", " CHF")
    if p.get("exemples"):
        h += "<h2>Produits suisses relevés</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in p["exemples"][:6]) + "</ul>"
    o = p.get("origine")
    if o in ("suisse", "saison"):
        h += f"""<h2>Le choix suisse</h2>
<p><span class="tag ch">{ORIGINE_TXT[o]}</span> {"Hors saison, le produit vendu en Suisse est souvent importé : vérifiez l'origine sur l'étiquette. " if o == "saison" else ""}Le prix suisse paie en partie des salaires suisses et, pour la viande et les œufs, des règles d'élevage plus strictes. <a href="../../pourquoi-plus-cher/">Ce que paie la différence</a> · <a href="../../acheter-suisse/">Où l'acheter moins cher, en direct</a></p>"""
    else:
        h += f"""<h2>Un produit importé</h2>
<p><span class="tag">{ORIGINE_TXT['import']}</span> {"Même produit, souvent même usine : " if p.get("marque") else ""}la différence de prix ne va pas à un producteur suisse. C'est le type d'achat qui vaut le trajet en France.</p>"""
    h += f"""<h2>Et pour tout le rayon ?</h2>
<p>Sur l'ensemble du rayon {RAYON_NOM[p['rayon']]}, la Suisse est en moyenne {pc(g)} plus chère que la France (comparaison officielle Eurostat–OFS, mise à jour ce mois-ci). Un seul produit peut s'en écarter beaucoup.</p>
<p><a class="btn" href="../../">Calculer mon économie, trajet compris</a></p>
<p class="muted">Sources : Suisse, {e(p['src_ch'])} ; France, {e(p['src_fr'])}. Change : BCE. <a href="../">Tous les produits</a> · <a href="../../methodologie/">Méthode</a>.</p>"""
    return h


def page_produits_index(prods, sy):
    rows = []
    for r in ("m", "c", "f", "p", "b"):
        for p in sorted([x for x in prods if x["rayon"] == r], key=lambda x: -x["ecart"]):
            rows.append((f"<a href=\"{p['id']}/\">{e(p['label'])}</a><small>{RAYON_NOM[r]} · {ORIGINE_TXT[p['origine']].lower()}</small>",
                         f"{nf(p['ch'])} CHF/{p['unite']}", f"{nf(p['fr'])} CHF/{p['unite']}", f"<b>{pc(p['ecart'])}</b>"))
    return ("<h1>Prix produit par produit : Suisse et France</h1>"
            "<p class=\"lede\">Une trentaine de produits relevés chaque mois des deux côtés de la frontière, en francs suisses. "
            "Ce sont des exemples : l'écart moyen de chaque rayon vient de la comparaison officielle Eurostat–OFS. "
            "Pour chaque produit, on indique s'il est produit en Suisse ou importé.</p>"
            + kpis([(RAYON_NOM[k].capitalize(), pc(sy["gaps"][k]), "écart moyen du rayon") for k in ("m", "c", "f", "p", "b")])
            + tableau(["Produit", "Suisse", "France", "Écart"], rows))


SOURCES_SUISSE = [
    ("Rappn, classement 2026 des supermarchés suisses (reprend le test K-Tipp d'août 2025)", "https://rappn.ch/en/cheapest-supermarket-switzerland"),
    ("Blick, test d'À bon entendeur (RTS), avril 2024", "https://www.blick.ch/fr/suisse/denner-le-plus-cher-faire-ses-courses-a-lidl-ou-a-la-coop-la-difference-de-prix-est-minime-id19648764.html"),
    ("Blick, comparaison des prix de la viande, septembre 2025", "https://www.blick.ch/wirtschaft/in-welchem-supermarkt-ist-fleisch-wirklich-am-billigsten-preisschlacht-zwischen-den-detailhaendlern-die-grosse-blick-analyse-id21205522.html"),
    ("Tio.ch, test K-Tipp de 25 produits, novembre 2024", "https://www.tio.ch/svizzera/economia/1796522/la-carne-costa-meno-e-in-qualche-caso-molto-meno"),
]


SOURCES_POURQUOI = [
    ("Agristat, taux d'autosuffisance 2023, repris par Swissmilk", "https://api.swissmilk.ch/wp-content/uploads/2025/07/20250722_Arbeitsblatt_Herkunft-Lebensmittel_Konsum_FR.pdf"),
    ("OFAG et OSMV, Année viticole 2024", "https://pro-strapi.swisswine.ch/uploads/2025_04_29_Communique_de_presse_Rapport_OFAG_et_OSMV_2024_FR_ef928ec222.pdf"),
    ("OSAV, durée de transport des animaux (LPA art. 15, OPAn art. 152a)", "https://www.blv.admin.ch/dam/fr/sd-web/prjzlxDGNguC/fachinformation-15.5-fr.pdf"),
    ("FRC, poules pondeuses", "https://www.frc.ch/wp-content/uploads/2013/03/FRC_MC_57-poules-pondeuses1.pdf"),
    ("CIWF, rapport sur les cages (France, 2023)", "https://ciwf.org.uk/media/7458732/rapport-cages-web.pdf"),
    ("swissinfo, effectifs maximaux et sorties en plein air", "https://www.swissinfo.ch/fre/politics/comment-l-%c3%a9levage-intensif-impacte-le-bien-%c3%aatre-animal/47846158"),
    ("Marchés équitables Suisse, moniteur des prix (FHNW), 2024", "https://fairemaerkteschweiz.ch/fr/nouveau-calcul-du-moniteur-des-prix-lecart-de-prix-se-creuse-pour-la-viande/"),
    ("FRC, enquête sur les marges des légumes, 2022", "https://enquetes.frc.ch/marges-legumes"),
    ("swissinfo, la vente directe dans les fermes suisses, mars 2026", "https://www.swissinfo.ch/fre/la-suisse-insolite/la-vente-directe-une-affaire-qui-roule-dans-les-fermes-suisses/91091352"),
    ("swissinfo, Coop dépasse Migros (Nielsen), novembre 2025", "https://www.swissinfo.ch/eng/agribusiness/coop-overtakes-migros-in-core-business/90267923"),
]


def _sources(lst):
    return "<h2>Sources</h2><ul>" + "".join(f'<li><a href="{u}" rel="noopener">{e(t)}</a></li>' for t, u in lst) + "</ul>"


def page_pourquoi(sy):
    g, grp = sy["gaps"], sy["groupes"]
    h = f"""<h1>Pourquoi c'est plus cher en Suisse, et ce que paie la différence</h1>
<p class="lede">Ce que la Suisse produit elle-même (viande, laitages, fruits et légumes) coûte en moyenne {pc(grp['suisse']['ecart'])} de plus qu'en France. Ce qu'elle importe (épicerie, huiles, boissons) coûte {pc(grp['import']['ecart'])} de plus : un écart encore plus grand, qui ne revient pas aux producteurs suisses.</p>
{kpis([("Produit en Suisse", pc(grp['suisse']['ecart']), "plus cher qu'en France"), ("Importé", pc(grp['import']['ecart']), "plus cher qu'en France"), ("Part du producteur", "30 à 42 ct.", "par franc payé en magasin")])}
<h2>Ce que la Suisse produit</h2>
<p>Part de la consommation couverte par la production suisse, et écart de prix du rayon avec la France ce mois-ci.</p>
""" + tableau(["Aliment", "Produit en Suisse (2023)", "Écart avec la France"], [
        ("Lait, fromage, beurre", "113 %", pc(g.get("c"))), ("Viande", "86 %", pc(g.get("m"))),
        ("Pommes de terre", "69 %", pc(g.get("f")) + " (fruits et légumes)"), ("Œufs", "57 %", pc(g.get("c")) + " (avec les laitages)"),
        ("Céréales (pain, farine)", "47 %", pc(g.get("p"))), ("Légumes", "44 %", pc(g.get("f"))),
        ("Vin", "35,5 % des vins tranquilles (2024)", "non mesuré"), ("Huiles végétales", "25 %", pc(g.get("b")) + " (épicerie)"),
        ("Fruits", "21 % (pommes et poires : bien plus)", pc(g.get("f"))),
        ("Café, cacao, riz, épices, fruits exotiques", "0 %", pc(g.get("b")) + " (épicerie)")]) + f"""
<h2>Ce que paie la différence</h2>
<p>Une partie de l'écart vient de coûts que tout le monde paie en Suisse : salaires, terrain, bâtiments, transport. Une autre vient de la protection douanière des produits agricoles suisses, qui maintient les prix intérieurs plus hauts. Pour la viande et les œufs, une partie paie aussi des règles d'élevage plus strictes, inscrites dans la loi :</p>
""" + tableau(["Règle", "Suisse", "Union européenne, France"], [
        ("Poules en cage", "Interdites depuis 1991", "Cages « aménagées » autorisées ; 28 % des pondeuses françaises en cage (2023)"),
        ("Taille maximale des élevages", "18 000 poules pondeuses, 27 000 poulets, 1 500 porcs, 300 veaux d'engraissement", "Pas de plafond"),
        ("Transport des animaux", "6 heures de trajet au plus, 8 heures en tout", "Nettement plus long autorisé, selon l'espèce"),
        ("Sorties régulières en plein air (programme SRPA)", "85 % des bovins, 50 % des porcs, 85 % des pondeuses, 8 % des poulets", "Pas de programme national équivalent")]) + """
<p class="muted">À qualité égale, l'écart est plus faible : les labels français (Label Rouge, bio) ont des règles proches des règles suisses. Les prix moyens comparés ici mélangent toutes les qualités.</p>
<h2>Où va le franc payé en magasin</h2>
<ul>
<li>Le paysan touche environ <b>30 centimes par franc</b> dépensé dans le commerce de détail, contre 45 en 1990.</li>
<li>Selon le moniteur des prix de Marchés équitables Suisse (2024), la part du producteur est d'environ 42 centimes pour les produits conventionnels et 34 centimes pour les produits IP-Suisse et bio.</li>
<li>Pour les légumes, le coût de production ne représente souvent qu'un quart à un tiers du prix en rayon (enquête FRC sur quelques exploitations, 2022). Le reste paie l'emballage, la logistique, les magasins et la marge.</li>
<li>Coop et Migros font ensemble environ 80 % des ventes alimentaires des grandes enseignes suisses (Nielsen, 2025).</li>
</ul>
<p>En vente directe, le producteur garde l'essentiel du prix. Environ une exploitation suisse sur cinq vend une partie de sa production à la ferme.</p>
<p><a class="btn" href="../acheter-suisse/">Acheter suisse moins cher, près de chez vous</a> <a class="btn" href="../">Calculer mon économie</a></p>
<p class="muted">Ce site ne reçoit aucun financement des producteurs ni des enseignes. Les sources de la filière (Proviande, Union suisse des paysans) sont signalées comme telles ; les chiffres ci-dessus viennent de sources publiques ou indépendantes.</p>
""" + _sources(SOURCES_POURQUOI)
    return h


def page_acheter_suisse(site, fermes_info):
    n = (fermes_info or {}).get("total")
    h = f"""<h1>Acheter suisse moins cher, près de chez vous</h1>
<p class="lede">En direct, le paysan garde l'essentiel du prix, contre environ 30 à 40 centimes par franc en magasin. Magasins à la ferme, distributeurs de lait et d'œufs, boucheries, fromageries, marchés et caves autour de votre localité.</p>
<form class="sentence" id="sentence" autocomplete="off" onsubmit="return false">
  <span class="ln">Près de
    <span class="slot" id="slotFrom"><input id="from" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="fromList" aria-label="Votre localité" placeholder="votre localité" spellcheck="false"><ul class="list" id="fromList" role="listbox" hidden></ul></span></span>
  <span class="ln">à moins de
    <span class="slot"><select id="rayon" aria-label="Distance"><option value="5">5 km</option><option value="10" selected>10 km</option><option value="20">20 km</option></select></span></span>
</form>
<div class="seg multi" id="types" role="group" aria-label="Types de points de vente"></div>
<div id="direct" aria-live="polite"><p class="muted">{('Choisissez votre localité. ' + nf(n, 0) + ' points de vente référencés en Suisse.') if n else 'Carte en préparation : la liste des points de vente sera disponible après le prochain relevé.'}</p></div>
<h2>Les bons plans pour payer moins cher</h2>
""" + tableau(["Moyen", "Pour quoi", "Pourquoi c'est intéressant"], [
        ("Morceaux moins nobles, origine suisse", "Viande", "Haché, émincé, ragoût, volaille : bien moins cher que l'entrecôte, en grande surface aussi"),
        ("Caissettes à la ferme (5 à 10 kg)", "Viande", "Le paysan vend toute la bête, sans intermédiaire ; se congèle"),
        ("Magasins à la ferme, libre-service 24 h/24", "Œufs, légumes, fruits, fromage", "Prix fixé par le producteur, produits de saison"),
        ("Distributeurs de lait et d'œufs", "Lait, œufs", "Produits du jour, sans emballage pour le lait"),
        ("Marchés", "Légumes, fruits, fromage", "Producteurs de la région, souvent des prix en fin de marché"),
        ("Paniers en abonnement", "Légumes", "Prix fixe à l'année, légumes de saison"),
        ("Caves et vignerons", "Vin", "Prix du domaine, caves ouvertes"),
        ("Invendus du jour", "Tout", "Applications anti-gaspillage des boulangeries et magasins")]) + f"""
<p class="muted">Liste tirée d'OpenStreetMap (© contributeurs OpenStreetMap, licence ODbL), mise à jour chaque mois : un point de vente manque ou a fermé ? <a href="https://www.openstreetmap.org/" rel="noopener">Corrigez-le sur OpenStreetMap</a>, il apparaîtra ici au relevé suivant. Les prix de la vente directe ne sont publiés nulle part : vous connaissez le prix d'une caissette ? <a href="{e(site.get('contact_url') or '')}" rel="noopener">Signalez-le</a>.</p>
<p><a href="../pourquoi-plus-cher/">Pourquoi c'est plus cher en Suisse</a> · <a href="../">Calculer mon économie</a></p>
<script id="data" type="application/json">{{"root":"../","f":{'true' if n else 'false'}}}</script>
<script src="../direct.js?v=1"></script>"""
    return h


def page_suisse(sy):
    mags = sy["magasins_ch"]
    h = """<h1>Quel supermarché suisse est le moins cher ?</h1>
<p class="lede">Avant d'aller en France, la première économie se fait souvent en Suisse : les discounters coûtent environ 5 % de moins que Migros, et Coop environ 3 % de plus. Synthèse des tests de prix publiés, avec leurs sources.</p>
"""
    h += tableau(["Enseigne", "Panier de 100 produits (K-Tipp, août 2025)", "Par rapport à Migros"],
                 [("Aldi", "230,94 CHF", "−5,2 %"), ("Lidl", "232,83 CHF", "−4,4 %"), ("Migros", "243,54 CHF", "référence"),
                  ("Coop", "250,70 CHF", "+2,9 %")], "Le test le plus récent")
    h += tableau(["Enseigne", "30 produits, toujours le moins cher du rayon (À bon entendeur, 2024)"],
                 [("Lidl", "162,05 CHF"), ("Aldi", "166,59 CHF"), ("Coop", "167,82 CHF"), ("Migros", "179,37 CHF"), ("Denner", "181,67 CHF")],
                 "Les premiers prix")
    h += """<h2>Ce qu'il faut retenir</h2>
<ul><li><b>Les discounters (Aldi, Lidl) sont les moins chers</b> sur un panier courant, de 4 à 5 % sous Migros.</li>
<li><b>Les produits de marque</b> (Nutella, Coca-Cola…) coûtent pratiquement le même prix partout.</li>
<li><b>Sur les premiers prix</b> (M-Budget, Prix Garantie), Migros et Coop s'alignent souvent sur les discounters ; l'écart se joue sur les produits courants.</li>
<li><b>Viande</b> : en septembre 2025, Lidl, Coop et Aldi étaient à quelques centimes les uns des autres, Migros et Denner derrière.</li></ul>
<h2>Et dans le calculateur ?</h2>
<p>Le calculateur vous demande où vous faites vos courses en Suisse et ajuste les prix suisses en conséquence : """ + ", ".join(
        f"{e(m['label'])} : {pc((m['f'] - 1) * 100) if m['f'] != 1 else 'moyenne suisse'}" for m in mags) + """. Plus vous achetez déjà chez un discounter, plus l'économie en France est petite.</p>
<p><a class="btn" href="../">Faire le calcul</a></p>
<h2>Sources</h2><ul>""" + "".join(f'<li><a href="{u}" rel="noopener">{e(t)}</a></li>' for t, u in SOURCES_SUISSE) + """</ul>
<p class="muted">Les tests portent sur des paniers et des dates précis ; les prix changent souvent. Aucune enseigne n'a été consultée ni rémunérée.</p>"""
    return h


def page_partenaires(site):
    contact = (f'<a href="mailto:{e(site["contact_email"])}">{e(site["contact_email"])}</a>' if site.get("contact_email")
               else f'<a href="{e(site["contact_url"])}" rel="noopener">formulaire de contact</a>')
    return f"""<h1>Partenaires et licences</h1>
<p class="lede">Panier Suisse France est indépendant. Son principe : payer moins là où ça ne coûte rien aux paysans suisses. Ses chiffres ne sont jamais influencés par un partenaire ; ce qui peut l'être, c'est leur diffusion.</p>
<h2>Ce que nous proposons</h2>
<ul><li><b>Producteurs et marques suisses</b> (interprofessions, marques régionales, labels) : soutien d'une rubrique comme « Acheter suisse moins cher », signalé comme tel, sans droit sur les chiffres.</li>
<li><b>Cantons et services de l'agriculture</b> : la carte des points de vente directe complétée avec vos listes de producteurs, sous votre accord.</li>
<li><b>Fermes</b> : toutes les fermes référencées apparaissent gratuitement ; l'ordre d'affichage ne s'achète pas.</li>
<li><b>Études sur le tourisme d'achat</b> : écarts de prix par rayon et par origine, évolution mensuelle depuis 2006, essence aux cinq frontières.</li>
<li><b>Le calculateur sur votre site</b> : gratuit en version standard (<a href="../widget/">widget</a>), sous licence pour une version personnalisée.</li>
<li><b>Baromètre mensuel</b> pour les médias : chiffres, texte et image prêts à publier.</li></ul>
<h2>Nos règles</h2>
<ul><li>Aucun partenaire ne peut modifier un chiffre, une source ou un classement ; aucune enseigne comparée ne peut acheter une place ou un texte.</li>
<li>Toute licence ou tout partenariat rémunéré est indiqué publiquement sur cette page.</li>
<li>La méthode et les données restent publiques.</li></ul>
<h2>Partenaires actuels</h2><p>Aucun.</p>
<h2>Contact</h2><p>{contact}</p>"""

def ecrire_csv(d: Path, sy, series, pub):
    """Exports tableur (séparateur point-virgule, décimales avec virgule, comme Excel en Suisse romande)."""
    import csv
    f = lambda v: "" if v is None else str(round(v, 4)).replace(".", ",")
    with open(d / "ecarts_par_rayon.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["rayon", "ecart_ce_mois_pct", "ecart_officiel_pct", "annee_officielle", "effet_change_pct", "evolution_releves_pct", "ecart_releves_pct"])
        off = sy.get("officiel") or {}
        for k in ("m", "c", "f", "p", "b"):
            dt_ = (off.get("detail") or {}).get(k, {})
            w.writerow([RAYON_NOM[k], f(sy["gaps"][k]), f(dt_.get("officiel")), off.get("annee", ""), f(dt_.get("change")),
                        f(dt_.get("evolution")), f((sy.get("releves") or {}).get(k))])
    with open(d / "historique_fruits_legumes.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["mois", "ecart_pct", "panier_suisse_chf", "panier_france_chf", "eur_chf", "nb_produits"])
        for r in series.get("panier") or []:
            w.writerow([r["m"], f(r["ecart"]), f(r["ch"]), f(r["fr"]), f(r["fx"]), r["n"]])
    with open(d / "produits.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["produit", "rayon", "unite", "prix_suisse_chf", "prix_france_chf", "prix_france_eur", "ecart_pct", "mois", "source_suisse", "source_france"])
        for p in produits_liste(pub):
            w.writerow([p["label"], RAYON_NOM[p["rayon"]], p["unite"], f(p["ch"]), f(p["fr"]), f(p["fr_eur"]), f(p["ecart"]),
                        p.get("mois") or "", p["src_ch"], p["src_fr"]])


# ------------------------------------------------------------------ main

def main(out: Path):
    latest, series, extra, site = charger()
    global PIED_IMAGE
    PIED_IMAGE = site["base_url"].split("://", 1)[-1]
    pcfg = yaml.safe_load((ROOT / "config/panier.yaml").read_text(encoding="utf-8"))
    zones_ess, ch_ess, maj_ess = essence_effective(latest, extra)
    lat2 = copy.deepcopy(latest)
    lat2.setdefault("carburant", {})["destinations"] = zones_ess
    lat2["carburant"]["ch"] = ch_ess
    sy = synthese(lat2, series, extra.get("pli"))
    pub = public_latest(latest, zones_ess, ch_ess)
    publies = bool(pub.get("magasins"))
    version = latest.get("genere_le", "").replace("-", "") + (maj_ess or "")[:10].replace("-", "")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    # fichiers statiques
    shutil.copy(SITE / "base.css", out / "style.css")
    for f in ("calc.js", "app.js", "essence.js", "direct.js"):
        shutil.copy(SITE / f, out / f)
    for d in ("fonts", "img", "vendor", "v1", "v2", "v3"):
        if (SITE / d).exists():
            shutil.copytree(SITE / d, out / d)
    shutil.copy(ROOT / "METHODOLOGIE.md", out / "METHODOLOGIE.md")
    (out / "data").mkdir()
    (out / "data/latest.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copy(DATA / "series.json", out / "data/series.json")
    if latest.get("origines"):
        (out / "data/origines.json").write_text(json.dumps(latest["origines"], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ecrire_csv(out / "data", sy, series, pub)
    for f in ("essence.json", "controles.json", "pli.json"):
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
    upd = (f"Prix mis à jour le 20 de chaque mois, essence chaque jour. Dernier relevé : {date_longue(gen)}, "
           f"prochain : {nxt.day} {MOIS[nxt.month - 1]}.")
    titre_fl, titre_viande, resume_fl, resume_fx = textes_synthese(sy, series)
    payload = {"latest": pub, "carte": extra.get("carte"), "credits": extra.get("credits"),
               "essence": {"zones": zones_ess, "genere_le": maj_ess}, "synth": sy, "root": ""}
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    g = sy["gaps"]
    desc = (f"Ce que la Suisse importe coûte {nf(sy['groupes']['import']['economie'], 0)} % de moins en France ; ce qu'elle produit, "
            f"mieux vaut souvent l'acheter suisse. Votre économie réelle, trajet compris, depuis votre localité.")
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": site["nom"], "url": site["base_url"] + "/",
                         "inLanguage": "fr-CH", "description": desc}, ensure_ascii=False)
    faq = faq_accueil(sy, mags_pub(pub), publies, latest.get("destinations") or [])
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": site["nom"], "url": site["base_url"] + "/", "inLanguage": "fr-CH", "description": desc},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                                            for q, a in faq]}]}, ensure_ascii=False)
    render("index.html", "", 0, "Courses Suisse ou France : où acheter quoi pour payer moins | Panier Suisse France", desc, "index",
           data_json=data_json, upd_text=upd, titre_fl=titre_fl, titre_viande=titre_viande, resume_fl=resume_fl,
           resume_fx=resume_fx, regles=sy["regles"], jsonld=jsonld, faq=faq, economie=nf(sy["total"]["economie"], 0),
           eco_import=nf(sy["groupes"]["import"]["economie"], 0), ecart_suisse=nf(sy["groupes"]["suisse"]["ecart"], 0),
           magasins_ch=sy["magasins_ch"], pli_annee=(sy.get("officiel") or {}).get("annee", ""), gap_m=nf(g["m"], 0),
           og_title="Payer moins là où ça ne coûte rien aux paysans suisses")

    dests = latest.get("destinations") or []
    mags = {d["id"]: d for d in ((pub.get("magasins") or {}).get("destinations") or [])}
    fx_now = sy["fx"]
    stations, ofdf_zones = donnees_stations(extra, dests, ch_ess, (extra.get("essence") or {}).get("fx", {}).get("eur_chf") or fx_now)
    (out / "data/stations.json").write_text(json.dumps(stations, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    route = calibrer_routes(latest["origines"], dests) if latest.get("origines") else {"facteur": 1.3, "kmh": 60}
    sig_body = ("Station : \nLocalité : \nPrix sans plomb 95 (CHF/L) : \nPrix diesel (CHF/L) : \nDate du relevé : \n"
                "(Une photo du panneau de prix est la bienvenue.)")
    import urllib.parse as _u
    signal_url = (f"mailto:{site['contact_email']}?subject=" + _u.quote("Prix essence") + "&body=" + _u.quote(sig_body)
                  if site.get("contact_email") else
                  "https://github.com/GregBrocard/Panier-suisse-france/issues/new?title=" + _u.quote("Prix essence : ")
                  + "&labels=prix&body=" + _u.quote(sig_body))
    lacs = json.loads((DATA / "lacs.json").read_text(encoding="utf-8"))["lacs"] if (DATA / "lacs.json").exists() \
        else (extra.get("carte") or {}).get("lacs", [])
    ess_data = {"root": "../", "lacs": lacs, "usure": sy["regles"]["usure_chf_km"], "ofdf_zones": ofdf_zones, "route": route,
                "ref_defaut": {"sp95": sy["essence"].get("sp95_ch"), "diesel": sy["essence"].get("diesel_ch")},
                "ofdf_date": ch_ess.get("date_texte") or "", "signal_url": signal_url}
    upd_ess = (f"Stations françaises : prix officiels du {date_longue(maj_ess)}. " if maj_ess else "") + \
              f"Prix moyens suisses : douane suisse, {ch_ess.get('date_texte') or 'mensuel'}."
    render("essence.html", "essence/", 1, "Prix de l'essence près de la Suisse : où faire le plein | Panier Suisse France",
           "Indiquez votre localité : la station qui vous fait le plus économiser, trajet compris, en Suisse ou en France voisine.",
           "essence", content=page_essence(sy, zones_ess, ch_ess, maj_ess, dests, fx_now), upd_text=upd_ess,
           usure=nf(sy["regles"]["usure_chf_km"]), data_json=json.dumps(ess_data, ensure_ascii=False).replace("</", "<\\/"))
    render("page.html", "zones/", 1, "Courses en France voisine : les 12 villes comparées | Panier Suisse France",
           "Annemasse, Saint-Julien, Pontarlier, Saint-Louis… Supermarchés, essence et économie depuis la Suisse, ville par ville.",
           "zones", content=page_zones_index(dests, mags, zones_ess, publies), wide=True)
    for d in dests:
        render("page.html", f"zones/{d['id']}/", 2, f"Courses à {d['nom']} : magasins, prix, économie | Panier Suisse France",
               f"Supermarchés de {d['nom']} et leur niveau de prix, essence du jour, économie depuis les villes suisses proches.",
               "zones", content=page_zone(d, sy, mags.get(d["id"]), zones_ess.get(d["id"]), latest.get("origines"), publies), wide=True)
    # baromètre courant + archives
    for i, m in enumerate(mois_list):
        prev = snaps[mois_list[i - 1]] if i > 0 else None
        image_partage(out / "og" / f"barometre-{m}.png", f"Baromètre de {mois_long(m)}", "Les mêmes courses en Suisse et en France",
                      og_chiffres(snaps[m]))
        others = [x for x in reversed(mois_list) if x != m]
        render("page.html", f"barometre/{m}/", 2, f"Baromètre des prix Suisse – France, {mois_long(m)} | Panier Suisse France",
               f"Écarts de prix entre la Suisse et la France en {mois_long(m)} : viande, fruits et légumes, produits laitiers, marques, essence.",
               "barometre", content=page_barometre(snaps[m], prev, others, site["base_url"], courant=False, series=series), script=SCRIPT_COPY,
               og_image=f"og/barometre-{m}.png")
    last = mois_list[-1]
    render("page.html", "barometre/", 1, f"Prix Suisse–France : le baromètre de {mois_long(last)} | Panier Suisse France",
           f"Chaque mois, les mêmes courses comparées en Suisse et en France. {mois_long(last).capitalize()} : viande {pc(g['m'])}, fruits et légumes {pc(g['f'])}.",
           "barometre", content=page_barometre(snaps[last], snaps[mois_list[-2]] if len(mois_list) > 1 else None,
                                               [x for x in reversed(mois_list) if x != last], site["base_url"], series=series),
           script=SCRIPT_COPY, og_image=f"og/barometre-{last}.png")
    h, sc = page_douane(sy["regles"])
    render("page.html", "douane/", 1, "Douane : ce qu'on peut ramener de France en 2026 | Panier Suisse France",
           "Combien de viande, d'alcool et de tabac peut-on ramener de France ? Calcul de la TVA et des droits de douane, et mode d'emploi de la détaxe.",
           "douane", content=h, script=sc)
    render("page.html", "methodologie/", 1, "Comment on compare les prix Suisse–France | Panier Suisse France",
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
    prods = produits_liste(pub)
    for pr in prods:
        render("page.html", f"prix/{pr['id']}/", 2, f"Prix {pr['label']} : Suisse ou France ? | Panier Suisse France",
               f"{pr['label']} : {nf(pr['ch'])} CHF en Suisse, {nf(pr['fr'])} CHF en France ({pc(pr['ecart'])}). Prix relevés chaque mois.",
               "prix", content=page_produit(pr, series, sy))
    render("page.html", "prix/", 1, "Prix Suisse–France produit par produit | Panier Suisse France",
           "Une trentaine de produits relevés chaque mois en Suisse et en France : viande, fruits, légumes, laitages, marques.",
           "prix", content=page_produits_index(prods, sy), wide=True)
    fo = DATA / "fermes_osm.json"
    fermes_info = None
    if fo.exists():
        fj = json.loads(fo.read_text(encoding="utf-8"))
        pts = [p_[:8] for p_ in fj.get("points") or []]
        (out / "data/fermes.json").write_text(json.dumps({"source": fj.get("source"), "genere_le": fj.get("genere_le"),
                                                          "types": fj.get("types"), "points": pts},
                                                         ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        fermes_info = {"total": len(pts), "par_type": fj.get("par_type")}
    render("page.html", "pourquoi-plus-cher/", 1, "Pourquoi la viande et les laitages sont plus chers en Suisse | Panier Suisse France",
           "Ce que paie l'écart de prix des produits suisses : salaires, règles d'élevage, part du producteur. Chiffres officiels.",
           None, content=page_pourquoi(sy))
    render("page.html", "acheter-suisse/", 1, "Acheter suisse moins cher : fermes, distributeurs, boucheries | Panier Suisse France",
           "Magasins à la ferme, distributeurs de lait et d'œufs, boucheries et marchés près de chez vous, et les bons plans.",
           "direct", content=page_acheter_suisse(site, fermes_info))
    render("page.html", "suisse/", 1, "Quel supermarché suisse est le moins cher ? | Panier Suisse France",
           "Aldi, Lidl, Migros, Coop, Denner : la synthèse des tests de prix publiés, avec leurs sources.", None,
           content=page_suisse(sy))
    render("page.html", "partenaires/", 1, "Partenaires et licences | Panier Suisse France",
           "Le calculateur et les données sur votre site, études sur le tourisme d'achat, règles de neutralité.", None,
           content=page_partenaires(site))
    render("page.html", "a-propos/", 1, "À propos | Panier Suisse France", "Un projet indépendant, des sources publiques.", None,
           content=page_apropos())
    render("page.html", "mentions-legales/", 1, "Mentions légales | Panier Suisse France", "Éditeur, hébergement, sources.", None,
           content=page_mentions(site))
    render("page.html", "confidentialite/", 1, "Confidentialité | Panier Suisse France", "Aucun cookie, aucune donnée personnelle.", None,
           content=page_confidentialite(site))
    render("page.html", "404.html", 0, "Page introuvable | Panier Suisse France", "Page introuvable.", None,
           content=f'<h1>Page introuvable</h1><p><a href="{site["base_url"]}/">Retour au calculateur</a></p>')

    # images et fichiers techniques
    image_partage(out / "og" / "accueil.png", "Payer moins là où ça ne coûte", "rien aux paysans suisses. Le calcul depuis votre ville.",
                  og_chiffres({"groupes": sy["groupes"], "gaps": g, "total": sy["total"]}))
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
    print(f"site v3.1 : {len(pages)} pages dans {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist"))
    main(Path(ap.parse_args().out))
