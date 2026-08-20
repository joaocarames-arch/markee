/* ==========================================================================
   markee dashboard — app.js
   Vanilla SPA: hash routing, JWT auth, fetch helper, and all views.
   All comments in English; all user-facing text in European Portuguese.
   ========================================================================== */
'use strict';

/* --------------------------------------------------------------------------
   Constants
   -------------------------------------------------------------------------- */
const API_BASE = '/api/v1';
const TOKEN_KEY = 'markee_token';

const ROUTES = ['/dashboard', '/assessment', '/search', '/watchlists', '/alerts', '/deadlines', '/settings', '/login'];

// Nav items (path, PT label, inline SVG path markup)
const NAV_ITEMS = [
  { path: '/dashboard', label: 'Painel', icon: 'grid' },
  { path: '/assessment', label: 'Verificação', icon: 'shield' },
  { path: '/search', label: 'Pesquisa', icon: 'search' },
  { path: '/watchlists', label: 'Vigilâncias', icon: 'eye' },
  { path: '/alerts', label: 'Alertas', icon: 'bell' },
  { path: '/deadlines', label: 'Prazos', icon: 'clock' },
  { path: '/settings', label: 'Definições', icon: 'cog' },
];

// Page titles per route
const PAGE_TITLES = {
  '/dashboard': 'Painel',
  '/assessment': 'Verificação de marca',
  '/search': 'Pesquisa de marcas',
  '/watchlists': 'Vigilâncias',
  '/alerts': 'Alertas',
  '/deadlines': 'Prazos',
  '/settings': 'Definições',
};

// Plan display metadata (PT labels + monthly price in EUR)
const PLAN_META = {
  free: { label: 'Free', price: 0 },
  individual: { label: 'Individual', price: 5 },
  pro: { label: 'Pro', price: 29 },
  profissional: { label: 'Profissional', price: 99 },
  enterprise: { label: 'Enterprise', price: 249 },
};
const PLAN_ORDER = ['free', 'individual', 'pro', 'profissional', 'enterprise'];

/* --------------------------------------------------------------------------
   SVG icon set (returns markup strings)
   -------------------------------------------------------------------------- */
const ICONS = {
  grid: '<path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  cog: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  menu: '<path d="M3 12h18M3 6h18M3 18h18"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash: '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
  close: '<path d="M18 6L6 18M6 6l12 12"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  refresh: '<path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
  printer: '<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
};

function icon(name, size) {
  const s = size || 20;
  const body = ICONS[name] || '';
  return `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

/* --------------------------------------------------------------------------
   Utilities
   -------------------------------------------------------------------------- */

/** Escape a string for safe insertion into HTML. */
function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Read the JWT from localStorage (or null). */
function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (_) {
    return null;
  }
}

function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (_) {
    /* storage unavailable */
  }
}

function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (_) {
    /* noop */
  }
}

/** Format an ISO date/datetime string into PT-PT "DD mmm YYYY". */
const ptDateFmt = new Intl.DateTimeFormat('pt-PT', { day: '2-digit', month: 'short', year: 'numeric' });
function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return ptDateFmt.format(d);
}

/** Whole-day difference between due date and today (positive = future). */
function daysUntil(dateStr) {
  if (!dateStr) return null;
  const due = new Date(dateStr);
  if (Number.isNaN(due.getTime())) return null;
  const today = new Date();
  const a = Date.UTC(due.getFullYear(), due.getMonth(), due.getDate());
  const b = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((a - b) / 86400000);
}

/** Build a countdown descriptor { text, level } from a due date. */
function countdown(dateStr) {
  const d = daysUntil(dateStr);
  if (d === null) return { text: '—', level: 'ok' };
  if (d < 0) {
    const n = Math.abs(d);
    return { text: n === 1 ? 'Há 1 dia · Vencido' : `Há ${n} dias · Vencido`, level: 'danger' };
  }
  if (d === 0) return { text: 'Hoje', level: 'danger' };
  if (d === 1) return { text: 'Amanhã', level: 'warning' };
  const level = d <= 30 ? 'warning' : 'ok';
  return { text: `Em ${d} dias`, level };
}

/** PT label for a trademark status value + badge color class. */
function statusLabel(status) {
  if (!status) return { text: 'Desconhecido', cls: 'badge-neutral' };
  const key = String(status).toLowerCase();
  const map = {
    registered: { text: 'Registada', cls: 'badge-success' },
    registada: { text: 'Registada', cls: 'badge-success' },
    pending: { text: 'Pendente', cls: 'badge-warning' },
    filed: { text: 'Submetida', cls: 'badge-warning' },
    published: { text: 'Publicada', cls: 'badge-accent' },
    opposition: { text: 'Oposição', cls: 'badge-warning' },
    expired: { text: 'Expirada', cls: 'badge-danger' },
    refused: { text: 'Recusada', cls: 'badge-danger' },
    withdrawn: { text: 'Retirada', cls: 'badge-neutral' },
    rejected: { text: 'Rejeitada', cls: 'badge-danger' },
  };
  return map[key] || { text: status, cls: 'badge-neutral' };
}

/** PT label + badge color for an alert type. */
function alertTypeLabel(type) {
  if (!type) return { text: 'Alerta', cls: 'badge-neutral' };
  const key = String(type).toLowerCase();
  const map = {
    similarity: { text: 'Semelhança', cls: 'badge-accent' },
    opposition: { text: 'Oposição', cls: 'badge-warning' },
    renewal: { text: 'Renovação', cls: 'badge-warning' },
    expiry: { text: 'Expiração', cls: 'badge-danger' },
    deadline: { text: 'Prazo', cls: 'badge-warning' },
    new_filing: { text: 'Novo pedido', cls: 'badge-accent' },
    system: { text: 'Sistema', cls: 'badge-neutral' },
  };
  return map[key] || { text: type, cls: 'badge-neutral' };
}

/** PT label for a deadline type. */
function deadlineTypeLabel(type) {
  if (!type) return 'Prazo';
  const key = String(type).toLowerCase();
  const map = {
    renewal: 'Renovação',
    opposition: 'Oposição',
    grace_period: 'Período de tolerância',
    grace: 'Período de tolerância',
    response: 'Resposta',
    payment: 'Pagamento',
    declaration_of_use: 'Declaração de uso',
  };
  return map[key] || type;
}

/** Extract a readable applicant name from varied shapes (string | {name}). */
function applicantName(a) {
  if (!a) return '';
  if (typeof a === 'string') return a;
  if (typeof a === 'object') return a.name || a.applicant_name || a.full_name || '';
  return String(a);
}

/* --------------------------------------------------------------------------
   Toasts
   -------------------------------------------------------------------------- */
function toast(message, type) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type || 'info'}`;
  el.setAttribute('role', 'status');
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.25s ease';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 260);
  }, 3600);
}

/* --------------------------------------------------------------------------
   API helper
   -------------------------------------------------------------------------- */

/**
 * Perform an API request.
 * @param {string} method - HTTP verb.
 * @param {string} path - Path relative to API_BASE (e.g. "/alerts").
 * @param {{body?: object, form?: object, auth?: boolean}} [opts]
 * @returns {Promise<any>} Parsed JSON, or null for empty/204 responses.
 */
