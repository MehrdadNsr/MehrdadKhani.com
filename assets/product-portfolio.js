(() => {
 const nav=document.querySelector('nav'),menu=document.querySelector('.menu');
 function closeMenu(){nav.classList.remove('open');menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label','Open menu');}
 menu.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?'Close menu':'Open menu');});
 nav.addEventListener('click',e=>{if(e.target.closest('a'))closeMenu();});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMenu();menu.focus();}});
 const canvas=document.getElementById('network'),c=canvas.getContext('2d'),stage=canvas.parentElement,button=document.getElementById('motion');
 if(!c)return;
 const labels=[...document.querySelectorAll('.orbit-label')];let interacting=false;stage.addEventListener('pointerenter',()=>interacting=true);stage.addEventListener('pointerleave',()=>interacting=false);stage.addEventListener('focusin',()=>interacting=true);stage.addEventListener('focusout',()=>interacting=false);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');let active=!reduced.matches,visible=false,raf=0,angle=-.4,mode=0,time=0,last=0,w=0,h=0,drag=false,px=0;
 const points=Array.from({length:190},(_,i)=>{const y=1-2*(i+.5)/190,r=Math.sqrt(1-y*y),a=i*2.399963;return{x:Math.cos(a)*r,y,z:Math.sin(a)*r};});
 function draw(){c.clearRect(0,0,w,h);const scale=Math.min(w*.36,h*.34),cx=w*.52,cy=h*.51;
  const transformed=points.map((p,i)=>{let {x,y,z}=p;if(mode===1){x=Math.sign(x)*Math.pow(Math.abs(x),.5);y=Math.sign(y)*Math.pow(Math.abs(y),.5);z=Math.sign(z)*Math.pow(Math.abs(z),.5);}else if(mode===2){const t=i/190*Math.PI*8;x=Math.cos(t)*.75;y=(i/190-.5)*2.1;z=Math.sin(t)*.75;}const rx=x*Math.cos(angle)+z*Math.sin(angle),rz=-x*Math.sin(angle)+z*Math.cos(angle);return{x:cx+rx*scale,y:cy+(y*.92+rz*.22)*scale,z:rz};});
  for(let i=0;i<transformed.length;i++){const p=transformed[i];for(let j=i+1;j<transformed.length;j++){if(j-i>24&&mode===2)break;const q=transformed[j],d=Math.hypot(p.x-q.x,p.y-q.y,(p.z-q.z)*scale);if(d<scale*.34){c.strokeStyle=`rgba(76,112,46,${(.28+.12*p.z)*(1-d/(scale*.4))})`;c.lineWidth=.7;c.beginPath();c.moveTo(p.x,p.y);c.lineTo(q.x,q.y);c.stroke();}}}
  transformed.sort((a,b)=>a.z-b.z);for(const p of transformed){c.fillStyle=`rgba(73,109,46,${.42+p.z*.3})`;c.beginPath();c.arc(p.x,p.y,1.3+(p.z+1)*.8,0,Math.PI*2);c.fill();}
  c.strokeStyle='#6c8b4540';c.lineWidth=1;c.beginPath();c.ellipse(cx,cy,scale*1.23,scale*.43,-.4,0,Math.PI*2);c.stroke();
  labels.forEach((label,i)=>{const a=angle*.75+i*Math.PI*2/labels.length;const depth=Math.sin(a),x=Math.cos(a)*Math.min(w*.31,210),y=depth*Math.min(h*.29,160);label.style.transform=`translate(calc(-50% + ${x}px),calc(-50% + ${y}px))`;label.style.zIndex=String(Math.round((depth+1)*5)+1);});
 }
 function stop(){cancelAnimationFrame(raf);raf=0;}
 function loop(now){raf=0;if(!active||!visible||document.hidden)return;const dt=Math.min((now-(last||now))/1000,.04);last=now;time+=dt;if(!drag&&!interacting)angle+=dt*.16;draw();raf=requestAnimationFrame(loop);}
 function start(){if(active&&visible&&!document.hidden&&!raf){last=0;raf=requestAnimationFrame(loop);}else draw();}
 new ResizeObserver(()=>{const r=stage.getBoundingClientRect();w=r.width;h=r.height;const d=Math.min(devicePixelRatio||1,2);canvas.width=w*d;canvas.height=h*d;c.setTransform(d,0,0,d,0,0);draw();}).observe(stage);
 new IntersectionObserver(([e])=>{visible=e.isIntersecting;visible?start():stop();}).observe(stage);
 document.addEventListener('visibilitychange',()=>document.hidden?stop():start());
 function updateMotion(){button.textContent=active?'Motion: on':'Motion: off';button.setAttribute('aria-pressed',String(active));stop();start();}
 button.addEventListener('click',()=>{active=!active;updateMotion();});reduced.addEventListener('change',()=>{active=!reduced.matches;updateMotion();});updateMotion();
 canvas.addEventListener('pointerdown',e=>{drag=true;px=e.clientX;canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(drag){angle+=(e.clientX-px)*.008;px=e.clientX;draw();}});['pointerup','pointercancel','lostpointercapture'].forEach(type=>canvas.addEventListener(type,()=>drag=false));
 const notes=['From pharmaceutical teams to AI products.','Bring people and work together.','Build. Review. Improve.'];
 document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{mode=Number(b.dataset.mode);document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.getElementById('stage-note').textContent=notes[mode];draw();}));
})();
