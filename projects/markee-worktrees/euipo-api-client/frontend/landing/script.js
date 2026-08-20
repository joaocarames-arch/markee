/**
 * markee — Cinematic landing page behaviour.
 *
 * Orchestrates: Lenis inertial scrolling, GSAP/ScrollTrigger choreography,
 * a Three.js particle wave field in the hero, magnetic buttons, tilt cards,
 * the custom cursor and the engine showcase tabs.
 *
 * Everything degrades gracefully:
 * - prefers-reduced-motion disables Lenis, WebGL and all choreography.
 * - Small screens / coarse pointers skip WebGL, cursor, magnetic and tilt.
 * - Missing CDN globals (gsap/Lenis) fall back to a static, readable page.
 */

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const pointerFine = window.matchMedia('(pointer: fine)').matches;
const isDesktop = window.matchMedia('(min-width: 1024px)').matches;
const hasGsap = typeof window.gsap !== 'undefined' && typeof window.ScrollTrigger !== 'undefined';
const hasLenis = typeof window.Lenis !== 'undefined';

if (hasGsap) {
  gsap.registerPlugin(ScrollTrigger);
}

if (reducedMotion) {
  document.body.classList.add('reduced-motion');
}

/* ==========================================================================
   Text splitting helpers
   ========================================================================== */

/**
 * Wraps the contents of each .hero__line in an inner span so the line can
 * slide up from behind an overflow clip.
 */
function splitHeroLines() {
  document.querySelectorAll('.hero__line').forEach((line) => {
    const inner = document.createElement('span');
    inner.className = 'hero__line-inner';
    while (line.firstChild) {
      inner.appendChild(line.firstChild);
    }
    line.appendChild(inner);
  });
}

/** Splits an element's text into per-word spans (class "w"). */
function splitWords(el) {
  const words = el.textContent.trim().split(/\s+/);
  el.textContent = '';
  words.forEach((word, i) => {
    const span = document.createElement('span');
    span.className = 'w';
    span.textContent = word;
    el.appendChild(span);
    if (i < words.length - 1) {
      el.appendChild(document.createTextNode(' '));
    }
  });
}

/** Splits an element's text into per-character spans (class "ch"). */
function splitChars(el) {
  const chars = el.textContent.trim().split('');
  el.textContent = '';
  chars.forEach((ch) => {
    const span = document.createElement('span');
    span.className = 'ch';
    span.textContent = ch;
    el.appendChild(span);
  });
}

/* ==========================================================================
   Smooth scrolling (Lenis) + GSAP ticker integration
   ========================================================================== */

let lenis = null;

function initLenis() {
  if (!hasLenis || !hasGsap || reducedMotion) {
    return;
  }

  lenis = new Lenis({
    duration: 1.15,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
  });

  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((time) => {
    lenis.raf(time * 1000);
  });
  gsap.ticker.lagSmoothing(0);
}

/** Scrolls to a target element, through Lenis when available. */
function scrollToTarget(target) {
  if (lenis) {
    lenis.scrollTo(target, { offset: -96 });
  } else {
    target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth' });
  }
}

function initAnchorLinks() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const id = link.getAttribute('href').slice(1);
      const target = id ? document.getElementById(id) : null;
      if (target) {
        event.preventDefault();
        scrollToTarget(target);
      }
    });
  });
}

/* ==========================================================================
   Preloader
   ========================================================================== */

function initPreloader(onDone) {
  const preloader = document.getElementById('preloader');
  if (!preloader) {
    onDone();
    return;
  }

  let finished = false;
  const finish = () => {
    if (finished) {
      return;
    }
    finished = true;
    preloader.classList.add('is-done');
    onDone();
  };

  if (document.readyState === 'complete') {
    setTimeout(finish, 250);
  } else {
    window.addEventListener('load', () => setTimeout(finish, 250));
  }
  // Hard ceiling so a slow CDN asset never traps the visitor behind the veil.
  setTimeout(finish, 2600);
}

/* ==========================================================================
   Navigation — condense + auto-hide, mobile menu
   ========================================================================== */

