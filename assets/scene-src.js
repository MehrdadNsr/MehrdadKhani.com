/*
  mehrdadkhani.com - 3D scenes
  Three scroll-reactive objects, one per <div data-scene="…">:
    antibody   an IgG C-alpha trace (PDB 1IGT), heavy chains red, light chains pale
    column     a chromatography column with a packed bed and a protein band that
               elutes down the bed as you scroll past it
    bioreactor a stirred-tank bioreactor, impellers turning, bubbles rising
  Each scene renders only while on screen, pauses when the tab is hidden, honours
  prefers-reduced-motion (one static frame), and hands over to a CSS fallback if
  WebGL is unavailable or the context is lost.
*/
import {
  Scene, PerspectiveCamera, WebGLRenderer, Group, Mesh, Object3D, Color, Vector3,
  MeshStandardMaterial, MeshPhysicalMaterial, MeshBasicMaterial,
  SphereGeometry, CylinderGeometry, TubeGeometry, TorusGeometry, BoxGeometry, RingGeometry,
  CatmullRomCurve3, InstancedMesh, BufferGeometry, Float32BufferAttribute, Points, PointsMaterial,
  DirectionalLight, HemisphereLight, PointLight,
  SRGBColorSpace, ACESFilmicToneMapping, AdditiveBlending, DoubleSide
} from 'three';

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;

const PALETTE = {
  crimson: 0xd8203a, crimsonDeep: 0x6b0d1c, ember: 0xff4d63,
  bone: 0xe9e8ea, steel: 0x9aa0a8, graphite: 0x2a2e34, smoke: 0x15181c
};

/* shared pointer for parallax --------------------------------------------- */
const pointer = { x: 0, y: 0 };
addEventListener('pointermove', (e) => {
  pointer.x = (e.clientX / innerWidth) * 2 - 1;
  pointer.y = (e.clientY / innerHeight) * 2 - 1;
}, { passive: true });

