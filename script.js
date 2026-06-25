document.addEventListener('DOMContentLoaded', () => {
  // Intersection Observer for scroll animations
  const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.15
  };

  const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target); // Only animate once
      }
    });
  }, observerOptions);

  const revealElements = document.querySelectorAll('.scroll-reveal');
  revealElements.forEach(el => {
    observer.observe(el);
  });

  // Shrink navbar on scroll
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.style.padding = '0.5rem 2rem';
      navbar.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.5)';
    } else {
      navbar.style.padding = '1rem 2rem';
      navbar.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.4)';
    }
  });

  // Scroll to Top Button Logic
  const scrollTopBtn = document.getElementById('scrollTopBtn');
  
  if (scrollTopBtn) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 400) {
        scrollTopBtn.classList.add('show');
      } else {
        scrollTopBtn.classList.remove('show');
      }
    });

    scrollTopBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  }
});
