/* Calcul des économies : fonctions pures, sans accès à la page.
   Utilisé par le calculateur, le widget et les tests (tests/calc.test.mjs).
   Même formule que scraper/synthese.py (taux_economie). */
(function (root) {
  'use strict';

  // Part de la dépense suisse économisée en France, pour un mélange de catégories.
  // gaps : écart Suisse/France en % par catégorie (m viande, f fruits et légumes, c crèmerie, b épicerie et boissons)
  // idx  : niveau de prix du magasin choisi (1 = supermarché français moyen)
  // fch : niveau du magasin suisse habituel (1 = moyenne suisse), appliqué hors produits de marque (b)
  function savingsRate(gaps, w, idx, fch) {
    let tot = 0, sw = 0;
    for (const k of Object.keys(w)) {
      const g = gaps[k];
      if (g == null || isNaN(g)) continue;
      const gAdj = (1 + g / 100) * (k !== 'b' ? (fch || 1) : 1) / (idx || 1) - 1;
      tot += w[k] * (1 - 1 / (1 + gAdj));
      sw += w[k];
    }
    return sw > 0 ? tot / sw : 0;
  }

  // Droits de douane sur la viande au-delà de la franchise (CHF/kg par tranche)
  function meatDuty(excessKg, tiers) {
    let rest = Math.max(0, excessKg), done = 0, duty = 0;
    for (const [upTo, rate] of tiers) {
      const cap = upTo == null ? Infinity : upTo - done;
      const q = Math.min(rest, cap);
      duty += q * rate; rest -= q; done += q;
      if (rest <= 0) break;
    }
    return duty;
  }

  /* p : paramètres saisis
       spend (CHF), km (aller), minutes (aller, ou null), w (poids), idx, persons,
       mode ('essence' | 'diesel' | 'ev' | 'tp'), conso (L ou kWh /100 km), tpCost (CHF aller-retour),
       wear (bool), fill (bool), tank (L), fuelFR (CHF/L dans la zone), card (bool), vtime (CHF/h)
     S : synthèse (gaps, regles, essence, viande_fr_chf_kg, fx) */
  function compute(p, S) {
    const R = S.regles, spend = Math.max(0, +p.spend || 0), km = Math.max(0, +p.km || 0);
    const persons = Math.max(1, Math.round(+p.persons || 1));
    const rate = savingsRate(S.gaps, p.w, p.idx, p.fch);
    const fr = spend * (1 - rate), gross = spend - fr;
    const car = p.mode !== 'tp';
    const fuelCH = p.mode === 'diesel' ? S.essence.diesel_ch : S.essence.sp95_ch;
    let roadEnergy = 0;
    if (p.mode === 'tp') roadEnergy = Math.max(0, +p.tpCost || 0);
    else if (p.mode === 'ev') roadEnergy = 2 * km * (+p.conso || R.conso_ev_kwh) / 100 * R.electricite_chf_kwh;
    else roadEnergy = 2 * km * (+p.conso || 0) / 100 * (fuelCH || 2.2);
    const roadWear = car && p.wear ? 2 * km * R.usure_chf_km : 0;
    const road = roadEnergy + roadWear;
    let fuelG = 0;
    if (p.fill && car && p.mode !== 'ev' && fuelCH && p.fuelFR) fuelG = Math.max(0, +p.tank || 0) * (fuelCH - p.fuelFR);
    const cardFee = p.card ? fr * R.frais_carte : 0;
    const lim = R.franchise_chf * persons;
    const vat = fr > lim ? fr * R.tva_alimentaire : 0;
    const meatKg = S.viande_fr_chf_kg ? (p.w.m || 0) * fr / S.viande_fr_chf_kg : 0;
    const meatExcess = Math.max(0, meatKg - R.viande_franchise_kg * persons);
    const duty = meatDuty(meatExcess, R.viande_droits);
    // droits sur la viande : estimation affichée en avertissement, non déduite (la quantité réelle est inconnue)
    const net = gross - road + fuelG - vat - cardFee;
    const frEUR = S.fx ? fr / S.fx : null;
    const detaxe = frEUR != null && frEUR > R.detaxe_min_eur ? fr * R.tva_fr_alimentaire / (1 + R.tva_fr_alimentaire) : 0;
    const minsRoad = p.minutes != null ? 2 * p.minutes : Math.round(2 * km);
    const mins = minsRoad + R.douane_minutes;
    const vt = +p.vtime > 0 ? +p.vtime : 25;
    return { spend, km, rate, fr, gross, roadEnergy, roadWear, road, fuelG, cardFee, lim, vat, meatKg, meatExcess,
             duty, net, detaxe, minsRoad, mins, vt, vGiven: +p.vtime > 0, timeC: vt * mins / 60, persons };
  }

  // Montant de courses à partir duquel le trajet est rentable (null si jamais)
  function breakEven(p, S) {
    const f = s => compute(Object.assign({}, p, { spend: s }), S).net;
    if (f(5000) <= 0) return null;
    if (f(0) > 0) return 0;
    let lo = 0, hi = 5000;
    for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (f(mid) > 0) hi = mid; else lo = mid; }
    return hi;
  }

  // Mode « Où faire le plein » : gain net d'un détour vers une station.
  // p : litres, conso (L/100 km), pref (prix habituel CHF/L), wear (bool), usure (CHF/km)
  // st : { km (aller), prix (CHF/L) }
  function fuelGain(p, st) {
    const fuel = (p.litres || 0) * ((p.pref || 0) - st.prix);
    const drive = 2 * st.km * (p.conso || 0) / 100 * (p.pref || st.prix);
    const wear = p.wear ? 2 * st.km * (p.usure || 0) : 0;
    return { fuel, drive, wear, net: fuel - drive - wear };
  }

  function haversine(a, b) {
    const R = 6371, r = Math.PI / 180;
    const dl = (b[0] - a[0]) * r, dn = (b[1] - a[1]) * r;
    const h = Math.sin(dl / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dn / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  const api = { savingsRate, meatDuty, compute, breakEven, fuelGain, haversine };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PSF = api;
})(typeof window !== 'undefined' ? window : globalThis);
