/* Panier Suisse France — mode « Où faire le plein ». Même base de localités que le calculateur. */
(function(){
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const ROOT = D.root || '';
  const $ = s => document.querySelector(s);
  const nf = (v,d=2) => v==null||isNaN(v) ? '—' : v.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).replace(/[  ]/g,' ');
  const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[-'’]/g,' ');
  const store = { get(){ try{ return JSON.parse(localStorage.getItem('psf-ess')||'{}'); }catch(e){ return {}; } },
                  set(v){ try{ localStorage.setItem('psf-ess', JSON.stringify(v)); }catch(e){} } };
  const dateFr = s => { if(!s) return ''; const d=new Date(s); return isNaN(d)?'':d.toLocaleDateString('fr-CH',{day:'numeric',month:'short'}); };
  const Q = new URLSearchParams(location.search);

  let ORI=null, oriP=null, NAMES=[], dIdx={}, ST=null, stP=null;
  const st = {o:null, prefEdited:false, shown:false};

  function loadOri(){
    if(oriP) return oriP;
    oriP = fetch(ROOT+'data/origines.json').then(r=>r.json()).then(j=>{ ORI=j; NAMES=ORI.liste.map(x=>norm(x[0])); dIdx=Object.fromEntries(ORI.destinations.map((id,i)=>[id,i]));
      if(document.activeElement===inp && inp.value){ hits=search(inp.value); cur=hits.length?0:-1; renderList(); } return ORI; })
      .catch(()=>{ oriP=null; });
    return oriP;
  }
  function loadSt(){
    if(stP) return stP;
    stP = fetch(ROOT+'data/stations.json').then(r=>r.json()).then(j=>{ ST=j; coverage(); return ST; }).catch(()=>{ stP=null; });
    return stP;
  }
  loadSt();

  // ---------- autocomplétion (identique au calculateur)
  const inp=$('#from'), lst=$('#fromList'); let hits=[], cur=-1;
  function search(q){
    if(!ORI) return [];
    q=norm(q).trim(); if(!q) return [];
    const isNpa=/^\d/.test(q), out=[];
    for(let i=0;i<ORI.liste.length&&out.length<80;i++){ const n=NAMES[i]; if(isNpa?String(ORI.liste[i][2]).startsWith(q):(n.startsWith(q)||n.includes(' '+q))) out.push(i); }
    out.sort((a,b)=>(NAMES[a].startsWith(q)?0:1)-(NAMES[b].startsWith(q)?0:1)||NAMES[a].length-NAMES[b].length);
    return out.slice(0,8);
  }
  function renderList(){
    if(!ORI){ lst.innerHTML='<li aria-disabled="true"><span>Chargement des localités…</span></li>'; lst.hidden=false; return; }
    if(!hits.length){ lst.innerHTML='<li aria-disabled="true"><span>Aucune localité trouvée</span></li>'; lst.hidden=false; return; }
    lst.innerHTML=hits.map((i,k)=>{const [n,c,p]=ORI.liste[i];return `<li role="option" id="o${i}" data-i="${i}" aria-selected="${k===cur}"><span>${esc(n)}</span><small>${p} ${c}</small></li>`;}).join('');
    lst.hidden=false; inp.setAttribute('aria-expanded','true');
  }
  function closeList(){ lst.hidden=true; inp.setAttribute('aria-expanded','false'); cur=-1; }
  function setOrigin(i){ st.o=i; inp.value=ORI.liste[i][0]; closeList(); $('#slotFrom').classList.remove('bad'); prefillPref(); save(); if(st.shown) run(); }
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

  // ---------- bulles d'aide
  document.querySelectorAll('.info').forEach(box=>{ const b=box.querySelector('.ibtn'), p=box.querySelector('.pop');
    b.addEventListener('click',e=>{ e.preventDefault(); e.stopPropagation(); p.hidden=!p.hidden; b.setAttribute('aria-expanded',String(!p.hidden)); }); });
  document.addEventListener('click',e=>{ if(!e.target.closest('.info')) document.querySelectorAll('.info .pop').forEach(x=>x.hidden=true); });

  // ---------- prix de référence : zone frontière suisse la plus proche (OFDF)
  const home = () => st.o!=null&&ORI ? ORI.coords[st.o] : null;
  function refZone(){
    const h=home(); if(!h) return null; let best=null, bd=1e9;
    for(const z of D.ofdf_zones){ const d=PSF.haversine(h,[z.lat,z.lon]); if(d<bd){bd=d;best=z;} }
    return best;
  }
  function prefillPref(){
    if(st.prefEdited) return; const z=refZone(), f=$('#fuel').value;
    const v = z && z[f] ? z[f] : D.ref_defaut[f];
    if(v) $('#pref').value=v.toFixed(2);
  }
  $('#pref').addEventListener('input',()=>{ st.prefEdited=true; save(); if(st.shown) run(); });
  $('#fuel').addEventListener('change',()=>{ st.prefEdited=false; prefillPref(); save(); if(st.shown) run(); });
  ['#litres','#conso','#radius','#wear'].forEach(s=>$(s).addEventListener(s==='#wear'||s==='#radius'?'change':'input',()=>{ save(); if(st.shown) run(); }));

  function save(){ store.set({o: st.o!=null&&ORI ? ORI.liste[st.o].slice(0,2).join('|') : null, l:$('#litres').value, f:$('#fuel').value,
    c:$('#conso').value, r:$('#radius').value, w:$('#wear').checked, p: st.prefEdited ? $('#pref').value : null}); }

  // ---------- distances : itinéraires OSRM vers les villes frontalières quand ils existent, sinon estimation calibrée
  // le segment domicile -> station traverse-t-il un lac ? (alors la distance à vol d'oiseau ne vaut rien)
  function cross(a,b,c,d){ const o=(p,q,r)=>(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]);
    return (o(a,b,c)>0)!==(o(a,b,d)>0) && (o(c,d,a)>0)!==(o(c,d,b)>0); }
  function overLake(h,s){ const A=[h[1],h[0]], B=[s.lon,s.lat];
    for(const ring of D.lacs||[]){ for(let i=0;i<ring.length;i++){ if(cross(A,B,ring[i],ring[(i+1)%ring.length])) return true; } } return false; }
  function legOf(s){
    const h=home(); const f=D.route.facteur, v=D.route.kmh;
    const lake=overLake(h,s);
    let km=f*PSF.haversine(h,[s.lat,s.lon])*(lake?2:1), via=false;
    if(s.z!=null && dIdx[s.z]!=null){ const r=ORI.dist[st.o], k=dIdx[s.z];
      if(r && r[2*k]!=null){ const k2=r[2*k]+f*s.zk; if(lake || k2<km){ km=k2; via=true; } } }
    let min=km/v*60;
    if(via){ const r=ORI.dist[st.o], k=dIdx[s.z]; min=r[2*k+1]+f*s.zk/v*60; }
    return {km, min: min + (s.pays==='FR'?5:0), via};
  }

  function stations(){
    const f=$('#fuel').value, out=[];
    for(const x of ST.fr){ const p=f==='sp95'?x[5]:x[6]; if(p==null) continue;
      out.push({pays:'FR', lat:x[0], lon:x[1], nom:x[2]||'Station', adr:[x[3],x[4]].filter(Boolean).join(', '), prix:p, maj:f==='sp95'?x[7]:x[8], z:x[9], zk:x[10], src:'Prix officiel (France)'}); }
    for(const x of ST.ch){ const p=f==='sp95'?x[4]:x[5]; if(p==null) continue;
      out.push({pays:'CH', lat:x[0], lon:x[1], nom:x[2], adr:x[3], prix:p, maj:x[6], src:x[7], vieux:x[8]}); }
    return out;
  }

  function run(){
    if(!ST||!ORI||st.o==null) return;
    const p={litres:+$('#litres').value||0, conso:+$('#conso').value||0, pref:+$('#pref').value||0, wear:$('#wear').checked, usure:D.usure};
    const R=+$('#radius').value, h=home();
    const rows=stations().map(s=>{ const l=legOf(s); const g=PSF.fuelGain(p,{km:l.km,prix:s.prix}); return Object.assign(s,l,g); }).filter(s=>s.km<=90);
    rows.sort((a,b)=>b.net-a.net);
    const best=rows[0], near=rows.filter(s=>s.km<=R).sort((a,b)=>b.net-a.net)[0];
    $('#waiting').hidden=true; $('#res').hidden=false;
    const route=s=>`https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${h[0]}%2C${h[1]}%3B${s.lat}%2C${s.lon}`;
    const card=(title,s,empty)=>{
      if(!s) return `<div class="card"><span class="ct">${title}</span><p class="muted">${empty}</p></div>`;
      const pos=s.net>0;
      return `<div class="card ${pos?'':'neg'}"><span class="ct">${title}</span>
        <span class="cg">${pos?'+':'−'}${nf(Math.abs(s.net),0)}<small> CHF</small></span>
        <span class="cn">${esc(s.nom)} <span class="flag">${s.pays==='FR'?'France':'Suisse'}</span></span>
        <span class="ca">${esc(s.adr)}</span>
        <span class="cd">${nf(s.prix)} CHF/L${s.maj?' · '+(s.pays==='FR'?'mis à jour le ':'relevé le ')+dateFr(s.maj):''}${s.vieux?' · à confirmer':''} · ${nf(s.km,0)} km, ${nf(s.min,0)} min${s.via?'':' (distance estimée)'}</span>
        <span class="cx">Plein : ${pos||s.fuel>0?'−':'+'}${nf(Math.abs(s.fuel))} CHF · trajet aller-retour : +${nf(s.drive)} CHF${s.wear?` · usure : +${nf(s.wear)} CHF`:''}</span>
        <a class="cr" href="${route(s)}" target="_blank" rel="noopener">Itinéraire</a></div>`;
    };
    const verdict = best && best.net>0.5 ? '' : `<p class="warn" style="grid-column:1/-1">Aucun détour n'est rentable pour ${nf(p.litres,0)} litres avec ces prix : faites le plein à votre station habituelle.</p>`;
    const nearest=rows.slice().sort((a,b)=>a.km-b.km)[0];
    $('#cards').innerHTML=verdict+(best&&best.net>0?card('Le plus rentable',best,''):card('La station au prix connu la plus proche',nearest,'Aucune station avec un prix connu à moins de 90 km.'))
      +card(`Le plus rentable à moins de ${R} km`,near&&near.net>0?near:null,`Aucune station avec un prix connu et rentable à moins de ${R} km. <a href="${esc(D.signal_url)}" target="_blank" rel="noopener">Signalez un prix</a> : il aidera tout le monde.`);
    let pos=rows.filter(s=>s.net>0).slice(0,15);
    $('#listTitle').textContent = pos.length ? 'Toutes les stations rentables' : 'Les stations les plus proches avec un prix connu';
    if(!pos.length) pos=rows.slice().sort((a,b)=>a.km-b.km).slice(0,6);
    $('#tStations tbody').innerHTML=pos.length?pos.map(s=>`<tr><td>${esc(s.nom)} <span class="flag">${s.pays}</span><small>${esc(s.adr)}</small></td><td>${nf(s.prix)} CHF<small>${s.maj?dateFr(s.maj):''}${s.vieux?', à confirmer':''}</small></td><td>${nf(s.km,0)} km<small>${nf(s.min,0)} min</small></td><td><b>${s.net>=0?'+':'−'}${nf(Math.abs(s.net),0)} CHF</b></td></tr>`).join(''):'<tr><td colspan="4" class="muted">Aucune.</td></tr>';
    const z=refZone();
    $('#resNote').innerHTML=`Gain net = (prix habituel − prix de la station) × litres − carburant brûlé pour l'aller-retour${p.wear?' − usure de la voiture':''}. Prix habituel : ${nf(p.pref)} CHF/L${st.prefEdited?' (votre prix)':z?` (moyenne ${esc(z.nom)}, douane suisse, ${esc(D.ofdf_date)})`:''}. Distances : itinéraire réel jusqu'à la ville frontalière quand il existe, sinon estimation (vol d'oiseau × ${nf(D.route.facteur,2)}). Le temps n'est pas déduit. Pour la France, le réservoir passe la douane sans formalité.`;
    if(!$('#res').dataset.scrolled){ $('#res').dataset.scrolled='1'; document.getElementById('answer').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth', block:'start'}); }
  }

  $('#go').addEventListener('click',()=>{
    if(st.o==null){ $('#slotFrom').classList.add('bad'); $('#missing').hidden=false; $('#missing').textContent='Indiquez votre localité dans la case en rouge.'; return; }
    $('#missing').hidden=true; st.shown=true;
    Promise.all([loadOri(),loadSt()]).then(run);
  });

  function coverage(){
    $('#cov').innerHTML=`<b>Quelles stations ?</b> ${ST.fr.length} stations françaises proches de la frontière, au prix officiel du jour. ${ST.ch.length} station${ST.ch.length>1?'s':''} suisse${ST.ch.length>1?'s':''} avec un prix relevé, sur ${ST.ch_total} stations recensées en Suisse : la Suisse n'oblige pas les stations à publier leurs prix et aucune source ouverte n'existe. <a href="${esc(D.signal_url)}" target="_blank" rel="noopener">Signalez le prix de votre station</a> : il est vérifié puis ajouté avec sa date.`;
  }

  // ---------- état initial
  (function restore(){
    const S=store.get(), has=Q.has('de');
    if(Q.get('l')||S.l) $('#litres').value=Q.get('l')||S.l;
    if((Q.get('f')||S.f)==='diesel') $('#fuel').value='diesel';
    if(S.c) $('#conso').value=S.c; if(S.r) $('#radius').value=S.r; if(S.w===false) $('#wear').checked=false;
    if(S.p && !has){ $('#pref').value=S.p; st.prefEdited=true; } else { prefillPref(); }
    const de = has ? Q.get('de')+'|'+(Q.get('ct')||'') : S.o;
    if(de){ loadOri().then(()=>{ if(!ORI) return; const [n,c]=de.split('|'); let i=ORI.liste.findIndex(x=>x[0]===n&&(!c||x[1]===c)); if(i<0) i=ORI.liste.findIndex(x=>norm(x[0])===norm(n));
      if(i>=0){ st.o=i; inp.value=ORI.liste[i][0]; prefillPref(); if(has){ st.shown=true; loadSt().then(run); } } }); }
  })();
})();