function initNav() {
  const nav = document.getElementById('siteNav');
  const toggle = document.getElementById('navToggle');
  const menu = document.getElementById('mobileMenu');
  if (!nav) {
    return;
  }

  let lastY = window.scrollY;
  let menuOpen = false;

  const onScroll = (y) => {
    nav.classList.toggle('is-condensed', y > 40);
    // Hide when scrolling down past the hero, reveal on any upward intent.
    if (!menuOpen && y > 400 && y > lastY + 4) {
      nav.classList.add('is-hidden');
    } else if (y < lastY - 4 || y <= 400) {
      nav.classList.remove('is-hidden');
    }
    lastY = y;
  };

  if (lenis) {
    lenis.on('scroll', ({ scroll }) => onScroll(scroll));
  } else {
    window.addEventListener('scroll', () => onScroll(window.scrollY), { passive: true });
  }

  if (toggle && menu) {
    const setMenu = (open) => {
      menuOpen = open;
      menu.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    };

    toggle.addEventListener('click', () => setMenu(menu.hidden));
    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => setMenu(false));
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menuOpen) {
        setMenu(false);
        toggle.focus();
      }
    });
  }
}

/* ==========================================================================
   GSAP choreography
   ========================================================================== */

function playHeroIntro() {
  if (!hasGsap || reducedMotion) {
    return;
  }

  const tl = gsap.timeline({ defaults: { ease: 'power4.out' } });
  tl.from('.hero__line-inner', {
    yPercent: 115,
    duration: 1.3,
    stagger: 0.12,
  });
  tl.from(
    '[data-hero-fade]',
    { opacity: 0, y: 28, duration: 1.0, stagger: 0.12 },
    '-=0.9'
  );
  tl.from(
    '.site-nav__inner',
    { opacity: 0, y: -24, duration: 0.8 },
    '-=0.8'
  );
}

function initScrollAnimations() {
  if (!hasGsap || reducedMotion) {
    return;
  }

  // Generic section reveals.
  gsap.utils.toArray('.reveal').forEach((el) => {
    gsap.from(el, {
      opacity: 0,
      y: 48,
      duration: 1.1,
      ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 86%', once: true },
    });
  });

  // Manifesto: each word lights up as the statement scrubs through view.
  const manifesto = document.querySelector('.manifesto__text');
  if (manifesto) {
    gsap.to(manifesto.querySelectorAll('.w'), {
      opacity: 1,
      stagger: 0.4,
      ease: 'none',
      scrollTrigger: {
        trigger: manifesto,
        start: 'top 78%',
        end: 'bottom 45%',
        scrub: 0.6,
      },
    });
  }

  // Stat counters.
  gsap.utils.toArray('[data-count]').forEach((el) => {
    const target = parseInt(el.dataset.count, 10);
    const state = { value: 0 };
    ScrollTrigger.create({
      trigger: el,
      start: 'top 88%',
      once: true,
      onEnter: () => {
        gsap.to(state, {
          value: target,
          duration: 1.6,
          ease: 'power2.out',
          onUpdate: () => {
            el.textContent = String(Math.round(state.value));
          },
        });
      },
    });
  });

  // Footer wordmark: characters rise into place.
  const footerChars = document.querySelectorAll('.site-footer__wordmark .ch');
  if (footerChars.length) {
    gsap.from(footerChars, {
      yPercent: 70,
      opacity: 0,
      duration: 1.1,
      stagger: 0.05,
      ease: 'power4.out',
      scrollTrigger: {
        trigger: '.site-footer__wordmark',
        start: 'top 92%',
        once: true,
      },
    });
  }

  // Feature showcase: pinned horizontal scroll on desktop only. On smaller
  // screens the panels stack vertically and use the generic reveal below.
  const mm = gsap.matchMedia();
  mm.add('(min-width: 1024px)', () => {
    const viewport = document.getElementById('featuresViewport');
    const track = document.getElementById('featuresTrack');
    const progress = document.getElementById('featuresProgress');
    if (!viewport || !track) {
      return;
    }

    const distance = () => track.scrollWidth - viewport.clientWidth;

    const tween = gsap.to(track, {
      x: () => -distance(),
      ease: 'none',
      scrollTrigger: {
        trigger: viewport,
        start: 'top top',
        end: () => `+=${distance()}`,
        pin: true,
        scrub: 0.8,
        invalidateOnRefresh: true,
        anticipatePin: 1,
        onUpdate: (self) => {
          if (progress) {
            progress.style.width = `${(self.progress * 100).toFixed(2)}%`;
          }
        },
      },
    });

    // Depth parallax: each panel's visual drifts against the track motion.
    gsap.utils.toArray('.feature-panel__visual').forEach((visual) => {
      gsap.fromTo(
        visual,
        { x: 60 },
        {
          x: -60,
          ease: 'none',
          scrollTrigger: {
            trigger: visual,
            containerAnimation: tween,
            start: 'left right',
            end: 'right left',
            scrub: true,
          },
        }
      );
    });
  });

  mm.add('(max-width: 1023px)', () => {
    gsap.utils.toArray('.feature-panel').forEach((panel) => {
      gsap.from(panel, {
        opacity: 0,
        y: 56,
        duration: 1.0,
        ease: 'power3.out',
        scrollTrigger: { trigger: panel, start: 'top 88%', once: true },
      });
    });
  });
}