/* a small scene runner shared by all three objects ------------------------- */
class SceneHost {
  constructor(el, build) {
    this.el = el;
    this.canvas = el.querySelector('canvas') || el.appendChild(document.createElement('canvas'));
    this.visible = false; this.raf = 0; this.t = 0; this.last = 0;
    this.drag = { on: false, x: 0, vx: 0, rot: 0 };
    this.scrollRot = 0;
    try {
      this.renderer = new WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
    } catch (err) { this.fail(); return; }
    const r = this.renderer;
    r.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
    r.setClearColor(0x000000, 0);
    r.outputColorSpace = SRGBColorSpace;
    r.toneMapping = ACESFilmicToneMapping;
    r.toneMappingExposure = 1.15;
    this.canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); this.fail(); });

    this.scene = new Scene();
    this.camera = new PerspectiveCamera(30, 1, 0.1, 60);
    this.root = new Group(); this.scene.add(this.root);
    this.scene.add(new HemisphereLight(0xffffff, 0x1a0b0e, 1.6));
    const key = new DirectionalLight(0xffffff, 2.6); key.position.set(-3, 5, 4); this.scene.add(key);
    const rim = new DirectionalLight(PALETTE.ember, 2.2); rim.position.set(4, 1.5, -3); this.scene.add(rim);
    const fill = new DirectionalLight(0xc9ccd4, 0.9); fill.position.set(-4, -2, 3); this.scene.add(fill);

    try { this.update = build(this) || (() => {}); } catch (err) { this.fail(); return; }

    this.resize();
    new ResizeObserver(() => this.resize()).observe(el);
    new IntersectionObserver((entries) => {
      this.visible = entries[0].isIntersecting;
      if (this.visible) this.start(); else this.stop();
    }, { rootMargin: '120px 0px' }).observe(el);
    document.addEventListener('visibilitychange', () => (document.hidden ? this.stop() : this.visible && this.start()));

    if (el.dataset.drag !== undefined) this.enableDrag();
    el.dataset.ready = '1';
    el.classList.add('is-rendered');
    this.frame(performance.now());          // always paint one frame
  }

  fail() {
    this.stop();
    this.el.classList.add('is-fallback');
    this.el.classList.remove('is-rendered');
    this.el.dataset.ready = '0';
  }

  resize() {
    const w = Math.max(1, this.el.clientWidth), h = Math.max(1, this.el.clientHeight);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    // keep the object fully in frame on narrow containers
    const s = this.camera.aspect < 0.9 ? 0.72 : this.camera.aspect < 1.25 ? 0.86 : 1;
    this.root.scale.setScalar(s * (this.baseScale || 1));
    if (!this.raf) this.frame(performance.now());
  }

  enableDrag() {
    const c = this.canvas;
    c.style.touchAction = 'pan-y';
    c.addEventListener('pointerdown', (e) => { this.drag.on = true; this.drag.x = e.clientX; this.drag.vx = 0; c.setPointerCapture(e.pointerId); });
    c.addEventListener('pointermove', (e) => {
      if (!this.drag.on) return;
      const dx = e.clientX - this.drag.x; this.drag.x = e.clientX;
      this.drag.rot += dx * 0.008; this.drag.vx = dx * 0.008;
    });
    const up = () => { this.drag.on = false; };
    c.addEventListener('pointerup', up); c.addEventListener('pointercancel', up); c.addEventListener('lostpointercapture', up);
  }

  // 0 when the section enters from below, 1 when it has scrolled past the top
  progress() {
    const r = this.el.getBoundingClientRect();
    return clamp((innerHeight - r.top) / (innerHeight + r.height), 0, 1);
  }

  start() { if (!this.raf && !reduced) this.raf = requestAnimationFrame((t) => this.loop(t)); }
  stop() { if (this.raf) cancelAnimationFrame(this.raf); this.raf = 0; }
  loop(t) { this.frame(t); this.raf = requestAnimationFrame((n) => this.loop(n)); }

  frame(now) {
    const dt = Math.min(0.05, (now - (this.last || now)) / 1000); this.last = now;
    if (!reduced) {
      this.t += dt;
      if (!this.drag.on) { this.drag.rot += this.drag.vx; this.drag.vx *= 0.94; }
    }
    this.update({ t: this.t, dt, progress: this.progress(), pointer, drag: this.drag.rot, reduced });
    this.renderer.render(this.scene, this.camera);
    this.el.dataset.frames = String((+this.el.dataset.frames || 0) + 1);
  }
}

/* helpers ------------------------------------------------------------------ */
function dust(count, radius, color, size) {
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = radius * Math.cbrt(Math.random()), th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th); pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th); pos[i * 3 + 2] = r * Math.cos(ph);
  }
  const g = new BufferGeometry(); g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  return new Points(g, new PointsMaterial({ color, size, sizeAttenuation: true, transparent: true, opacity: 0.55, blending: AdditiveBlending, depthWrite: false }));
}

