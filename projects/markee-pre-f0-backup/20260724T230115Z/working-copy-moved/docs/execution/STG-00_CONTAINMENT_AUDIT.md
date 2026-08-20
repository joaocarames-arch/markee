# STG-00 — Baseline congelada e contenção imediata (auditoria factual read-only)

- Working directory: `/home/batata/projects/markee`
- Perfil: Max-2 (papel crítico/read-only)
- Data UTC: 2026-07-24T20:47Z
- Git HEAD: `51aa7d0e057479275df7955f1fa7c8cbdd711d4c` (master)
- Âmbito: inspecionar repo, Git, Docker/processos, schedules, código, testes, migrations, imagem e BD apenas em modo read-only; HTTP GET/HEAD permitido. Nenhum `.env`/token/secret lido em valor. Nenhum deploy, DNS, rebuild, rotação, migration, schedule edit, backup mutável, commit ou push.
- Veredicto: **BLOCKED** (existem provas factuais de exposição pública e de BPI tecnicamente capaz; gates de João pendentes; testes de contenção ainda não existem).

## 0. Sumário executivo

A baseline factual de STG-00 confirma os pontos críticos que motivaram este stage e acrescenta três factos novos que mudam a ordem de execução:

1. **BPI está tecnicamente ativo.** O `beat_schedule` inclui `parse-bpi-daily` (86400 s) e `calculate-deadlines-hourly` (3600 s); a task `parse_bpi.download_and_parse` resolve `source = "inpi_bpi"` e `calculate_deadlines.recalculate_all` cria `Deadline` a partir de qualquer `LifecycleEvent.event_type == "publication"` independente da `source`. Não existe kill switch, feature flag, env var, default-off ou short-circuit em código. BPI NO-GO é declaração, não controlo.
2. **A instância pública atual é a mesma da local**, com bind em `127.0.0.1:8000` mas exposta por Cloudflare Tunnel sem access restriction observável em `markee.batata.cc` e `app.markee.batata.cc` (HTTP 200). `/api/v1/billing/plans` é público; `/api/v1/auth/register` e `/api/v1/billing/checkout` exigem auth; `/api/v1/trademarks` é público e devolve mock EUIPO quando a BD está vazia. A landing servida contém claims `alert-mock` no DOM e copy comercial que não coincide com o pacote editorial aprovado pela auditoria recente.
3. **Imagem contém `/app/.env`** (presença confirmada por `test -e`; sha256 registado abaixo). `Dockerfile` faz `COPY . .` sem `.dockerignore`; `.env` é local e gitignored, mas está presente no contexto de build desta imagem porque o host tem `.env` no contexto de build. `docker-compose.yml` não monta `.env` por volume; o ficheiro veio do `COPY` durante o `docker build`. `.env.example` existe e tem o mesmo tamanho de 526 bytes, o que reforça a tese de que entrou por cópia acidental do working tree, não por intent. Rotation é obrigatória antes de qualquer promoção da imagem.

O stage STG-00 mantém-se **PARTIAL/CRITICAL** e está **BLOCKED** quanto a `READY_FOR_FORJA` porque (a) não existe ainda failing test que prove `source=inpi_bpi` ⇒ `0` deadlines/alertas; (b) não existe kill switch/default-off; (c) a imagem com `.env` e a URL pública estão simultaneamente expostas; (d) a decisão João sobre contenção/rotação é OPEN.

## 1. Evidence map

### 1.1 Git / repo

- HEAD: `51aa7d0e057479275df7955f1fa7c8cbdd711d4c` (`git rev-parse HEAD`).
- Working tree não-promovido: `config/bpi_event_taxonomy.yaml`, `contents/`, `docs/ACTION_PLAN_TO_LIVE.md`, `docs/REQUIREMENTS.md`, `docs/SITEMAP.md`, `docs/execution/`, `docs/research/` — todos untracked. Nada foi adicionado ao índice nesta missão.
- Último commit: `51aa7d0 test: cover watchlist API endpoints` (autor/committer não impressos por opção read-only).

### 1.2 Schedules BPI/deadlines (CONFIRMED)