async function request(method, path, opts) {
  const options = opts || {};
  const headers = {};
  let body;

  if (options.auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = new URLSearchParams(options.form).toString();
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(options.body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { method, headers, body });
  } catch (_) {
    throw new Error('Não foi possível contactar o servidor. Verifique a ligação.');
  }

  // Handle auth expiry globally.
  if (response.status === 401) {
    clearToken();
    if (currentPath() !== '/login') navigate('/login');
    throw new Error('Sessão expirada. Inicie sessão novamente.');
  }

  if (response.status === 204 || response.status === 205) return null;

  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (_) {
      payload = text;
    }
  }

  if (!response.ok) {
    let detail = 'Ocorreu um erro inesperado.';
    if (payload && typeof payload === 'object') {
      if (typeof payload.detail === 'string') detail = payload.detail;
      else if (Array.isArray(payload.detail) && payload.detail.length) {
        detail = payload.detail.map((d) => d.msg || d.detail || '').filter(Boolean).join(' ') || detail;
      } else if (payload.message) detail = payload.message;
    } else if (typeof payload === 'string' && payload) {
      detail = payload;
    }
    throw new Error(detail);
  }

  return payload;
}

/* --------------------------------------------------------------------------
   Router + application state
   -------------------------------------------------------------------------- */
const state = {
  user: null,
  sidebarOpen: false,
  authMode: 'login', // 'login' | 'register'
  expandedWatchlist: null,
};

