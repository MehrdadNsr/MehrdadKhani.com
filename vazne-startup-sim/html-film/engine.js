// ===== Vazne film engine: deterministic seek-based renderer =====
const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
function fa(s){ return String(s).replace(/[0-9]/g, d => FA_DIGITS[+d]).replace(/\./g,'٫'); }
function faText(s){ // convert digits to Persian only when the string has Persian letters
  s = String(s); return /[؀-ۿ]/.test(s) ? s.replace(/[0-9]/g, d => FA_DIGITS[+d]) : s; }
function fmtNum(n){ n = Math.round(n); return n.toLocaleString('en-US'); }
function clamp(x,a=0,b=1){ return Math.max(a,Math.min(b,x)); }
function lerp(a,b,t){ return a+(b-a)*t; }
const E = {
  out: t => 1-Math.pow(1-t,3), outQ: t => 1-Math.pow(1-t,5), inOut: t => t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2,
  outBack: t => { const c=1.70158; return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2); },
  outExpo: t => t>=1?1:1-Math.pow(2,-10*t), lin: t=>t,
};
// progress of a segment starting at s lasting d, given local time T
function seg(T,s,d,e=E.out){ return e(clamp((T-s)/d)); }
function hexToRgb(h){ h=h.replace('#',''); return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]; }
function mixHex(a,b,t){ const A=hexToRgb(a),B=hexToRgb(b); return `rgb(${A.map((v,i)=>Math.round(lerp(v,B[i],t))).join(',')})`; }
// rich text: *word* → highlight, **word** → mint highlight, ~word~ → red, ^word^ → blue
function richSpans(text){
  const out=[]; const re=/(\*\*[^*]+\*\*|\*[^*]+\*|~[^~]+~|\^[^^]+\^)/g; let last=0, m;
  while((m=re.exec(text))){ if(m.index>last) out.push({t:text.slice(last,m.index)}); const s=m[0];
    if(s.startsWith('**')) out.push({t:s.slice(2,-2),c:'mint'}); else if(s.startsWith('*')) out.push({t:s.slice(1,-1),c:'amber'});
    else if(s.startsWith('~')) out.push({t:s.slice(1,-1),c:'red'}); else out.push({t:s.slice(1,-1),c:'blue'}); last=m.index+s.length; }
  if(last<text.length) out.push({t:text.slice(last)});
  return out;
}
// build word spans for kinetic reveal; returns array of word elements
function buildWords(container,text){
  const words=[]; container.innerHTML='';
  const isLatin = w => /^[A-Za-z0-9$€£%.,:+×\-–—'’"()\/#@&]+$/.test(w) && /[A-Za-z]/.test(w);
  for(const part of richSpans(faText(text))){
    const toks=part.t.split(/(\s+)/).filter(x=>x.length);
    let i=0;
    while(i<toks.length){
      const w=toks[i];
      if(/^\s+$/.test(w)){ container.appendChild(document.createTextNode(' ')); i++; continue; }
      let run=w, j=i+1;
      if(isLatin(w)){ while(j+1<toks.length && /^\s+$/.test(toks[j]) && isLatin(toks[j+1])){ run+=' '+toks[j+1]; j+=2; } }
      const sp=document.createElement('span'); sp.className='w'+(part.c?' hl '+part.c:''); sp.textContent=run; if(run!==w||isLatin(w)){ sp.dir='ltr'; sp.style.unicodeBidi='isolate'; }
      container.appendChild(sp); words.push(sp); i=j;
    }
  }
  return words;
}
function revealWords(words,T,start,per,rise=30){
  words.forEach((w,i)=>{ const p=seg(T,start+i*per,0.35,E.out); w.style.opacity=p; w.style.transform=`translateY(${(1-p)*rise}px)`; });
}
const MOODS = {
  quiet:   ['#1b2a44','#0e1a2b'], hopeful: ['#3a2a12','#1c2a3a'], tense: ['#3a1a24','#1a2030'], low: ['#0c1424','#090b12'],
  build:   ['#3d2a0f','#1a3328'], triumph: ['#4a3208','#1f3a2c'], warm: ['#3a2416','#2a1e33'], end: ['#1a1a2a','#0d0d14'], ai: ['#12304a','#1a1a3a'],
};
window.FILM = { scenes:[], total:0, fps:30 };
const $ = s => document.querySelector(s);
function buildTicks(){ const t=$('#ticks'); t.innerHTML=''; for(let i=0;i<=10;i++){ const e=document.createElement('i'); e.style.right=(i*10)+'%'; t.appendChild(e);} }
window.loadScenes = function(data){
  FILM.fps = data.fps||30; FILM.scenes = data.scenes; let t=0;
  for(const s of FILM.scenes){ s.start = t; t += s.dur; s._el=null; }
  FILM.total = t; buildTicks();
  $('#scenes').innerHTML='';
  return FILM.total;
};
window.totalDuration = () => FILM.total;
function ensureScene(s,i){
  if(s._el) return s._el;
  const el=document.createElement('div'); el.className='scene s-'+s.type; el.style.zIndex=String(10+i);
  const safe=document.createElement('div'); safe.className='safe'; el.appendChild(safe);
  const tpl=TEMPLATES[s.type]||TEMPLATES.text;
  s._state = tpl.build(safe,s.params||{},s) || {};
  s._render = tpl.render; s._el=el; $('#scenes').appendChild(el); return el;
}
const FADE=0.5;
window.seek = function(t){
  const S=FILM.scenes; let cur=-1;
  for(let i=0;i<S.length;i++){ if(t>=S[i].start && t<S[i].start+S[i].dur){ cur=i; break; } }
  if(cur<0) cur = t>=FILM.total? S.length-1 : 0;
  for(let i=0;i<S.length;i++){
    const s=S[i]; const T=t-s.start; const visible = T>-0.01 && T<s.dur+FADE;
    if(!visible){ if(s._el){ s._el.style.opacity=0; s._el.style.display='none'; } continue; }
    const el=ensureScene(s,i); el.style.display='block';
    const fin = seg(T,0,FADE,E.out); const fout = 1-seg(T,s.dur,FADE,E.lin);
    const op = Math.min(fin,fout); el.style.opacity=op;
    const sc = lerp(1.02,1,fin); el.style.transform=`scale(${sc})`;
    s._render(s._state, clamp(T,0,s.dur+FADE), s.params||{}, s);
  }
  // HUD
  const s=S[cur]; const T=t-s.start;
  const nxt=S[cur+1]; const yA=s.year??0; const yB=nxt?(nxt.year??yA):yA;
  const blend = nxt ? seg(T, s.dur-1.0, 1.0, E.inOut) : 0; const y = lerp(yA,yB,blend);
  const pct = clamp(y/10)*100;
  $('#trackFill').style.width=pct+'%'; $('#marker').style.right=pct+'%'; $('#yearNow').style.right=pct+'%';
  $('#yearNow').textContent = y<0.05 ? 'امروز' : (y>=9.95?'سال ۱۰':'سال '+fa(Math.max(1,Math.round(y))));
  $('#datePill').textContent = s.date ? faText(s.date) : '';
  $('#datePill').style.opacity = s.date?1:0;
  const p = s.p; const probEl=$('#prob');
  if(p==null){ probEl.style.opacity=0; } else { probEl.style.opacity=1; const pv=Math.round(p*100); $('#probV').textContent=fa(pv)+'٪'; $('#probBar').style.width=pv+'%';
    $('#probBar').style.background = pv>=60?'var(--mint)':(pv>=35?'var(--amber)':'var(--red)'); }
  $('#hud').style.opacity = (s.hud===false)?0:1;
  // background mood
  const mA = MOODS[s.mood]||MOODS.quiet; const mB = nxt?(MOODS[nxt.mood]||mA):mA; const mb = nxt? seg(T,s.dur-1.2,1.2,E.inOut):0;
  const cA=mixHex(mA[0],mB[0],mb), cB=mixHex(mA[1],mB[1],mb);
  const a=$('#blobA'), b=$('#blobB');
  a.style.setProperty('--blob',cA); b.style.setProperty('--blob',cB);
  a.style.transform=`translate(${-300+Math.sin(t*0.11)*140}px, ${-200+Math.cos(t*0.09)*120}px)`;
  b.style.transform=`translate(${420+Math.cos(t*0.08)*160}px, ${900+Math.sin(t*0.1)*150}px)`;
  window.__t=t;
};