- Ficheiro: `app/tasks/__init__.py:39-65` — `celery_app.conf.beat_schedule` declara:
  - `"parse-bpi-daily": {"task": "app.tasks.parse_bpi.download_and_parse", "schedule": 86400.0}` (linhas 45-48).
  - `"calculate-deadlines-hourly": {"task": "app.tasks.calculate_deadlines.recalculate_all", "schedule": 3600.0}` (linhas 49-52).
- `app/tasks/parse_bpi.py:50` — `source = await ingestion.get_or_create_source(db, "inpi_bpi")`.
- `app/tasks/parse_bpi.py:55-65` — download, parser, `ingest_bpi_events` → cria `LifecycleEvent` com `source="inpi_bpi"` e, se `event_type == "publication"`, calcula `deadline_date = add_months(event.event_date, 2)`.
- `app/tasks/calculate_deadlines.py:64-79` — após percorre `LifecycleEvent` por `(trademark, publication)`, cria `Deadline` independente da source.
- `app/services/ingestion.py:927` — `event.source` para BPI.
- Sem kill switch. Verificação: `grep -rE "kill[_-]?switch|BPI_ENABLED|BPI_DISABLED|allow_bpi|enable_bpi|bpi_enabled|public_dev|MAINTENANCE"` em `app/`, `config/`, `frontend/` devolve 0 ocorrências para a flag ou default-off. `app/core/config.py` não declara campo de controlo BPI.

### 1.3 Estado dos workers (CONFIRMED em ambiente atual)

- `docker compose ps` mostra `markee-app-1`, `markee-worker-1`, `markee-beat-1` como `Up 11 hours`. Beat command line: `celery -A app.tasks beat --loglevel=info` (lido via `/proc/1/cmdline` dentro do contentor).
- `docker compose exec -T beat celery -A app.tasks inspect scheduled` respondeu `- empty -` no instante da inspeção. Isto é compatível com beat estar entre batidas, **não** é prova de schedule desativada. A schedule continua carregada no `celery_app.conf` da imagem em execução. Classificação: **probable** para "schedule desativada em runtime"; **confirmed** para "schedule carregada no worker/beat da imagem atual".

### 1.4 Source lineage BPI → eventos/deadlines/alerts (CONFIRMED)

- `app/services/ingestion.py:ingest_bpi_events` (linhas 802-944) cria `LifecycleEvent(trademark_id, event_type, event_date, deadline_date, description, source, source_reference, ...)`; aceita `event_type == "publication"` e define `deadline_date = add_months(event.event_date, 2)`.
- `app/tasks/calculate_deadlines.py:67-79` cria `Deadline(deadline_type="opposition", due_date=opposition.due_date, ...)` para cada trademark com publicação; **não filtra source**.
- `app/services/alerts.py` e `app/tasks/send_alerts.py` são despoletados por eventos; pipeline pode entregar `Alert` se houver `AlertRule` correspondente. Chain `BPI event → LifecycleEvent publication → Deadline opposition → Alert` é tecnicamente possível e não tem source deny.
- `config/bpi_event_taxonomy.yaml` confirma `source: inpi_bpi` e `event_types` com `priority: P0` (`application_published` etc.) — materializa a intenção operacional e contradiz `BPI NO-GO`.

### 1.5 Checkout / mock alcançável (CONFIRMED)

- `GET /api/v1/billing/plans` em `http://127.0.0.1:8000` devolve 200 com `PLAN_LIMITS` (cinco planos, preços e features). **Endpoint público**. Conteúdo observado (parcial): `"free":{...},"individual":{...},"pro":{"max_marks":100,"max_users":5,...,"features":{"import_csv":true,"pdf_reports":true,"telegram_alerts":true}},"profissional":{...}`.
- `POST /api/v1/billing/checkout` em `127.0.0.1:8000` devolve 401 sem auth (auth wall presente). O caminho mock permanece: `app/services/billing.py:94` (`f"cus_mock_{slug}"`), `app/services/billing.py:121` (`{"id":"cs_mock_123","url":success_url,...}`). Não há teste que prove 0 POST públicos.
- `POST /api/v1/auth/register` em `127.0.0.1:8000` devolve 422 com validação Pydantic para emails reservados (filtra `.local`); o endpoint está vivo e serve o frontend.
- `GET /api/v1/trademarks?q=…` em `127.0.0.1:8000` é público e, quando a BD está vazia, devolve `service._mock_search(q, limit)` — `app/api/trademarks.py:66-68` comenta "Fall back to the EUIPO (mock) service so the UI is never empty in dev.". Confirmação de mock em produção pública.
- Landing servida em `127.0.0.1:8000/` contém `alert-mock` no DOM e copy "Sem contratos de permanência. Mude de plano quando quiser." — claims que necessitam anti-claim aplicado (ver STG-01 editorial, READY_FOR_JOAO).