/* ==========================================================================
   Engine showcase — accessible tabs with animated transitions
   ========================================================================== */

function animateMeters(panel) {
  panel.querySelectorAll('.sim-meter').forEach((meter) => {
    const value = parseInt(meter.dataset.meter, 10) || 0;
    const fill = meter.querySelector('.sim-meter__fill');
    if (!fill) {
      return;
    }
    fill.style.setProperty('--target', String(value));
    if (hasGsap && !reducedMotion) {
      gsap.fromTo(
        fill,
        { width: '0%' },
        { width: `${value}%`, duration: 1.2, ease: 'power3.out', delay: 0.15 }
      );
    } else {
      fill.style.width = `${value}%`;
    }
  });
}

function initEngineTabs() {
  const tabs = Array.from(document.querySelectorAll('[data-engine-tab]'));
  const panels = tabs.map((tab) =>
    document.getElementById(tab.getAttribute('aria-controls'))
  );
  if (!tabs.length) {
    return;
  }

  let current = 0;

  const select = (index, focus = false) => {
    if (index === current || !panels[index]) {
      return;
    }
    tabs[current].classList.remove('is-active');
    tabs[current].setAttribute('aria-selected', 'false');
    tabs[current].setAttribute('tabindex', '-1');
    panels[current].classList.remove('is-active');
    panels[current].hidden = true;

    current = index;
    tabs[current].classList.add('is-active');
    tabs[current].setAttribute('aria-selected', 'true');
    tabs[current].removeAttribute('tabindex');
    panels[current].hidden = false;
    panels[current].classList.add('is-active');

    if (focus) {
      tabs[current].focus();
    }
    if (hasGsap && !reducedMotion) {
      gsap.fromTo(
        panels[current],
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.55, ease: 'power3.out' }
      );
    }
    if (index === 0) {
      animateMeters(panels[0]);
    }
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => select(index));
    tab.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
        event.preventDefault();
        select((index + 1) % tabs.length, true);
      } else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
        event.preventDefault();
        select((index - 1 + tabs.length) % tabs.length, true);
      }
    });
  });

  // Fire the similarity meters the first time the stage scrolls into view.
  const stage = document.querySelector('.engine__stage');
  if (stage && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          animateMeters(panels[0]);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(stage);
  } else if (panels[0]) {
    animateMeters(panels[0]);
  }
}

/* ==========================================================================
   Pointer flourishes — magnetic buttons, tilt cards, custom cursor
   ========================================================================== */

function initMagnetic() {
  if (!hasGsap || reducedMotion || !pointerFine) {
    return;
  }

  document.querySelectorAll('.magnetic').forEach((el) => {
    const strength = 0.32;
    el.addEventListener('pointermove', (event) => {
      const rect = el.getBoundingClientRect();
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      gsap.to(el, {
        x: dx * strength,
        y: dy * strength,
        duration: 0.4,
        ease: 'power3.out',
      });
    });
    el.addEventListener('pointerleave', () => {
      gsap.to(el, { x: 0, y: 0, duration: 0.7, ease: 'elastic.out(1, 0.4)' });
    });
  });
}