function currentPath() {
  const raw = window.location.hash.replace(/^#/, '') || '/dashboard';
  const path = raw.split('?')[0];
  return ROUTES.includes(path) ? path : '/dashboard';
}

function navigate(path) {
  window.location.hash = path;
}

/* --------------------------------------------------------------------------
   Render helpers: loading / error / empty
   -------------------------------------------------------------------------- */
function renderLoading(message) {
  return `
    <div class="state-block" role="status" aria-live="polite">
      <div class="spinner"></div>
      <p>${esc(message || 'A carregar…')}</p>
    </div>`;
}

function renderError(message, retryId) {
  const retry = retryId
    ? `<button class="btn btn-primary" id="${esc(retryId)}">${icon('refresh', 16)} Tentar novamente</button>`
    : '';
  return `
    <div class="state-block error" role="alert">
      <div class="state-icon">${icon('close', 40)}</div>
      <h3>Algo correu mal</h3>
      <p>${esc(message || 'Não foi possível carregar os dados.')}</p>
      ${retry}
    </div>`;
}

function renderEmpty(title, message, iconName) {
  return `
    <div class="state-block">
      <div class="state-icon">${icon(iconName || 'inbox', 44)}</div>
      <h3>${esc(title)}</h3>
      ${message ? `<p>${esc(message)}</p>` : ''}
    </div>`;
}

/* --------------------------------------------------------------------------
   Shell (sidebar + topbar) rendering
   -------------------------------------------------------------------------- */
function renderShell(path) {
  const root = document.getElementById('root');
  const email = state.user ? state.user.email : '';
  const initial = email ? email.charAt(0).toUpperCase() : 'M';
  const title = PAGE_TITLES[path] || 'markee';

  const navHtml = NAV_ITEMS.map((item) => {
    const active = item.path === path ? ' active' : '';
    return `
      <a class="nav-item${active}" href="#${item.path}" ${item.path === path ? 'aria-current="page"' : ''}>
        ${icon(item.icon)}<span>${esc(item.label)}</span>
      </a>`;
  }).join('');

  root.innerHTML = `
    <div class="shell">
      <aside class="sidebar${state.sidebarOpen ? ' open' : ''}" id="sidebar" aria-label="Navegação principal">
        <div class="sidebar-brand">
          <img class="dashboard-wordmark" src="/assets/brand-v2/logos/markee-wordmark-dark.svg?v=brand-v2-matrix-20260820" alt="markee" />
        </div>
        <nav class="sidebar-nav" aria-label="Menu">
          ${navHtml}
        </nav>
        <div class="sidebar-footer">
          <div class="sidebar-user">
            <div class="user-avatar" aria-hidden="true">${esc(initial)}</div>
            <div class="user-meta">
              <div class="user-email" title="${esc(email)}">${esc(email)}</div>
              <div class="user-role">Sessão iniciada</div>
            </div>
          </div>
          <button class="btn btn-ghost btn-block" id="logout-btn">
            ${icon('logout', 16)} Terminar sessão
          </button>
        </div>
      </aside>

      <div class="overlay${state.sidebarOpen ? ' open' : ''}" id="overlay"></div>

      <div class="content">
        <header class="topbar">
          <button class="icon-btn hamburger" id="hamburger" aria-label="Abrir menu" aria-expanded="${state.sidebarOpen}">
            ${icon('menu')}
          </button>
          <h1 class="topbar-title">${esc(title)}</h1>
          <div class="topbar-actions" id="topbar-actions"></div>
        </header>
        <main class="view" id="view" tabindex="-1"></main>
      </div>
    </div>`;

  // Wire shell interactions.
  const logout = document.getElementById('logout-btn');
  if (logout) logout.addEventListener('click', doLogout);

  const hamburger = document.getElementById('hamburger');
  if (hamburger) hamburger.addEventListener('click', () => toggleSidebar());

  const overlay = document.getElementById('overlay');
  if (overlay) overlay.addEventListener('click', () => toggleSidebar(false));

  // Close off-canvas sidebar when a nav link is tapped (mobile).
  root.querySelectorAll('.nav-item').forEach((link) =>
    link.addEventListener('click', () => {
      if (window.matchMedia('(max-width: 900px)').matches) toggleSidebar(false);
    })
  );
}

function toggleSidebar(force) {
  state.sidebarOpen = typeof force === 'boolean' ? force : !state.sidebarOpen;
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  const hamburger = document.getElementById('hamburger');
  if (sidebar) sidebar.classList.toggle('open', state.sidebarOpen);
  if (overlay) overlay.classList.toggle('open', state.sidebarOpen);
  if (hamburger) hamburger.setAttribute('aria-expanded', String(state.sidebarOpen));
}

/** Set topbar action buttons for the current view. */
function setTopbarActions(html) {
  const el = document.getElementById('topbar-actions');
  if (el) el.innerHTML = html || '';
}

function getView() {
  return document.getElementById('view');
}

async function doLogout() {
  clearToken();
  state.user = null;
  navigate('/login');
}

/* --------------------------------------------------------------------------
   View: Login / Register
   -------------------------------------------------------------------------- */
function renderAuth() {
  const root = document.getElementById('root');
  const isRegister = state.authMode === 'register';

  root.innerHTML = `
    <div class="auth-wrap">
      <div class="glass-card auth-card">
        <div class="auth-brand"><img class="dashboard-wordmark" src="/assets/brand-v2/logos/markee-wordmark-dark.svg?v=brand-v2-matrix-20260820" alt="markee" /></div>
        <p class="auth-sub">Monitorização profissional de marcas</p>

        <div class="auth-toggle" role="tablist" aria-label="Modo de autenticação">
          <button role="tab" aria-selected="${!isRegister}" class="${!isRegister ? 'active' : ''}" data-mode="login">Entrar</button>
          <button role="tab" aria-selected="${isRegister}" class="${isRegister ? 'active' : ''}" data-mode="register">Criar conta</button>
        </div>

        <div id="auth-error" aria-live="assertive"></div>

        <form id="auth-form" novalidate>
          ${isRegister ? `
          <div class="field">
            <label for="af-name">Nome completo</label>
            <input class="input" id="af-name" name="full_name" type="text" autocomplete="name" required />
          </div>
          <div class="field">
            <label for="af-company">Empresa</label>
            <input class="input" id="af-company" name="company_name" type="text" autocomplete="organization" />
          </div>` : ''}
          <div class="field">
            <label for="af-email">Email</label>
            <input class="input" id="af-email" name="email" type="email" autocomplete="email" required />
          </div>
          <div class="field">
            <label for="af-password">Palavra-passe</label>
            <input class="input" id="af-password" name="password" type="password" autocomplete="${isRegister ? 'new-password' : 'current-password'}" required minlength="6" />
          </div>
          <button class="btn btn-primary btn-block" type="submit" id="auth-submit">
            ${isRegister ? 'Criar conta' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>`;

  // Mode toggle.
  root.querySelectorAll('.auth-toggle button').forEach((btn) =>
    btn.addEventListener('click', () => {
      state.authMode = btn.getAttribute('data-mode');
      renderAuth();
    })
  );

  const form = document.getElementById('auth-form');
  form.addEventListener('submit', onAuthSubmit);

  const first = document.getElementById(isRegister ? 'af-name' : 'af-email');
  if (first) first.focus();
}

function showAuthError(message) {
  const box = document.getElementById('auth-error');
  if (!box) return;
  box.innerHTML = message
    ? `<div class="form-error">${icon('close', 16)}<span>${esc(message)}</span></div>`
    : '';
}

async function onAuthSubmit(event) {
  event.preventDefault();
  showAuthError('');
  const isRegister = state.authMode === 'register';
  const form = event.currentTarget;
  const submit = document.getElementById('auth-submit');

  const email = form.email.value.trim();
  const password = form.password.value;

  if (!email || !password) {
    showAuthError('Preencha o email e a palavra-passe.');
    return;
  }
  if (isRegister && !form.full_name.value.trim()) {
    showAuthError('Indique o seu nome completo.');
    return;
  }

  submit.disabled = true;
  submit.textContent = isRegister ? 'A criar conta…' : 'A entrar…';

  try {
    if (isRegister) {
      await request('POST', '/auth/register', {
        body: {
          email,
          password,
          full_name: form.full_name.value.trim(),
          company_name: form.company_name.value.trim() || null,
        },
      });
    }
    // Log in (either directly, or right after registering).
    const tokenResp = await request('POST', '/auth/login', {
      form: { username: email, password },
    });
    if (!tokenResp || !tokenResp.access_token) {
      throw new Error('Resposta de autenticação inválida.');
    }
    setToken(tokenResp.access_token);
    state.user = await request('GET', '/auth/me', { auth: true });
    toast(isRegister ? 'Conta criada com sucesso.' : 'Sessão iniciada.', 'success');
    navigate('/dashboard');
  } catch (err) {
    showAuthError(err.message || 'Falha na autenticação.');
    submit.disabled = false;
    submit.textContent = isRegister ? 'Criar conta' : 'Entrar';
  }
}

/* --------------------------------------------------------------------------
   View: Dashboard
   -------------------------------------------------------------------------- */
async function renderDashboard() {
  const view = getView();
  setTopbarActions('');
  view.innerHTML = renderLoading('A carregar o painel…');

  try {
    // Marks watched = sum of items across all watchlists.
    const watchlists = await request('GET', '/watchlists', { auth: true });
    const itemCounts = await Promise.all(
      watchlists.map((w) =>
        request('GET', `/watchlists/${w.id}/items`, { auth: true })
          .then((items) => (Array.isArray(items) ? items.length : 0))
          .catch(() => 0)
      )
    );
    const marksWatched = itemCounts.reduce((a, b) => a + b, 0);

    const [unread, deadlines, recentAlerts] = await Promise.all([
      request('GET', '/alerts?unread_only=true', { auth: true }),
      request('GET', '/deadlines?upcoming_only=true', { auth: true }),
      request('GET', '/alerts?unread_only=false', { auth: true }),
    ]);

    const unreadCount = Array.isArray(unread) ? unread.length : 0;
    const upcomingCount = Array.isArray(deadlines) ? deadlines.length : 0;
    const alertsList = Array.isArray(recentAlerts) ? recentAlerts.slice(0, 5) : [];
    const deadlineList = Array.isArray(deadlines) ? deadlines.slice(0, 5) : [];

    view.innerHTML = `
      <div class="stat-grid">
        ${statCard('Marcas vigiadas', marksWatched, 'eye', `${watchlists.length} vigilância(s)`)}
        ${statCard('Alertas por ler', unreadCount, 'bell', unreadCount ? 'Requerem atenção' : 'Tudo em dia')}
        ${statCard('Prazos a aproximar-se', upcomingCount, 'clock', upcomingCount ? 'Ver prazos' : 'Sem prazos próximos')}
      </div>

      <div class="dash-columns">
        <section class="page-section">
          <h2 class="section-title">Alertas recentes</h2>
          <div class="glass-card">
            ${alertsList.length ? alertsList.map(dashboardAlertRow).join('') : renderEmpty('Sem alertas', 'Ainda não existem alertas.', 'bell')}
          </div>
        </section>
        <section class="page-section">
          <h2 class="section-title">Próximos prazos</h2>
          <div class="glass-card">
            ${deadlineList.length ? deadlineList.map(dashboardDeadlineRow).join('') : renderEmpty('Sem prazos', 'Nenhum prazo a aproximar-se.', 'clock')}
          </div>
        </section>
      </div>`;
  } catch (err) {
    view.innerHTML = renderError(err.message, 'retry-dashboard');
    bindRetry('retry-dashboard', renderDashboard);
  }
}

function statCard(label, value, iconName, sub) {
  return `
    <div class="glass-card stat-card">
      <div class="stat-head">
        <span>${esc(label)}</span>
        <span class="stat-icon">${icon(iconName, 18)}</span>
      </div>
      <div class="stat-value">${esc(value)}</div>
      <div class="stat-sub">${esc(sub)}</div>
    </div>`;
}

function dashboardAlertRow(a) {
  const t = alertTypeLabel(a.alert_type);
  const dot = a.is_read ? '' : '<span class="badge badge-accent">Novo</span>';
  return `
    <div class="compact-row">
      <div class="compact-main">
        <div class="compact-title">${esc(a.title)}</div>
        <div class="compact-sub">${formatDate(a.created_at)}</div>
      </div>
      <div class="flex gap-sm">${dot}<span class="badge ${t.cls}">${esc(t.text)}</span></div>
    </div>`;
}

function dashboardDeadlineRow(d) {
  const cd = countdown(d.due_date);
  return `
    <div class="compact-row">
      <div class="compact-main">
        <div class="compact-title">${esc(deadlineTypeLabel(d.deadline_type))}</div>
        <div class="compact-sub mono">${esc(d.due_date || '')}</div>
      </div>
      <span class="countdown ${cd.level}">${esc(cd.text)}</span>
    </div>`;
}

/* --------------------------------------------------------------------------
   View: Search
   -------------------------------------------------------------------------- */
function renderSearch() {
  const view = getView();
  setTopbarActions('');
  view.innerHTML = `
    <form class="search-bar" id="search-form" role="search">
      <input class="input" id="search-q" type="search" placeholder="Pesquise por uma marca…"
             aria-label="Texto da marca" />
      <select class="select" id="search-jur" aria-label="Jurisdição">
        <option value="">Todas as jurisdições</option>
        <option value="EUIPO">EUIPO</option>
        <option value="INPI">INPI</option>
      </select>
      <button class="btn btn-primary" type="submit">${icon('search', 16)} Pesquisar</button>
    </form>
    <div id="search-results">
      ${renderEmpty('Pesquise por uma marca…', 'Introduza um termo para procurar marcas em bases europeias e nacionais.', 'search')}
    </div>`;

  const form = document.getElementById('search-form');
  form.addEventListener('submit', doSearch);
  const q = document.getElementById('search-q');
  if (q) q.focus();
}

async function doSearch(event) {
  event.preventDefault();
  const q = document.getElementById('search-q').value.trim();
  const jur = document.getElementById('search-jur').value;
  const container = document.getElementById('search-results');

  if (!q) {
    container.innerHTML = renderEmpty('Introduza um termo', 'Escreva o nome de uma marca para pesquisar.', 'search');
    return;
  }

  container.innerHTML = renderLoading('A pesquisar marcas…');

  const params = new URLSearchParams({ q, limit: '50', offset: '0' });
  if (jur) params.set('jurisdiction', jur);

  try {
    const results = await request('GET', `/trademarks?${params.toString()}`, { auth: true });
    if (!Array.isArray(results) || results.length === 0) {
      container.innerHTML = renderEmpty('Sem resultados', `Não foram encontradas marcas para “${q}”.`, 'search');
      return;
    }
    container.innerHTML = `<div class="result-grid">${results.map(searchResultCard).join('')}</div>`;
  } catch (err) {
    container.innerHTML = renderError(err.message, 'retry-search');
    const btn = document.getElementById('retry-search');
    if (btn) btn.addEventListener('click', () => doSearch(event));
  }
}

function searchResultCard(tm) {
  const st = statusLabel(tm.status);
  const classes = Array.isArray(tm.nice_classes) ? tm.nice_classes : [];
  const applicants = Array.isArray(tm.applicants) ? tm.applicants.map(applicantName).filter(Boolean) : [];
  const appNum = tm.application_number || tm.registration_number || tm.source_id || '';

  return `
    <div class="glass-card list-card">
      <div class="list-card-head">
        <div>
          <div class="list-card-title">${esc(tm.word_mark || 'Marca figurativa')}</div>
          ${appNum ? `<div class="compact-sub mono">${esc(appNum)}</div>` : ''}
        </div>
        <span class="badge ${st.cls}">${esc(st.text)}</span>
      </div>
      <div class="list-card-meta">
        ${tm.jurisdiction ? `<span class="badge badge-neutral">${esc(tm.jurisdiction)}</span>` : ''}
        ${tm.application_date ? `<span>Pedido: <span class="mono">${esc(formatDate(tm.application_date))}</span></span>` : ''}
      </div>
      ${classes.length ? `<div class="chip-row">${classes.map((c) => `<span class="chip">Cl. ${esc(c)}</span>`).join('')}</div>` : ''}
      ${applicants.length ? `<div class="list-card-body">${esc(applicants.join(', '))}</div>` : ''}
    </div>`;
}

/* --------------------------------------------------------------------------
   View: Watchlists
   -------------------------------------------------------------------------- */
async function renderWatchlists() {
  const view = getView();
  setTopbarActions(`<button class="btn btn-primary" id="new-watchlist">${icon('plus', 16)} Nova vigilância</button>`);
  const newBtn = document.getElementById('new-watchlist');
  if (newBtn) newBtn.addEventListener('click', openWatchlistModal);

  view.innerHTML = renderLoading('A carregar vigilâncias…');

  try {
    const watchlists = await request('GET', '/watchlists', { auth: true });
    if (!Array.isArray(watchlists) || watchlists.length === 0) {
      view.innerHTML = renderEmpty('Sem vigilâncias', 'Crie a primeira vigilância para monitorizar marcas semelhantes.', 'eye');
      return;
    }

    // Fetch item counts in parallel for display.
    const counts = await Promise.all(
      watchlists.map((w) =>
        request('GET', `/watchlists/${w.id}/items`, { auth: true })
          .then((items) => (Array.isArray(items) ? items.length : 0))
          .catch(() => 0)
      )
    );

    view.innerHTML = `<div class="card-list" id="watchlist-list">
      ${watchlists.map((w, i) => watchlistCard(w, counts[i])).join('')}
    </div>`;

    bindWatchlistCards(watchlists);

    // Re-open a previously expanded watchlist after a refetch.
    if (state.expandedWatchlist && watchlists.some((w) => w.id === state.expandedWatchlist)) {
      loadWatchlistItems(state.expandedWatchlist);
    }
  } catch (err) {
    view.innerHTML = renderError(err.message, 'retry-watchlists');
    bindRetry('retry-watchlists', renderWatchlists);
  }
}

function watchlistCard(w, count) {
  const jurisdictions = Array.isArray(w.jurisdictions) ? w.jurisdictions : [];
  return `
    <div class="glass-card list-card" data-watchlist="${esc(w.id)}">
      <div class="list-card-head">
        <div>
          <button class="btn-ghost list-card-title" data-toggle-items="${esc(w.id)}"
                  style="padding:0;background:none;border:none;color:inherit;font:inherit;cursor:pointer;text-align:left;">
            ${esc(w.name)}
          </button>
          <div class="list-card-meta">
            <span class="badge badge-accent">Limiar ${esc(w.similarity_threshold)}%</span>
            <span class="badge badge-neutral">${esc(count)} marca(s)</span>
            ${jurisdictions.map((j) => `<span class="badge badge-neutral">${esc(j)}</span>`).join('')}
          </div>
        </div>
        <div class="flex gap-sm" style="align-items:center;">
          <label class="toggle-switch" title="Ativa/Inativa">
            <input type="checkbox" data-toggle-active="${esc(w.id)}" ${w.is_active ? 'checked' : ''}
                   aria-label="Ativar vigilância ${esc(w.name)}" />
            <span class="toggle-slider"></span>
          </label>
          <button class="icon-btn" data-delete-watchlist="${esc(w.id)}" aria-label="Eliminar vigilância ${esc(w.name)}">
            ${icon('trash', 18)}
          </button>
        </div>
      </div>
      <div class="watchlist-items" id="items-${esc(w.id)}" hidden></div>
    </div>`;
}

function bindWatchlistCards(watchlists) {
  const view = getView();

  view.querySelectorAll('[data-toggle-items]').forEach((btn) =>
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-toggle-items');
      const container = document.getElementById(`items-${id}`);
      if (!container) return;
      if (container.hidden) {
        state.expandedWatchlist = id;
        loadWatchlistItems(id);
      } else {
        container.hidden = true;
        state.expandedWatchlist = null;
      }
    })
  );

  view.querySelectorAll('[data-toggle-active]').forEach((input) =>
    input.addEventListener('change', async () => {
      const id = input.getAttribute('data-toggle-active');
      try {
        await request('PUT', `/watchlists/${id}`, { auth: true, body: { is_active: input.checked } });
        toast(input.checked ? 'Vigilância ativada.' : 'Vigilância desativada.', 'success');
      } catch (err) {
        input.checked = !input.checked;
        toast(err.message, 'error');
      }
    })
  );

  view.querySelectorAll('[data-delete-watchlist]').forEach((btn) =>
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-delete-watchlist');
      const wl = watchlists.find((w) => String(w.id) === String(id));
      const name = wl ? wl.name : 'esta vigilância';
      if (!window.confirm(`Eliminar “${name}”? Esta ação é irreversível.`)) return;
      try {
        await request('DELETE', `/watchlists/${id}`, { auth: true });
        if (String(state.expandedWatchlist) === String(id)) state.expandedWatchlist = null;
        toast('Vigilância eliminada.', 'success');
        renderWatchlists();
      } catch (err) {
        toast(err.message, 'error');
      }
    })
  );
}