### 1.6 Kill switch / default-off (ABSENT)

- `grep -rE "kill[_-]?switch|BPI_ENABLED|BPI_DISABLED|allow_bpi|enable_bpi|bpi_enabled|public_dev|MAINTENANCE"` em `app/`, `config/`, `frontend/` devolve apenas matches em `app/services/euipo_service.py`, `app/services/billing.py`, `app/api/trademarks.py`, `app/services/ingestion.py` — todos relacionados com fallback mock de EUIPO/Stripe, não com BPI. **Não existe kill switch nem default-off para BPI.**
- `app/core/config.py` (`app/core/config.py:1-89`) não declara variáveis de controlo de BPI.

### 1.7 Imagem e segredos (CONFIRMED)

- `Dockerfile`: `FROM python:3.12-slim`, `COPY requirements.txt .`, `RUN pip install ...`, `COPY . .`, depois `chown markee:markee /app` e `USER markee`. Não existe `.dockerignore` no repo (`ls .dockerignore 2>/dev/null` ⇒ inexistente).
- `.env` no host: `/home/batata/projects/markee/.env` (526 bytes), gitignored. Como `docker-compose.yml` faz `build.context=.`, o `COPY . .` copia `.env` para a imagem.
- Verificação em runtime: `docker compose exec -T app sh -c 'test -e /app/.env && echo HAS_ENV'` ⇒ `HAS_ENV`. `sha256sum /app/.env` ⇒ `64cf63b61386fb8c1346bb68f12b602bee8a53e65277dcdcdc875d449efc3b83`. **Conteúdo do ficheiro não lido nem impresso nesta auditoria.**
- `docker compose exec -T app env` mostrou variáveis de secret em env vars (presença sem valor), incluindo `SECRET_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `EUIPO_API_CLIENT_SECRET`, `TELEGRAM_BOT_TOKEN`, `SMTP_PASSWORD`. Tudo truncado para 2 caracteres + `***` na recolha. Presença confirmada; valores não impressos.
- `.env.example` (526 bytes) tem o mesmo tamanho, consistente com copy de template em vez de segredos reais; o risco é sim, o `.env` em si ser cópia ou conter valores gerados localmente.
- Imagens atuais: `markee-app:latest (id dc2181ca81ad, 2.43GB)`, `markee-worker:latest (fcc696a78525)`, `markee-beat:latest (6038520b141a)` — todas `latest`, não pinadas por digest.

### 1.8 URL pública / bind / proxy (CONFIRMED, classificação public-dev)

- Bind local: `docker-compose.yml` faz `ports: ["127.0.0.1:8000:8000"]` para `app`. Loopback no host, exposto externamente apenas pela cloudflared.
- Cloudflare Tunnel config: `/etc/cloudflared/config.yml` mapeia:
  - `hostname: markee.batata.cc → service: http://127.0.0.1:8000` (com `httpHostHeader: 127.0.0.1:8000`).
  - `hostname: app.markee.batata.cc → service: http://127.0.0.1:8000`.
  - Sem Access policy / `cf-access` / `noTLSVerify` observada para estes hosts.
- Probes HTTP: `curl https://markee.batata.cc/`, `https://markee.batata.cc/api/v1/health` ⇒ 200. Resposta JSON idêntica à do `127.0.0.1:8000`. Não existe environment banner nem robots/noindex no HTML servido.
- Classificação: **public-dev**. Não há `Release`, `Environment`, manifest, `healthcheck` distinto, nem assinatura de staging ou produção. Ver STG-12/13 para produção separada.

