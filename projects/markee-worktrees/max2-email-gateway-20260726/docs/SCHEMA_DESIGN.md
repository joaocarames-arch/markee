# Schema Design — markee

> Last updated: 2026-07-24
> PostgreSQL 15 with 4 schemas: raw, core, events, app.

---

## Design Rationale

Separação em 4 schemas PostgreSQL com propósitos distintos:

| Schema | Propósito | Dados | Retenção |
|---|---|---|---|
| `raw` | Respostas originais das APIs | JSONB imutável | 90 dias (particionado por mês) |
| `core` | Entidades de domínio normalizadas | Marcas, titulares, representantes, classes | Indefinida |
| `events` | Eventos legais do ciclo de vida | Oposições, renovações, caducidades | Indefinida |
| `app` | Dados da aplicação | Utilizadores, watchlists, alertas, subscrições | Indefinida |

**Vantagens:**
- Separação clara de responsabilidades
- Políticas de retenção e backup diferentes por schema
- Permissões granulares (app nunca escreve em raw/core diretamente)
- raw pode ser truncado sem afetar dados de negócio

---

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- trigram indexes for similarity
CREATE EXTENSION IF NOT EXISTS "pgvector";   -- vector embeddings (future)
```

---

## Schema: raw

Respostas originais das APIs. Imutável. Particionado por mês para facilitar purga.

```sql
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE raw.api_responses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL,  -- FK → core.sources.id (soft reference, cross-schema)
    source_run_id   UUID,           -- FK → core.source_runs.id
    endpoint        TEXT NOT NULL,
    request_params  JSONB,
    response_status INTEGER,
    response_headers JSONB,
    response_body   JSONB,
    response_size_bytes INTEGER,
    duration_ms     INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

-- Partições mensais (criar programaticamente)
CREATE TABLE raw.api_responses_2026_07 PARTITION OF raw.api_responses
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE raw.api_responses_2026_08 PARTITION OF raw.api_responses
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

CREATE INDEX idx_raw_source_created ON raw.api_responses (source_id, created_at DESC);
```

---

## Schema: core

Entidades de domínio normalizadas. O coração do sistema.

```sql
CREATE SCHEMA IF NOT EXISTS core;

-- Fontes de dados
CREATE TABLE core.sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(64) NOT NULL UNIQUE,
    source_type     VARCHAR(32) NOT NULL,  -- api_rest, xml_bulk, pdf_bulletin, html_scrape
    base_url        TEXT,
    auth_method     VARCHAR(32),           -- none, oauth2_client_credentials, subscription_portal
    is_enabled      BOOLEAN NOT NULL DEFAULT true,
    priority        INTEGER NOT NULL CHECK (priority >= 1),
    config_snapshot JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Execuções de fontes
CREATE TABLE core.source_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES core.sources(id),
    run_type        VARCHAR(32) NOT NULL,  -- incremental_poll, full_backfill, daily_parse
    status          VARCHAR(16) NOT NULL,  -- running, completed, failed, partial
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    items_processed INTEGER DEFAULT 0,
    items_new       INTEGER DEFAULT 0,
    items_updated   INTEGER DEFAULT 0,
    items_failed    INTEGER DEFAULT 0,
    error_message   TEXT,
    cursor_value    VARCHAR(128),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_runs_source_id ON core.source_runs(source_id);
CREATE INDEX idx_runs_status ON core.source_runs(status);

-- Marcas
CREATE TABLE core.trademarks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id               VARCHAR(64) NOT NULL,
    jurisdiction            VARCHAR(8) NOT NULL CHECK (jurisdiction IN ('EU', 'PT', 'WIPO')),
    application_number      VARCHAR(32) NOT NULL UNIQUE,
    registration_number     VARCHAR(32) UNIQUE,
    word_mark               VARCHAR(512) NOT NULL,
    mark_feature            VARCHAR(32) NOT NULL DEFAULT 'Word',
    figurative_mark_url     TEXT,
    status                  VARCHAR(64) NOT NULL,
    status_date             TIMESTAMPTZ,
    application_date        DATE,
    registration_date       DATE,
    expiry_date             DATE,
    renewal_status          VARCHAR(64),
    opposition_period_end   DATE,
    update_date             TIMESTAMPTZ,
    nice_classes            INTEGER[],
    raw_data                JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_trademarks_app_number ON core.trademarks(application_number);
CREATE INDEX idx_trademarks_word_mark_trgm ON core.trademarks USING GIN (word_mark gin_trgm_ops);
CREATE INDEX idx_trademarks_status ON core.trademarks(status);
CREATE INDEX idx_trademarks_expiry_date ON core.trademarks(expiry_date);
CREATE INDEX idx_trademarks_update_date ON core.trademarks(update_date);
CREATE INDEX idx_trademarks_nice_classes ON core.trademarks USING GIN (nice_classes);
CREATE INDEX idx_trademarks_jurisdiction ON core.trademarks(jurisdiction);

