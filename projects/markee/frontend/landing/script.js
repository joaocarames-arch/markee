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
   Language switching — English default, Portuguese optional
   ========================================================================== */

const i18n = {
  "pt": {
    "meta.title": "markee — Monitorização de marcas · INPI & EUIPO",
    "meta.description": "O markee observa os registos de marcas de Portugal e da Europa em permanência. Alertas de similaridade, gestão de prazos e prospeção de clientes para profissionais de PI.",
    "preloader.meta": "A PREPARAR A VIGÍLIA",
    "skip.content": "Saltar para o conteúdo",
    "nav.home_aria": "markee — página inicial",
    "nav.features": "Funcionalidades",
    "nav.engine": "O Motor",
    "nav.pricing": "Preços",
    "nav.login": "Entrar",
    "nav.create": "Criar conta",
    "nav.service_status": "Estado do serviço",
    "hero.eyebrow": "INPI · EUIPO — MONITORIZAÇÃO CONTÍNUA DE MARCAS",
    "hero.title": "A sua marca, sob vigilância absoluta.",
    "hero.title.line1": "A sua marca,",
    "hero.title.line2": "sob vigilância",
    "hero.title.line3": "<em class=\"hero__title-accent\">absoluta.</em>",
    "hero.subtitle": "O markee observa os registos de Portugal e da Europa em permanência — deteta conflitos, antecipa prazos e transforma vigilância em vantagem.",
    "hero.cta.primary": "Entrar",
    "hero.cta.secondary": "Explorar funcionalidades",
    "hero.meta.location": "38.7223° N, 9.1393° W — LISBOA",
    "hero.meta.scroll": "DESLIZE",
    "hero.meta.est": "EST. 2026 — SEMPRE ATENTO",
    "ticker.inpi": "INPI — PORTUGAL",
    "ticker.euipo": "EUIPO — UNIÃO EUROPEIA",
    "ticker.bpi": "BOLETIM DA PROPRIEDADE INDUSTRIAL",
    "ticker.nice": "45 CLASSES DE NICE",
    "ticker.phonetic": "ANÁLISE FONÉTICA PT",
    "ticker.alerts": "ALERTAS EM TEMPO ÚTIL",
    "manifesto.aria": "Manifesto",
    "manifesto.eyebrow": "O NOSSO PONTO DE PARTIDA",
    "manifesto.text": "Uma marca é mais do que um nome. É território. E território defende-se — com atenção permanente, não com sorte.",
    "features.eyebrow": "FUNCIONALIDADES",
    "features.title": "Cinco instrumentos.<br />Uma única vigília.",
    "feature.sim.title": "Alertas de similaridade",
    "feature.sim.desc": "Cada novo pedido publicado é comparado com as suas marcas através de três lentes: semelhança textual, fonética afinada para português e sobreposição de classes de Nice.",
    "feature.sim.meta": "50% TEXTUAL · 30% FONÉTICA · 20% CLASSES",
    "feature.life.title": "Ciclo de vida e prazos",
    "feature.life.desc": "Renovações, períodos de oposição e períodos de graça calculados automaticamente. Cada data crítica aparece no calendário com bastante antecedência.",
    "feature.life.meta": "RENOVAÇÃO · OPOSIÇÃO · PERÍODO DE GRAÇA",
    "feature.structured.title": "Leitura estruturada de pedidos",
    "feature.structured.desc": "Os pedidos publicados são indexados em formato estruturado para apoiar a pesquisa e a comparação de marcas.",
    "feature.structured.meta": "PEDIDOS PUBLICADOS · DADOS ESTRUTURADOS",
    "feature.prospect.title": "Prospeção de clientes",
    "feature.prospect.desc": "Para profissionais de PI: identifique empresas com atividade recente de marcas que ainda não têm representação — e chegue primeiro.",
    "feature.prospect.meta": "OPORTUNIDADES · MULTI-CLIENTE",
    "feature.email.title": "Alertas por email",
    "feature.email.desc": "Cada alerta chega por email com o contexto necessário para agir de imediato.",
    "feature.email.meta": "MONITORING",
    "stats.label": "Números do markee",
    "stats.official": "registos oficiais<br />INPI · EUIPO",
    "stats.classes": "classes de Nice<br />cobertas",
    "stats.weights": "pesos do motor<br />textual · fonética · classes",
    "stats.pt": "fonética afinada<br />para português",
    "engine.eyebrow": "O MOTOR EM AÇÃO",
    "engine.title": "Veja como o markee<br />pensa uma colisão.",
    "engine.aria": "Demonstração do motor",
    "engine.sim.title": "Deteção de similaridade",
    "engine.sim.desc": "Um pedido novo é decomposto e pontuado contra a sua watchlist em três dimensões independentes.",
    "engine.deadlines.title": "Prazos sob controlo",
    "engine.deadlines.desc": "Cada marca ganha uma linha temporal viva: renovações, oposições e períodos de graça, sempre à vista.",
    "engine.alert.title": "Alerta entregue",
    "engine.alert.desc": "O resultado chega onde estiver — caixa de correio — com o que decide.",
    "engine.report": "RELATÓRIO DE SIMILARIDADE",
    "engine.your_mark": "A sua marca",
    "engine.new_application": "Pedido novo",
    "engine.textual": "Textual",
    "engine.phonetic": "Fonética",
    "engine.classes": "Classes",
    "engine.verdict": "Similaridade global — risco elevado de confusão. Recomenda-se análise de oposição.",
    "engine.timeline.label": "LINHA TEMPORAL — A sua marca",
    "engine.timeline.registered": "Registo concedido — EUIPO",
    "engine.timeline.opposition": "Prazo de oposição a pedido conflituante — faltam 101 dias",
    "engine.timeline.renewal": "Renovação decenal — lembretes automáticos a 180, 90 e 30 dias",
    "engine.sent": "NOTIFICAÇÕES ENVIADAS",
    "engine.email_one": "Detetámos um novo pedido com 87% de similaridade à sua marca «A sua marca».",
    "engine.email_meta": "EUIPO · CLASSES 9, 42 · HÁ 12 MIN",
    "engine.email_two": "Pedido novo com 87% de similaridade publicado. Prazo de oposição previsto a 2026-11-02.",
    "pricing.eyebrow": "PREÇOS",
    "pricing.title": "Escolha a intensidade<br />da sua vigilância.",
    "pricing.note": "Sem contratos de permanência. Mude de plano quando quiser.",
    "pricing.per_month": "/mês",
    "pricing.tier.free": "Free",
    "pricing.tier.individual": "Individual",
    "pricing.tier.pro": "Pro",
    "pricing.tier.professional": "Profissional",
    "pricing.tier.enterprise": "Enterprise",
    "pricing.free.1": "1 marca monitorizada",
    "pricing.free.2": "Cobertura EUIPO + INPI",
    "pricing.free.3": "Alertas de renovação",
    "pricing.email": "Notificações por email",
    "pricing.start": "Começar",
    "pricing.ind.1": "5 marcas monitorizadas",
    "pricing.ind.2": "Alertas de similaridade",
    "pricing.ind.3": "Alertas de oposição",
    "pricing.pro.1": "100 marcas monitorizadas",
    "pricing.pro.2": "Fonética afinada para PT",
    "pricing.pro.3": "Analytics básico",
    "pricing.prof.1": "500 marcas monitorizadas",
    "pricing.prof.2": "Prospeção de clientes",
    "pricing.prof.3": "Gestão multi-cliente",
    "pricing.prof.4": "Relatórios white-label",
    "pricing.ent.1": "Marcas ilimitadas",
    "pricing.ent.2": "API completa",
    "pricing.ent.3": "SSO empresarial",
    "final.eyebrow": "O PRÓXIMO PASSO",
    "final.title": "Enquanto lê isto,<br />alguém pode estar a registar<br /><em>algo demasiado parecido.</em>",
    "final.hint": "PLANO TRIAL DISPONÍVEL PARA TESTAR A FUNCIONALIDADE",
    "footer.aria": "Rodapé",
    "footer.product": "PRODUTO",
    "footer.platform": "PLATAFORMA",
    "footer.registers": "REGISTOS",
    "footer.inpi": "INPI — Portugal",
    "footer.euipo": "EUIPO — Europa",
    "footer.rights": "© 2026 MARKEE — TODOS OS DIREITOS RESERVADOS",
    "footer.made": "FEITO EM LISBOA · VIGILANTE POR NATUREZA",
    "language.aria": "Escolher idioma",
    "nav.aria": "Navegação principal",
    "nav.open_menu": "Abrir menu",
    "nav.close_menu": "Fechar menu",
    "theme.aria": "Alternar tema claro/escuro",
    "theme.label": "Tema"
  },
  "en": {
    "meta.title": "markee — EU trademark protection and search",
    "meta.description": "markee helps you check, understand, register and monitor EU trademarks with technology-supported research and professional oversight.",
    "preloader.meta": "PREPARING THE WATCH",
    "skip.content": "Skip to content",
    "nav.home_aria": "markee — home page",
    "nav.features": "Features",
    "nav.engine": "The Engine",
    "nav.pricing": "Pricing",
    "nav.login": "Log in",
    "nav.create": "Create account",
    "nav.service_status": "Service status",
    "hero.eyebrow": "EU TRADEMARK SEARCH · CLEARANCE · REGISTRATION",
    "hero.title": "Can I protect this trademark?",
    "hero.title.line1": "Can I protect",
    "hero.title.line2": "this trademark?",
    "hero.title.line3": "<em class=\"hero__title-accent\">Find out before you file.</em>",
    "hero.subtitle": "markee helps you assess whether a trademark can be protected, understand the main EU risks, and move from search to expert review and filing.",
    "hero.cta.primary": "Check your trademark",
    "hero.cta.secondary": "Register a trademark",
    "hero.meta.location": "38.7223° N, 9.1393° W — LISBON",
    "hero.meta.scroll": "SCROLL",
    "hero.meta.est": "EST. 2026 — ALWAYS WATCHING",
    "ticker.inpi": "INPI — PORTUGAL",
    "ticker.euipo": "EUIPO — EUROPEAN UNION",
    "ticker.bpi": "INDUSTRIAL PROPERTY BULLETIN",
    "ticker.nice": "45 NICE CLASSES",
    "ticker.phonetic": "PT PHONETIC ANALYSIS",
    "ticker.alerts": "TIMELY ALERTS",
    "manifesto.aria": "Manifesto",
    "manifesto.eyebrow": "OUR STARTING POINT",
    "manifesto.text": "A trademark is more than a name. It is territory. And territory is defended — with permanent attention, not luck.",
    "features.eyebrow": "FEATURES",
    "features.title": "One trademark journey.<br />Five practical steps.",
    "feature.sim.title": "Trademark check",
    "feature.sim.desc": "Start with a preliminary check of the proposed name, the intended goods or services and the relevant EU trademark territory.",
    "feature.sim.meta": "NAME · GOODS/SERVICES · EU TERRITORY",
    "feature.life.title": "Understand the risks",
    "feature.life.desc": "See whether obvious absolute-ground concerns or potentially relevant earlier marks should be reviewed before you file.",
    "feature.life.meta": "ABSOLUTE GROUNDS · EARLIER RIGHTS · LIMITATIONS",
    "feature.structured.title": "Expert review",
    "feature.structured.desc": "Use technology-supported research as the starting point, then bring in professional judgment where the result needs legal analysis.",
    "feature.structured.meta": "STRUCTURED ANALYSIS · PROFESSIONAL JUDGMENT",
    "feature.prospect.title": "Register",
    "feature.prospect.desc": "Turn a promising assessment into a trademark registration workflow without re-entering the same information twice.",
    "feature.prospect.meta": "APPLICATION · SPECIFICATION · FILING",
    "feature.email.title": "Monitor and maintain",
    "feature.email.desc": "After filing, keep watching for deadlines, new risks and decisions that need attention.",
    "feature.email.meta": "MONITORING",
    "stats.label": "markee numbers",
    "stats.official": "official registers<br />INPI · EUIPO",
    "stats.classes": "Nice classes<br />covered",
    "stats.weights": "engine weights<br />textual · phonetic · classes",
    "stats.pt": "phonetics tuned<br />for Portuguese",
    "engine.eyebrow": "THE ENGINE IN ACTION",
    "engine.title": "See how markee<br />reads a collision.",
    "engine.aria": "Engine demonstration",
    "engine.sim.title": "Similarity detection",
    "engine.sim.desc": "A new application is decomposed and scored against your watchlist across three independent dimensions.",
    "engine.deadlines.title": "Deadlines under control",
    "engine.deadlines.desc": "Every mark gets a living timeline: renewals, oppositions and grace periods, always visible.",
    "engine.alert.title": "Alert delivered",
    "engine.alert.desc": "The result reaches you where you work — inbox included — with what matters.",
    "engine.report": "SIMILARITY REPORT",
    "engine.your_mark": "Your mark",
    "engine.new_application": "New application",
    "engine.textual": "Textual",
    "engine.phonetic": "Phonetic",
    "engine.classes": "Classes",
    "engine.verdict": "Overall similarity — high risk of confusion. Opposition analysis recommended.",
    "engine.timeline.label": "TIMELINE — Your mark",
    "engine.timeline.registered": "Registration granted — EUIPO",
    "engine.timeline.opposition": "Opposition deadline for conflicting application — 101 days left",
    "engine.timeline.renewal": "Ten-year renewal — automatic reminders at 180, 90 and 30 days",
    "engine.sent": "NOTIFICATIONS SENT",
    "engine.email_one": "We detected a new application with 87% similarity to your mark “Your mark”.",
    "engine.email_meta": "EUIPO · CLASSES 9, 42 · 12 MIN AGO",
    "engine.email_two": "New application published with 87% similarity. Expected opposition deadline: 2026-11-02.",
    "pricing.eyebrow": "SERVICES",
    "pricing.title": "Choose the right level<br />of trademark support.",
    "pricing.note": "Clear service packages. Start with a preliminary check and escalate when professional review is needed.",
    "pricing.per_month": "/month",
    "pricing.tier.free": "Free",
    "pricing.tier.individual": "Individual",
    "pricing.tier.pro": "Pro",
    "pricing.tier.professional": "Professional",
    "pricing.tier.enterprise": "Enterprise",
    "pricing.free.1": "1 monitored mark",
    "pricing.free.2": "EUIPO + INPI coverage",
    "pricing.free.3": "Renewal alerts",
    "pricing.email": "Email notifications",
    "pricing.start": "Start",
    "pricing.ind.1": "5 monitored marks",
    "pricing.ind.2": "Similarity alerts",
    "pricing.ind.3": "Opposition alerts",
    "pricing.pro.1": "100 monitored marks",
    "pricing.pro.2": "PT-tuned phonetics",
    "pricing.pro.3": "Basic analytics",
    "pricing.prof.1": "500 monitored marks",
    "pricing.prof.2": "Client prospecting",
    "pricing.prof.3": "Multi-client management",
    "pricing.prof.4": "White-label reports",
    "pricing.ent.1": "Unlimited marks",
    "pricing.ent.2": "Full API",
    "pricing.ent.3": "Enterprise SSO",
    "final.eyebrow": "THE NEXT STEP",
    "final.title": "While you read this,<br />someone may be filing<br /><em>something far too similar.</em>",
    "final.hint": "TRIAL PLAN AVAILABLE TO TEST THE FEATURE",
    "footer.aria": "Footer",
    "footer.product": "PRODUCT",
    "footer.platform": "PLATFORM",
    "footer.registers": "REGISTERS",
    "footer.inpi": "INPI — Portugal",
    "footer.euipo": "EUIPO — Europe",
    "footer.rights": "© 2026 MARKEE — ALL RIGHTS RESERVED",
    "footer.made": "BUILT IN LISBON · TECHNOLOGY-DRIVEN BY DESIGN",
    "language.aria": "Choose language",
    "nav.aria": "Main navigation",
    "nav.open_menu": "Open menu",
    "nav.close_menu": "Close menu",
    "theme.aria": "Toggle light/dark theme",
    "theme.label": "Theme"
  }
};
const LANG_STORAGE_KEY = 'markee-language';
const THEME_STORAGE_KEY = 'markee-theme';
const THEME_META = {
  dark: { chrome: '#08090a', logo: '/assets/brand-v2/logos/markee-wordmark-dark.svg?v=theme-olive-20260820' },
  light: { chrome: '#fbfcf7', logo: '/assets/brand-v2/logos/markee-wordmark-light.svg?v=theme-olive-20260820' },
};
const themeListeners = [];

