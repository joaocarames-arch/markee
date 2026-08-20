# markee — Trademark Monitoring SaaS

## What is markee
SaaS for monitoring trademarks at INPI (Portugal) and EUIPO (Europe). Features: similarity alerts, lifecycle/deadline management, client prospection for IP professionals.

## Target Users
- IP professionals and patent attorneys
- Trademark lawyers
- Corporate legal departments
- SMEs with trademark portfolios

## Current State
The existing codebase has bugs and weak aesthetics. We are REWRITING FROM SCRATCH.

## New Stack Decision
- **Backend:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 15 (with pg_trgm + pgvector) + Celery + Redis
- **Frontend:** Vanilla HTML/CSS/JS (NO React, NO Streamlit, NO build step). FastAPI serves both API and static frontend.
- **Infra:** Docker Compose, self-hosted
- **Auth:** JWT-based, OAuth2PasswordBearer
- **Language:** All UI text in European Portuguese (PT-PT)

## Design System (MANDATORY)
Follow the BRAND_MANUAL.md file in the project root. Key tokens:

### Colors
```css
--color-accent: #35d0e0;
--color-accent-hover: #5edcf0;
--color-accent-pressed: #25a8b8;
--color-bg-primary: #08090a;
--color-bg-secondary: #111214;
--color-bg-surface: #1a1c1f;
--color-text-primary: #e8e8e8;
--color-text-secondary: #8a8d93;
--color-border: rgba(255, 255, 255, 0.08);
--color-danger: #e05252;
--color-success: #4ade80;
--color-warning: #f5a623;
```

### Typography
- Headings + Body: Inter (Google Fonts)
- Monospace: JetBrains Mono (Google Fonts)

### Spacing
```css
--space-xs: 4px; --space-sm: 8px; --space-md: 16px;
--space-lg: 24px; --space-xl: 32px; --space-2xl: 48px;
```

### Border Radius
```css
--radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-xl: 24px;
```

### Glassmorphism
```css
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
}
```

### Shadows
```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
--shadow-md: 0 4px 12px rgba(0,0,0,0.4);
--shadow-lg: 0 12px 32px rgba(0,0,0,0.5);
--shadow-glow: 0 0 20px rgba(53,208,224,0.25);
```

## Pricing Tiers
| Tier | Price | Features |
|------|-------|----------|
| Free | €0/mês | 1 brand, EUIPO+INPI, renewal alerts, email |
| Individual | €5/mês | 5 brands, similarity alerts, opposition alerts, email |
| Pro | €29/mês | 100 brands, phonetic PT, Telegram alerts, basic analytics |
| Profissional | €99/mês | 500 brands, client prospection, multi-client, white-label |
| Enterprise | €249/mês | unlimited brands, full API, SSO, WIPO |

## Key Services (preserve logic, rewrite code)
1. **EUIPO Service** — OAuth2 client for EUIPO/TMview REST API. Falls back to mock mode without credentials.
2. **BPI Parser** — Parses Boletim da Propriedade Industrial PDFs from INPI. Uses pdfplumber + pymupdf.
3. **Similarity Engine** — rapidfuzz (textual) + jellyfish (phonetic, PT-aware) + Nice class overlap. Weights: 50% textual, 30% phonetic, 20% classes.
4. **Lifecycle Engine** — Tracks renewal deadlines, opposition periods, grace periods.
5. **Alerts Service** — Email (aiosmtplib) + Telegram (python-telegram-bot) notifications.
6. **Billing** — Stripe integration for subscriptions.
7. **Prospection** — Identifies potential clients for IP professionals based on trademark activity.

## Database Models (preserve schema, rewrite code)
- User (email, hashed_password, full_name, company_name, is_active, is_superuser)
- Trademark (source_id, application_number, word_mark, figurative_mark_url, status, nice_classes, applicants, jurisdiction, raw_data)
- Watchlist (user_id, name, similarity_threshold, phonetic_weight, class_weight, jurisdictions, is_active)
- WatchlistItem (watchlist_id, mark_text, nice_classes, notes)
- Alert (user_id, title, body, alert_type, is_read, is_dismissed)
- Subscription (user_id, plan_type, status, stripe_customer_id, max_marks, max_users, max_clients)
- Team (name, owner_id)
- Portfolio (team_id, client_name, client_email, notes)
- LifecycleEvent (trademark_id, event_type, event_date, deadline_date, description)

## Celery Tasks
- poll_euipo — periodic EUIPO API polling for new trademark filings
- parse_bpi — daily BPI PDF parsing
- match_similar — run similarity engine against new trademarks vs watchlists
- calculate_deadlines — compute upcoming deadlines from lifecycle events
- check_expiry — check for trademarks nearing expiry
- send_alerts — dispatch notifications via email/Telegram

## Docker Compose Services
- db (PostgreSQL 15 with pg_trgm)
- redis (Redis 7)
- app (FastAPI/uvicorn on :8000)
- worker (Celery worker)
- beat (Celery beat scheduler)
- Frontend served by FastAPI itself (no separate container)

## API Structure
```
/api/v1/auth/          — register, login, me
/api/v1/trademarks/    — search, list, detail
/api/v1/watchlists/    — CRUD watchlists + items
/api/v1/alerts/        — list, mark read, dismiss
/api/v1/deadlines/     — list upcoming deadlines
/api/v1/portfolios/    — client portfolio management
/api/v1/billing/       — subscription, checkout, webhook
/api/v1/health/        — health check
```

## Frontend Pages (vanilla JS, served by FastAPI)
- `/` — Landing page (hero, features, pricing, CTA)
- `/login` — Login + register
- `/app` — Dashboard (stats overview)
- `/app/search` — Trademark search
- `/app/watchlists` — Watchlist management
- `/app/alerts` — Alert center
- `/app/deadlines` — Deadline calendar
- `/app/settings` — Account + subscription management

## Frontend Requirements
- Dark mode, glassmorphism, ciano #35d0e0 accent (per BRAND_MANUAL.md)
- Responsive (mobile + desktop)
- SPA-like: vanilla JS with fetch() calls to API, no page reloads
- Use CSS custom properties (design tokens) from BRAND_MANUAL.md
- Inter font for everything, JetBrains Mono for codes/numbers
- Frosted glass cards, subtle animations, scroll reveals
- Custom cursor effect (dot + ring) on landing page only
- Keep existing logos in assets/logos/

## Code Standards
- Python: type hints on all public functions, Google-style docstrings
- All code comments and git commits in English
- All UI text in European Portuguese (PT-PT)
- 4-space indentation for Python, 2-space for CSS/JS/HTML
- No wildcard imports
- Pydantic v2 for all schemas
- SQLAlchemy 2.0 async style
- Tests: pytest + pytest-asyncio, minimum 80% coverage on services

## Quality Bar
- No TODO/FIXME comments left in final code
- Proper error handling on all API endpoints
- Input validation on all forms
- Loading states in frontend
- Accessible (ARIA labels, keyboard nav, semantic HTML)
- Mobile-first responsive design