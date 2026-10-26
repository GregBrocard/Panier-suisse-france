/* Panier Suisse France — « Acheter suisse moins cher » : points de vente directe proches d'une localité. */
(function(){
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const ROOT = D.root || '';
  const $ = s => document.querySelector(s);
  const nf = (v,d=1) => v==null||isNaN(v) ? '—' : v.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d});
  const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[-'’]/g,' ');
  const store = { get(){ try{ return JSON.parse(localStorage.getItem('psf-direct')||'{}'); }catch(e){ return {}; } },
                  set(v){ try{ localStorage.setItem('psf-direct', JSON.stringify(v)); }catch(e){} } };
  const ROUTE = 1.39; // facteur route (rapport médian distance routière / vol d'oiseau, voir méthodologie)
  const hav = (a,b) => { const R=6371, r=Math.PI/180, dl=(b[0]-a[0])*r, dn=(b[1]-a[1])*r;
    const h=Math.sin(dl/2)**2+Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin(dn/2)**2; return 2*R*Math.asin(Math.sqrt(h)); };
  const ORDER = ['ferme','distributeur','boucherie','fromagerie','marche','cave'];
  let ORI=null, oriP=null, NAMES=[], F=null, fP=null, o=null;
  const S0 = store.get(); let types = new Set(S0.t || ORDER);

  function loadOri(){ if(oriP) return oriP; oriP=fetch(ROOT+'data/origines.json').then(r=>r.json()).then(j=>{ ORI=j; NAMES=ORI.liste.map(x=>norm(x[0])); return ORI; }).catch(()=>{ oriP=null; }); return oriP; }
  function loadF(){ if(!D.f) return Promise.resolve(null); if(fP) return fP; fP=fetch(ROOT+'data/fermes.json').then(r=>{ if(!r.ok) throw 0; return r.json(); }).then(j=>{ F=j; seg(); return F; }).catch(()=>{ fP=null; }); return fP; }
  loadF();

  function seg(){
    const T=(F&&F.types)||{};
    $('#types').innerHTML=ORDER.filter(k=>T[k]).map(k=>`<button type="button" data-k="${k}" aria-pressed="${types.has(k)}">${esc(T[k])}</button>`).join('');
  }
  $('#types').addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b) return; const k=b.dataset.k;
    if(types.has(k)) types.delete(k); else types.add(k); b.setAttribute('aria-pressed',types.has(k)); save(); run(); });
  $('#rayon').addEventListener('change',()=>{ save(); run(); });
  if(S0.r) $('#rayon').value=S0.r;
  function save(){ store.set({o: o!=null&&ORI?ORI.liste[o].slice(0,2).join('|'):null, r:$('#rayon').value, t:[...types]}); }

  const inp=$('#from'), lst=$('#fromList'); let hits=[], cur=-1;
  function search(q){ if(!ORI) return []; q=norm(q).trim(); if(!q) return []; const isN=/^\d/.test(q), out=[];
    for(let i=0;i<ORI.liste.length&&out.length<80;i++){ const n=NAMES[i]; if(isN?String(ORI.liste[i][2]).startsWith(q):(n.startsWith(q)||n.includes(' '+q))) out.push(i); }
    out.sort((a,b)=>(NAMES[a].startsWith(q)?0:1)-(NAMES[b].startsWith(q)?0:1)||NAMES[a].length-NAMES[b].length); return out.slice(0,8); }
  function renderList(){
    if(!ORI){ lst.innerHTML='<li aria-disabled="true"><span>Chargement des localités…</span></li>'; lst.hidden=false; return; }
    if(!hits.length){ lst.innerHTML='<li aria-disabled="true"><span>Aucune localité trouvée</span></li>'; lst.hidden=false; return; }
    lst.innerHTML=hits.map((i,k)=>{const [n,c,p]=ORI.liste[i];return `<li role="option" data-i="${i}" aria-selected="${k===cur}"><span>${esc(n)}</span><small>${p} ${c}</small></li>`;}).join('');
    lst.hidden=false; inp.setAttribute('aria-expanded','true'); }
  function closeList(){ lst.hidden=true; inp.setAttribute('aria-expanded','false'); cur=-1; }
  function setO(i){ o=i; inp.value=ORI.liste[i][0]; closeList(); save(); loadF().then(run); }
  inp.addEventListener('focus',loadOri);
  inp.addEventListener('input',()=>{ o=null; loadOri(); hits=search(inp.value); cur=hits.length?0:-1; renderList(); });
  inp.addEventListener('keydown',e=>{
    if(e.key==='ArrowDown'){ e.preventDefault(); cur=Math.min(hits.length-1,cur+1); renderList(); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); cur=Math.max(0,cur-1); renderList(); }
    else if(e.key==='Enter'){ e.preventDefault(); if(hits[cur]!=null) setO(hits[cur]); }
    else if(e.key==='Escape') closeList(); });
  lst.addEventListener('mousedown',e=>{ const li=e.target.closest('li[data-i]'); if(li){ e.preventDefault(); setO(+li.dataset.i); }});
  inp.addEventListener('blur',()=>setTimeout(()=>{ if(!lst.hidden){ if(hits.length===1) setO(hits[0]); else closeList(); } },150));

  function run(){
    const box=$('#direct');
    if(o==null||!ORI) return;
    if(!F){ box.innerHTML='<p class="muted">La liste des points de vente n\'est pas encore disponible.</p>'; return; }
    const c=ORI.coords[o]; if(!c){ box.innerHTML='<p class="muted">Position de la localité inconnue.</p>'; return; }
    const R=+$('#rayon').value, T=F.types||{};
    const near=F.points.filter(p=>types.has(p[0])).map(p=>({p, km:hav(c,[p[1],p[2]])*ROUTE})).filter(x=>x.km<=R).sort((a,b)=>a.km-b.km);
    if(!near.length){ box.innerHTML=`<p>Aucun point de vente référencé à moins de ${R} km de ${esc(ORI.liste[o][0])}. Essayez une distance plus grande, ou <a href="https://www.openstreetmap.org/" rel="noopener">ajoutez une ferme que vous connaissez</a>.</p>`; return; }
    const cnt=ORDER.map(k=>[k,near.filter(x=>x.p[0]===k).length]).filter(x=>x[1]);
    let h=`<p class="headline">Près de ${esc(ORI.liste[o][0])}, à moins de ${R} km : ${cnt.map(([k,n])=>`<b>${n}</b> ${esc((T[k]||k).toLowerCase())}${n>1&&!/s$/.test(T[k]||'')?'s':''}`).join(', ')}.</p>`;
    for(const [k] of cnt){
      const rows=near.filter(x=>x.p[0]===k).slice(0,8);
      h+=`<h3>${esc(T[k]||k)}</h3><ul class="plist">`+rows.map(({p,km})=>{
        const [,lat,lon,nom,loc,prod,hrs,web]=p;
        const map=`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
        return `<li><b>${esc(nom||T[k]||'Sans nom')}</b>${loc?' · '+esc(loc):''} <span class="muted">environ ${nf(km)} km</span>`
          +(prod?`<br><small>${esc(prod)}</small>`:'')+(hrs?`<br><small>Horaires : ${esc(hrs)}</small>`:'')
          +`<br><small><a href="${map}" rel="noopener" target="_blank">Plan</a>${web?` · <a href="${esc(web)}" rel="noopener" target="_blank">Site</a>`:''}</small></li>`; }).join('')+'</ul>';
    }
    h+=`<p class="muted">Distances estimées (vol d'oiseau × ${String(ROUTE).replace('.',',')}). Liste OpenStreetMap du ${esc(F.genere_le||'')}.</p>`;
    box.innerHTML=h;
  }
  if(S0.o){ loadOri().then(()=>{ if(!ORI) return; const [n,cn]=S0.o.split('|'); const i=ORI.liste.findIndex(x=>x[0]===n&&x[1]===cn); if(i>=0){ o=i; inp.value=n; loadF().then(run); } }); }
})();
