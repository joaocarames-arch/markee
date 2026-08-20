# Backlog — markee

> Last updated: 2026-07-24
> Estado reconciliado contra o repositório real. `[x]` significa que há código e testes a cobrir a capacidade; itens parciais ficam abertos com evidência e nota.

---

## Evidência usada

- Estrutura real: `app/`, `app/models/`, `app/services/`, `app/api/`, `app/tasks/`, `tests/`, `config/`, `docs/`, `frontend/`.
- Migrações: `alembic/versions/001_initial_migration.py`, `alembic/versions/002_data_infrastructure.py`.
- Testes atuais: `tests/unit/test_lifecycle.py`, `tests/unit/test_similarity.py`, `tests/unit/test_bpi_parser.py`, `tests/unit/test_ingestion.py`, `tests/unit/test_confidence.py`, `tests/unit/test_prospection.py`, `tests/integration/test_api.py`, `tests/integration/test_schemas.py`, `tests/integration/test_watchlists_api.py`.
- Suite observada antes da implementação desta missão: `138 passed, 2 skipped, 1 warning`.

---

## P0 — Fundação

- [x] **P0-01** Estrutura do projeto criada. Paths: `app/`, `tests/`, `config/`, `docs/`, `frontend/`.
- [x] **P0-02** `docker-compose.yml` com db, redis, app, worker e beat. Nota: não foi alterado nem executado nesta missão.
- [x] **P0-03** `Dockerfile` para app FastAPI.
- [x] **P0-04** Dependências em `pyproject.toml`.
- [x] **P0-05** Alembic configurado com migrações `001` e `002`; cobertura em `tests/integration/test_schemas.py`.
- [x] **P0-06** Settings via pydantic-settings em `app/core/config.py`.
- [x] **P0-07** Async database/session dependency em `app/core/database.py` e `app/models/database.py`.
- [x] **P0-08** JWT e bcrypt em `app/core/security.py`; usado por `app/api/auth.py`.
- [x] **P0-09** Modelos SQLAlchemy para entidades principais em `app/models/`; cobertura metadata em `tests/integration/test_schemas.py`.
- [ ] **P0-10** Schemas Pydantic v2 para todas as entidades. Parcial: response/request models existem embutidos em routers (`app/api/*.py`) e helpers em `app/api/common.py`, mas não há camada completa dedicada `app/schemas/` para todas as entidades.

## P1 — Autenticação e Utilizadores

- [x] **P1-01** `POST /api/v1/auth/register` implementado em `app/api/auth.py`; testes em `tests/integration/test_api.py`.
- [x] **P1-02** `POST /api/v1/auth/login` implementado; testes de sucesso, credenciais inválidas e utilizador inativo em `tests/integration/test_api.py`.
- [x] **P1-03** `GET /api/v1/auth/me` implementado em `app/api/auth.py`; testes dedicados em `tests/integration/test_api.py`.
- [x] **P1-04** Modelo `app/models/user.py`; schema público `UserOut` em `app/api/auth.py`.
- [x] **P1-05** Testes de autenticação completos para a API atual: registo, login, credenciais inválidas, utilizador inativo, `/me`, pedido sem token e token expirado em `tests/integration/test_api.py`.

## P1 — Fontes de Dados (EUIPO API)

- [x] **P1-06** Serviço EUIPO com OAuth2/mock mode em `app/services/euipo_service.py`.
- [x] **P1-07** Mock mode sem credenciais; coberto via fallback API e ingestão.
- [x] **P1-08** Pesquisa de marcas: `EUIPOService.search_trademarks`; cobertura em `tests/unit/test_ingestion.py` e `tests/integration/test_api.py`.
- [x] **P1-09** Detalhe de marca: `EUIPOService.get_trademark`; API usa fallback mock em `app/api/trademarks.py`.
- [x] **P1-10** Polling incremental: `EUIPOService.poll_incremental` / `app/tasks/poll_euipo.py`; cobertura em `tests/unit/test_ingestion.py`.
- [ ] **P1-11** Testes EUIPO completos. Parcial: mock mode e pipeline local cobertos; integração sandbox real não deve ser executada sem rede/credenciais.

## P1 — Fontes de Dados (INPI BPI)

- [x] **P1-12** Parser/download BPI em `app/services/bpi_parser.py`.
- [x] **P1-13** Extração de eventos; testes em `tests/unit/test_bpi_parser.py`.
- [x] **P1-14** Mapeamento de termos PT para `event_type`; testes em `tests/unit/test_bpi_parser.py`.
- [x] **P1-15** Testes do parser com texto/fixtures locais em `tests/unit/test_bpi_parser.py`. Nota: sem chamadas reais ao INPI.

## P1 — Ingestão e Normalização

- [x] **P1-16** Orquestrador de ingestão em `app/services/ingestion.py`.
- [x] **P1-17** Versionamento com `trademark_versions`; testes em `tests/unit/test_ingestion.py`.
- [x] **P1-18** Holders/representatives e relações N:M em modelos/migração `002`; cobertura metadata em `tests/integration/test_schemas.py`.
- [x] **P1-19** Testes de ingestão com fixtures locais em `tests/unit/test_ingestion.py`.

## P1 — Celery Tasks