function getStoredLanguage() {
  try {
    return localStorage.getItem('markee-language');
  } catch (error) {
    return null;
  }
}

function setStoredLanguage(language) {
  try {
    localStorage.setItem('markee-language', language);
  } catch (error) {
    // Private browsing or locked-down storage should not break the site.
  }
}

function applyLanguage(language) {
  const lang = language === 'en' ? 'en' : 'pt';
  const dictionary = i18n[lang];
  document.documentElement.lang = lang === 'en' ? 'en' : 'pt-PT';

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    const value = dictionary[key];
    if (typeof value !== 'string') {
      return;
    }
    const attr = el.dataset.i18nAttr;
    if (attr) {
      el.setAttribute(attr, value);
    } else {
      // Hero lines are wrapped in .hero__line-inner by splitHeroLines();
      // write into the wrapper so the intro clip animation keeps working.
      const inner = el.querySelector('.hero__line-inner');
      (inner || el).innerHTML = value;
    }
  });

  document.title = dictionary['meta.title'];
  const metaDescription = document.querySelector('meta[name="description"]');
  if (metaDescription) {
    metaDescription.setAttribute('content', dictionary['meta.description']);
  }

  document.querySelectorAll('[data-lang-option]').forEach((button) => {
    const active = button.dataset.langOption === lang;
    button.setAttribute('aria-pressed', String(active));
    button.classList.toggle('is-active', active);
  });
}