async function loadWatchlistItems(id) {
  const container = document.getElementById(`items-${id}`);
  if (!container) return;
  container.hidden = false;
  container.innerHTML = renderLoading('A carregar marcas…');

  try {
    const items = await request('GET', `/watchlists/${id}/items`, { auth: true });
    const list = Array.isArray(items) ? items : [];
    container.innerHTML = `
      ${list.length
        ? list.map((it) => watchlistItemRow(id, it)).join('')
        : `<p class="text-secondary text-sm">Ainda não há marcas nesta vigilância.</p>`}
      <form class="inline-form" data-add-item="${esc(id)}">
        <div class="field">
          <label for="mk-${esc(id)}">Marca</label>
          <input class="input" id="mk-${esc(id)}" name="mark_text" type="text" placeholder="Texto da marca" required />
        </div>
        <div class="field">
          <label for="cl-${esc(id)}">Classes (opcional)</label>
          <input class="input" id="cl-${esc(id)}" name="nice_classes" type="text" placeholder="ex: 9, 35, 42" />
        </div>
        <div class="field">
          <label for="nt-${esc(id)}">Notas (opcional)</label>
          <input class="input" id="nt-${esc(id)}" name="notes" type="text" placeholder="Notas" />
        </div>
        <button class="btn btn-primary" type="submit">${icon('plus', 16)} Adicionar marca</button>
      </form>`;

    // Remove-item bindings.
    container.querySelectorAll('[data-remove-item]').forEach((btn) =>
      btn.addEventListener('click', async () => {
        const itemId = btn.getAttribute('data-remove-item');
        try {
          await request('DELETE', `/watchlists/${id}/items/${itemId}`, { auth: true });
          toast('Marca removida.', 'success');
          loadWatchlistItems(id);
        } catch (err) {
          toast(err.message, 'error');
        }
      })
    );

    // Add-item form.
    const form = container.querySelector('[data-add-item]');
    if (form) form.addEventListener('submit', (e) => onAddItem(e, id));
  } catch (err) {
    container.innerHTML = renderError(err.message);
  }
}