### 1.9 BD counts e estado (CONFIRMED, 0 rows)

- Schemas presentes: `app`, `core`, `events`, `public`, `raw` (`\\dn` no contentor `markee-db-1`).
- Tabelas observadas em `app.*`: `users, subscriptions, teams, team_members, client_portfolios, watchlists, watchlist_items, alerts, alert_deliveries, prospection_opportunities, review_queue`. `core.*`, `events.*`, `raw.*` também povoadas.
- Contagens (`docker compose exec -T db psql ...` em 2026-07-24T20:47Z):
  - `app.users`: 0
  - `core.trademarks`: 0
  - `core.documents`: 0
  - `core.sources`: 0
  - `core.source_runs`: 0
  - `events.lifecycle_events`: 0
  - `app.deadlines`: 0
  - `app.alerts`: 0
  - `app.subscriptions`: 0
  - `app.watchlists`: 0
- BD observada vazia, mas isso **não** constitui controlo BPI: o pipeline BPI pode continuar a agendar/baixar PDFs/inserir eventos em qualquer momento em que `parse-bpi-daily` corra, mesmo sem dados anteriores.

### 1.10 Backup / manifest / restore (ABSENT)

- `data/` e `backups/` **não existem** no working tree (`ls data/ backups/` ⇒ `No such file or directory`).
- `docker compose` não define volume de backup nem job Cron.
- Nenhum dump `pg_dump` localizado no host. Migration state: 2 ficheiros `alembic/versions/001_initial_migration.py`, `002_data_infrastructure.py`. Sem inventário de schema diff zero.
- Não há baseline dump antes desta missão. STG-00 recomenda dump read-only antes de qualquer correção futura (próprio stage, tarefa 8) — não foi produzido nesta auditoria porque é ação mutável fora do scope read-only.

## 2. Validação por afirmação de STG-00

| # | Afirmação STG-00 | Veredito | Evidência |
|---|---|---|---|
| 1 | BPI discovery/download/parse/ingest agendado | **CONFIRMED** | `app/tasks/__init__.py:39-48`; `app/tasks/parse_bpi.py:49-87` |
| 2 | Source BPI → `events.lifecycle_events` | **CONFIRMED** | `app/services/ingestion.py:802-944` |
| 3 | Source BPI → `app.deadlines` (via publication) | **CONFIRMED (sem source filter)** | `app/tasks/calculate_deadlines.py:64-79` |
| 4 | Source BPI → `app.alerts` | **PROBABLE** (chain tecnicamente possível) | `app/tasks/calculate_deadlines.py` + `app/services/alerts.py` + `app/tasks/send_alerts.py`; sem source deny observado |
| 5 | Kill switch / default-off | **ABSENT** | `grep` retorna 0 matches; `app/core/config.py` sem flag BPI |
| 6 | Checkout mock alcançável | **CONFIRMED** | `/api/v1/billing/plans` público 200; `/api/v1/billing/checkout` 401 mas reachable; `app/services/billing.py:94,121` |
| 7 | Mock data em ambiente público | **CONFIRMED** | `/api/v1/trademarks` público com fallback mock EUIPO em BD vazia; landing com `alert-mock` |
| 8 | Imagem contém `.env` (presença) | **CONFIRMED** | `test -e /app/.env` ⇒ HAS_ENV; sha256 `64cf63b6…3b83` |
| 9 | URL pública, bind/proxy, public-dev | **CONFIRMED** | cloudflared mapeia `markee.batata.cc` e `app.markee.batata.cc` para `127.0.0.1:8000`; HTTPS 200; sem Access policy |
| 10 | BD counts/estado (sem PII) | **CONFIRMED (0 rows)** | queries em `markee-db-1` retornam 0 para todas as tabelas-alvo |
| 11 | Backup/manifest disponível | **ABSENT** | `data/` e `backups/` inexistentes; sem `pg_dump`; sem job agendado |

## 3. Afirmações desconhecidas / a confirmar