/**
 * Re-applies text splitting after a language switch replaced translated
 * innerHTML, then rebuilds the animations that target the split spans.
 */
function refreshSplitText() {
  const manifesto = document.querySelector('[data-split-words]');
  if (manifesto && manifesto.dataset.i18n && hasGsap && !reducedMotion) {
    splitWords(manifesto);
    buildManifestoScrub();
  }
}

function initLanguageSwitch() {
  const initial = getStoredLanguage() || document.documentElement.dataset.defaultLang || 'en';
  applyLanguage(initial);
  document.querySelectorAll('[data-lang-option]').forEach((button) => {
    button.addEventListener('click', () => {
      const language = button.dataset.langOption === 'en' ? 'en' : 'pt';
      setStoredLanguage(language);
      applyLanguage(language);
      refreshSplitText();
      if (hasGsap) {
        ScrollTrigger.refresh();
      }
    });
  });
}

function getStoredTheme() {
  try {
    return localStorage.getItem('markee-theme');
  } catch (error) {
    return null;
  }
}

function setStoredTheme(theme) {
  try {
    localStorage.setItem('markee-theme', theme);
  } catch (error) {
    // Locked-down storage should not break the switch.
  }
}

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function onThemeChange(callback) {
  themeListeners.push(callback);
}

function applyTheme(theme) {
  const next = theme === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  const meta = THEME_META[next];
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) {
    themeColor.setAttribute('content', meta.chrome);
  }
  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    const active = next === 'light';
    button.setAttribute('aria-checked', String(active));
  });
  document.querySelectorAll('.site-nav__logo, .dashboard-wordmark').forEach((logo) => {
    logo.setAttribute('src', meta.logo);
  });
  themeListeners.forEach((callback) => callback(next));
}

