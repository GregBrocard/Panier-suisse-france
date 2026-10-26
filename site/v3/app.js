/* Panier Suisse France — page principale (calculateur, magasins, graphiques). */
(function(){
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const L = D.latest, SY = D.synth, ROOT = D.root || ''; let H = null;
  const $ = s => document.querySelector(s);
  const nf = (v,d=2) => v==null||isNaN(v) ? '—' : v.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).replace(/[  ]/g,' ');
  const pc = v => v==null||isNaN(v) ? '—' : (v>0?'+':v<0?'−':'') + Math.abs(Math.round(v)) + ' %';
  const MO = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
  const ml = m => { if(!m) return '—'; const [y,mm]=m.split('-'); return MO[+mm-1]+' '+y; };
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[-'’]/g,' ');
  const store = { get(){ try{ return JSON.parse(localStorage.getItem('psf-v2')||'{}'); }catch(e){ return {}; } },
                  set(v){ try{ localStorage.setItem('psf-v2', JSON.stringify(v)); }catch(e){} } };
  const Q = new URLSearchParams(location.search);
  if(Q.get('embed')==='1') document.body.classList.add('embed');

  // ---------- données
  const DEST = L.destinations || [];
  const MAG = L.magasins && L.magasins.destinations ? Object.fromEntries(L.magasins.destinations.map(d=>[d.id,d])) : {};
  let ORI = null, oriP = null, NAMES = [], dIdx = {};
  const fuel = L.carburant||{}, fch = fuel.ch||{};
  const ESS = D.essence && D.essence.zones ? D.essence.zones : null;
  const fd = id => (ESS && ESS[id]) || (fuel.destinations||{})[id] || null;
  const roll = SY.fl_roll||[];
  const meat = (L.viande||[]).filter(v=>v.ecart!=null);
  const br = (L.marques||[]).filter(v=>v.ecart!=null);
  const G = SY.gaps;

  function loadOri(){
    if(oriP) return oriP;
    oriP = fetch(ROOT+'data/origines.json').then(r=>{ if(!r.ok) throw new Error(r.status); return r.json(); }).then(j=>{
      ORI=j; NAMES=ORI.liste.map(x=>norm(x[0])); dIdx=Object.fromEntries((ORI.destinations||[]).map((id,i)=>[id,i]));
      if(document.activeElement===inp && inp.value){ hits=search(inp.value); cur=hits.length?0:-1; renderList(); }
      return ORI; }).catch(()=>{ oriP=null; lst.innerHTML='<li aria-disabled="true"><span>Liste des localités indisponible, réessayez.</span></li>'; lst.hidden=false; });
    return oriP;
  }

  // ---------- état (rien n'est présélectionné)
  const MIX = SY.mix;
  const st = {o:null, dest:null, store:'avg', mix:'mixte', kmManual:false, shown:false};
  const trip = (oi,id) => { if(!ORI||oi==null||!id) return null; const r=ORI.dist[oi]; const k=dIdx[id]; return r&&k!=null&&r[2*k]!=null ? [r[2*k],r[2*k+1]] : null; };

  // ---------- autocomplétion
  const BIG = new Set(['zurich','geneve','basel','lausanne','bern','winterthur','luzern','st. gallen','lugano','biel/bienne','thun','bellinzona','koniz','fribourg','la chaux de fonds','schaffhausen','chur','vernier','uster','sion','lancy','neuchatel','emmen','yverdon les bains','zug','kriens','rapperswil jona','dubendorf','montreux','dietikon','frauenfeld','wetzikon','baar','riehen','meyrin','carouge','wadenswil','renens','aarau','allschwil','kreuzlingen','onex','bulle','nyon','vevey','olten','baden','monthey','martigny','sierre','gland','morges','pully','thonex','versoix','delemont','porrentruy','le locle','ecublens','prilly','aigle','payerne','plan les ouates','chene bourg','grand lancy','rolle','aubonne','orbe','vallorbe','le sentier','sainte croix','estavayer le lac','romont','chatel st denis','bex','villeneuve','la tour de peilz','lutry','epalinges','echallens','cossonay','moudon','avenches','grandson','fleurier','boudry','peseux','saint imier','tramelan','moutier','coppet','saint cergue','begnins']);
  const inp=$('#from'), lst=$('#fromList'); let hits=[], cur=-1;
  const label = i => ORI.liste[i][0];
  function search(q){
    if(!ORI) return [];
    q=norm(q).trim(); if(!q) return [];
    const isNpa=/^\d/.test(q), out=[];
    for(let i=0;i<ORI.liste.length&&out.length<80;i++){ const n=NAMES[i]; if(isNpa?String(ORI.liste[i][2]).startsWith(q):(n.startsWith(q)||n.includes(' '+q))) out.push(i); }
    const big=i=>BIG.has(NAMES[i])?0:1;
    out.sort((a,b)=>(NAMES[a].startsWith(q)?0:1)-(NAMES[b].startsWith(q)?0:1)||big(a)-big(b)||NAMES[a].length-NAMES[b].length);
    return out.slice(0,8);
  }
  function renderList(){
    if(!ORI){ lst.innerHTML='<li aria-disabled="true"><span>Chargement des localités…</span></li>'; lst.hidden=false; return; }
    if(!hits.length){ lst.innerHTML='<li aria-disabled="true"><span>Aucune localité trouvée</span></li>'; lst.hidden=false; return; }
    lst.innerHTML=hits.map((i,k)=>{const [n,c,p]=ORI.liste[i];return `<li role="option" id="o${i}" data-i="${i}" aria-selected="${k===cur}"><span>${esc(n)}</span><small>${p} ${c}</small></li>`;}).join('');
    lst.hidden=false; inp.setAttribute('aria-expanded','true'); if(cur>=0) inp.setAttribute('aria-activedescendant','o'+hits[cur]);
  }
  function closeList(){ lst.hidden=true; inp.setAttribute('aria-expanded','false'); cur=-1; }
  function setOrigin(i){ st.o=i; inp.value=label(i); closeList(); $('#slotFrom').classList.remove('bad'); st.kmManual=false; fillDest(); update(); }
  inp.addEventListener('focus',loadOri);
  inp.addEventListener('input',()=>{ st.o=null; loadOri(); hits=search(inp.value); cur=hits.length?0:-1; renderList(); });
  inp.addEventListener('keydown',e=>{
    if(e.key==='ArrowDown'){ e.preventDefault(); if(lst.hidden){hits=search(inp.value);cur=0;} else cur=Math.min(hits.length-1,cur+1); renderList(); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); cur=Math.max(0,cur-1); renderList(); }
    else if(e.key==='Enter'){ e.preventDefault(); if(hits[cur]!=null) setOrigin(hits[cur]); }
    else if(e.key==='Escape'){ closeList(); }
  });
  lst.addEventListener('mousedown',e=>{ const li=e.target.closest('li[data-i]'); if(li){ e.preventDefault(); setOrigin(+li.dataset.i); }});
  inp.addEventListener('blur',()=>setTimeout(()=>{ if(!lst.hidden){ if(hits.length===1||(hits.length&&norm(inp.value)===NAMES[hits[0]])) setOrigin(hits[0]); else closeList(); } },150));

  // ---------- destinations
  const sel=$('#to');
  function fillDest(){
    const rows=DEST.map(x=>({x,t:trip(st.o,x.id)})).sort((a,b)=>(a.t?a.t[1]:1e9)-(b.t?b.t[1]:1e9)||a.x.nom.localeCompare(b.x.nom));
    sel.innerHTML=`<option value="" ${st.dest?'':'selected'} disabled>choisir un lieu</option>`+rows.map(r=>`<option value="${r.x.id}" ${r.x.id===st.dest?'selected':''}>${esc(r.x.nom)}${r.t?` (${r.t[0]} km)`:''}</option>`).join('');
    sel.classList.toggle('empty',!st.dest); fitSelect();
  }
  const meas=document.createElement('span'); meas.style.cssText='position:absolute;visibility:hidden;white-space:pre;left:-9999px'; document.body.appendChild(meas);
  function fitSelect(){ const t = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : ''; meas.style.font=getComputedStyle(sel).font; meas.textContent=t; sel.style.width=(meas.getBoundingClientRect().width+parseFloat(getComputedStyle(sel).fontSize)*1.1)+'px'; }
  window.addEventListener('resize',fitSelect); if(document.fonts&&document.fonts.ready) document.fonts.ready.then(fitSelect);
  function setDest(id){ if(!DEST.some(x=>x.id===id)) return; st.dest=id; st.store='avg'; st.kmManual=false; sel.value=id; sel.classList.remove('empty'); $('#slotTo').classList.remove('bad'); fitSelect(); update(); }
  sel.addEventListener('change',()=>setDest(sel.value));

  // ---------- habitudes
  $('#mix').innerHTML=MIX.map(m=>`<button type="button" data-m="${m.id}" aria-pressed="${m.id===st.mix}">${m.label}</button>`).join('');
  function setMix(id){ if(!MIX.some(m=>m.id===id)) return; st.mix=id; $('#mix').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x.dataset.m===id)); }
  $('#mix').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;setMix(b.dataset.m);update();});
  function syncFill(){ const on=$('#fill').checked && $('#mode').value!=='tp' && $('#mode').value!=='ev'; $('#tank').disabled=!on; $('#tankField').classList.toggle('off',!on); }
  function syncMode(){
    const m=$('#mode').value, car=m!=='tp';
    $('#consoLab').textContent = m==='ev' ? 'Électricité (kWh/100 km)' : m==='diesel' ? 'Diesel (L/100 km)' : 'Essence (L/100 km)';
    if(m==='ev' && (+$('#conso').value<10)) $('#conso').value=SY.regles.conso_ev_kwh;
    if(m!=='ev' && (+$('#conso').value>=12)) $('#conso').value=7;
    $('#conso').disabled=!car; $('#tpField').hidden=car; $('#wear').disabled=!car; syncFill();
  }
  $('#fill').addEventListener('change',()=>{ syncFill(); update(); });
  $('#mode').addEventListener('change',()=>{ syncMode(); update(); });
  $('#km').addEventListener('input',()=>{st.kmManual=true;update();});
  ['#spend','#conso','#persons','#tank','#vtime','#tpCost'].forEach(s=>$(s).addEventListener('input',()=>{ if(s==='#spend') $('#slotSpend').classList.remove('bad'); update(); }));
  ['#wear','#card','#storeCH'].forEach(s=>$(s).addEventListener('change',update));
  document.querySelectorAll('.info').forEach(box=>{ const b=box.querySelector('.ibtn'), p=box.querySelector('.pop');
    b.addEventListener('click',e=>{ e.preventDefault(); e.stopPropagation(); const open=p.hidden; document.querySelectorAll('.info .pop').forEach(x=>x.hidden=true); document.querySelectorAll('.info .ibtn').forEach(x=>x.setAttribute('aria-expanded','false')); p.hidden=!open; b.setAttribute('aria-expanded',String(open)); }); });
  document.addEventListener('click',e=>{ if(!e.target.closest('.info')){ document.querySelectorAll('.info .pop').forEach(x=>x.hidden=true); document.querySelectorAll('.info .ibtn').forEach(x=>x.setAttribute('aria-expanded','false')); } });

  // ---------- validation et calcul
  function missing(){
    const m=[];
    if(st.o==null) m.push(['slotFrom','votre lieu de départ']);
    if(!st.dest) m.push(['slotTo','la ville où vous faites vos courses']);
    if(!(+$('#spend').value>0)) m.push(['slotSpend','le montant de vos courses']);
    return m;
  }
  $('#go').addEventListener('click',()=>{
    const m=missing();
    ['slotFrom','slotTo','slotSpend'].forEach(id=>$('#'+id).classList.toggle('bad',m.some(x=>x[0]===id)));
    if(m.length){ $('#missing').hidden=false; $('#missing').textContent='Il manque '+m.map(x=>x[1]).join(', ')+'. Complétez les cases en rouge.'; return; }
    $('#missing').hidden=true; st.shown=true; update(); document.getElementById('answer').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth', block:'start'});
  });

  function params(idx, spend){
    const t=trip(st.o,st.dest);
    if(!st.kmManual && t) $('#km').value=t[0];
    const mode=$('#mode').value, z=fd(st.dest), fk = mode==='diesel'?'diesel':'sp95';
    return { spend: spend!=null?spend:+$('#spend').value||0, km:+$('#km').value||0, minutes: t&&!st.kmManual?t[1]:null,
      w: MIX.find(m=>m.id===st.mix).w, idx, persons:+$('#persons').value||1, mode, conso:+$('#conso').value||0,
      tpCost:+$('#tpCost').value||0, wear:$('#wear').checked, fill:$('#fill').checked, tank:+$('#tank').value||0,
      fuelFR: z&&z.moyenne_chf?z.moyenne_chf[fk]:null, card:$('#card').checked, vtime:+$('#vtime').value,
      fch: (SY.magasins_ch.find(m=>m.id===$('#storeCH').value)||{f:1}).f };
  }
  const compute = (idx, spend) => PSF.compute(params(idx, spend), SY);
  function idxNow(){
    const m=MAG[st.dest]; if(!m||!m.magasins.length) return {idx:1,name:null};
    if(st.store==='avg') return {idx:m.indice_median||1,name:null};
    const s=m.magasins.find(x=>String(x.dm)===String(st.store)); return s?{idx:s.indice,name:s.nom}:{idx:m.indice_median||1,name:null};
  }
  function save(){
    store.set({o: st.o!=null&&ORI ? ORI.liste[st.o].slice(0,2).join('|') : null, dest: st.dest, spend: $('#spend').value, mix: st.mix,
      conso: $('#conso').value, persons: $('#persons').value, vtime: $('#vtime').value, fill: $('#fill').checked, tank: $('#tank').value,
      mode: $('#mode').value, wear: $('#wear').checked, card: $('#card').checked, tp: $('#tpCost').value, storeCH: $('#storeCH').value});
  }
  function update(){ if(!st.kmManual){ const t=trip(st.o,st.dest); if(t) $('#km').value=t[0]; } renderStores(); drawMap(); if(st.shown && !missing().length) showResult(); save(); }
  function shareURL(){
    const u=new URL(location.href.split('#')[0]); const p=u.searchParams; [...p.keys()].forEach(k=>{ if(k!=='embed') p.delete(k); });
    if(st.o!=null&&ORI){ p.set('de', ORI.liste[st.o][0]); p.set('ct', ORI.liste[st.o][1]); }
    if(st.dest) p.set('a', st.dest); if(+$('#spend').value>0) p.set('m', $('#spend').value);
    if(st.mix!=='mixte') p.set('mix', st.mix); if(+$('#persons').value>1) p.set('p', $('#persons').value);
    if($('#mode').value!=='essence') p.set('mode', $('#mode').value);
    if($('#storeCH').value!=='discount') p.set('ch', $('#storeCH').value);
    return u.toString();
  }
  function bePlot(p, be){
    const S0=0, S1=Math.max(300, Math.ceil((Math.max(+p.spend||0, be||0)*1.6)/50)*50), N=24, pts=[];
    for(let i=0;i<=N;i++){ const s=S0+(S1-S0)*i/N; pts.push([s, PSF.compute(Object.assign({},p,{spend:s}),SY).net]); }
    const ys=pts.map(x=>x[1]), y0=Math.min(0,...ys), y1=Math.max(10,...ys), W=320, Hh=120, pad=24;
    const X=s=>pad+(s-S0)/(S1-S0)*(W-pad-6), Y=v=>6+(y1-v)/(y1-y0||1)*(Hh-pad-6);
    const path='M'+pts.map(q=>X(q[0]).toFixed(1)+' '+Y(q[1]).toFixed(1)).join('L');
    const you=+p.spend||0, yv=PSF.compute(p,SY).net;
    return `<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="Économie selon le montant des courses"><line class="ax" x1="${pad}" x2="${W-6}" y1="${Hh-pad}" y2="${Hh-pad}"/><line class="zero" x1="${pad}" x2="${W-6}" y1="${Y(0)}" y2="${Y(0)}"/><path class="ln" d="${path}"/>${you?`<circle class="pt" cx="${X(Math.min(you,S1))}" cy="${Y(yv)}" r="4"/>`:''}<text x="${pad}" y="${Hh-6}">0 CHF</text><text x="${W-6}" y="${Hh-6}" text-anchor="end">${S1} CHF de courses</text><text x="${pad-4}" y="${Y(0)+4}" text-anchor="end">0</text></svg>`;
  }
  function showResult(){
    const {idx,name}=idxNow(), p=params(idx), c=PSF.compute(p,SY), dd=DEST.find(x=>x.id===st.dest)||{}, o=ORI&&st.o!=null?ORI.liste[st.o]:null;
    $('#waiting').hidden=true; $('#res').hidden=false;
    const t=trip(st.o,st.dest);
    // fourchette : du magasin le moins cher au plus cher de la ville
    const ms=(MAG[st.dest]&&MAG[st.dest].magasins)||[];
    let rng='';
    if(ms.length>1 && st.store==='avg'){ const ix=ms.map(x=>x.indice); const lo=PSF.compute(Object.assign({},p,{idx:Math.max(...ix)}),SY).net, hi=PSF.compute(Object.assign({},p,{idx:Math.min(...ix)}),SY).net;
      rng=`<p class="how">Selon le magasin choisi : de ${lo<0?'−':''}${nf(Math.abs(lo),0)} à ${hi<0?'−':''}${nf(Math.abs(hi),0)} CHF.</p>`; }
    $('#verdict').innerHTML=(c.net>=0
      ? `<span class="amount">${nf(c.net,0)}<small>CHF</small></span><span class="what">d'économie à ${esc(name||dd.nom)}</span>`
      : `<span class="amount loss">−${nf(-c.net,0)}<small>CHF</small></span><span class="what">de perte : mieux vaut rester en Suisse</span>`)
      + `<p class="how">${esc(o?o[0]:'')} → ${esc(dd.nom)} : ${c.km} km${t?`, environ ${t[1]} min`:''}${dd.passage?', '+esc(dd.passage):''}. Trajet aller-retour compris.</p>`
      + rng + `<p class="how">Franchise : jusqu'à ${nf(c.lim,0)} CHF d'achats sans TVA suisse (${c.persons} adulte${c.persons>1?'s':''}).</p>`
      + `<div class="share"><button type="button" id="shareBtn">Partager ce calcul</button><a id="waBtn" href="https://wa.me/?text=${encodeURIComponent('Mes courses en France : '+(c.net>=0?nf(c.net,0)+' CHF d\'économie':'pas rentable')+' — '+shareURL())}" target="_blank" rel="noopener">WhatsApp</a><span class="muted" id="shareMsg" aria-live="polite"></span></div>`;
    const r=(a,b,cls='')=>`<div class="r ${cls}"><span>${a}</span><span>${b}</span></div>`, sg=v=>(v>=0?'− ':'+ ')+nf(Math.abs(v),0)+' CHF';
    let h=r('Vos courses en Suisse',nf(c.spend,0)+' CHF')+r('Les mêmes en France',nf(c.fr,0)+' CHF')+r('Différence',sg(c.gross));
    if(p.mode==='tp') h+=r('Billet aller-retour','+ '+nf(c.roadEnergy,0)+' CHF');
    else h+=r(`${p.mode==='ev'?'Électricité':p.mode==='diesel'?'Diesel':'Essence'} aller-retour, ${2*c.km} km`,'+ '+nf(c.roadEnergy,0)+' CHF');
    if(c.roadWear) h+=r('Usure de la voiture (TCS)','+ '+nf(c.roadWear,0)+' CHF');
    if(p.fill && c.fuelG) h+=r('Plein en France',sg(c.fuelG));
    if(c.cardFee) h+=r('Frais de carte en euros','+ '+nf(c.cardFee,0)+' CHF');
    if(c.vat) h+=r('TVA à la douane','+ '+nf(c.vat,0)+' CHF');
    h+=r(c.net>=0?'Vous économisez':'Vous perdez',nf(Math.abs(c.net),0)+' CHF','t');
    const be=PSF.breakEven(p,SY);
    const beTxt = be==null?'<b>Pas rentable</b>, même avec 5000 CHF de courses.':be===0?'<b>Rentable dès le premier franc.</b>':`Rentable dès <b>${nf(Math.ceil(be/5)*5,0)} CHF</b> de courses.`;
    const vatTxt = be!=null && be < c.lim ? ` Attention : au-delà de ${nf(c.lim,0)} CHF, la TVA suisse s'ajoute sur tout, d'où la marche sur la courbe.` : '';
    h+=`<div class="be"><span>${beTxt}${vatTxt}</span>${bePlot(p,be)}</div>`;
    if(c.fr>c.lim) h+=`<p class="warn">Plus de ${nf(c.lim,0)} CHF d'achats : déclarez-les à la douane, la TVA suisse s'applique sur tout.</p>`;
    if(c.meatExcess>0) h+=`<p class="warn">Votre budget correspond à environ ${nf(c.meatKg,1)} kg de viande. Au-delà de ${c.persons} kg, la douane prend 17 CHF par kg en plus (environ ${nf(c.duty,0)} CHF ici, non compté ci-dessus).</p>`;
    if(c.detaxe>0) h+=`<p class="muted">Détaxe possible : jusqu'à ${nf(c.detaxe,0)} CHF de TVA française remboursable si vous dépensez plus de 100 € dans le même magasin, moins les frais de l'opérateur (non compté). <a href="${ROOT}douane/">Comment faire</a>.</p>`;
    const after=c.net-c.timeC;
    h+=`<div class="opp"><b>${c.mins} minutes</b> (aller-retour ${c.minsRoad} min, plus 15 min de douane et de parking). C'est le coût d'opportunité : ce temps, vous pourriez le passer à autre chose. ${c.vGiven?'À':'À titre d\'exemple, à'} ${nf(c.vt,0)} CHF de l'heure, il vaut <b>${nf(c.timeC,0)} CHF</b>${after>=0?`, et le trajet reste avantageux (${nf(after,0)} CHF de gain).`:`, soit plus que ce que vous économisez (${nf(-after,0)} CHF de perte si l'on compte le temps).`}</div>`;
    $('#bill').innerHTML=h;
    const pr=$('#partners'); if(pr) pr.hidden=false;
    $('#shareBtn').addEventListener('click',async()=>{ const url=shareURL(); try{ if(navigator.share){ await navigator.share({title:'Mes courses en France',url}); return; } await navigator.clipboard.writeText(url); $('#shareMsg').textContent='Lien copié.'; }catch(e){ $('#shareMsg').textContent=url; } });
  }

  // ---------- magasins
  function renderStores(){
    const m=MAG[st.dest], dd=DEST.find(x=>x.id===st.dest);
    $('#magTitle').textContent = dd ? 'Les magasins à '+dd.nom : 'Les magasins';
    $('#magPhoto').hidden = !dd; $('#magSplit').classList.toggle('solo', !dd);
    $('#magLede').innerHTML = dd ? `Du moins cher au plus cher. Choisissez un magasin pour refaire le calcul à son niveau de prix. <a href="${ROOT}zones/${dd.id}/">Tout sur ${esc(dd.nom)}</a>.` : 'Choisissez une ville dans le formulaire pour voir ses magasins, du moins cher au plus cher.';
    $('#magasins').hidden=!dd;
    if(!dd){ $('#stores').innerHTML='<p class="muted" style="padding:14px 0;border-top:1px solid var(--ink)">Choisissez une ville dans le formulaire pour voir ses magasins.</p>'; $('#magSrc').textContent=''; $('#how2').hidden=true; return; }
    if(!m||!m.magasins.length){ $('#stores').innerHTML='<p class="muted" style="padding:14px 0;border-top:1px solid var(--ink)">Pas encore de prix par magasin pour cette ville : le calcul utilise la moyenne française.</p>'; $('#magSrc').textContent=''; return; }
    const ready=st.o!=null && +$('#spend').value>0;
    const lvl=idx=>{ const p=Math.round(Math.abs(idx-1)*100);
      return p<1?'<span class="lv">Prix dans la moyenne française</span>':`<span class="lv ${idx<1?'down':'up'}">${p} % ${idx<1?'moins cher':'plus cher'} qu'un supermarché français moyen</span>`; };
    const row=(id,n,s,idx)=>{ const on=String(st.store)===String(id), c=ready?compute(idx):null;
      return `<label class="store"><input type="radio" name="store" value="${id}" ${on?'checked':''}><span><span class="n">${esc(n)}</span><br><span class="s">${s}</span><br>${lvl(idx)}</span><span class="g">${c?(c.net>=0?'':'−')+nf(Math.abs(c.net),0)+' CHF':'—'}<small>${c?(c.net>=0?'économisés':'perdus'):''}</small></span></label>`; };
    $('#stores').innerHTML=row('avg','Tous les magasins de la ville',m.magasins.length>1?m.magasins.length+' magasins, prix du magasin du milieu':'1 seul magasin référencé',m.indice_median)+m.magasins.map(s=>row(s.dm,s.nom,esc(s.adresse||s.cp||''),s.indice)).join('');
    $('#stores').onchange=e=>{ st.store=e.target.value; update(); };
    $('#how2').hidden=false;
    $('#magSrc').innerHTML=`${ready?'Montant à droite : ce que vous économisez dans ce magasin, trajet compris.':'Remplissez le formulaire pour voir combien vous économisez dans chaque magasin.'} Source des prix par magasin : <a href="https://www.quechoisir.org/carte-interactive-drives-n21243/" target="_blank" rel="noopener">UFC-Que Choisir</a>.`;
  }

  // ---------- carte
  const C=D.carte;
  function drawMap(){
    const el=$('#map'); if(!C||!el) return;
    const o=st.o!=null&&ORI?ORI.liste[st.o]:null; let oc=(o&&ORI.coords)?[ORI.coords[st.o][1],ORI.coords[st.o][0]]:null; const dd=DEST.find(x=>x.id===st.dest);
    const horsCarte = oc && (oc[0]>C.bbox[2] || oc[1]>C.bbox[3] || oc[0]<C.bbox[0] || oc[1]<C.bbox[1]); if(horsCarte) oc=null;
    const pts=DEST.map(x=>[x.lon,x.lat]); if(oc) pts.push(oc);
    let x0=Math.min(...pts.map(p=>p[0]))-.25,x1=Math.max(...pts.map(p=>p[0]))+.25,y0=Math.min(...pts.map(p=>p[1]))-.2,y1=Math.max(...pts.map(p=>p[1]))+.2;
    const k=Math.cos((y0+y1)/2*Math.PI/180); let w=(x1-x0)*k,h=y1-y0;
    if(w/h>16/9){const nh=w*9/16;y0-=(nh-h)/2;y1+=(nh-h)/2;h=nh;} else {const nw=h*16/9;x0-=(nw-w)/2/k;x1+=(nw-w)/2/k;w=nw;}
    const W=800,Hh=450,X=lon=>(lon-x0)*k/w*W,Y=lat=>(y1-lat)/h*Hh, path=ring=>'M'+ring.map(p=>X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1)).join('L')+'Z';
    let svg=`<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="Carte de la frontière franco-suisse">`;
    for(const [iso,rings] of Object.entries(C.pays).sort((a,b)=>(a[0]==='CHE')-(b[0]==='CHE'))) svg+=`<path class="${iso==='CHE'?'ch':'other'}" d="${rings.map(path).join('')}"/>`;
    for(const r of C.lacs) svg+=`<path class="lake" d="${path(r)}"/>`;
    svg+=`<text class="c" x="${W-22}" y="38" text-anchor="end">Suisse</text><text class="c" x="22" y="38">France</text>`;
    if(oc&&dd) svg+=`<line class="route" x1="${X(oc[0])}" y1="${Y(oc[1])}" x2="${X(dd.lon)}" y2="${Y(dd.lat)}"/>`;
    for(const x of DEST){const on=x.id===st.dest; svg+=`<g data-d="${x.id}"><title>${esc(x.nom)}</title><circle class="hit" cx="${X(x.lon)}" cy="${Y(x.lat)}" r="22"/><circle class="dst ${on?'on':''}" cx="${X(x.lon)}" cy="${Y(x.lat)}" r="${on?10:6}"/></g>`;}
    if(dd) svg+=`<text x="${X(dd.lon)-16}" y="${Y(dd.lat)+8}" text-anchor="end">${esc(dd.nom)}</text>`;
    if(oc) svg+=`<rect class="org" x="${X(oc[0])-8}" y="${Y(oc[1])-8}" width="16" height="16"/><text x="${X(oc[0])+16}" y="${Y(oc[1])+8}" style="font-weight:500">${esc(o[0])}</text>`;
    svg+=`</svg><span class="cap">${horsCarte?'Votre localité est hors de cette carte. ':''}Touchez un point pour choisir la ville</span>`;
    el.innerHTML=svg;
    el.querySelectorAll('g[data-d]').forEach(g=>g.addEventListener('click',()=>setDest(g.dataset.d)));
  }

  // ---------- crédits photo
  const CR=D.credits||{};
  document.querySelectorAll('[data-credit]').forEach(el=>{const c=CR[el.dataset.credit]; if(c) el.innerHTML=`<a href="${esc(c.page)}" target="_blank" rel="noopener">${esc(c.auteur.split(',')[0])}</a>, ${esc(c.licence)}`;});

  // ---------- chiffres du mois et tableaux
  const E=SY.essence||{};
  const fig=(k,v,s)=>`<div class="fig"><span>${k}</span><b>${pc(v)}</b><small>${s}</small></div>`;
  $('#figs').innerHTML=fig('Viande',G.m,'plus cher en Suisse')+fig('Fruits et légumes',G.f,'plus cher en Suisse')+fig('Produits laitiers',G.c,'plus cher en Suisse')
    +fig('Épicerie et boissons',G.b,'plus cher en Suisse')+fig('Essence',E.sp95_ecart,'sans plomb, Genève comparé à la France voisine');
  const gp=g=>`<span class="${g>0?'up':'down'}">${pc(g)}</span>`;
  const rep=x=>x?`<span class="flag" title="Trop peu de produits ce mois-ci">valeur du mois précédent</span>`:'';
  const off=(L.officiel.produits||[]).filter(p=>p.ecart!=null && (p.groupe||'fl')==='fl');
  const crem=(L.officiel.produits||[]).filter(p=>p.ecart!=null && p.groupe==='cremerie');
  const un=u=>u==='L'?'L':u;
  const lab=(t,h)=>{ const hs=[...document.querySelectorAll(t+' thead th')].map(x=>x.textContent); document.querySelectorAll(t+' tbody tr').forEach(tr=>[...tr.children].forEach((td,i)=>td.setAttribute('data-label',hs[i]||''))); };
  $('#tOff tbody').innerHTML=off.map(p=>`<tr class="click" tabindex="0" data-id="${p.id}"><td>${esc(p.label)}<small>${ml(p.mois)}</small></td><td>${nf(p.ch)} CHF</td><td>${nf(p.fr_chf)} CHF<small>soit ${nf(p.fr_eur)} EUR</small></td><td>${gp(p.ecart)}</td></tr>`).join('');
  $('#tCrem tbody').innerHTML=crem.map(p=>`<tr><td>${esc(p.label)}<small>${ml(p.mois)}, par ${un(p.unit)}</small></td><td>${nf(p.ch)} CHF/${un(p.unit)}</td><td>${nf(p.fr_chf)} CHF/${un(p.unit)}<small>soit ${nf(p.fr_eur)} EUR</small></td><td>${gp(p.ecart)}</td></tr>`).join('') || '<tr><td colspan="4" class="muted">Disponible au prochain relevé.</td></tr>';
  $('#tMeat tbody').innerHTML=(L.viande||[]).map(v=>`<tr><td>${esc(v.label)}${rep(v.reprise)}<small>Suisse : prix Migros, médiane de ${v.ch_n} produit${v.ch_n>1?'s':''}</small></td><td>${nf(v.ch_migros||v.ch)} CHF</td><td>${nf(v.fr_chf)} CHF<small>soit ${nf(v.fr_eur)} EUR</small></td><td>${gp(v.ch_migros&&v.fr_chf?(v.ch_migros/v.fr_chf-1)*100:v.ecart)}</td></tr>`).join('');
  $('#tBrand tbody').innerHTML=(L.marques||[]).filter(v=>(v.fr_n||0)>=5).map(v=>{const u=v.unit==='L'?'L':'kg', n=v.fr_n||0; return `<tr><td>${esc(v.label)}${rep(v.reprise_ch||v.reprise_fr)}<small>${n} relevés en France${v.fenetre_mois?' sur '+v.fenetre_mois+' mois':''}${n<10?', indicatif':''}</small></td><td>${v.ch_unit!=null?nf(v.ch_unit)+' CHF/'+u:'—'}</td><td>${v.fr_unit_chf!=null?nf(v.fr_unit_chf)+' CHF/'+u+`<small>soit ${nf(v.fr_unit_eur)} EUR/${u}</small>`:'—'}</td><td>${v.ecart!=null?gp(v.ecart):'—'}</td></tr>`;}).join('');
  ['#tOff','#tCrem','#tMeat','#tBrand'].forEach(lab);

  // ---------- état initial : lien partagé, sinon derniers réglages
  (function restore(){
    const S=store.get(), has=Q.has('de')||Q.has('a')||Q.has('m');
    const v=(k,sk)=>Q.has(k)?Q.get(k):(has?null:S[sk]);
    const sp=v('m','spend'); if(sp) $('#spend').value=sp;
    const mx=v('mix','mix'); if(mx) setMix(mx);
    const pp=v('p','persons'); if(pp) $('#persons').value=pp;
    const md=v('mode','mode'); if(md && [...$('#mode').options].some(o=>o.value===md)) $('#mode').value=md;
    const sc=v('ch','storeCH'); if(sc && [...$('#storeCH').options].some(o=>o.value===sc)) $('#storeCH').value=sc;
    if(!has){ if(S.conso) $('#conso').value=S.conso; if(S.vtime) $('#vtime').value=S.vtime; if(S.tank) $('#tank').value=S.tank;
      if(S.fill) $('#fill').checked=true; if(S.wear===false) $('#wear').checked=false; if(S.card) $('#card').checked=true; if(S.tp) $('#tpCost').value=S.tp; }
    syncMode();
    const a=v('a','dest'); if(a && DEST.some(x=>x.id===a)){ st.dest=a; }
    const de = Q.has('de') ? Q.get('de')+'|'+(Q.get('ct')||'') : (has?null:S.o);
    fillDest(); renderStores(); drawMap();
    if(de){ loadOri().then(()=>{ if(!ORI) return; const [n,c]=de.split('|'); let i=ORI.liste.findIndex(x=>x[0]===n&&(!c||x[1]===c)); if(i<0) i=ORI.liste.findIndex(x=>norm(x[0])===norm(n));
      if(i>=0){ st.o=i; inp.value=label(i); fillDest(); if(has && !missing().length) st.shown=true; update(); } }); }
    else if(st.dest) update();
  })();

  // ---------- graphiques : chargés seulement quand on arrive à la section (historique + bibliothèque)
  let charts=[], itemC=null, curItem=off.length?off[0].id:null, fxMap={}, pan=[], ready=false;
  const hexA=(h,a)=>{const n=parseInt(h.replace('#',''),16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;};
  const tk=()=>({color:css('--muted'),font:{size:11}});
  const step=()=> innerWidth<600 ? 4 : 2;
  const yr=arr=>(v,i)=>arr[i]&&arr[i].endsWith('-01')&&(+arr[i].slice(0,4))%step()===0?arr[i].slice(0,4):'';
  function loadScript(src){ return new Promise((ok,ko)=>{ const s=document.createElement('script'); s.src=src; s.onload=ok; s.onerror=ko; document.head.appendChild(s); }); }
  let chartsP=null;
  function initCharts(){
    if(chartsP) return chartsP;
    chartsP=Promise.all([fetch(ROOT+'data/series.json').then(r=>r.json()), window.Chart?Promise.resolve():loadScript(ROOT+'vendor/chart.umd.min.js')])
      .then(([series])=>{ H=series; pan=H.panier||[]; fxMap=Object.fromEntries(H.fx); Chart.defaults.font.family='IBM Plex Sans, Helvetica, Arial, sans-serif'; ready=true; draw(); })
      .catch(()=>{ document.querySelectorAll('.canvas').forEach(c=>c.innerHTML='<p class="muted">Graphique indisponible.</p>'); });
    return chartsP;
  }
  function draw(){
    if(!ready) return;
    charts.forEach(c=>c.destroy()); charts=[];
    const lb=pan.map(p=>p.m);
    charts.push(new Chart($('#gap'),{type:'line',data:{labels:lb,datasets:[
      {label:'Chaque mois',data:pan.map(p=>p.ecart),borderColor:css('--muted'),borderWidth:1,pointRadius:0,tension:.2},
      {label:'Moyenne 12 mois',data:roll,borderColor:css('--ink'),borderWidth:2.5,pointRadius:0,tension:.3,fill:{target:{value:0},above:hexA(css('--red'),.12),below:hexA(css('--fr'),.14)}}]},
      options:{maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{callbacks:{title:i=>ml(i[0].label),label:c=>c.dataset.label+' : '+pc(c.parsed.y)}}},
        scales:{x:{grid:{display:false},border:{color:css('--ink')},ticks:{...tk(),autoSkip:false,maxRotation:0,callback:yr(lb)}},y:{grid:{color:css('--line')},border:{display:false},ticks:{...tk(),callback:v=>(v>0?'+':'')+v+' %'}}}}}));
    const fl=H.fx.map(f=>f[0]);
    charts.push(new Chart($('#fx'),{type:'line',data:{labels:fl,datasets:[{data:H.fx.map(f=>f[1]),borderColor:css('--ink'),borderWidth:1.5,pointRadius:0,tension:.2}]},
      options:{maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{callbacks:{title:i=>ml(i[0].label),label:c=>'1 EUR = '+nf(c.parsed.y,4)+' CHF'}}},
        scales:{x:{grid:{display:false},border:{color:css('--ink')},ticks:{...tk(),autoSkip:false,maxRotation:0,callback:(v,i)=>fl[i].endsWith('-01')&&(+fl[i].slice(0,4))%(step()*2)===0?fl[i].slice(0,4):''}},y:{grid:{color:css('--line')},border:{display:false},ticks:{...tk(),callback:v=>nf(v,2)+' CHF'}}}}}));
    const mv=(L.viande||[]).filter(v=>(v.ch_migros||v.ch)&&v.fr_chf);
    charts.push(new Chart($('#meatC'),{type:'bar',data:{labels:mv.map(v=>v.label),datasets:[
      {label:'Suisse',data:mv.map(v=>v.ch_migros||v.ch),backgroundColor:css('--red'),borderRadius:4,barPercentage:.7,categoryPercentage:.7},
      {label:'France',data:mv.map(v=>v.fr_chf),backgroundColor:css('--fr'),borderRadius:4,barPercentage:.7,categoryPercentage:.7}]},
      options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.dataset.label+' : '+nf(c.parsed.x)+' CHF/kg'}}},
        scales:{x:{beginAtZero:true,grid:{color:css('--line')},border:{display:false},ticks:{...tk(),callback:v=>v+' CHF'}},y:{grid:{display:false},border:{color:css('--ink')},ticks:{color:css('--ink'),font:{size:13}}}}}}));
    if($('#detail').open) drawItem(curItem);
  }
  function drawItem(id){
    if(!id||!ready) return; curItem=id;
    document.querySelectorAll('#tOff tbody tr').forEach(tr=>tr.setAttribute('aria-selected',tr.dataset.id===id));
    const rows=(H.produits[id]||[]).filter(r=>fxMap[r[0]]), meta=off.find(p=>p.id===id);
    $('#itemTitle').textContent=(meta?meta.label:id)+' : prix en CHF par kg';
    if(itemC) itemC.destroy();
    const lb=rows.map(r=>r[0]);
    itemC=new Chart($('#item'),{type:'line',data:{labels:lb,datasets:[
      {label:'Suisse',data:rows.map(r=>r[1]),borderColor:css('--red'),borderWidth:2,pointRadius:0,tension:.25},
      {label:'France',data:rows.map(r=>+(r[2]*fxMap[r[0]]).toFixed(3)),borderColor:css('--fr'),borderWidth:2,pointRadius:0,tension:.25}]},
      options:{maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{callbacks:{title:i=>ml(i[0].label),label:c=>c.dataset.label+' : '+nf(c.parsed.y)+' CHF/kg'}}},
        scales:{x:{grid:{display:false},border:{color:css('--ink')},ticks:{...tk(),autoSkip:false,maxRotation:0,callback:yr(lb)}},y:{beginAtZero:true,grid:{color:css('--line')},border:{display:false},ticks:{...tk(),callback:v=>v+' CHF'}}}}});
  }
  $('#tOff tbody').addEventListener('click',e=>{const tr=e.target.closest('tr');if(tr)drawItem(tr.dataset.id);});
  $('#tOff tbody').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){const tr=e.target.closest('tr');if(tr){e.preventDefault();drawItem(tr.dataset.id);}}});
  $('#detail').addEventListener('toggle',()=>{ if($('#detail').open) initCharts().then(()=>drawItem(curItem)); });
  if(!document.body.classList.contains('embed')){
    const target=document.getElementById('histoire');
    if('IntersectionObserver' in window){ const io=new IntersectionObserver(es=>{ if(es.some(x=>x.isIntersecting)){ io.disconnect(); initCharts(); } },{rootMargin:'600px'}); io.observe(target); }
    else initCharts();
  }
  let rw=innerWidth; addEventListener('resize',()=>{ if(Math.abs(innerWidth-rw)>100){ rw=innerWidth; draw(); } });
  try{ matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{draw();drawMap();}); new MutationObserver(()=>{draw();drawMap();}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']}); }catch(e){}
})();
