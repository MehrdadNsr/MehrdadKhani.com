/* Project real molecular coordinates into a rotating 3D view using Canvas 2D.
   No WebGL dependency. Hidden scenes pause; reduced motion stays static. */
(() => {
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const hosts = [];
  const TAU = Math.PI * 2;
  function host(el, draw) {
    const canvas = el.querySelector('canvas'), ctx = canvas.getContext('2d');
    if (!ctx) return;
    const h = { el, canvas, ctx, w: 0, h: 0, angle: -.22, drag: false, visible: false, frame: 0, time: 0, last: 0, draw };
    const paint = () => { ctx.clearRect(0, 0, h.w, h.h); draw(h); };
    h.paint = paint;
    const loop = now => {
      h.frame = 0;
      if (!h.visible || document.hidden || motion.matches) return;
      const dt = Math.min((now - (h.last || now)) / 1000, .04); h.last = now;
      h.time += dt; if (!h.drag) h.angle += dt * .12;
      paint(); h.frame = requestAnimationFrame(loop);
    };
    h.start = () => { if (!h.frame && h.visible && !document.hidden && !motion.matches) { h.last = 0; h.frame = requestAnimationFrame(loop); } else paint(); };
    h.stop = () => { cancelAnimationFrame(h.frame); h.frame = 0; };
    new ResizeObserver(() => { const r = el.getBoundingClientRect(); h.w = r.width; h.h = r.height; const dpr = Math.min(devicePixelRatio || 1, 2); canvas.width = h.w * dpr; canvas.height = h.h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); paint(); }).observe(el);
    new IntersectionObserver(([entry]) => { h.visible = entry.isIntersecting; h.visible ? h.start() : h.stop(); }).observe(el);
    if (el.hasAttribute('data-drag')) {
      let x = 0;
      canvas.style.touchAction = 'pan-y';
      canvas.addEventListener('pointerdown', e => { h.drag = true; x = e.clientX; canvas.setPointerCapture(e.pointerId); });
      canvas.addEventListener('pointermove', e => { if (!h.drag) return; h.angle += (e.clientX - x) * .009; x = e.clientX; paint(); });
      ['pointerup','pointercancel','lostpointercapture'].forEach(event => canvas.addEventListener(event, () => { h.drag = false; }));
    }
    el.classList.add('is-rendered'); el.dataset.ready = '1'; hosts.push(h); return h;
  }
  function molecule(h, chains) {
    const {ctx:c,w,h:height,angle:a} = h;
    const scale = Math.min(w * .37, height * .37), cx = w / 2, cy = height * .49;
    // Orbit guides provide depth without competing with the molecular trace.
    c.strokeStyle = '#acbba11a'; c.lineWidth = 1;
    c.beginPath(); c.ellipse(cx,cy,scale*1.12,scale*.48,-.35,0,TAU);c.stroke();
    c.beginPath(); c.ellipse(cx,cy,scale*.66,scale*1.17,.5,0,TAU);c.stroke();
    const lines = [];
    for (const [id,flat] of Object.entries(chains)) {
      let previous;
      for (let i=0;i<flat.length;i+=3) {
        const x=flat[i],y=flat[i+1],z=flat[i+2];
        const rx=x*Math.cos(a)+z*Math.sin(a), rz=-x*Math.sin(a)+z*Math.cos(a);
        const perspective=3.7/(3.7-rz), p={x:cx+rx*scale*perspective,y:cy-y*scale*perspective,z:rz};
        if(previous)lines.push({a:previous,b:p,z:(previous.z+rz)/2,heavy:flat.length>900});
        previous=p;
      }
    }
    lines.sort((a,b)=>a.z-b.z);
    c.lineCap='round';c.lineJoin='round';
    for(const l of lines){
      const light=Math.max(.30,Math.min(1,.65+l.z*.32));
      c.strokeStyle=l.heavy?`rgba(255,120,95,${light})`:`rgba(230,233,211,${light})`;
      c.lineWidth=Math.max(1.4,3.3+l.z*1.2);c.beginPath();c.moveTo(l.a.x,l.a.y);c.lineTo(l.b.x,l.b.y);c.stroke();
    }
    c.fillStyle='#ff785f';c.beginPath();c.arc(cx+Math.cos(a)*scale*1.12,cy+Math.sin(a)*scale*.48,3,0,TAU);c.fill();
  }
  function column(h) {
    const {ctx:c,w,h:height}=h, cx=w/2, top=height*.12, ch=height*.7, cw=Math.min(100,w*.3), left=cx-cw/2;
    const r=h.el.getBoundingClientRect(), p=Math.max(0,Math.min(1,(innerHeight-r.top)/(innerHeight+r.height)));
    const glass=c.createLinearGradient(left,0,left+cw,0);glass.addColorStop(0,'#9bafa025');glass.addColorStop(.3,'#ffffff12');glass.addColorStop(.75,'#b8c8ae08');glass.addColorStop(1,'#c5d8b635');
    c.fillStyle=glass;c.strokeStyle='#c6d4bd70';c.lineWidth=1;c.beginPath();c.roundRect(left,top,cw,ch,12);c.fill();c.stroke();
    for(let y=0;y<45;y++)for(let x=0;x<11;x++){c.fillStyle=`rgba(185,201,167,${.12+(Math.sin(x*7+y*3)+1)*.09})`;c.beginPath();c.arc(left+7+x*(cw-14)/10,top+15+y*(ch-30)/44,2,0,TAU);c.fill();}
    const bandY=top+25+p*(ch-65),band=c.createLinearGradient(0,bandY-15,0,bandY+20);band.addColorStop(0,'#ff785f00');band.addColorStop(.5,'#ff785faa');band.addColorStop(1,'#ff785f00');c.fillStyle=band;c.fillRect(left+2,bandY-15,cw-4,35);
    const steel=c.createLinearGradient(left,0,left+cw,0);steel.addColorStop(0,'#788777');steel.addColorStop(.4,'#c8d0bd');steel.addColorStop(1,'#535e50');c.fillStyle=steel;
    c.fillRect(cx-4,top-24,8,24);c.fillRect(cx-4,top+ch,8,24);
    for(const y of [top-5,top+ch-6]){c.beginPath();c.roundRect(left-9,y,cw+18,12,3);c.fill();}
    c.strokeStyle='#ff785f77';c.beginPath();c.moveTo(left+cw+12,bandY);c.lineTo(left+cw+35,bandY);c.stroke();
  }
  async function boot() {
    const el=document.querySelector('[data-scene="antibody"]');
    if(el)try{const res=await fetch(el.dataset.src);if(!res.ok)throw Error('Molecule data unavailable');const chains=await res.json();host(el,h=>molecule(h,chains));}catch{el.classList.add('is-fallback');}
    document.querySelectorAll('[data-scene="column"]').forEach(el=>host(el,column));
    // The third visual is a secondary static illustration, keeping focus on skills.
    document.querySelectorAll('[data-scene="bioreactor"]').forEach(el=>el.classList.add('is-fallback'));
  }
  document.addEventListener('visibilitychange',()=>hosts.forEach(h=>document.hidden?h.stop():h.start()));
  motion.addEventListener('change',()=>hosts.forEach(h=>{h.stop();h.start();}));
  addEventListener('scroll',()=>hosts.forEach(h=>{if(h.visible&&h.el.dataset.scene==='column')h.paint();}),{passive:true});
  boot();
})();