function initTiltCards() {
  if (!hasGsap || reducedMotion || !pointerFine) {
    return;
  }

  document.querySelectorAll('.tilt-card').forEach((card) => {
    card.addEventListener('pointermove', (event) => {
      const rect = card.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;
      // Glow spotlight follows the pointer (consumed by CSS ::before layers).
      card.style.setProperty('--mx', `${(px * 100).toFixed(1)}%`);
      card.style.setProperty('--my', `${(py * 100).toFixed(1)}%`);
      gsap.to(card, {
        rotateY: (px - 0.5) * 8,
        rotateX: (0.5 - py) * 8,
        transformPerspective: 900,
        duration: 0.5,
        ease: 'power2.out',
      });
    });
    card.addEventListener('pointerleave', () => {
      gsap.to(card, { rotateX: 0, rotateY: 0, duration: 0.9, ease: 'elastic.out(1, 0.5)' });
    });
  });
}

function initCursor() {
  if (!hasGsap || reducedMotion || !pointerFine || !isDesktop) {
    return;
  }

  const dot = document.getElementById('cursorDot');
  const ring = document.getElementById('cursorRing');
  if (!dot || !ring) {
    return;
  }

  document.body.classList.add('has-cursor');

  const pos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
  const ringPos = { x: pos.x, y: pos.y };

  window.addEventListener('pointermove', (event) => {
    pos.x = event.clientX;
    pos.y = event.clientY;
    gsap.set(dot, { x: pos.x, y: pos.y });
  });

  // The ring trails the dot with a soft lerp for a filmic lag.
  gsap.ticker.add(() => {
    ringPos.x += (pos.x - ringPos.x) * 0.16;
    ringPos.y += (pos.y - ringPos.y) * 0.16;
    gsap.set(ring, { x: ringPos.x, y: ringPos.y });
  });

  document.querySelectorAll('a, button').forEach((el) => {
    el.addEventListener('pointerenter', () => document.body.classList.add('cursor-hover'));
    el.addEventListener('pointerleave', () => document.body.classList.remove('cursor-hover'));
  });
}

/* ==========================================================================
   Three.js — hero particle wave field
   ========================================================================== */

const VERTEX_SHADER = /* glsl */ `
  uniform float uTime;
  uniform vec2 uMouse;
  uniform float uPixelRatio;
  varying float vElevation;
  varying float vDepth;

  void main() {
    vec3 pos = position;

    // Layered travelling waves; the pointer skews the phase for interactivity.
    float phase = uTime * 0.55 + uMouse.x * 1.4;
    float wave =
      sin(pos.x * 0.35 + phase) * 0.55 +
      cos(pos.z * 0.28 + uTime * 0.4 + uMouse.y * 1.2) * 0.45 +
      sin((pos.x + pos.z) * 0.12 + uTime * 0.25) * 0.35;
    pos.y += wave;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    vElevation = wave;
    vDepth = -mvPosition.z;
    gl_PointSize = uPixelRatio * (16.0 / vDepth) * (1.0 + wave * 0.35);
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  uniform vec3 uColor;
  varying float vElevation;
  varying float vDepth;

  void main() {
    // Soft round sprite.
    float d = distance(gl_PointCoord, vec2(0.5));
    float sprite = smoothstep(0.5, 0.08, d);

    // Fade with distance so the field dissolves into the darkness.
    float fog = smoothstep(42.0, 10.0, vDepth);

    // Crests glow brighter and slightly whiter.
    float crest = smoothstep(-0.4, 1.2, vElevation);
    vec3 color = mix(uColor * 0.55, mix(uColor, vec3(1.0), 0.25), crest);

    float alpha = sprite * fog * (0.25 + crest * 0.55);
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(color, alpha);
  }
`;

