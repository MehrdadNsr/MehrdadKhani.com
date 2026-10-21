/* mehrdadkhani.com - page behaviour (nav, reveals, counters). The 3D scenes
   live in assets/scene.js and load as a module after this. */
document.addEventListener('DOMContentLoaded', () => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* nav: solid once scrolled, mobile toggle, active section */
  const nav = document.getElementById('navbar');
  const links = document.querySelector('.nav-links');
  const toggle = document.querySelector('.nav-toggle');
  const onScroll = () => nav && nav.classList.toggle('scrolled', scrollY > 24);
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    links.addEventListener('click', (e) => { if (e.target.closest('a')) { links.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); } });
  }
  const navAnchors = [...document.querySelectorAll('.nav-links a[href^="#"]')];
  const sections = navAnchors.map((a) => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (sections.length && 'IntersectionObserver' in window) {
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        navAnchors.forEach((a) => a.classList.toggle('active', a.getAttribute('href') === '#' + en.target.id));
      });
    }, { rootMargin: '-35% 0px -55% 0px' });
    sections.forEach((s) => spy.observe(s));
  }

  /* reveal on scroll */
  const reveals = document.querySelectorAll('.reveal');
  if (reduced || !('IntersectionObserver' in window)) {
    reveals.forEach((el) => el.classList.add('visible'));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('visible'); io.unobserve(en.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -5% 0px' });
    reveals.forEach((el) => io.observe(el));
    // Safety net: when the 3D scenes keep a slow device busy, observer callbacks
    // can lag behind the scroll. Anything that has entered the viewport is shown.
    let pending = false;
    const sweep = () => {
      pending = false;
      const limit = innerHeight * 1.05;
      reveals.forEach((el) => { if (!el.classList.contains('visible') && el.getBoundingClientRect().top < limit) { el.classList.add('visible'); io.unobserve(el); } });
    };
    addEventListener('scroll', () => { if (!pending) { pending = true; requestAnimationFrame(sweep); } }, { passive: true });
    setTimeout(sweep, 800);
  }

  /* metric counters: count up once when they scroll into view */
  const counters = document.querySelectorAll('[data-count]');
  const run = (el) => {
    const target = parseFloat(el.dataset.count), suffix = el.dataset.suffix || '', dur = 1400, start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - t, 3);
      el.firstChild.nodeValue = Math.round(target * e).toLocaleString('en-US') + (t < 1 ? '' : suffix);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  if (reduced) counters.forEach((el) => { el.firstChild.nodeValue = parseFloat(el.dataset.count).toLocaleString('en-US') + (el.dataset.suffix || ''); });
  else {
    const io = new IntersectionObserver((entries) => { entries.forEach((en) => { if (en.isIntersecting) { run(en.target); io.unobserve(en.target); } }); }, { threshold: 0.5 });
    counters.forEach((el) => io.observe(el));
  }

  /* scroll to top */
  const top = document.getElementById('scrollTopBtn');
  if (top) {
    addEventListener('scroll', () => top.classList.toggle('show', scrollY > 600), { passive: true });
    top.addEventListener('click', () => scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' }));
  }

  /* footer year */
  document.querySelectorAll('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
});