function watchlistItemRow(watchlistId, item) {
  const classes = Array.isArray(item.nice_classes) ? item.nice_classes : [];
  return `
    <div class="item-row">
      <div class="item-main">
        <div class="item-mark">${esc(item.mark_text)}</div>
        ${classes.length ? `<div class="chip-row" style="margin-top:4px;">${classes.map((c) => `<span class="chip">Cl. ${esc(c)}</span>`).join('')}</div>` : ''}
        ${item.notes ? `<div class="item-notes">${esc(item.notes)}</div>` : ''}
      </div>
      <button class="icon-btn" data-remove-item="${esc(item.id)}" aria-label="Remover marca ${esc(item.mark_text)}">
        ${icon('close', 18)}
      </button>
    </div>`;
}

async function onAddItem(event, watchlistId) {
  event.preventDefault();
  const form = event.currentTarget;
  const markText = form.mark_text.value.trim();
  if (!markText) {
    toast('Indique o texto da marca.', 'error');
    return;
  }
  const classesRaw = form.nice_classes.value.trim();
  const niceClasses = classesRaw
    ? classesRaw.split(',').map((s) => parseInt(s.trim(), 10)).filter((n) => Number.isFinite(n))
    : null;
  const notes = form.notes.value.trim() || null;

  const submit = form.querySelector('button[type="submit"]');
  if (submit) submit.disabled = true;

  try {
    await request('POST', `/watchlists/${watchlistId}/items`, {
      auth: true,
      body: { mark_text: markText, nice_classes: niceClasses, notes },
    });
    toast('Marca adicionada.', 'success');
    loadWatchlistItems(watchlistId);
  } catch (err) {
    toast(err.message, 'error');
    if (submit) submit.disabled = false;
  }
}

/* --------------------------------------------------------------------------
   Modal: create watchlist
   -------------------------------------------------------------------------- */
function openWatchlistModal() {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `
    <div class="glass-card modal" role="dialog" aria-modal="true" aria-labelledby="wl-modal-title">
      <div class="modal-head">
        <h2 id="wl-modal-title">Nova vigilância</h2>
        <button class="icon-btn" id="wl-modal-close" aria-label="Fechar">${icon('close')}</button>
      </div>
      <form id="wl-form">
        <div class="field">
          <label for="wl-name">Nome</label>
          <input class="input" id="wl-name" name="name" type="text" placeholder="ex: Marcas de moda" required />
        </div>
        <div class="field">
          <label for="wl-threshold">Limiar de semelhança</label>
          <div class="range-row">
            <input type="range" id="wl-threshold" name="threshold" min="0" max="100" value="80" />
            <span class="range-value mono" id="wl-threshold-val">80%</span>
          </div>
        </div>
        <div class="field">
          <label>Jurisdições</label>
          <div class="checkbox-row">
            <label class="checkbox-label"><input type="checkbox" name="jur" value="EUIPO" checked /> EUIPO</label>
            <label class="checkbox-label"><input type="checkbox" name="jur" value="INPI" checked /> INPI</label>
          </div>
        </div>
        <div class="flex gap-sm" style="margin-top:var(--space-md);justify-content:flex-end;">
          <button class="btn" type="button" id="wl-cancel">Cancelar</button>
          <button class="btn btn-primary" type="submit" id="wl-submit">Criar vigilância</button>
        </div>
      </form>
    </div>`;

  document.body.appendChild(backdrop);

  const close = () => backdrop.remove();
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  document.getElementById('wl-modal-close').addEventListener('click', close);
  document.getElementById('wl-cancel').addEventListener('click', close);
  document.addEventListener('keydown', function escClose(e) {
    if (e.key === 'Escape') { close(); document.removeEventListener('keydown', escClose); }
  });

  const range = document.getElementById('wl-threshold');
  const rangeVal = document.getElementById('wl-threshold-val');
  range.addEventListener('input', () => { rangeVal.textContent = `${range.value}%`; });

  document.getElementById('wl-name').focus();

  document.getElementById('wl-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const name = form.name.value.trim();
    if (!name) { toast('Indique um nome.', 'error'); return; }
    const jurisdictions = Array.from(form.querySelectorAll('input[name="jur"]:checked')).map((c) => c.value);
    const submit = document.getElementById('wl-submit');
    submit.disabled = true;
    submit.textContent = 'A criar…';
    try {
      await request('POST', '/watchlists', {
        auth: true,
        body: {
          name,
          similarity_threshold: parseInt(range.value, 10),
          phonetic_weight: 0.3,
          class_weight: 0.2,
          nice_classes_filter: null,
          jurisdictions: jurisdictions.length ? jurisdictions : null,
        },
      });
      toast('Vigilância criada.', 'success');
      close();
      renderWatchlists();
    } catch (err) {
      toast(err.message, 'error');
      submit.disabled = false;
      submit.textContent = 'Criar vigilância';
    }
  });
}

/* --------------------------------------------------------------------------
   View: Alerts
   -------------------------------------------------------------------------- */
const alertsState = { unreadOnly: false };