async function initWebGL() {
  if (reducedMotion || !isDesktop || !pointerFine) {
    return;
  }

  const canvas = document.getElementById('webglCanvas');
  if (!canvas) {
    return;
  }

  let THREE;
  try {
    THREE = await import('three');
  } catch {
    return; // CDN unavailable — the CSS gradient fallback stays in place.
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: false,
      powerPreference: 'high-performance',
    });
  } catch {
    return; // WebGL unavailable on this device.
  }

  const pixelRatio = Math.min(window.devicePixelRatio, 1.75);
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    58,
    canvas.clientWidth / canvas.clientHeight,
    0.1,
    100
  );
  camera.position.set(0, 5.5, 15);
  camera.lookAt(0, 0, -4);

  // Flat grid of points; the vertex shader turns it into a rolling sea.
  const cols = 150;
  const rows = 85;
  const spacing = 0.38;
  const positions = new Float32Array(cols * rows * 3);
  let i = 0;
  for (let x = 0; x < cols; x += 1) {
    for (let z = 0; z < rows; z += 1) {
      positions[i] = (x - cols / 2) * spacing;
      positions[i + 1] = 0;
      positions[i + 2] = (z - rows / 2) * spacing - 6;
      i += 3;
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const material = new THREE.ShaderMaterial({
    vertexShader: VERTEX_SHADER,
    fragmentShader: FRAGMENT_SHADER,
    uniforms: {
      uTime: { value: 0 },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uPixelRatio: { value: pixelRatio },
      uColor: { value: new THREE.Color(0x35d0e0) },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });

  scene.add(new THREE.Points(geometry, material));
  document.body.classList.add('has-webgl');

  // Pointer state, eased every frame so the field reacts without jitter.
  const mouseTarget = { x: 0, y: 0 };
  const mouseEased = { x: 0, y: 0 };
  window.addEventListener('pointermove', (event) => {
    mouseTarget.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouseTarget.y = (event.clientY / window.innerHeight) * 2 - 1;
  });

  const clock = new THREE.Clock();
  let running = false;

  const render = () => {
    mouseEased.x += (mouseTarget.x - mouseEased.x) * 0.035;
    mouseEased.y += (mouseTarget.y - mouseEased.y) * 0.035;

    material.uniforms.uTime.value = clock.getElapsedTime();
    material.uniforms.uMouse.value.set(mouseEased.x, mouseEased.y);

    // Gentle camera parallax for spatial depth.
    camera.position.x = mouseEased.x * 1.6;
    camera.position.y = 5.5 - mouseEased.y * 0.9;
    camera.lookAt(0, 0, -4);

    renderer.render(scene, camera);
  };

  const setRunning = (value) => {
    if (value === running) {
      return;
    }
    running = value;
    renderer.setAnimationLoop(running ? render : null);
  };

  // Only burn GPU while the hero is actually on screen and the tab is visible.
  let heroVisible = true;
  const observer = new IntersectionObserver(
    (entries) => {
      heroVisible = entries[0].isIntersecting;
      setRunning(heroVisible && !document.hidden);
    },
    { threshold: 0.05 }
  );
  observer.observe(canvas);

  document.addEventListener('visibilitychange', () => {
    setRunning(heroVisible && !document.hidden);
  });

  window.addEventListener('resize', () => {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  });

  setRunning(true);
}

/* ==========================================================================
   Boot
   ========================================================================== */

function boot() {
  splitHeroLines();
  const manifesto = document.querySelector('[data-split-words]');
  if (manifesto && !reducedMotion && hasGsap) {
    splitWords(manifesto);
  }
  const footerMark = document.querySelector('[data-split-chars]');
  if (footerMark) {
    splitChars(footerMark);
  }

  initLenis();
  initAnchorLinks();
  initNav();
  initEngineTabs();
  initMagnetic();
  initTiltCards();
  initCursor();
  initScrollAnimations();
  initWebGL();

  initPreloader(() => {
    playHeroIntro();
    if (hasGsap) {
      ScrollTrigger.refresh();
    }
  });

  // Recalculate pinned distances once fonts finish loading (layout shifts).
  if (hasGsap && document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => ScrollTrigger.refresh());
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