- **UNKNOWN — `GATE-JOAO-CONTENCAO`**: autorização para `access-restricted/maintenance` da instância pública não foi dada nem negada explicitamente. Default: **fail-closed, manter como está, sem novos lockdowns sem autorização**.
- **UNKNOWN — rotação de credenciais**: existência/valor de `STRIPE_*`, `SMTP_*`, `TELEGRAM_*`, `EUIPO_*` em `.env` do host. Nada lido em valor. Decisão de rotação é OPEN e exige `GATE-CREDENTIALS`.
- **UNKNOWN — proveniência dos claims da landing**: a copy atualmente servida diverge do pacote `contents/` aprovado pela auditoria independente recente (ver STG-01 editorial). Não é papel desta missão aplicar a copy; é papel de STG-08 e STG-09. Esta auditoria confirma que **o que está público não coincide com o que foi aprovado**.
- **UNKNOWN — efeito operacional efetivo da schedule**: `inspect scheduled` devolveu empty no instante da inspeção, mas isso é compatível com beat entre batidas. Classificação: **probable "schedule ociosa neste instante"**, **confirmed "schedule carregada e pronta para a próxima batida"**.

## 4. Work packages para Forja/Fable (TDD)

> Nenhum item abaixo foi escrito em código. Todos descrevem failing tests, paths e critérios de aceitação. Implementação gated por João quando envolve credenciais, imagem ou acesso público.

### WP1 — `STG00-WP1-BPI-CONTAINMENT` (PRIORITÁRIO)

Objetivo: provar por teste que `source=inpi_bpi` nunca cria `app.deadlines` nem `app.alerts`, em qualquer ambiente que não esteja explicitamente habilitado por feature flag.

**Failing tests a criar (red-first):**

- `tests/stg00/test_bpi_source_deny_deadlines.py::test_bpi_publication_never_creates_deadline` — invoca `LifecycleEngine.calculate_opposition_deadline` para uma publicação cuja `trademark.source=="inpi_bpi"` e exige `Deadline` zero.
- `tests/stg00/test_bpi_source_deny_deadlines.py::test_calculate_deadlines_skips_bpi_trademarks` — chama `recalculate_all` numa fixture com trademarks `source="inpi_bpi"` e exige `app.deadlines` vazio.
- `tests/stg00/test_bpi_source_deny_ingestion.py::test_bpi_event_not_ingested_when_disabled` — `ingest_bpi_events([...])` em ambiente `BPI_ENABLED=False` devolve `BPIIngestSummary(created=0, queued_for_review=N, ...)` e nenhuma linha em `events.lifecycle_events` com `source="inpi_bpi"`.
- `tests/stg00/test_bpi_source_deny_alerts.py::test_alert_rule_deny_bpi_source` — `AlertRule` com `deny_sources=["inpi_bpi"]` não cria `Alert` mesmo com `LifecycleEvent` correspondente.
- `tests/stg00/test_bpi_beat_schedule_disabled.py::test_parse_bpi_not_in_beat_schedule_when_disabled` — em modo `BPI_ENABLED=False`, `celery_app.conf.beat_schedule` **não** contém a entrada `parse-bpi-daily`.
- `tests/stg00/test_bpi_calculate_deadlines_schedule_disabled.py::test_calculate_deadlines_runs_only_for_authorized_sources` — em ambiente não-BPI, o schedule `calculate-deadlines-hourly` filtra marcas por `source not in DENY_SOURCES`.
- `tests/stg00/test_bpi_kill_switch_default_off.py::test_default_setting_disables_bpi` — `Settings()` sem override → `BPI_ENABLED=False`, `BPI_SCHEDULE_ENABLED=False`, `BPI_INGESTION_ALLOWED=False`.
- `tests/stg00/test_bpi_dispatch_deny.py::test_send_alerts_dispatcher_drops_bpi_events` — `send_alerts.dispatch_pending_alerts` não envia `Alert` cuja origem raiz tem `source="inpi_bpi"`.

**Paths a tocar (apenas referência, sem alteração nesta missão):**

