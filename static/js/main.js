// ===========================
// AOS Animations
// ===========================
document.addEventListener('DOMContentLoaded', () => {
  AOS.init({
    duration: 600,
    easing: 'ease-out-cubic',
    once: true,
    offset: 60,
    disable: 'mobile',
  });

  initNavbar();
  initReadingProgress();
  initMobileNav();
  initTypingEffect();
  initNewsletterForm();
});

// ===========================
// Navbar: scroll effects
// ===========================
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const onScroll = () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ===========================
// Reading Progress Bar
// ===========================
function initReadingProgress() {
  const bar = document.getElementById('reading-progress');
  if (!bar) return;

  const postBody = document.querySelector('.post-body');
  if (!postBody) return;

  const update = () => {
    const total = document.documentElement.scrollHeight - window.innerHeight;
    const progress = total > 0 ? (window.scrollY / total) * 100 : 0;
    bar.style.width = Math.min(100, progress) + '%';
  };

  window.addEventListener('scroll', update, { passive: true });
  update();
}

// ===========================
// Mobile Navigation Toggle
// ===========================
function initMobileNav() {
  const toggle = document.getElementById('nav-toggle');
  const navLinks = document.getElementById('nav-links');
  if (!toggle || !navLinks) return;

  toggle.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    const spans = toggle.querySelectorAll('span');
    const isOpen = navLinks.classList.contains('open');
    if (isOpen) {
      spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
    } else {
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
    }
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!toggle.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove('open');
      const spans = toggle.querySelectorAll('span');
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
    }
  });
}

// ===========================
// Typing Effect (Hero)
// ===========================
function initTypingEffect() {
  const el = document.getElementById('typed-text');
  if (!el) return;

  const words = ['Generative AI', 'LLM Era', 'AI Agents', 'RAG Systems', 'Future of Work'];
  let wordIdx = 0;
  let charIdx = 0;
  let isDeleting = false;
  let delay = 120;

  const tick = () => {
    const current = words[wordIdx];
    if (isDeleting) {
      el.textContent = current.substring(0, charIdx - 1);
      charIdx--;
      delay = 60;
    } else {
      el.textContent = current.substring(0, charIdx + 1);
      charIdx++;
      delay = 120;
    }

    if (!isDeleting && charIdx === current.length) {
      delay = 2200;
      isDeleting = true;
    } else if (isDeleting && charIdx === 0) {
      isDeleting = false;
      wordIdx = (wordIdx + 1) % words.length;
      delay = 400;
    }

    setTimeout(tick, delay);
  };

  setTimeout(tick, 1000);
}

// ===========================
// Newsletter Form (UI only)
// ===========================
function initNewsletterForm() {
  document.querySelectorAll('.newsletter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (input && input.value && input.value.includes('@')) {
        btn.textContent = '✓ Subscribed!';
        btn.style.background = '#10b981';
        input.value = '';
        setTimeout(() => {
          btn.textContent = 'Subscribe';
          btn.style.background = '';
        }, 3000);
      } else if (input) {
        input.style.borderColor = '#ef4444';
        setTimeout(() => { input.style.borderColor = ''; }, 2000);
      }
    });
  });
}

// ===========================
// Smooth scroll for anchor links
// ===========================
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="#"]');
  if (!link) return;
  const id = link.getAttribute('href').slice(1);
  const target = document.getElementById(id);
  if (target) {
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});

// ===========================
// Prism.js: apply after DOM load
// ===========================
if (typeof Prism !== 'undefined') {
  Prism.highlightAll();
}