async function renderAlerts() {
  const view = getView();
  setTopbarActions(`
    <label class="checkbox-label">
      <input type="checkbox" id="alerts-unread" ${alertsState.unreadOnly ? 'checked' : ''} />
      Só por ler
    </label>`);
  const toggle = document.getElementById('alerts-unread');
  if (toggle) toggle.addEventListener('change', () => {
    alertsState.unreadOnly = toggle.checked;
    loadAlerts();
  });

  await loadAlerts();
}

async function loadAlerts() {
  const view = getView();
  view.innerHTML = renderLoading('A carregar alertas…');
  try {
    const alerts = await request('GET', `/alerts?unread_only=${alertsState.unreadOnly}`, { auth: true });
    const list = Array.isArray(alerts) ? alerts.filter((a) => !a.is_dismissed) : [];
    if (list.length === 0) {
      view.innerHTML = renderEmpty('Sem alertas.', alertsState.unreadOnly ? 'Não há alertas por ler.' : 'Ainda não recebeu alertas.', 'bell');
      return;
    }
    view.innerHTML = `<div class="card-list">${list.map(alertCard).join('')}</div>`;
    bindAlertActions();
  } catch (err) {
    view.innerHTML = renderError(err.message, 'retry-alerts');
    bindRetry('retry-alerts', loadAlerts);
  }
}

function alertCard(a) {
  const t = alertTypeLabel(a.alert_type);
  const scores = [];
  if (a.similarity_score !== null && a.similarity_score !== undefined) {
    scores.push(`<span class="badge badge-accent">Semelhança ${Math.round(a.similarity_score)}%</span>`);
  }
  if (a.phonetic_score !== null && a.phonetic_score !== undefined) {
    scores.push(`<span class="badge badge-neutral">Fonética ${Math.round(a.phonetic_score)}%</span>`);
  }
  if (a.class_overlap_score !== null && a.class_overlap_score !== undefined) {
    scores.push(`<span class="badge badge-neutral">Classes ${Math.round(a.class_overlap_score)}%</span>`);
  }

  return `
    <div class="glass-card list-card alert-card ${a.is_read ? '' : 'unread'}">
      <div class="list-card-head">
        <div>
          <div class="list-card-title">${esc(a.title)}</div>
          <div class="compact-sub">${formatDate(a.created_at)}</div>
        </div>
        <span class="badge ${t.cls}">${esc(t.text)}</span>
      </div>
      ${a.body ? `<div class="list-card-body">${esc(a.body)}</div>` : ''}
      ${scores.length ? `<div class="score-row">${scores.join('')}</div>` : ''}
      <div class="list-card-actions">
        ${a.is_read ? '' : `<button class="btn btn-sm" data-read="${esc(a.id)}">Marcar como lido</button>`}
        <button class="btn btn-sm btn-danger" data-dismiss="${esc(a.id)}">Dispensar</button>
      </div>
    </div>`;
}

function bindAlertActions() {
  const view = getView();
  view.querySelectorAll('[data-read]').forEach((btn) =>
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-read');
      btn.disabled = true;
      try {
        await request('POST', `/alerts/${id}/read`, { auth: true });
        toast('Alerta marcado como lido.', 'success');
        loadAlerts();
      } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
      }
    })
  );
  view.querySelectorAll('[data-dismiss]').forEach((btn) =>
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-dismiss');
      btn.disabled = true;
      try {
        await request('POST', `/alerts/${id}/dismiss`, { auth: true });
        toast('Alerta dispensado.', 'success');
        loadAlerts();
      } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
      }
    })
  );
}

/* --------------------------------------------------------------------------
   View: Deadlines
   -------------------------------------------------------------------------- */
async function renderDeadlines() {
  const view = getView();
  setTopbarActions('');
  view.innerHTML = renderLoading('A carregar prazos…');
  try {
    const deadlines = await request('GET', '/deadlines?upcoming_only=true', { auth: true });
    const list = Array.isArray(deadlines) ? deadlines : [];
    if (list.length === 0) {
      view.innerHTML = renderEmpty('Sem prazos', 'Não existem prazos a aproximar-se.', 'clock');
      return;
    }
    view.innerHTML = `<div class="card-list">${list.map(deadlineCard).join('')}</div>`;
  } catch (err) {
    view.innerHTML = renderError(err.message, 'retry-deadlines');
    bindRetry('retry-deadlines', renderDeadlines);
  }
}

function deadlineCard(d) {
  const cd = countdown(d.due_date);
  return `
    <div class="glass-card list-card">
      <div class="list-card-head">
        <div>
          <div class="list-card-title">${esc(deadlineTypeLabel(d.deadline_type))}</div>
          <div class="compact-sub mono">${esc(d.due_date || '')}</div>
        </div>
        <span class="countdown ${cd.level}">${esc(cd.text)}</span>
      </div>
      ${d.description ? `<div class="list-card-body">${esc(d.description)}</div>` : ''}
      ${d.status ? `<div><span class="badge badge-neutral">${esc(d.status)}</span></div>` : ''}
    </div>`;
}

/* --------------------------------------------------------------------------
   View: Settings
   -------------------------------------------------------------------------- */
async function renderSettings() {
  const view = getView();
  setTopbarActions('');
  view.innerHTML = renderLoading('A carregar definições…');
  try {
    const [subscription, plans] = await Promise.all([
      request('GET', '/billing/subscription', { auth: true }),
      request('GET', '/billing/plans', { auth: true }),
    ]);

    const user = state.user || {};
    const currentPlan = subscription && subscription.plan_type ? String(subscription.plan_type).toLowerCase() : 'free';

    view.innerHTML = `
      <div class="settings-grid">
        <section class="glass-card card-pad">
          <h2 class="card-title">Conta</h2>
          <div class="info-list">
            <div class="info-row"><span class="info-label">Email</span><span class="info-value">${esc(user.email || '—')}</span></div>
            <div class="info-row"><span class="info-label">Nome</span><span class="info-value">${esc(user.full_name || '—')}</span></div>
            <div class="info-row"><span class="info-label">Empresa</span><span class="info-value">${esc(user.company_name || '—')}</span></div>
            <div class="info-row"><span class="info-label">Membro desde</span><span class="info-value mono">${esc(formatDate(user.created_at))}</span></div>
          </div>
        </section>

        <section class="glass-card card-pad">
          <h2 class="card-title">Subscrição</h2>
          <div class="info-list">
            <div class="info-row"><span class="info-label">Plano atual</span>
              <span class="info-value"><span class="badge badge-accent">${esc((PLAN_META[currentPlan] || {}).label || currentPlan)}</span></span></div>
            <div class="info-row"><span class="info-label">Estado</span><span class="info-value">${esc(subscription && subscription.status ? subscription.status : 'ativo')}</span></div>
            <div class="info-row"><span class="info-label">Máx. de marcas</span><span class="info-value mono">${esc(subscription && subscription.max_marks != null ? subscription.max_marks : '—')}</span></div>
            <div class="info-row"><span class="info-label">Máx. de utilizadores</span><span class="info-value mono">${esc(subscription && subscription.max_users != null ? subscription.max_users : '—')}</span></div>
            ${subscription && subscription.current_period_end ? `<div class="info-row"><span class="info-label">Renova a</span><span class="info-value mono">${esc(formatDate(subscription.current_period_end))}</span></div>` : ''}
          </div>
        </section>

        <section class="page-section">
          <h2 class="section-title">Planos disponíveis</h2>
          <div class="plan-grid" id="plan-grid">
            ${renderPlanCards(plans, currentPlan)}
          </div>
        </section>
      </div>`;

    bindPlanButtons();
  } catch (err) {
    view.innerHTML = renderError(err.message, 'retry-settings');
    bindRetry('retry-settings', renderSettings);
  }
}