- [x] **P1-20** `app/tasks/poll_euipo.py` existe.
- [x] **P1-21** `app/tasks/parse_bpi.py` existe.
- [x] **P1-22** `app/tasks/calculate_deadlines.py` existe.
- [x] **P1-23** `app/tasks/check_expiry.py` existe.
- [x] **P1-24** Configuração Celery em `app/tasks/__init__.py`. Nota: schedules/worker live não foram executados nesta missão.

## P2 — API de Marcas

- [x] **P2-01** `GET /api/v1/trademarks/` com paginação/filtros básicos em `app/api/trademarks.py`; cobertura em `tests/integration/test_api.py`.
- [x] **P2-02** `GET /api/v1/trademarks/{application_number}` implementado; cobertura em `tests/integration/test_api.py`.
- [ ] **P2-03** Pesquisa textual com `pg_trgm`. Parcial: modelo/migração têm índices trgm e serviço de similarity usa SQL; endpoint atual usa `ILIKE`, não pg_trgm explícito.
- [x] **P2-04** Testes dos endpoints de marcas em `tests/integration/test_api.py`.

## P2 — Similarity Engine

- [x] **P2-05** Similaridade textual, fonética e classes em `app/services/similarity_engine.py`.
- [x] **P2-06** Pesos configuráveis 50/30/20; testes em `tests/unit/test_similarity.py`.
- [x] **P2-07** Task de matching em `app/tasks/match_similar.py`.
- [x] **P2-08** Testes do engine em `tests/unit/test_similarity.py` e fonética PT em `tests/unit/test_pt_phonetics.py`.

## P2 — Watchlists

- [x] **P2-09** CRUD watchlists em `app/api/watchlists.py`.
- [x] **P2-10** CRUD items em `app/api/watchlists.py`.
- [x] **P2-11** Testes dos endpoints de watchlists. Cobertura dedicada em `tests/integration/test_watchlists_api.py`: autenticação obrigatória, listagem por utilizador, criação válida, validação suportada, CRUD sem cruzar utilizadores e items user-scoped.

## P2 — Alertas

- [x] **P2-12** `GET /api/v1/alerts/` em `app/api/alerts.py`.
- [x] **P2-13** Marcar lido/dismiss em `app/api/alerts.py`.
- [x] **P2-14** Criação de alertas em `app/services/alerts.py`.
- [x] **P2-15** Task de envio em `app/tasks/send_alerts.py`. Nota: sem emails/Telegram reais nesta missão.
- [ ] **P2-16** Testes de alertas. Pendente: falta cobertura dedicada de API/service.

## P2 — Prazos (Deadlines)

- [x] **P2-17** `GET /api/v1/deadlines/` em `app/api/deadlines.py`. Nota: sem teste dedicado de endpoint.
- [x] **P2-18** Lifecycle engine em `app/services/lifecycle_engine.py`; task em `app/tasks/calculate_deadlines.py`.
- [x] **P2-19** Testes de cálculo em `tests/unit/test_lifecycle.py`.

## P3 — Frontend (Landing Page)

- [x] **P3-01** Static frontend servido por FastAPI em `app/main.py`; assets em `frontend/`.
- [x] **P3-02** Landing page em `frontend/landing/index.html`.
- [x] **P3-03** Login/registo no dashboard frontend em `frontend/dashboard/app.js`.
- [x] **P3-04** Design system/glassmorphism em `frontend/landing/styles.css` e `frontend/dashboard/styles.css`.

## P3 — Frontend (Dashboard SPA)

- [x] **P3-05** Dashboard `/app` em `frontend/dashboard/`.
- [x] **P3-06** Pesquisa de marcas no dashboard.
- [x] **P3-07** Gestão de watchlists no dashboard.
- [x] **P3-08** Central de alertas no dashboard.
- [x] **P3-09** Calendário/lista de prazos no dashboard.
- [x] **P3-10** Definições/conta/subscrição no dashboard.

## P3 — Billing (Stripe)

- [x] **P3-11** Serviço Stripe/mock em `app/services/billing.py`.
- [x] **P3-12** `POST /api/v1/billing/checkout` em `app/api/billing.py`. Nota: mock quando sem Stripe.
- [x] **P3-13** `POST /api/v1/billing/webhook` em `app/api/billing.py`.
- [x] **P3-14** `GET /api/v1/billing/subscription` em `app/api/billing.py`.

## P3 — Prospecting

- [x] **P3-15** Serviço de prospeção em `app/services/prospection.py`; testes em `tests/unit/test_prospection.py`.
- [x] **P3-16** CRUD portfolios em `app/api/portfolios.py`.
- [x] **P3-17** Testes de prospecting em `tests/unit/test_prospection.py`.

---

## Próximos itens realmente pendentes, por prioridade

1. **P0-10** — Extrair/normalizar schemas Pydantic v2 para todas as entidades, se a equipa quiser uma camada `app/schemas/` explícita.
2. **P2-16** — Testes de alertas.
3. **P2-17** — Teste dedicado do endpoint de deadlines e revisão de ownership/user-scope.
4. **P2-03** — Usar `pg_trgm` explicitamente na pesquisa textual da API.

## Regras

- Cada tarefa deve continuar a ser um commit atómico.
- TDD estrito: teste falha primeiro pelo motivo esperado, depois código mínimo.
- Nada de deploy/push/chamadas reais a Stripe, email/Telegram, EUIPO ou INPI sem autorização explícita.