function initThemeSwitch() {
  const systemQuery = window.matchMedia('(prefers-color-scheme: light)');
  const stored = getStoredTheme();
  applyTheme(stored === 'light' || stored === 'dark' ? stored : getSystemTheme());

  systemQuery.addEventListener('change', () => {
    if (!getStoredTheme()) {
      applyTheme(getSystemTheme());
    }
  });

  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      setStoredTheme(next);
      applyTheme(next);
      if (hasGsap) {
        ScrollTrigger.refresh();
      }
    });
  });
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
      toggle.setAttribute('aria-label', open ? i18n[document.documentElement.lang === 'en' ? 'en' : 'pt']['nav.close_menu'] : i18n[document.documentElement.lang === 'en' ? 'en' : 'pt']['nav.open_menu']);
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

// Manifesto scrub tween, rebuilt whenever the words are re-split (e.g. after
// a language switch replaced the translated text and its .w spans).
let manifestoScrub = null;

function buildManifestoScrub() {
  if (!hasGsap || reducedMotion) {
    return;
  }
  const manifesto = document.querySelector('.manifesto__text');
  if (!manifesto) {
    return;
  }
  if (manifestoScrub) {
    if (manifestoScrub.scrollTrigger) {
      manifestoScrub.scrollTrigger.kill();
    }
    manifestoScrub.kill();
    manifestoScrub = null;
  }
  const words = manifesto.querySelectorAll('.w');
  if (!words.length) {
    return;
  }
  manifestoScrub = gsap.to(words, {
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
  buildManifestoScrub();

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
      uColor: { value: new THREE.Color(0xa7c957) },
    },
    transparent: true,
    depthWrite: false,
    blending: document.documentElement.getAttribute('data-theme') === 'light'
      ? THREE.NormalBlending
      : THREE.AdditiveBlending,
  });

  onThemeChange((theme) => {
    material.uniforms.uColor.value.set(theme === 'light' ? 0x5f7f2a : 0xa7c957);
    material.blending = theme === 'light' ? THREE.NormalBlending : THREE.AdditiveBlending;
    material.needsUpdate = true;
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
  initLanguageSwitch();
  initThemeSwitch();
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