function renderPlanCards(plans, currentPlan) {
  const keys = PLAN_ORDER.filter((k) => plans && Object.prototype.hasOwnProperty.call(plans, k));
  const effectiveKeys = keys.length ? keys : PLAN_ORDER;
  return effectiveKeys
    .map((key) => {
      const meta = PLAN_META[key] || { label: key, price: 0 };
      const plan = (plans && plans[key]) || {};
      const isCurrent = key === currentPlan;
      const limits = [];
      if (plan.max_marks != null) limits.push(`${plan.max_marks} marca(s)`);
      if (plan.max_users != null) limits.push(`${plan.max_users} utilizador(es)`);
      if (plan.max_clients != null) limits.push(`${plan.max_clients} cliente(s)`);
      return `
        <div class="plan-card ${isCurrent ? 'current' : ''}">
          <div class="plan-name">${esc(meta.label)}</div>
          <div class="plan-price">€${esc(meta.price)}<small>/mês</small></div>
          <div class="plan-limits">
            ${limits.map((l) => `<span>${esc(l)}</span>`).join('')}
          </div>
          ${isCurrent
            ? `<button class="btn btn-block" disabled>Plano atual</button>`
            : `<button class="btn btn-primary btn-block" data-plan="${esc(key)}">Escolher plano</button>`}
        </div>`;
    })
    .join('');
}

function bindPlanButtons() {
  const view = getView();
  view.querySelectorAll('[data-plan]').forEach((btn) =>
    btn.addEventListener('click', async () => {
      const plan = btn.getAttribute('data-plan');
      btn.disabled = true;
      btn.textContent = 'A processar…';
      try {
        const origin = window.location.origin + window.location.pathname;
        const resp = await request('POST', '/billing/checkout', {
          auth: true,
          body: {
            plan,
            success_url: `${origin}#/settings`,
            cancel_url: `${origin}#/settings`,
          },
        });
        if (resp && resp.checkout_url) {
          window.location = resp.checkout_url;
        } else {
          toast('Pagamentos indisponíveis de momento.', 'error');
          btn.disabled = false;
          btn.textContent = 'Escolher plano';
        }
      } catch (err) {
        toast(err.message || 'Pagamentos indisponíveis de momento.', 'error');
        btn.disabled = false;
        btn.textContent = 'Escolher plano';
      }
    })
  );
}

/* --------------------------------------------------------------------------
   View: Assessment (free trademark check)
   -------------------------------------------------------------------------- */

// Static legal note kept in source so the disclaimer is always present even
// before the API responds: "não constitui aconselhamento jurídico".
const ASSESSMENT_DISCLAIMER_NOTE =
  'Esta verificação é automática e informativa; não constitui aconselhamento jurídico nem garante o registo da marca.';

/** PT label + badge class for an assessment verdict. */
function verdictMeta(verdict) {
  const map = {
    eligible: { label: 'Elegível para registo', cls: 'badge-success', level: 'ok' },
    eligible_with_risk: { label: 'Elegível com reservas', cls: 'badge-warning', level: 'warning' },
    not_recommended: { label: 'Registo não recomendado', cls: 'badge-danger', level: 'danger' },
  };
  return map[verdict] || { label: verdict || '—', cls: 'badge-neutral', level: 'ok' };
}

/** PT label + level for a risk / distinctiveness value. */
function riskMeta(level) {
  const map = {
    low: { label: 'Baixo', level: 'ok' },
    medium: { label: 'Médio', level: 'warning' },
    high: { label: 'Elevado', level: 'danger' },
  };
  return map[level] || { label: level || '—', level: 'ok' };
}

function distinctivenessMeta(level) {
  const map = {
    fully_met: { label: 'Totalmente cumprido', level: 'ok' },
    partially_met: { label: 'Parcialmente cumprido', level: 'warning' },
    not_met: { label: 'Não cumprido', level: 'danger' },
  };
  return map[level] || { label: level || '—', level: 'ok' };
}

function renderAssessment() {
  const view = getView();
  setTopbarActions('');
  view.innerHTML = `
    <div class="assessment-intro glass-card card-pad">
      <p class="text-secondary">
        Verifique gratuitamente a viabilidade de registo de uma marca: distintividade,
        classes de Nice recomendadas, marcas semelhantes e risco de oposição.
      </p>
    </div>
    <form class="glass-card card-pad assessment-form" id="assessment-form" novalidate>
      <div class="field">
        <label for="as-mark">Marca a verificar</label>
        <input class="input" id="as-mark" name="mark_name" type="text"
               placeholder="ex: Zyphora" required maxlength="255" />
      </div>
      <div class="assessment-form-row">
        <div class="field">
          <label for="as-jur">Jurisdição</label>
          <select class="select" id="as-jur" name="jurisdiction">
            <option value="EU">União Europeia (EUIPO)</option>
            <option value="PT">Portugal (INPI)</option>
          </select>
        </div>
        <div class="field">
          <label for="as-classes">Classes de Nice (opcional)</label>
          <input class="input" id="as-classes" name="nice_classes" type="text"
                 placeholder="ex: 35, 42, 45" />
        </div>
      </div>
      <div class="field">
        <label for="as-desc">Descrição da atividade</label>
        <textarea class="input" id="as-desc" name="business_description" rows="3"
                  placeholder="Descreva os produtos ou serviços (ex: plataforma SaaS de gestão)"></textarea>
      </div>
      <button class="btn btn-primary" type="submit" id="as-submit">
        ${icon('check', 16)} Verificar marca
      </button>
    </form>
    <div id="assessment-result" aria-live="polite"></div>`;

  const form = document.getElementById('assessment-form');
  form.addEventListener('submit', doAssessment);
  const mark = document.getElementById('as-mark');
  if (mark) mark.focus();
}

async function doAssessment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const container = document.getElementById('assessment-result');
  const markName = form.mark_name.value.trim();
  if (!markName) {
    toast('Indique o nome da marca a verificar.', 'error');
    return;
  }

  const classesRaw = form.nice_classes.value.trim();
  const niceClasses = classesRaw
    ? classesRaw.split(',').map((s) => parseInt(s.trim(), 10)).filter((n) => Number.isFinite(n) && n >= 1 && n <= 45)
    : null;

  const submit = document.getElementById('as-submit');
  if (submit) submit.disabled = true;
  container.innerHTML = renderLoading('A analisar a marca…');

  try {
    const report = await request('POST', '/assessments', {
      auth: true,
      body: {
        mark_name: markName,
        jurisdiction: form.jurisdiction.value || 'EU',
        business_description: form.business_description.value.trim(),
        nice_classes: niceClasses && niceClasses.length ? niceClasses : null,
      },
    });
    container.innerHTML = renderAssessmentReport(report);
    const printBtn = document.getElementById('as-print');
    if (printBtn) printBtn.addEventListener('click', () => window.print());
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    container.innerHTML = renderError(err.message, 'as-retry');
    const retry = document.getElementById('as-retry');
    if (retry) retry.addEventListener('click', () => doAssessment(event));
  } finally {
    if (submit) submit.disabled = false;
  }
}

