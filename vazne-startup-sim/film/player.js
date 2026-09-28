// ===== Real-time player for the HTML film (browser). Loads scenes_timed.json + audio, plays with a tap. =====
(function(){
  const q = new URLSearchParams(location.search);
  const SCENES_URL = q.get('scenes') || 'scenes_timed.json';
  const MUSIC_URL = q.get('music') || 'music.mp3';
  const overlay = document.createElement('div');
  overlay.id = 'playOverlay';
  overlay.innerHTML = `<div class="pbox"><div class="plate"></div><div class="pt">وزنه</div><div class="ps">فیلم مسیر ده‌ساله</div><button id="playBtn">▶ پخش</button><div class="ph">صدا رو روشن کن · تمام‌صفحه بهتره</div></div>`;
  const style = document.createElement('style');
  style.textContent = `#playOverlay{position:absolute;inset:0;z-index:999;background:rgba(6,8,12,.92);display:flex;align-items:center;justify-content:center;font-family:'Vazir',sans-serif;color:#F4F6F8;direction:rtl}
  #playOverlay .pbox{text-align:center} #playOverlay .plate{width:120px;height:120px;border-radius:50%;border:18px solid #FFB020;margin:0 auto 30px;position:relative;box-shadow:0 0 60px rgba(255,176,32,.35)} #playOverlay .plate:after{content:'';position:absolute;inset:24px;border-radius:50%;background:#FFB020}
  #playOverlay .pt{font-family:'Lalezar';font-size:120px;line-height:1} #playOverlay .ps{font-size:36px;color:#A7B1BC;margin:10px 0 50px}
  #playBtn{font-family:'Vazir';font-size:44px;font-weight:800;padding:26px 80px;border-radius:60px;border:0;background:#FFB020;color:#1a1000;cursor:pointer} #playOverlay .ph{font-size:26px;color:#66707B;margin-top:30px}
  #progressTap{position:absolute;inset:0;z-index:998}
  html,body{background:#000} #stage{transform-origin:top left}`;
  document.head.appendChild(style);
  function fit(){ const s=Math.min(innerWidth/1080, innerHeight/1920); const st=document.getElementById('stage'); st.style.transform=`scale(${s})`; st.style.left=((innerWidth-1080*s)/2)+'px'; st.style.top=((innerHeight-1920*s)/2)+'px'; st.style.position='absolute'; }
  addEventListener('resize', fit);
  async function boot(){
    const data = await (await fetch(SCENES_URL)).json();
    const total = window.loadScenes(data);
    fit(); window.seek(0);
    document.getElementById('stage').appendChild(overlay);
    const music = new Audio(MUSIC_URL); music.preload = 'auto';
    const clips = data.scenes.map((s, i) => s.tts_url ? { at: s.start + (s.tts_lead || 0.6), a: new Audio(s.tts_url), done: false } : null);
    document.getElementById('playBtn').onclick = async () => {
      overlay.remove();
      try { await music.play(); } catch (e) { console.warn('music blocked', e); }
      const t0 = performance.now();
      function loop(){
        const t = music.duration && !music.paused ? music.currentTime : (performance.now() - t0) / 1000;
        window.seek(Math.min(t, total - 0.01));
        clips.forEach(c => { if (c && !c.done && t >= c.at) { c.done = true; c.a.play().catch(()=>{}); } });
        if (t < total) requestAnimationFrame(loop); else { music.pause(); }
      }
      requestAnimationFrame(loop);
    };
  }
  window.addEventListener('DOMContentLoaded', () => { document.fonts.ready.then(boot); });
})();