-- Versões de marcas
CREATE TABLE core.trademark_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trademark_id        UUID NOT NULL REFERENCES core.trademarks(id) ON DELETE CASCADE,
    version_number      INTEGER NOT NULL,
    snapshot            JSONB NOT NULL,
    diff_from_previous  JSONB,
    change_source       VARCHAR(64) NOT NULL,
    change_type         VARCHAR(32) NOT NULL,
    raw_response_id     UUID,  -- soft ref to raw.api_responses
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trademark_id, version_number)
);

CREATE INDEX idx_versions_trademark_id ON core.trademark_versions(trademark_id);

-- Titulares
CREATE TABLE core.holders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   VARCHAR(64) NOT NULL,
    name        VARCHAR(512) NOT NULL,
    address     TEXT,
    country     CHAR(2),
    type        VARCHAR(32) CHECK (type IN ('natural', 'legal')),
    raw_data    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_holders_name_trgm ON core.holders USING GIN (name gin_trgm_ops);
CREATE INDEX idx_holders_source_id ON core.holders(source_id);

-- Representantes
CREATE TABLE core.representatives (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   VARCHAR(64) NOT NULL,
    name        VARCHAR(512) NOT NULL,
    address     TEXT,
    country     CHAR(2),
    type        VARCHAR(32) CHECK (type IN ('natural', 'legal', 'association')),
    raw_data    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reps_name_trgm ON core.representatives USING GIN (name gin_trgm_ops);
CREATE INDEX idx_reps_source_id ON core.representatives(source_id);

-- Relação Marca-Titular
CREATE TABLE core.trademark_holders (
    trademark_id UUID NOT NULL REFERENCES core.trademarks(id) ON DELETE CASCADE,
    holder_id    UUID NOT NULL REFERENCES core.holders(id) ON DELETE CASCADE,
    role         VARCHAR(32) NOT NULL DEFAULT 'applicant',
    since_date   DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trademark_id, holder_id, role)
);

-- Relação Marca-Representante
CREATE TABLE core.trademark_representatives (
    trademark_id      UUID NOT NULL REFERENCES core.trademarks(id) ON DELETE CASCADE,
    representative_id UUID NOT NULL REFERENCES core.representatives(id) ON DELETE CASCADE,
    role              VARCHAR(32) NOT NULL DEFAULT 'representative',
    since_date        DATE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trademark_id, representative_id)
);

-- Classes de Nice
CREATE TABLE core.nice_classes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_number    INTEGER NOT NULL UNIQUE CHECK (class_number >= 1 AND class_number <= 45),
    description_pt  TEXT,
    description_en  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Produtos e Serviços