- `app/core/config.py` — adicionar `BPI_ENABLED`, `BPI_SCHEDULE_ENABLED`, `BPI_INGESTION_ALLOWED`, `BPI_DENY_SOURCES` (default `["inpi_bpi"]`).
- `app/tasks/__init__.py` — gate em `beat_schedule` (remover/condicionar entradas BPI).
- `app/tasks/parse_bpi.py` — early-return quando `BPI_ENABLED=False`.
- `app/tasks/calculate_deadlines.py` — filtro de trademarks com `source in DENY_SOURCES`.
- `app/services/ingestion.py` — `ingest_bpi_events` aceita `enabled: bool` (default False em runtime).
- `app/services/alerts.py` e `app/tasks/send_alerts.py` — denylist de sources.
- `app/models/source.py` (se necessário) — coluna `enabled: bool` em `core.sources` (idempotente com migration existente se já existir).

**Acceptance:**

- 8 failing tests acima passam (verde).
- `celery -A app.tasks inspect scheduled` mostra schedule BPI ausente em `BPI_ENABLED=False` (gate: alvo STG-11 staging).
- `pytest tests/stg00` retorna 0 falhas, 0 skips inesperados.
- `grep -RE "BPI_ENABLED|BPI_SCHEDULE_ENABLED" app/` lista os 4+ locais acima; nenhum match em produção BPI.

**Stop conditions (gate duro):**

- Qualquer teste mostra evento BPI a criar `Deadline` ou `Alert`.
- Schedule BPI ativa em runtime quando `BPI_ENABLED=False`.
- Mock apresentado como real.
- Imagem com secret é promovida sem rotação.

**Rollback:** manter `BPI_ENABLED=True` no config atual até ao gate João; rollback consiste em reverter as 4+ flags e remover o deny. Não apagar dados existentes.

**Gate João:** obrigatório antes de qualquer deploy da alteração — afeta `app/tasks/__init__.py`, schedule efetiva e BD.

### WP2 — `STG00-WP2-MOCK-CHECKOUT`

Objetivo: tornar impossível apresentar checkout/upgrade ou dados mock como reais em ambiente público.

**Failing tests:**

- `tests/stg00/test_public_billing_plans_disabled_when_free_beta.py::test_plans_endpoint_returns_disabled_or_410_in_public_dev` — exige 410 Gone ou payload com `enabled=false` quando `BILLING_MODE=free_beta`.
- `tests/stg00/test_checkout_returns_disabled_for_public.py::test_checkout_404_or_410_when_disabled` — `POST /billing/checkout` devolve 410 quando `BILLING_MODE=free_beta`.
- `tests/stg00/test_trademarks_mock_labeled.py::test_trademark_response_includes_source_label_when_mock` — resposta mock inclui `"source_label": "mock"` ou equivalente.
- `tests/stg00/test_trademarks_no_mock_when_no_real.py::test_empty_query_returns_unavailable_instead_of_mock` — pesquisa sem fonte real devolve `{ "available": false, "reason": "no_real_source" }`.
- `tests/stg00/test_landing_no_prohibited_claims.py` — snapshot do HTML servido não contém "monitorização", "entregue", "24/7", "tempo real", "oficial", "cobrado", "pago", "renovação automática" sem evidence.

**Acceptance:** cinco testes verdes; landing anti-claims aplicada; `BillingStatus` correto em `/app#/settings`.

**Gate João:** decisão `OD-15` (free beta vs Stripe) e revisão do anti-claim em STG-08/09.

### WP3 — `STG00-WP3-IMAGE-SECRETS`

Objetivo: impedir `.env`/secrets na imagem final e criar rotina de rotação sem imprimir valores.

**Failing tests:**

- `tests/stg00/test_dockerignore_excludes_env.py::test_env_not_in_image_context` — `.dockerignore` presente e contém `.env`, `.venv`, `__pycache__`, `.git`, `tests/`, `data/`, `docs/`.
- `tests/stg00/test_image_has_no_env.py::test_release_image_has_no_env` — comando executado contra imagem de release: `docker run --rm $IMG sh -c 'test ! -e /app/.env && test ! -e /.env'` retorna 0.
- `tests/stg00/test_image_no_secrets_in_env.py::test_release_image_does_not_print_known_secrets` — `docker run --rm $IMG env | grep -E "STRIPE_SECRET_KEY|SECRET_KEY|TELEGRAM_BOT_TOKEN|SMTP_PASSWORD"` ⇒ 0 linhas.
- `tests/stg00/test_secret_rotation_record.py::test_rotation_record_excludes_values` — record de rotação arquiva presença e timestamp, nunca valor.