/* 1. antibody --------------------------------------------------------------- */
async function antibody(host) {
  host.camera.position.set(0, 0.1, 7.4); host.camera.lookAt(0, 0, 0);
  host.baseScale = 1; host.root.scale.setScalar(1);
  const mol = new Group(); host.root.add(mol);
  const particles = dust(320, 3.4, PALETTE.ember, 0.035); host.root.add(particles);
  const glow = new PointLight(PALETTE.crimson, 10, 7, 2); glow.position.set(0, -0.4, 1.2); host.root.add(glow);

  const res = await fetch(host.el.dataset.src || 'assets/igg-ca.json');
  const chains = await res.json();
  const heavy = new MeshPhysicalMaterial({ color: PALETTE.crimson, emissive: PALETTE.crimsonDeep, emissiveIntensity: 0.55, roughness: 0.32, metalness: 0.08, clearcoat: 0.8, clearcoatRoughness: 0.25 });
  const light = new MeshPhysicalMaterial({ color: PALETTE.bone, emissive: 0x2b2b30, emissiveIntensity: 0.35, roughness: 0.42, metalness: 0.05, clearcoat: 0.6, clearcoatRoughness: 0.3 });
  for (const [id, flat] of Object.entries(chains)) {
    const pts = [];
    for (let i = 0; i < flat.length; i += 3) pts.push(new Vector3(flat[i] * 1.9, flat[i + 1] * 1.9, flat[i + 2] * 1.9));
    const curve = new CatmullRomCurve3(pts, false, 'centripetal', 0.5);
    const isHeavy = flat.length / 3 > 300;
    const tube = new Mesh(new TubeGeometry(curve, Math.min(900, pts.length * 2), isHeavy ? 0.052 : 0.048, 7, false), isHeavy ? heavy : light);
    mol.add(tube);
  }
  mol.rotation.set(0.12, -0.35, 0.05);
  const base = { x: 0.12, z: 0.05 };
  return ({ t, progress, pointer, drag }) => {
    // wide screens: keep the molecule in the right third, clear of the copy;
    // narrow screens: centre it behind the stacked layout
    const targetX = host.camera.aspect < 0.9 ? 0.2 : host.camera.aspect < 1.25 ? 1.3 : 2.7;
    mol.position.x = lerp(mol.position.x, targetX, 0.08);
    mol.rotation.y = -0.35 + t * 0.12 + progress * 1.6 + drag;
    mol.rotation.x = lerp(mol.rotation.x, base.x + pointer.y * 0.18, 0.05);
    mol.rotation.z = lerp(mol.rotation.z, base.z - pointer.x * 0.12, 0.05);
    mol.position.y = Math.sin(t * 0.7) * 0.05;
    particles.rotation.y = -t * 0.03; particles.rotation.x = t * 0.015;
    glow.intensity = 9 + Math.sin(t * 1.3) * 2.5;
  };
}

/* 2. chromatography column -------------------------------------------------- */
function column(host) {
  host.camera.position.set(0, 0.1, 7.4); host.camera.lookAt(0, 0, 0);
  host.baseScale = 0.86; host.root.scale.setScalar(0.86);   // keeps both end caps inside the panel
  const g = new Group(); host.root.add(g);
  const R = 0.62, H = 3.4;

  const glass = new MeshPhysicalMaterial({ color: 0xbfc6d1, transparent: true, opacity: 0.16, roughness: 0.08, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.05, side: DoubleSide, depthWrite: false });
  g.add(new Mesh(new CylinderGeometry(R, R, H, 64, 1, true), glass));

  const steel = new MeshStandardMaterial({ color: PALETTE.steel, metalness: 0.9, roughness: 0.3 });
  const capGeo = new CylinderGeometry(R + 0.06, R + 0.06, 0.16, 64);
  const top = new Mesh(capGeo, steel); top.position.y = H / 2 + 0.08; g.add(top);
  const bot = new Mesh(capGeo, steel); bot.position.y = -H / 2 - 0.08; g.add(bot);
  const band = new Mesh(new TorusGeometry(R + 0.07, 0.025, 10, 72), steel); band.rotation.x = Math.PI / 2; band.position.y = H * 0.3; g.add(band);
  const band2 = band.clone(); band2.position.y = -H * 0.3; g.add(band2);
  const tube = new Mesh(new CylinderGeometry(0.05, 0.05, 0.7, 16), steel); tube.position.y = H / 2 + 0.5; g.add(tube);
  const tube2 = tube.clone(); tube2.position.y = -H / 2 - 0.5; g.add(tube2);

  // packed bed: instanced resin beads with a slight tint spread
  const bedH = H * 0.86, count = 1500;
  const bead = new InstancedMesh(new SphereGeometry(0.055, 8, 6), new MeshStandardMaterial({ color: 0xffffff, roughness: 0.55, metalness: 0.05 }), count);
  const dummy = new Object3D(), c = new Color();
  for (let i = 0; i < count; i++) {
    const rr = (R - 0.08) * Math.sqrt(Math.random()), th = Math.random() * Math.PI * 2;
    dummy.position.set(rr * Math.cos(th), (Math.random() - 0.5) * bedH, rr * Math.sin(th));
    dummy.scale.setScalar(0.8 + Math.random() * 0.5); dummy.updateMatrix(); bead.setMatrixAt(i, dummy.matrix);
    c.setHSL(0.97, 0.06 + Math.random() * 0.08, 0.72 + Math.random() * 0.2); bead.setColorAt(i, c);
  }
  bead.instanceMatrix.needsUpdate = true; bead.instanceColor.needsUpdate = true; g.add(bead);

  // the protein band: a glowing disc that elutes down the bed with scroll
  const prot = new Mesh(new CylinderGeometry(R - 0.03, R - 0.03, 0.26, 48), new MeshPhysicalMaterial({ color: PALETTE.crimson, emissive: PALETTE.crimson, emissiveIntensity: 1.1, transparent: true, opacity: 0.72, roughness: 0.3, depthWrite: false }));
  g.add(prot);
  const lamp = new PointLight(PALETTE.crimson, 14, 4, 2); g.add(lamp);
  const haze = dust(140, 2.2, PALETTE.ember, 0.03); g.add(haze);

  g.rotation.z = 0.18; g.rotation.x = 0.1;
  return ({ t, progress, pointer, reduced }) => {
    const p = reduced ? 0.45 : progress;
    const y = lerp(bedH / 2 - 0.2, -bedH / 2 + 0.2, clamp((p - 0.15) / 0.7, 0, 1));
    prot.position.y = y; lamp.position.set(0, y, 0.2);
    prot.scale.y = 1 + Math.sin(t * 2.2) * 0.08;
    g.rotation.y = t * 0.18 + progress * 1.2;
    g.rotation.x = lerp(g.rotation.x, 0.1 + pointer.y * 0.12, 0.05);
    g.rotation.z = lerp(g.rotation.z, 0.18 - pointer.x * 0.08, 0.05);
    haze.rotation.y = -t * 0.05;
  };
}