function renderAssessmentReport(r) {
  if (!r || typeof r !== 'object') {
    return renderError('Resposta de avaliação inválida.');
  }
  const vm = verdictMeta(r.verdict);
  const risk = riskMeta(r.risk_level);
  const dist = distinctivenessMeta(r.distinctiveness ? r.distinctiveness.level : '');
  const distScore = r.distinctiveness && typeof r.distinctiveness.score === 'number'
    ? Math.round(r.distinctiveness.score) : null;

  const classes = Array.isArray(r.recommended_classes) ? r.recommended_classes : [];
  const candidates = Array.isArray(r.candidates) ? r.candidates : [];
  const recommendations = Array.isArray(r.recommendations) ? r.recommendations : [];
  const disclaimers = Array.isArray(r.disclaimers) ? r.disclaimers : [];

  const classesHtml = classes.length
    ? classes.map((c) => `
        <div class="assessment-class">
          <div class="assessment-class-head">
            <span class="chip">Classe ${esc(c.class_number)}</span>
            <span class="assessment-class-title">${esc(c.title_pt)}</span>
          </div>
          ${c.reason ? `<div class="compact-sub">${esc(c.reason)}</div>` : ''}
        </div>`).join('')
    : `<p class="text-secondary text-sm">Sem recomendações de classes.</p>`;

  let candidatesHtml;
  if (r.candidates_provenance === 'unavailable') {
    candidatesHtml = renderEmpty(
      'Pesquisa de anterioridades indisponível',
      'Não foi possível consultar as bases de dados neste momento. Repita mais tarde para uma análise completa.',
      'search'
    );
  } else if (candidates.length === 0) {
    candidatesHtml = renderEmpty('Sem correspondência exata', 'Não foram identificadas marcas idênticas ou muito semelhantes.', 'check');
  } else {
    candidatesHtml = `<div class="card-list">${candidates.map(assessmentCandidateRow).join('')}</div>`;
  }

  return `
    <div class="assessment-report" id="assessment-report">
      <div class="assessment-report-head">
        <div>
          <div class="list-card-title">${esc(r.mark_name)}</div>
          <div class="list-card-meta">
            <span class="badge badge-neutral">${esc(r.jurisdiction)}</span>
            <span class="compact-sub">Gerado em ${formatDate(r.created_at)}</span>
          </div>
        </div>
        <button class="btn" id="as-print" type="button">${icon('printer', 16)} Imprimir / PDF</button>
      </div>

      <div class="glass-card card-pad assessment-verdict ${vm.level}">
        <span class="badge ${vm.cls}">${esc(vm.label)}</span>
        <p class="text-secondary">O registo de uma marca envolve sempre algum risco. Reveja o relatório e as recomendações antes de avançar.</p>
      </div>

      <div class="assessment-components">
        ${assessmentComponent('Distintividade', dist.label, dist.level,
          (distScore !== null ? `Pontuação ${distScore}/100. ` : '') + (r.distinctiveness ? esc(r.distinctiveness.rationale) : ''))}
        ${assessmentComponent('Marca idêntica', r.identical_match ? 'Encontrada' : 'Sem correspondência exata',
          r.identical_match ? 'danger' : 'ok',
          r.identical_match ? 'Existe uma marca idêntica registada.' : 'Nenhuma marca idêntica foi identificada.')}
        ${assessmentComponent('Risco de oposição', risk.label, risk.level,
          r.opposition_risk ? esc(r.opposition_risk.rationale) : '')}
      </div>

      <section class="page-section">
        <h2 class="section-title">Classes recomendadas para o registo</h2>
        <div class="glass-card card-pad assessment-classes">${classesHtml}</div>
      </section>

      <section class="page-section">
        <h2 class="section-title">Marcas anteriores semelhantes</h2>
        ${candidatesHtml}
      </section>

      <section class="page-section">
        <h2 class="section-title">A nossa recomendação</h2>
        <div class="glass-card card-pad">
          <ol class="assessment-reco-list">
            ${recommendations.map((rec) => `<li>${esc(rec)}</li>`).join('')}
          </ol>
        </div>
      </section>

      <section class="page-section assessment-disclaimer">
        <h2 class="section-title">Aviso legal</h2>
        <div class="glass-card card-pad">
          <p class="text-secondary text-sm">${esc(ASSESSMENT_DISCLAIMER_NOTE)}</p>
          <ul class="assessment-disclaimer-list">
            ${disclaimers.map((d) => `<li>${esc(d)}</li>`).join('')}
          </ul>
        </div>
      </section>
    </div>`;
}

function assessmentComponent(title, value, level, detail) {
  return `
    <div class="glass-card card-pad assessment-component ${esc(level)}">
      <div class="assessment-component-title">${esc(title)}</div>
      <div class="assessment-component-value countdown ${esc(level)}">${esc(value)}</div>
      ${detail ? `<div class="compact-sub">${detail}</div>` : ''}
    </div>`;
}

function assessmentCandidateRow(c) {
  const band = riskMeta(c.similarity_band);
  const sim = typeof c.similarity === 'number' ? Math.round(c.similarity) : '—';
  return `
    <div class="glass-card list-card">
      <div class="list-card-head">
        <div>
          <div class="list-card-title">${esc(c.word_mark)}</div>
          <div class="list-card-meta">
            ${c.jurisdiction ? `<span class="badge badge-neutral">${esc(c.jurisdiction)}</span>` : ''}
            ${c.source ? `<span class="compact-sub mono">${esc(c.source)}</span>` : ''}
          </div>
        </div>
        <span class="countdown ${band.level}">Semelhança ${esc(sim)}%</span>
      </div>
    </div>`;
}

/* --------------------------------------------------------------------------
   Small binding helper
   -------------------------------------------------------------------------- */
function bindRetry(id, fn) {
  const btn = document.getElementById(id);
  if (btn) btn.addEventListener('click', fn);
}

/* --------------------------------------------------------------------------
   Route dispatch
   -------------------------------------------------------------------------- */
const VIEW_RENDERERS = {
  '/dashboard': renderDashboard,
  '/assessment': renderAssessment,
  '/search': renderSearch,
  '/watchlists': renderWatchlists,
  '/alerts': renderAlerts,
  '/deadlines': renderDeadlines,
  '/settings': renderSettings,
};

async function router() {
  const path = currentPath();
  const token = getToken();

  // Unauthenticated: force login for any protected route.
  if (!token) {
    state.user = null;
    if (path !== '/login') {
      navigate('/login');
      return;
    }
    renderAuth();
    return;
  }

  // Authenticated but hitting login → send to dashboard.
  if (path === '/login') {
    navigate('/dashboard');
    return;
  }

  // Ensure we have the current user (validates the token).
  if (!state.user) {
    try {
      state.user = await request('GET', '/auth/me', { auth: true });
    } catch (err) {
      // request() already handles 401 (clears token + redirects).
      clearToken();
      navigate('/login');
      return;
    }
  }

  // Render shell then the active view.
  renderShell(path);
  const view = getView();
  if (view) view.focus({ preventScroll: true });

  const renderer = VIEW_RENDERERS[path] || renderDashboard;
  try {
    await renderer();
  } catch (err) {
    const v = getView();
    if (v) v.innerHTML = renderError(err.message);
  }
}

/* --------------------------------------------------------------------------
   Bootstrap
   -------------------------------------------------------------------------- */
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', () => {
  if (!window.location.hash) {
    window.location.hash = getToken() ? '#/dashboard' : '#/login';
  }
  router();
});

// If DOMContentLoaded already fired (defer scripts run before it, but guard anyway).
if (document.readyState !== 'loading' && !window.location.hash) {
  window.location.hash = getToken() ? '#/dashboard' : '#/login';
}