**Acceptance:** quatro testes verdes; build limpo (`docker build --no-cache`); `docker save | grep -c "STRIPE_SECRET_KEY"` ⇒ 0.

**Gate João:** autorização de rotação e downtime se aplicável.

### WP4 — `STG00-WP4-BASELINE-DB`

Objetivo: produzir dump/manifest read-only da BD atual antes de qualquer correção futura, e snapshot de git tree para auditoria externa.

**Failing tests (TDD-style para o próprio processo):**

- `tests/stg00/test_baseline_dump_created.py::test_dump_exists_and_checksummed` — `data/baseline/<timestamp>.sql.gz` existe e tem `sha256sum` registado em `data/baseline/MANIFEST.sha256`.
- `tests/stg00/test_baseline_restore_drill.py::test_dump_restores_to_clean_db` — restore em DB vazia devolve contagens idênticas.
- `tests/stg00/test_release_inventory.py::test_release_inventory_excludes_secrets` — `docs/execution/RELEASE_INVENTORY.md` lista imagens, contentores, schedules e env vars por nome, sem valores.

**Acceptance:** três testes verdes; baseline restaurável em DB vazia; MANIFEST anexado a este diretório.

**Gate João:** autorização para criar o dump (ação sobre BD em runtime); autorização para armazenar artefacto em path aprovado.

## 5. Veredicto

`BLOCKED`.

Razões:

1. **WP1 ainda não tem failing test**; nenhum dos 8 testes propostos existe em `tests/stg00/`. Forja/Fable não pode arrancar TDD sem isso.
2. **Kill switch / default-off inexistentes**; defaults inseguros estão em runtime.
3. **Imagem atual contém `.env`** e expõe segredos via env vars de contentor; rotação é `GATE-CREDENTIALS` (João).
4. **Instância pública serve a mesma imagem que a local**, sem Access policy, sem robots, sem environment banner; decisão `OD-04` e gate `GATE-JOAO-CONTENCAO` continuam OPEN.
5. **Pipeline BPI tecnicamente capaz**: schedule carregada, ingestion cria eventos, deadlines recalcula sem source filter, alerts/dispatch sem denylist observada. **Não** esperar por BD vazia como controlo.
6. **Mock e checkout alcançáveis**: `/api/v1/billing/plans` público, `/api/v1/trademarks` com fallback mock, `/api/v1/billing/checkout` reachable (auth wall existe mas não é bloqueio técnico ao mock).

Próximas ações ordenadas:

- João autoriza `STG00-WP3` (rotação de segredos) e contenção da URL pública (`GATE-JOAO-CONTENCAO`).
- Forja/Fable implementa `STG00-WP1` em worktree dedicada, com TDD e suíte verde; testes negativos primeiro; sem tocar `contents/**`.
- Max-2 acompanha execução e revê evidência (esta auditoria é o snapshot inicial; a revisão pós-execução entra no `EXECUTION_BOARD.md`).
- WP2, WP3 e WP4 podem correr em paralelo em worktrees distintas após `WP1` red.

## 6. Limitações e honestidade

- Não li valores de `.env`, tokens, segredos, headers Stripe-Signature, JWT ou PII. Presenças confirmadas via `test -e`/`env` truncado a 2 chars por chave.
- Não toquei código, config, testes, runtime, schedules, migrations, imagens, contentores, DNS, backup ou BD.
- Não fiz `git add`, `git commit`, `git push`, `docker build`, `docker pull`, `docker compose up/down/restart`, `celery …` com efeito mutável, `alembic`, `pg_dump`, `psql` write, `apt`, `pip install`, `npm`, nem nada que afete o estado dos contentores.
- O resultado de `celery inspect scheduled` foi "empty" no instante da inspeção; **isso não é prova de schedule desativada**. Schedule está carregada no worker/beat.
- Não há ainda backup da BD. Esta auditoria não produziu dump por respeito ao scope read-only. STG-00 recomenda-o como tarefa 8 do plano.
- `inspect scheduled` "empty" também pode indicar que o beat ainda não chegou à primeira batida depois do restart recente; validar com beat logs antes de qualquer ação.
- A landing serve claims que não coincidem com o pacote `contents/` aprovado. Esta missão não aplicou a copy. Correcção é papel de STG-08 com gates de STG-09.
- Não analisei `tests/e2e` (apenas confirmado diretório), `tests/unit/test_bpi_parser.py` (parser usa fixture sintética; não prova parser real), `app/services/billing.py` mocks, nem fluxos email/Telegram.