/* 3. stirred-tank bioreactor ------------------------------------------------ */
function bioreactor(host) {
  host.camera.position.set(0, 0.4, 8.0); host.camera.lookAt(0, 0, 0);
  const g = new Group(); host.root.add(g);
  const R = 1.05, H = 2.6;

  const glass = new MeshPhysicalMaterial({ color: 0xc3c9d2, transparent: true, opacity: 0.14, roughness: 0.06, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.04, side: DoubleSide, depthWrite: false });
  g.add(new Mesh(new CylinderGeometry(R, R, H, 72, 1, true), glass));
  const dome = new Mesh(new SphereGeometry(R, 72, 24, 0, Math.PI * 2, 0, Math.PI / 2), glass); dome.position.y = H / 2; g.add(dome);
  const dish = new Mesh(new SphereGeometry(R, 72, 24, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), glass); dish.position.y = -H / 2; dish.scale.y = 0.35; g.add(dish);

  const steel = new MeshStandardMaterial({ color: PALETTE.steel, metalness: 0.92, roughness: 0.28 });
  const plate = new Mesh(new CylinderGeometry(R + 0.12, R + 0.12, 0.12, 72), steel); plate.position.y = H / 2 + 0.02; g.add(plate);
  const ringB = new Mesh(new TorusGeometry(R + 0.03, 0.03, 10, 90), steel); ringB.rotation.x = Math.PI / 2; ringB.position.y = -H / 2; g.add(ringB);
  for (let i = 0; i < 3; i++) {
    const port = new Mesh(new CylinderGeometry(0.07, 0.07, 0.5, 16), steel);
    port.position.set(Math.cos(i * 2.1) * 0.55, H / 2 + 0.3, Math.sin(i * 2.1) * 0.55); g.add(port);
  }

  // broth: crimson liquid, a flat meniscus with a soft inner glow
  const liquid = new MeshPhysicalMaterial({ color: 0x8a1124, emissive: 0x3a0610, emissiveIntensity: 0.6, transparent: true, opacity: 0.6, roughness: 0.35, depthWrite: false });
  const level = H * 0.68;
  const broth = new Mesh(new CylinderGeometry(R - 0.02, R - 0.02, level, 72), liquid); broth.position.y = -H / 2 + level / 2 + 0.02; g.add(broth);
  const inner = new PointLight(PALETTE.crimson, 12, 5, 2); inner.position.set(0, -0.2, 0); g.add(inner);

  // shaft, two Rushton impellers, four baffles
  const shaft = new Mesh(new CylinderGeometry(0.045, 0.045, H + 0.6, 16), steel); shaft.position.y = 0.3; g.add(shaft);
  const impellers = new Group(); g.add(impellers);
  const bladeMat = new MeshStandardMaterial({ color: 0xb9bec6, metalness: 0.9, roughness: 0.25 });
  for (const y of [-0.55, 0.25]) {
    const disc = new Mesh(new CylinderGeometry(0.38, 0.38, 0.03, 48), bladeMat); disc.position.y = y; impellers.add(disc);
    for (let i = 0; i < 6; i++) {
      const b = new Mesh(new BoxGeometry(0.22, 0.17, 0.025), bladeMat);
      const a = (i / 6) * Math.PI * 2; b.position.set(Math.cos(a) * 0.46, y, Math.sin(a) * 0.46); b.rotation.y = -a; impellers.add(b);
    }
  }
  const baffleMat = new MeshStandardMaterial({ color: 0xa5aab2, metalness: 0.85, roughness: 0.35, transparent: true, opacity: 0.8 });
  for (let i = 0; i < 4; i++) {
    const bf = new Mesh(new BoxGeometry(0.1, H - 0.2, 0.02), baffleMat);
    const a = (i / 4) * Math.PI * 2; bf.position.set(Math.cos(a) * (R - 0.08), 0, Math.sin(a) * (R - 0.08)); bf.rotation.y = -a; g.add(bf);
  }

  // bubbles: instanced spheres rising through the broth, recycled at the top
  const nb = 160, bubbles = new InstancedMesh(new SphereGeometry(0.03, 8, 6), new MeshPhysicalMaterial({ color: 0xffd9df, transparent: true, opacity: 0.55, roughness: 0.1, clearcoat: 1 }), nb);
  const bState = []; const dummy = new Object3D();
  const bottomY = -H / 2 + 0.05, topY = bottomY + level - 0.05;
  for (let i = 0; i < nb; i++) {
    const rr = (R - 0.15) * Math.sqrt(Math.random()), th = Math.random() * Math.PI * 2;
    bState.push({ x: rr * Math.cos(th), z: rr * Math.sin(th), y: bottomY + Math.random() * (topY - bottomY), v: 0.25 + Math.random() * 0.35, s: 0.5 + Math.random() });
  }
  g.add(bubbles);
  const paint = () => {
    for (let i = 0; i < nb; i++) { const b = bState[i]; dummy.position.set(b.x, b.y, b.z); dummy.scale.setScalar(b.s); dummy.updateMatrix(); bubbles.setMatrixAt(i, dummy.matrix); }
    bubbles.instanceMatrix.needsUpdate = true;
  };
  paint();

  g.rotation.x = 0.16; g.rotation.y = -0.4;
  return ({ t, dt, progress, pointer, reduced }) => {
    impellers.rotation.y = t * 2.2 + progress * 6;
    if (!reduced) {
      for (const b of bState) { b.y += b.v * dt; b.x += Math.sin(t * 2 + b.z * 5) * dt * 0.05; if (b.y > topY) b.y = bottomY; }
      paint();
    }
    g.rotation.y = -0.4 + t * 0.1 + progress * 1.0;
    g.rotation.x = lerp(g.rotation.x, 0.16 + pointer.y * 0.1, 0.05);
    g.rotation.z = lerp(g.rotation.z, -pointer.x * 0.06, 0.05);
    inner.intensity = 10 + Math.sin(t * 1.7) * 3;
  };
}

/* boot --------------------------------------------------------------------- */
const builders = { antibody, column, bioreactor };
function boot() {
  const supported = (() => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; } })();
  document.querySelectorAll('[data-scene]').forEach((el) => {
    const build = builders[el.dataset.scene];
    if (!build || !supported) { el.classList.add('is-fallback'); el.dataset.ready = '0'; return; }
    new SceneHost(el, (host) => {
      const r = build(host);
      // async builders (antibody loads its data) return a promise of the updater
      if (r && typeof r.then === 'function') { let fn = () => {}; r.then((f) => { fn = f; host.frame(performance.now()); }).catch(() => host.fail()); return (s) => fn(s); }
      return r;
    });
  });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
