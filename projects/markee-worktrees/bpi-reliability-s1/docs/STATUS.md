# STATUS — markee

> Last updated: 2026-07-24
> Base factual reconciliada contra o repositório real `/home/batata/projects/markee`.

---

## Estado atual

**Fase:** implementação funcional de MVP técnico, não apenas planeamento.

A documentação antiga dizia que a estrutura, modelos, serviços, API, frontend e testes estavam “por criar”. Isso estava desatualizado. O repositório já contém backend FastAPI, modelos SQLAlchemy async, migrações Alembic, serviços principais, tasks Celery, frontend vanilla e testes.

## Stack observada

- Backend: FastAPI, SQLAlchemy async, Pydantic v2.
- Base de dados: PostgreSQL com schemas `raw`, `core`, `events`, `app`; fallback de testes para SQLite quando PostgreSQL não está acessível.
- Migrações: `alembic/versions/001_initial_migration.py`, `alembic/versions/002_data_infrastructure.py`.
- Frontend: vanilla HTML/CSS/JS em `frontend/landing/` e `frontend/dashboard/`, servido por `app/main.py`.
- Tasks: Celery em `app/tasks/`.
- Dependências: `pyproject.toml`.

## Componentes implementados com evidência

| Componente | Estado | Evidência |
|---|---:|---|
| Estrutura do projeto | Feito | `app/`, `tests/`, `config/`, `docs/`, `frontend/` |
| Docker base | Feito | `docker-compose.yml`, `Dockerfile` |
| Config/database/security | Feito | `app/core/config.py`, `app/core/database.py`, `app/models/database.py`, `app/core/security.py` |
| Modelos SQLAlchemy | Feito | `app/models/*.py`, `tests/integration/test_schemas.py` |
| Migrações/schemas PG | Feito | Alembic `001`, `002`, `tests/integration/test_schemas.py` |
| Auth register/login/me | Feito | `app/api/auth.py`, `tests/integration/test_api.py` cobre register/login, inativo, `/me`, pedido sem token e token expirado |
| EUIPO mock/polling | Feito/parcial | `app/services/euipo_service.py`, `app/tasks/poll_euipo.py`, testes locais; sem sandbox real |
| BPI parser | Feito | `app/services/bpi_parser.py`, `tests/unit/test_bpi_parser.py` |
| Ingestão/versionamento | Feito | `app/services/ingestion.py`, `app/services/raw_responses.py`, `tests/unit/test_ingestion.py` |
| API de marcas | Feito/parcial | `app/api/trademarks.py`, `tests/integration/test_api.py`; pesquisa endpoint usa `ILIKE`, não `pg_trgm` explícito |
| Similarity engine | Feito | `app/services/similarity_engine.py`, `tests/unit/test_similarity.py`, `tests/unit/test_pt_phonetics.py` |
| Watchlists API | Feito | `app/api/watchlists.py`, `tests/integration/test_watchlists_api.py` cobre autenticação, user-scope, criação, validação e ownership de watchlists/items |
| Alertas | Feito/parcial | `app/api/alerts.py`, `app/services/alerts.py`, `app/tasks/send_alerts.py`; faltam testes dedicados |
| Deadlines/lifecycle | Feito/parcial | `app/services/lifecycle_engine.py`, `app/api/deadlines.py`, `app/tasks/calculate_deadlines.py`, `tests/unit/test_lifecycle.py`; falta teste dedicado do endpoint |
| Billing | Feito/parcial | `app/services/billing.py`, `app/api/billing.py`; mock sem Stripe quando não configurado |
| Prospection | Feito | `app/services/prospection.py`, `tests/unit/test_prospection.py` |
| Frontend landing/dashboard | Feito/parcial | `frontend/landing/*`, `frontend/dashboard/*`; sem testes frontend dedicados |

## Lacunas prioritárias reais

1. `P0-10` — Schemas Pydantic v2 completos por entidade ainda estão dispersos nos routers; falta camada dedicada se esse continuar a ser o standard pretendido.
2. `P2-16` — Testes dedicados para alertas.
3. `P2-17` — Teste dedicado do endpoint de deadlines e revisão de user-scope/ownership.
4. `P2-03` — Pesquisa textual da API ainda não usa `pg_trgm` explicitamente.

## Alteração feita nesta missão

Item escolhido: completar a lacuna `P2-11` para endpoints de watchlists.

- Testes novos: `tests/integration/test_watchlists_api.py` com 6 testes dedicados.
- Código de produção: sem alteração; os comportamentos essenciais já estavam corretos em `app/api/watchlists.py` e `app/api/auth.py`.
- Contrato observado: `/api/v1/watchlists` requer bearer JWT; operações consultam `get_current_user`; watchlists e items são filtrados por ownership via `_get_owned_watchlist`; validação disponível vem dos modelos Pydantic/UUID de path.

## Verificação

Baseline declarada antes da alteração: `138 passed, 2 skipped, 1 warning`.

Verificação final desta missão antes do commit: `python -m pytest -q` devolveu `144 passed, 2 skipped, 1 warning in 26.75s`.

## Restrições respeitadas nesta missão

- Sem deploy.
- Sem push.
- Sem alterações a Docker em execução.
- Sem credenciais.
- Sem Stripe real.
- Sem emails/Telegram reais.
- Sem chamadas reais EUIPO/INPI.