## 7. Hashes before/after e confirmação de outputs autorizados

- Hash before (snapshot de `docs/execution/` no início desta missão, calculado em 2026-07-24T20:47Z):

```
784a587a22d54f6498154a2107ca581da6a770bfd514d6777d0be638d2b15d1a  docs/execution/STG-01_EDITORIAL_PRODUCT_SIGNOFF.md
```

- Hash after (estado canónico do ficheiro no disco, calculado em 2026-07-24T20:55Z, fim desta missão). Este é o hash que deve ser comparado com `sha256sum docs/execution/STG-00_CONTAINMENT_AUDIT.md` para verificação independente:

```
b790589764f6786fd115d13e7bbf629ee26b8453394a817dd62390d2cb9903c1  docs/execution/STG-00_CONTAINMENT_AUDIT.md
```

- Hash after do board (estado canónico no disco):

```
ee8e89c4bda6860c807cbdabbc4859af81694ed78bc1a4ca434478dcc11ae2c2  docs/execution/EXECUTION_BOARD.md
```

- Diff vs estado pré-missão: apenas dois paths novos (`docs/execution/STG-00_CONTAINMENT_AUDIT.md`, `docs/execution/EXECUTION_BOARD.md`). Nenhum ficheiro pré-existente foi tocado.
- Apenas dois ficheiros novos em `docs/execution/`:
  1. `docs/execution/STG-00_CONTAINMENT_AUDIT.md` (este).
  2. `docs/execution/EXECUTION_BOARD.md`.
- Nenhum outro path foi criado, alterado ou removido.

## 8. Anexos

### A.1 Comandos read-only corridos (resumo)

```
git rev-parse HEAD
git status
git log --oneline -30
docker ps -a
docker images
docker compose exec -T app sh -c 'test -e /app/.env && echo HAS_ENV; sha256sum /app/.env'
docker compose exec -T app env | grep -iE "secret|key|token|pass|mail" | sed -E "s/(=.{0,2}).{1,}/\1***/"
docker compose exec -T db psql -U markee -d markee -c "<counts>"
docker compose exec -T beat celery -A app.tasks inspect scheduled
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
curl -s http://localhost:8000/api/v1/health
curl -s -X POST http://localhost:8000/api/v1/auth/register -d '{"email":"smoke@max2.local","password":"x","full_name":"x"}'
curl -s http://localhost:8000/api/v1/billing/plans
curl -s -X POST http://localhost:8000/api/v1/billing/checkout -d '{"plan":"individual"}'
curl -s -o /dev/null -w "%{http_code}" https://markee.batata.cc/ https://markee.batata.cc/api/v1/health
sudo cat /etc/cloudflared/config.yml
grep -nE "kill[_-]?switch|BPI_ENABLED|BPI_DISABLED|allow_bpi|enable_bpi|bpi_enabled|public_dev|MAINTENANCE" app/ config/
grep -n "inpi_bpi" -ri app/ config/
sha256sum contents/**/*
```

Nenhum dos comandos tem efeito mutável.

### A.2 Notas de classificação

- **CONFIRMED**: leitura direta com caminho, linha ou hash.
- **PROBABLE**: cadeia de inferência com pontos intermédios confirmados, mas sem prova integral de runtime.
- **UNKNOWN**: peça não observada ou bloqueada por gates.
- **ABSENT**: procurado e não encontrado.
- **PUBLIC-DEV**: instância pública observada; sem identidade de staging/prod.