CREATE TABLE core.goods_services (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trademark_id    UUID NOT NULL REFERENCES core.trademarks(id) ON DELETE CASCADE,
    nice_class_id   UUID NOT NULL REFERENCES core.nice_classes(id),
    term            TEXT NOT NULL,
    language        VARCHAR(8) NOT NULL DEFAULT 'pt',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gs_trademark_id ON core.goods_services(trademark_id);

-- Documentos
CREATE TABLE core.documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trademark_id      UUID REFERENCES core.trademarks(id),
    document_type     VARCHAR(64) NOT NULL,
    source_url        TEXT,
    storage_path      TEXT,
    file_hash         VARCHAR(64),
    publication_date  DATE,
    language          VARCHAR(8) DEFAULT 'pt',
    metadata          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_docs_trademark_id ON core.documents(trademark_id);
```

---

## Schema: events

Eventos legais do ciclo de vida das marcas.

```sql
CREATE SCHEMA IF NOT EXISTS events;

CREATE TABLE events.lifecycle_events (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trademark_id      UUID NOT NULL REFERENCES core.trademarks(id) ON DELETE CASCADE,
    event_type        VARCHAR(64) NOT NULL,
    event_date        DATE NOT NULL,
    deadline_date     DATE,
    description       TEXT,
    source            VARCHAR(32) NOT NULL,
    source_reference  VARCHAR(128),
    raw_data          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_trademark_id ON events.lifecycle_events(trademark_id);
CREATE INDEX idx_events_event_type ON events.lifecycle_events(event_type);
CREATE INDEX idx_events_deadline_date ON events.lifecycle_events(deadline_date);
CREATE INDEX idx_events_trademark_type ON events.lifecycle_events(trademark_id, event_type);
```

---

## Schema: app

Dados da aplicação — utilizadores, watchlists, alertas, subscrições.

```sql
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE app.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    company_name    VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    is_superuser    BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app.watchlists (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    name                  VARCHAR(255) NOT NULL,
    similarity_threshold  FLOAT NOT NULL DEFAULT 0.75 CHECK (similarity_threshold >= 0 AND similarity_threshold <= 1),
    phonetic_weight       FLOAT NOT NULL DEFAULT 0.30 CHECK (phonetic_weight >= 0 AND phonetic_weight <= 1),
    class_weight          FLOAT NOT NULL DEFAULT 0.20 CHECK (class_weight >= 0 AND class_weight <= 1),
    jurisdictions         VARCHAR(8)[] NOT NULL DEFAULT '{EU,PT}',
    is_active             BOOLEAN NOT NULL DEFAULT true,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_watchlists_user_id ON app.watchlists(user_id);

CREATE TABLE app.watchlist_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id  UUID NOT NULL REFERENCES app.watchlists(id) ON DELETE CASCADE,
    mark_text     VARCHAR(512) NOT NULL,
    nice_classes  INTEGER[],
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_wl_items_watchlist_id ON app.watchlist_items(watchlist_id);

CREATE TABLE app.alerts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    title                   VARCHAR(512) NOT NULL,
    body                    TEXT,
    alert_type              VARCHAR(32) NOT NULL,
    severity                VARCHAR(16) NOT NULL DEFAULT 'info',
    reference_trademark_id  UUID REFERENCES core.trademarks(id),
    is_read                 BOOLEAN NOT NULL DEFAULT false,
    is_dismissed            BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alerts_user_id ON app.alerts(user_id);
CREATE INDEX idx_alerts_user_unread ON app.alerts(user_id, is_read) WHERE is_read = false;

CREATE TABLE app.deadlines (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    trademark_id        UUID NOT NULL REFERENCES core.trademarks(id),
    lifecycle_event_id  UUID REFERENCES events.lifecycle_events(id),
    deadline_type       VARCHAR(32) NOT NULL,
    deadline_date       DATE NOT NULL,
    warning_date        DATE,
    status              VARCHAR(16) NOT NULL DEFAULT 'pending',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_deadlines_user_date ON app.deadlines(user_id, deadline_date);
CREATE INDEX idx_deadlines_status ON app.deadlines(status);

CREATE TABLE app.subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES app.users(id) UNIQUE,
    plan_type               VARCHAR(32) NOT NULL,
    status                  VARCHAR(16) NOT NULL DEFAULT 'active',
    stripe_customer_id      VARCHAR(255),
    stripe_subscription_id  VARCHAR(255),
    max_marks               INTEGER NOT NULL,
    max_users               INTEGER DEFAULT 1,
    max_clients             INTEGER DEFAULT 0,
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app.teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    owner_id    UUID NOT NULL REFERENCES app.users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app.portfolios (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id       UUID NOT NULL REFERENCES app.teams(id) ON DELETE CASCADE,
    client_name   VARCHAR(512) NOT NULL,
    client_email  VARCHAR(255),
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_portfolios_team_id ON app.portfolios(team_id);
```

---

## Search Path

```sql
-- Application user (api) sees app schema first, then core/events
ALTER ROLE markee_api SET search_path = app, core, events, public;

-- ETL user (worker) sees raw and core
ALTER ROLE markee_worker SET search_path = core, raw, events, public;
```

---

## Permissions

```sql
-- API role: read core/events, full access to app
GRANT USAGE ON SCHEMA app, core, events TO markee_api;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO markee_api;
GRANT SELECT ON ALL TABLES IN SCHEMA events TO markee_api;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO markee_api;

-- Worker role: write to raw/core/events, read from app (for alert generation)
GRANT USAGE ON SCHEMA raw, core, events, app TO markee_worker;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw TO markee_worker;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core TO markee_worker;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA events TO markee_worker;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO markee_worker;
```

---

## Entity Relationship Summary

```
raw                          core                               events
─────                        ────                               ──────
api_responses ────────────── sources
                    ┌─────── source_runs
                    │
                    ├─────── trademarks ─────┬── trademark_versions
                    │         │              ├── trademark_holders ─── holders
                    │         │              ├── trademark_reps ────── representatives
                    │         │              ├── goods_services ────── nice_classes
                    │         │              ├── documents
                    │         │              │
                    │         └──────────────┬── lifecycle_events
                    │                        │
app                 │                        │
───                 │                        │
users               │                        │
├── watchlists ─────┤                        │
│   └── items       │                        │
├── alerts ─────────┼────────────────────────┤
├── deadlines ──────┼────────────────────────┤
├── subscriptions   │                        │
├── teams           │                        │
└── portfolios      │                        │
```

---

## Migration Strategy

1. **Alembic** para gestão de migrações.
2. Migrações são criadas com `alembic revision --autogenerate`.
3. Cada migração é atómica — um schema change por ficheiro.
4. Rollback testado antes de deploy para produção.
5. Dados em `raw` nunca são migrados — se o schema mudar, cria-se nova partição.
