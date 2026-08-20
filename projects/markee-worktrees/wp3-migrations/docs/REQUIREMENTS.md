# REQUIREMENTS — markee

Data: 2026-07-24
Versão: 1.0
Autor: Max-2
Âmbito: requisitos canónicos baseados em código local, testes e investigação BPI recente.

## 1. Regra de status baseada em evidência

- IMPLEMENTED: código existente + teste local cobre comportamento essencial.
- PARTIAL: código existe, mas falta teste dedicado, integração real, UI, política de segurança/roles ou contrato completo.
- PLANNED: há decisão/documento/arquitetura, mas sem implementação suficiente.
- BLOCKED: não pode avançar corretamente sem decisão, schema, credencial, validação legal ou dados/fixtures.
- DEFERRED: conscientemente fora da fase atual.
- OPEN DECISION: produto ainda não decidiu.

Regra crítica: documentação, copy da landing e nomes de ficheiros não chegam para marcar IMPLEMENTED. Todos os IMPLEMENTED abaixo têm evidência em código/teste local.

## 2. Fontes auditadas

- `README.md`, `CLAUDE.md`, `BRAND_MANUAL.md`, `FEATURES_RESEARCH.md`.
- `docs/STATUS.md`, `docs/BACKLOG.md`.
- `docs/SCHEMA_DESIGN.md`, `docs/DATA_DICTIONARY.md`, `docs/SOURCES_INVENTORY.md`.
- ADRs: `docs/adr/0001-use-postgresql-schemas.md`, `0002-versioning-strategy.md`, `0003-inpi-bpi-strategy.md`.
- BPI: `docs/research/BPI_VS_EUIPO_GAPS.md`, `docs/research/BPI_AUTOMATED_INGESTION.md`, `docs/research/BPI_DATA_CONTRACT.md`, `config/bpi_event_taxonomy.yaml`.
- Código: `app/main.py`, `app/api/*.py`, `app/services/*.py`, `app/tasks/*.py`, `app/models/*.py`, `alembic/versions/*.py`.
- Frontend: `frontend/landing/*`, `frontend/dashboard/*`.
- Testes: `tests/integration/test_api.py`, `tests/integration/test_watchlists_api.py`, `tests/integration/test_schemas.py`, `tests/unit/test_similarity.py`, `test_pt_phonetics.py`, `test_lifecycle.py`, `test_bpi_parser.py`, `test_ingestion.py`, `test_confidence.py`, `test_prospection.py`.
- Infra: `docker-compose.yml`, `Dockerfile`, `pyproject.toml`.

Validação executada nesta missão:
- `python -m pytest -q` no ambiente global falhou por falta de `email_validator`.
- `.venv/bin/python -m pytest -q` passou: `144 passed, 2 skipped, 1 warning in 27.06s`.

## 3. Visão do produto

Markee é um SaaS de monitorização de marcas para Portugal e Europa, orientado a profissionais de propriedade industrial, advogados de marcas, departamentos legais e PME com carteiras de marcas. O produto deve:

1. Pesquisar marcas e normalizar dados de fontes oficiais/agregadas.
2. Monitorizar marcas/watchlists contra novos pedidos e eventos.
3. Gerar alertas de similaridade, prazos e eventos jurídicos relevantes.
4. Preservar provenance e auditabilidade das fontes.
5. Apoiar prospeção legítima para profissionais de PI, com minimização RGPD.

## 4. Problema

Profissionais de PI e equipas legais precisam de detetar rapidamente conflitos, publicações, recusas, caducidades e prazos acionáveis. EUIPO/TMview/API e BPI têm granularidades diferentes: o BPI é especialmente valioso para prova de publicação, texto legal, páginas/excertos e eventos nacionais PT; EUIPO/TMview é melhor candidato para snapshot bibliográfico e pesquisa/similaridade. O risco é misturar fontes sem provenance, assumir equivalência não provada ou prometer ingestão diária antes de existir pipeline operacional.

## 5. Scope / non-scope

Scope P0:
- Auth básica, dashboard, pesquisa, watchlists, alertas, prazos, detalhe mínimo de marca.
- Portal administrativo mínimo em `/app#/admin` para `is_superuser`/admin autorizado: monitorização operacional read-only de health, users/accounts, planos/subscrições/uso, fontes/freshness, importações/source runs, jobs/queues/falhas, qualidade/reconciliação, review/quarantine, audit/system events e gates BPI. Ações mutáveis só entram quando forem idempotentes, auditadas, confirmadas e cobertas por testes deny/allow.
- Similaridade textual/fonética/classes já existente.
- Provenance/versionamento nas camadas raw/core/events/app.
- BPI P0 investigado, mas com decisão independente NO-GO para implementação como está: discovery, arquivo raw PDF, extração, parsing por secção para eventos prioritários, normalização, reconciliação, confidence/quarantine só podem avançar após os gates BPI desta especificação.

Non-scope P0:
- OCR profundo para todos os PDFs.
- Extração de contactos/listas gerais de procuradores.
- Enriquecimento de pessoas singulares para prospeção.
- Stripe real sem credenciais/testes controlados.
- SSO/white-label/API pública Enterprise.
- Relatórios PDF complexos.
- Provar ausência total de campos no ecossistema EUIPO/TMview; a investigação só prova o observado nas fontes consultadas.

## 6. Personas/roles comprovadas

Confirmadas por documentação local e coerentes com código:
- Utilizador autenticado: gere conta, watchlists, alertas e prazos.
- Profissional de PI / agente / advogado de marcas: principal utilizador para vigilância, prospeção e relatórios.
- Departamento legal corporativo: monitoriza carteira e prazos.
- PME titular de marcas: uso simples de vigilância.

Parciais/planeadas:
- Admin/ops: persona P0 decidida para `is_superuser`/admin autorizado; há evidência parcial em `quality/metrics`, `review_queue`, `is_superuser`, `app.subscriptions` e `core.source_runs`, mas falta UI, RBAC efetivo no router admin, endpoints agregados e testes deny.
- Team/member: modelos existem, mas falta fluxo completo de equipa no UI.
- Cliente final em portfolio: API/modelos existem; falta UI dedicada.

## 7. Requisitos funcionais

| ID | Descrição | Prior. | Estado | Critérios de aceitação verificáveis | Dependências | Risco | Evidência local |
|---|---|---:|---|---|---|---|---|
| FR-LAND-001 | Landing pública deve comunicar proposta de valor, funcionalidades e preços sem afirmar como operacional o que é apenas planeado. | P1 | PARTIAL | `/` serve HTML; links para `/app`; copy revista para distinguir BPI planeado/operacional. | `frontend/landing/*`, brand manual | Claims enganosos sobre BPI diário | `app/main.py:108`, `frontend/landing/index.html`; sem testes |
| FR-AUTH-001 | Permitir registo por email/password. | P0 | IMPLEMENTED | `POST /api/v1/auth/register` cria user, rejeita email duplicado e não devolve hash. | DB app.users, password hashing | Segurança de senha mínima | `app/api/auth.py`, `tests/integration/test_api.py` |
| FR-AUTH-002 | Permitir login e emissão de JWT bearer. | P0 | IMPLEMENTED | Credenciais válidas devolvem `access_token`; inválidas 401; user inativo 403. | `SECRET_KEY`, bcrypt/JWT | Token leak/localStorage | `app/api/auth.py`, `tests/integration/test_api.py` |
| FR-AUTH-003 | Permitir consultar utilizador atual sem campos secretos. | P0 | IMPLEMENTED | `GET /auth/me` requer token; token ausente/expirado é rejeitado; resposta sem password/hash. | Auth dependency | Dados sensíveis em resposta | `tests/integration/test_api.py` |
| FR-DASH-001 | Dashboard deve resumir watchlists, itens, alertas e prazos do utilizador. | P0 | PARTIAL | `/app#/dashboard` carrega APIs e mostra loading/error/empty; testes frontend/e2e por criar. | Auth, watchlists, alerts, deadlines | Métricas podem parecer completas sem dados reais | `frontend/dashboard/app.js:566` |
| FR-SEARCH-001 | Pesquisar marcas por texto, jurisdição e classe. | P0 | PARTIAL | `GET /trademarks` aceita `q`, `jurisdiction`, `nice_class`, limit/offset; retorna lista. Usar `pg_trgm` explicitamente fica por fechar. | `core.trademarks`, EUIPO service/mock | Performance e relevância | `app/api/trademarks.py`, `tests/integration/test_api.py`; backlog P2-03 aberto |
| FR-MARK-001 | Ver detalhe de uma marca por application number. | P0 | PARTIAL | API `GET /trademarks/{application_number}` devolve detalhe ou fallback; UI dedicada deve existir no P0 alvo. | Core trademark, events, documents | Sem timeline/provenance visível | API/testes existem; route frontend ausente |
| FR-WATCH-001 | CRUD de watchlists por utilizador com ownership. | P0 | IMPLEMENTED | List/create/get/update/delete exigem JWT e não cruzam utilizadores. | Auth, `app.watchlists` | Escalada de acesso | `app/api/watchlists.py`, `tests/integration/test_watchlists_api.py` |
| FR-WATCH-002 | CRUD mínimo de itens de watchlist. | P0 | IMPLEMENTED | List/create/delete items exigem ownership; campos `mark_text`, classes e notas persistem. | Watchlists | Dados inválidos de classes | `tests/integration/test_watchlists_api.py` |
| FR-WATCH-003 | Matching automático entre novos pedidos e watchlists. | P0 | PARTIAL | Task/engine existem; deve haver teste end-to-end ingestão→match→alert. | Ingestão, similarity, alerts | Alertas falsos/ausentes | `app/services/similarity_engine.py`, `app/tasks/match_similar.py`, testes similarity; sem pipeline e2e |
| FR-ALERT-001 | Listar alertas do utilizador, com filtro unread. | P0 | PARTIAL | `GET /alerts` requer JWT e filtra por user/unread; falta teste dedicado. | Auth, `app.alerts` | Alertas de outro user | `app/api/alerts.py`, frontend; sem teste |
| FR-ALERT-002 | Marcar alerta como lido ou dispensado. | P0 | PARTIAL | `POST /alerts/{id}/read` e `/dismiss` alteram estado; falta teste dedicado ownership. | Auth, alerts | Ownership não provado por teste | `app/api/alerts.py` |
| FR-ALERT-003 | Enviar notificações email/Telegram quando configurado. | P1 | PARTIAL | Sem credenciais deve não enviar; com credenciais deve registar delivery. Testes reais não executados. | SMTP/Telegram secrets | Envio acidental/privacidade | `app/services/alerts.py`, `app/tasks/send_alerts.py`, `docker-compose.yml` envs |
| FR-DEADLINE-001 | Listar prazos próximos por utilizador. | P0 | PARTIAL | `GET /deadlines?upcoming_only=true` devolve prazos ordenados/filtrados; falta teste endpoint e user-scope. | `app.deadlines`, auth, lifecycle | Prazos errados causam dano legal | `app/api/deadlines.py`, `tests/unit/test_lifecycle.py` |
| FR-DEADLINE-002 | Calcular prazos de renovação/oposição/grace de forma verificável. | P0 | BLOCKED | Deadlines/alertas derivados de BPI ficam congelados por defeito; oposição PT exige uma única semântica temporal validada, regra versionada `draft|validated`, `enabled=false` até aprovação, aprovador/data/base jurídica registados. | Lifecycle events, regras legais, BPI-GATE-01/02/13 | Cálculo legal incorreto e alertas indevidos | Código atual diverge: ingestão `+2 meses civis` vs lifecycle `+60 dias`; auditoria BPI CRITICAL |
| FR-BPI-001 | Descobrir boletins BPI oficiais por HTML público e janelas de data. | P0 | BLOCKED | Guardar publication_date, listing_url, source_url; rate limit; dedupe por data+URL; paginação com estrutura esperada, limite máximo, deteção de loops, robots/ToS recheck, kill switch e orçamento por run. | BPI-GATE-15 | Mudança HTML/502, loops, custo/ban | Investigação concluída; sem código; auditoria exige guards adicionais |
| FR-BPI-002 | Arquivar PDFs BPI como raw imutável com SHA-256 e metadados HTTP. | P0 | BLOCKED | Migration `raw.bpi_bulletins`; hash obrigatório; unique/upsert transacional; `archive_version`, republicação/supersession e URLs alternativas; nunca sobrescrever PDF. | BPI-GATE-03/05, storage | Perda de prova, duplicados concorrentes | `raw.api_responses` existe mas não substitui PDF imutável; schema específico não existe |
| FR-BPI-003 | Extrair texto por página e métricas de layout/imagens. | P0 | BLOCKED | Migration `raw.bpi_page_extractions`; guardar page_text, page_number, bulletin_number, text hash, parser_version, FK para boletim e índices úteis. | FR-BPI-002, BPI-GATE-03 | OCR/extraction não auditável | Código atual não faz extração por página |
| FR-BPI-004 | Parser BPI P0 por secção para pedidos, concessões, recusas e caducidades por falta de pagamento. | P0 | BLOCKED | Eventos normalizados seguem taxonomia reconciliada; fixtures reais locais; sem regex global; recusa usa expressão required formal; ST.17/aliases como heurísticas com scope, corroboradores e confidence caps. | FR-BPI-001..003, BPI-GATE-06/07/11, fixtures BPI | Parser atual demasiado genérico | `app/services/bpi_parser.py` existe, mas testes são texto simulado; novo contrato não implementado |
| FR-BPI-005 | Normalizar eventos BPI para contrato `BpiMarkEventNormalized`. | P0 | BLOCKED | Campos required por event_type com recusa de eventos inválidos; exemplos JSON válidos; source enums/event types canónicos; field_confidence, raw_text_hash, dedupe_key, parser_version. | FR-BPI-004, BPI-GATE-04/06/08/09 | Dados incompletos em core/events | Contrato e YAML divergem em 11 campos; sem modelos/tabelas específicas |
| FR-BPI-006 | Reconciliar eventos BPI com marcas core sem fundir por nome isolado. | P0 | BLOCKED | Matching por `(jurisdiction, application_number)`/registration number e holders quando necessário; constraints adequadas; conflitos para review; nunca `scalar_one_or_none()` só por número. | core.trademarks, holders, BPI-GATE-14 | Match errado entre fontes/jurisdições | Auditoria encontrou mapping atual insuficiente |
| FR-BPI-007 | Confidence/quarantine para extrações incertas. | P0 | BLOCKED | Thresholds gap-free: `score >= 0.85`, `0.65 <= score < 0.85`, `score < 0.65`; quarantine BPI explícita; review/replay; não depender só de `app.review_queue` genérica. | BPI-GATE-04/10, review_queue, quality | Aceitar dados errados automaticamente | Runtime atual usa `REVIEW_THRESHOLD = 0.6`; sem fluxo BPI-specific |
| FR-BPI-008 | Excluir/minimizar contactos e listas gerais de procuradores no MVP. | P0 | BLOCKED | Parser ignora contactos gerais; UI/export/leads não expõem dados sensíveis sem política RGPD aprovada, base legal, retenção, auditoria, encriptação/supressão e custo total operacional. | BPI-GATE-16, NFR-GDPR-001, NFR-COST-001 | Violação RGPD/prospeção abusiva | Docs BPI; implementação inexistente |
| FR-LEAD-001 | Gerar oportunidades de prospeção baseadas em eventos/marcas. | P1 | PARTIAL | Serviço calcula oportunidades e testes unitários passam; UI e filtros RGPD completos por fazer. | Core marks/events, portfolios | Prospeção intrusiva | `app/services/prospection.py`, `tests/unit/test_prospection.py` |
| FR-LEAD-002 | Gerir portfolios/clientes e associar marcas. | P1 | PARTIAL | API CRUD existe; UI dedicada e testes de integração completos por fazer. | Auth/team/portfolio models | Ownership/equipa | `app/api/portfolios.py`, modelos portfolio |
| FR-BILLING-001 | Mostrar plano atual e catálogo de planos. | P1 | PARTIAL | Settings chama subscription/plans; mock/dev permitido; UI indica estado. | Billing service | Confusão plano real vs mock | `app/api/billing.py`, `frontend/dashboard/app.js:1186` |
| FR-BILLING-002 | Criar checkout Stripe. | P1 | PARTIAL | Com Stripe configurado cria sessão; sem Stripe usa mock; teste real não executado. | Stripe secrets | Cobrança acidental | `app/services/billing.py`, `app/api/billing.py` |
| FR-BILLING-003 | Processar webhooks Stripe. | P1 | PARTIAL | Verificar assinatura e atualizar subscrição; testes dedicados por criar. | Stripe webhook secret | Segurança financeira | `app/api/billing.py` |
| FR-ACCOUNT-001 | Permitir ver dados básicos de conta e terminar sessão. | P0 | PARTIAL | `/settings` mostra user; logout limpa token. Falta editar conta/password. | Auth | Conta sem self-service | `frontend/dashboard/app.js` |
| FR-ADMIN-001 | Portal administrativo mínimo em `/app#/admin` é requisito P0 explícito para monitorização operacional e operação segura. | P0 | PLANNED/BLOCKED | Só `is_superuser`/admin autorizado acede; utilizador normal recebe 403/redirect; testes deny obrigatórios; navegação inclui overview, users, subscriptions/usage, sources, imports, jobs, quality, review, audit e BPI gates. | `app.users.is_superuser`, auth, endpoints admin, UI | Operar plataforma às cegas; exposição indevida | `is_superuser` existe; `/quality/metrics` existe; sem UI/RBAC/testes deny |
| FR-ADMIN-002 | Overview admin mostra health API/DB/workers, freshness, falhas e contagens essenciais. | P0 | PLANNED | `/app#/admin` ou `/app#/admin/overview` mostra estado de API, DB, worker/beat/Redis quando suportado, última ingestão por fonte, falhas recentes, backlog review/quarantine e contagens raw/core/events/app; empty/error states explícitos. | `/health`, `/api/v1/health`, `/api/v1/quality/metrics`, `core.source_runs` | Incidentes invisíveis | Health e quality existem parcialmente; falta agregador admin |
| FR-ADMIN-003 | Users/accounts admin lista contas sem secrets. | P0 | PLANNED | Listagem paginada/filtrada mostra email/nome/empresa, ativo, `is_superuser`, plano/subscrição resumida e datas; nunca mostra password/hash/token; deny tests para não-admin. | `app.users`, `app.subscriptions`, RBAC | Exposição de credenciais/PII | Modelos existem; API admin ausente |
| FR-ADMIN-004 | Plans/subscriptions/usage admin monitoriza catálogo, plano por utilizador, status, limites/consumo e saúde checkout/webhook. | P0 | PLANNED | UI indica claramente mock/dev vs Stripe real; mostra planos, subscrição por user, `status`, `max_marks`, `max_users`, `max_clients`, consumo quando existir e health de checkout/webhook; não inventa MRR/receita sem dados reais. | `app.subscriptions`, `/billing/plans`, `/billing/checkout`, `/billing/webhook`, Stripe config | Decisões comerciais com dados falsos | Billing parcial/mock no código; Stripe real não exercido |
| FR-ADMIN-005 | Sources/data admin mostra registry, modo e freshness sem secrets. | P0 | PLANNED | Mostra fonte, enabled/mode quando existir, último sucesso, freshness, volumes raw/core/events/app e erro mais recente; secrets, tokens e headers sensíveis redigidos. | `core.sources`, `core.source_runs`, `raw.api_responses`, schemas raw/core/events/app | Fontes paradas ou dados obsoletos | Modelos/source_runs existem; UI/API admin ausentes |
| FR-ADMIN-006 | Imports/source runs admin lista execuções e progresso. | P0 | PLANNED | Mostra run status, source, janela, progresso/contagens, duração, erros, parser/version quando disponível e drill-down para raw/reconciliation; retry/replay só quando idempotente, auditado e com confirmação. | `core.source_runs`, ingestion service, tasks | Reprocessamento destrutivo/duplicados | `source_runs` e ingestion existem; ações admin ausentes |
| FR-ADMIN-007 | Jobs/queues admin monitoriza Celery/Redis schedules e falhas. | P0 | PLANNED/BLOCKED | Mostra queued/running/failed/dead-letter, heartbeat/last run onde suportado; cancel/retry só com idempotência, auditoria e confirmação. | Celery, Redis, API job/queue | Jobs presos sem visibilidade; cancel inseguro | Celery tasks existem; não há API job/queue segura |
| FR-ADMIN-008 | Quality admin mostra completeness, confidence, provenance, duplicates/conflicts e reconciliação. | P0 | PLANNED | Métricas por fonte/run/campo; accepted/review/quarantine; links para raw/reconciliation; sem renderizar raw payload perigoso como HTML. | `/quality/metrics`, quality service, raw/core/events/app | Aceitar dados errados | Endpoint quality existe; drill-down/UI ausentes |
| FR-ADMIN-009 | Review/quarantine admin disponibiliza fila mínima e detalhe redigido. | P0 | PLANNED/BLOCKED | Fila mostra item, source/run, confidence, motivo e payload redigido; decisões accept/reject/repair/replay só após schema/policies, auditoria append-only e confirmação. | `app.review_queue`, policy/audit | Decisões não rastreáveis; PII exposta | Modelo review_queue existe; API/UI/actions ausentes |
| FR-ADMIN-010 | Audit/system events admin é append-only e redigido. | P0 | PLANNED/BLOCKED | Regista e lista alterações admin, retries/replays/cancel, roles, planos e config com actor/timestamp/correlation/result; não permite edição/apagamento via UI. | Modelo/API audit necessários | Sem cadeia de responsabilidade | Modelo audit específico não confirmado |
| FR-ADMIN-011 | BPI admin mostra pipeline/gates e mantém NO-GO enquanto blockers não forem resolvidos. | P0 | BLOCKED | Mostra estado discovery/archive/extraction/parsing/reconciliation, boletins/datas/pages/event counts, drift/quarantine e gate jurídico de deadlines; pipeline/actions disabled até BPI-GATE-01..16. | FR-BPI-001..008, BPI-GATE-01..16 | Ativar BPI incompleto ou deadlines errados | Docs/gates existem; tabelas/pipeline BPI não implementados |
| FR-REPORT-001 | Relatórios/export para clientes. | P2 | OPEN DECISION | Decidir formato CSV/PDF/API, permissões e dados pessoais; sem implementação atual. | Leads/alerts/deadlines | Exportar dados sensíveis | Apenas `is_exported` em oportunidades; sem rota/export |

## 8. Requisitos não funcionais

| ID | Descrição | Prior. | Estado | Critérios de aceitação verificáveis | Dependências | Risco | Evidência local |
|---|---|---:|---|---|---|---|---|
| NFR-QUALITY-001 | Provenance e qualidade devem acompanhar dados ingeridos. | P0 | PARTIAL | raw/core/events/app separados; confidence/source fields; BPI exige provenance completo. | ADRs, migrations | Dados sem audit trail | `alembic/versions/002_data_infrastructure.py`, `tests/integration/test_schemas.py` |
| NFR-SEC-001 | Segurança básica: JWT, hashing, não devolver segredos. | P0 | IMPLEMENTED | Testes de auth passam; secrets por env; respostas sem password/hash; qualquer UI/admin futura deve manter CSRF/auth adequado, rate limit, least privilege, confirmação para mutações e nunca renderizar raw payload perigoso como HTML. | Config/security | Token em localStorage e endpoints públicos por decidir | `app/core/security.py`, `tests/integration/test_api.py` |
| NFR-GDPR-001 | Minimização RGPD para titulares, contactos, prospeção e BPI. | P0 | PLANNED | Não extrair contactos gerais; mascarar dados judiciais sensíveis; base legal documentada. | Política produto/legal | Dados pessoais em UI/export | Docs BPI; implementação parcial em modelos genéricos |
| NFR-PERF-001 | Pesquisa e matching devem ser performantes em volume. | P1 | PARTIAL | Índice `pg_trgm`; endpoint search deve usar estratégia adequada; testes carga por criar. | PostgreSQL, pg_trgm | `ILIKE` degrada | migration cria índice; backlog P2-03 aberto |
| NFR-A11Y-001 | UI acessível, responsiva e navegável por teclado. | P1 | PARTIAL | HTML semântico, ARIA nos componentes críticos; auditoria Lighthouse/axe por fazer. | Frontend | Exclusão/utilização fraca | `frontend/*` tem ARIA/skip link; sem testes |
| NFR-OBS-001 | Observabilidade mínima e health checks. | P0 | PARTIAL | `/health`, `/api/v1/health`, docker healthchecks; logs estruturados/metrics por completar. | Docker, app | Incidentes invisíveis | `app/main.py`, `app/api/health.py`, `docker-compose.yml` |
| NFR-BACKUP-001 | Backups/DR para DB e raw BPI. | P0 | PLANNED | Política de backup, restore testado, raw PDF imutável. | Storage, DB | Perda de prova/dados | Não implementado; BPI docs recomendam retenção |
| NFR-IDEMP-001 | Ingestão idempotente e replayável. | P0 | PARTIAL | Versionamento append-only, raw hashes, source_runs; BPI dedupe_key por implementar. | raw/core/events | Duplicados ou sobrescrita | `app/services/ingestion.py`, `tests/unit/test_ingestion.py`, BPI contract |
| NFR-COST-001 | Custos controlados e sem chamadas externas involuntárias. | P0 | PARTIAL | Mock mode sem credenciais; avisar antes de serviços pagos/rede real; rate limits BPI. | Config | Custo/ban acidental | EUIPO/Stripe mock paths; docker envs vazios |
| NFR-TEST-001 | Testes automatizados como gate. | P0 | IMPLEMENTED | `.venv/bin/python -m pytest -q` passa; novos requisitos devem trazer teste. | venv/dev deps | Ambiente errado falha | 144 passed, 2 skipped no venv; global falhou por dependência |
| NFR-LEGAL-001 | Termos, privacidade e disclaimers jurídicos antes de produção pública. | P0 | PLANNED | Páginas legais existem e são aprovadas; disclaimers para prazos/alertas. | Decisão legal | Responsabilidade profissional | Páginas não existem |
| NFR-ADMIN-SEC-001 | Portal admin deve aplicar RBAC, redaction, least privilege, rate limit e auditoria em todas as rotas. | P0 | PLANNED/BLOCKED | Testes provam deny para anónimo/user normal e allow para superuser; respostas omitem password/hash/token/secrets/headers sensíveis/PII desnecessária; mutações exigem confirmação e audit. | FR-ADMIN-001..011, auth, audit | Exposição operacional/financeira/dados pessoais | `is_superuser` existe; controlos admin ainda não implementados |
| NFR-ADMIN-TEST-001 | Portal admin exige testes integração/e2e e observabilidade mínima antes de fechar P0. | P0 | PLANNED | Cobrir acesso, user-scope, redaction, estados vazio/erro, paginação/filtros, performance básica de listagens e logs/metrics/health. | Test suite, endpoints admin | Admin frágil em produção | Testes atuais não cobrem admin |

## 9. Matriz de rastreabilidade

| Requisito | Sitemap route/API | Schema/tabela | Teste/evidência |
|---|---|---|---|
| FR-LAND-001 | `/`, anchors landing | n/a | `frontend/landing/index.html`, `app/main.py` |
| FR-AUTH-001 | `/app#/login`, `POST /auth/register` | `app.users` | `tests/integration/test_api.py` |
| FR-AUTH-002 | `/app#/login`, `POST /auth/login` | `app.users` | `tests/integration/test_api.py` |
| FR-AUTH-003 | `/app`, `GET /auth/me` | `app.users` | `tests/integration/test_api.py` |
| FR-DASH-001 | `/app#/dashboard` | `app.watchlists`, `app.alerts`, `app.deadlines` | `frontend/dashboard/app.js` |
| FR-SEARCH-001 | `/app#/search`, `GET /trademarks` | `core.trademarks` | `tests/integration/test_api.py` |
| FR-MARK-001 | planned `/app#/marks/{application_number}`, `GET /trademarks/{application_number}` | `core.trademarks`, `events.lifecycle_events`, `core.documents` | API tests; UI ausente |
| FR-WATCH-001 | `/app#/watchlists`, `/watchlists*` | `app.watchlists` | `tests/integration/test_watchlists_api.py` |
| FR-WATCH-002 | `/app#/watchlists`, `/watchlists/{id}/items*` | `app.watchlist_items` | `tests/integration/test_watchlists_api.py` |
| FR-WATCH-003 | task matching, alerts | `app.watchlists`, `core.trademarks`, `app.alerts` | `tests/unit/test_similarity.py`, task exists |
| FR-ALERT-001 | `/app#/alerts`, `GET /alerts` | `app.alerts` | Código sem teste dedicado |
| FR-ALERT-002 | `/app#/alerts`, `/alerts/{id}/read|dismiss` | `app.alerts` | Código sem teste dedicado |
| FR-ALERT-003 | task send_alerts | `app.alert_deliveries` | Código sem teste real de canal |
| FR-DEADLINE-001 | `/app#/deadlines`, `GET /deadlines` | `app.deadlines` | endpoint sem teste; lifecycle unit |
| FR-DEADLINE-002 | deadlines/lifecycle | `events.lifecycle_events`, `app.deadlines` | `tests/unit/test_lifecycle.py` |
| FR-BPI-001 | admin/ops planned | planned raw BPI | BPI automated ingestion doc |
| FR-BPI-002 | admin/ops planned | planned `BpiBulletinRaw`; current `raw.api_responses` insufficient for PDF | BPI data contract |
| FR-BPI-003 | admin/ops planned | planned `BpiPageExtraction` | BPI data contract |
| FR-BPI-004 | task `parse_bpi` | planned normalized events | current `test_bpi_parser.py` only simulated; BLOCKED |
| FR-BPI-005 | events/deadlines | planned `BpiMarkEventNormalized`, `events.lifecycle_events` | BPI data contract |
| FR-BPI-006 | reconciliation | `core.trademarks`, holders/reps | BPI contract; no code |
| FR-BPI-007 | admin review | `app.review_queue` | model/migration exists; no BPI flow |
| FR-BPI-008 | parser/UI | n/a/policy | BPI docs; no code |
| FR-LEAD-001 | planned `/app#/leads`, `/portfolios/{id}/opportunities` | `app.prospection_opportunities` | `tests/unit/test_prospection.py` |
| FR-LEAD-002 | planned `/app#/portfolios`, `/portfolios*` | `app.client_portfolios` | API exists; tests partial/absent |
| FR-BILLING-001 | `/app#/settings`, `/billing/subscription`, `/billing/plans` | `app.subscriptions` | Código; sem Stripe real |
| FR-BILLING-002 | `/app#/settings`, `/billing/checkout` | `app.subscriptions` | Código; sem chamada real |
| FR-BILLING-003 | `/billing/webhook` | `app.subscriptions` | Código; sem teste dedicado |
| FR-ACCOUNT-001 | `/app#/settings` | `app.users` | Frontend/auth code |
| FR-ADMIN-001 | `/app#/admin`, planned admin API, `/quality/metrics` | `app.users`, `app.review_queue`, raw/core/events/app | Testes deny/allow admin obrigatórios; código parcial sem UI/role |
| FR-ADMIN-002 | `/app#/admin/overview`, `/health`, `/api/v1/health`, `/quality/metrics` | health/API, `core.source_runs`, `app.review_queue` | Testes integração/e2e empty/error/health por criar |
| FR-ADMIN-003 | `/app#/admin/users`, planned admin users API | `app.users`, `app.subscriptions` | Testes deny, redaction password/hash/token e paginação por criar |
| FR-ADMIN-004 | `/app#/admin/subscriptions`, `/billing/plans`, `/billing/*` admin view | `app.subscriptions` | Testes mock vs Stripe real, webhook health e limites/consumo por criar |
| FR-ADMIN-005 | `/app#/admin/sources`, planned source registry API | `core.sources`, `core.source_runs`, `raw.api_responses`, raw/core/events/app | Testes freshness/volumes/redaction por criar |
| FR-ADMIN-006 | `/app#/admin/imports`, planned source runs API | `core.source_runs`, `raw.api_responses`, reconciliation planned | Testes run status/filtros/drill-down; retry/replay blocked até idempotência/audit |
| FR-ADMIN-007 | `/app#/admin/jobs`, planned jobs API | Celery/Redis metadata; dead-letter se existir | Testes heartbeat/queued/running/failed por criar; API ausente |
| FR-ADMIN-008 | `/app#/admin/quality`, `/quality/metrics` | raw/core/events/app, `app.review_queue` | Testes completeness/confidence/provenance/redaction por criar |
| FR-ADMIN-009 | `/app#/admin/review`, planned review API | `app.review_queue`, audit planned | Testes fila/detalhe redigido/decisão auditada por criar; mutações blocked |
| FR-ADMIN-010 | `/app#/admin/audit`, planned audit API | audit table/API necessária | Testes append-only/redaction por criar; modelo ausente |
| FR-ADMIN-011 | `/app#/admin/bpi`, planned BPI gates/pipeline API | planned `raw.bpi_bulletins`, `raw.bpi_page_extractions`, BPI staging/reconciliation/quarantine | Testes gates BPI e legal-deadline gate por criar; NO-GO mantém-se |
| FR-REPORT-001 | planned `/app#/reports` | unknown | OPEN DECISION |
| NFR-QUALITY-001 | all data/admin | raw/core/events/app schemas | migration + schema tests |
| NFR-SEC-001 | auth/all private routes | `app.users` | auth tests |
| NFR-GDPR-001 | legal/prospeção/BPI | holders/reps/opportunities | docs only |
| NFR-PERF-001 | search/matching | `core.trademarks` indexes | migrations; no perf tests |
| NFR-A11Y-001 | frontend | n/a | manual code inspection only |
| NFR-OBS-001 | `/health`, `/quality/metrics` | n/a/raw | tests health, code quality |
| NFR-BACKUP-001 | ops | DB/raw storage | not implemented |
| NFR-IDEMP-001 | ingestion/BPI | raw/core/events | ingestion tests; BPI planned |
| NFR-COST-001 | external integrations | n/a | mock modes/config |
| NFR-TEST-001 | CI/local | n/a | pytest output |
| NFR-LEGAL-001 | legal pages | n/a | missing |
| NFR-ADMIN-SEC-001 | `/app#/admin*`, admin API | `app.users`, audit planned | deny/allow/redaction/security tests obrigatórios |
| NFR-ADMIN-TEST-001 | `/app#/admin*`, admin API | all admin-visible tables/APIs | integração/e2e: acesso, scope, empty/error, paginação/filtros, perf básica |

## 10. Secção BPI atualizada — decisão NO-GO

### Decisão independente

Decisão: NO-GO para implementar BPI P0 como está.

Confirmado:
- A investigação BPI está concluída ao nível documental para uma taxonomia operacional inicial: `config/bpi_event_taxonomy.yaml` tem 20 `event_type`, todos únicos, com distribuição atual 4 P0 / 13 P1 / 3 P2.
- Os 4 P0 continuam a ser a fatia correta para análise de produto: `application_published`, `grant_published`, `refusal_published`, `lapse_fee_nonpayment`.
- O BPI tem valor de prova oficial PT: número/data do boletim, página, secção e excerto.
- Existem artefactos de investigação (`BPI_VS_EUIPO_GAPS.md`, `BPI_AUTOMATED_INGESTION.md`, `BPI_DATA_CONTRACT.md`) e parser legacy (`app/services/bpi_parser.py`).

Confirmado como não implementado:
- Não existem migrations/tabelas `raw.bpi_bulletins` nem `raw.bpi_page_extractions`.
- Não existe staging/versionamento específico de eventos BPI antes de `events.lifecycle_events`.
- Não existem `dedupe_key` único, `parser_version`, `is_current_parse`, `supersedes_event_id`, tabela de conflitos/reconciliação, quarantine BPI explícita, constraints/índices/FKs BPI nem unique/upsert transacional.
- `events.lifecycle_events.trademark_id` é NOT NULL, pelo que eventos BPI não reconciliados não podem entrar diretamente no modelo real sem perda de contrato ou associação errada.
- Deadlines BPI/oposição PT não têm validação jurídica/versionamento/feature flag e há conflito real entre `+2 meses civis` e `+60 dias`.

Consequência: a implementação BPI P0 está bloqueada. Documentos, YAML ou parser legacy não autorizam trabalho de execução. A organização até aos gates é Max-2; a equipa de execução será decidida pelo João depois dos critérios de saída. Não há atribuição à Forja neste momento.

### Estado por estágio BPI

| Estágio | Estado | Requisito | Nota factual |
|---|---|---|---|
| Discovery | BLOCKED | FR-BPI-001 | Investigação concluída; falta implementação e guardas de paginação/robots/custo |
| Raw archive PDF | BLOCKED | FR-BPI-002 | Requer migration `raw.bpi_bulletins`, constraints e upsert transacional |
| Extraction por página | BLOCKED | FR-BPI-003 | Requer migration `raw.bpi_page_extractions`, FKs, índices e parser_version |
| Parsing P0 | BLOCKED | FR-BPI-004 | Parser legacy é regex global/texto simulado; precisa parser por secção e fixtures reais |
| Normalization | BLOCKED | FR-BPI-005 | Contrato e YAML divergem; required fields/exemplos/source enums por reconciliar |
| Reconciliation | BLOCKED | FR-BPI-006 | Matching deve incluir jurisdição/números fortes; modelo atual permite ambiguidades |
| Confidence/quarantine | BLOCKED | FR-BPI-007 | `review_queue` genérica existe, mas falta quarantine/versionamento BPI explícito |
| Exclusões RGPD/custo | BLOCKED | FR-BPI-008 | Política executável por aprovar antes de prospeção, OCR ou retenção indefinida |
| Deadlines/alertas BPI | BLOCKED | FR-DEADLINE-002 | Congelados por default até regra legal única validada |

### Taxonomia atual e prioridades

| Prioridade | Contagem | Estado |
|---|---:|---|
| P0 | 4 | Investigação concluída; implementação bloqueada |
| P1 | 13 | Planeado para depois dos gates P0; sem execução autorizada |
| P2 | 3 | Deferred/disabled, incluindo `opposition_filed` até fixture/justificação alinhada |

### Critérios de saída para GO WITH CHANGES

BPI só pode passar de NO-GO para GO WITH CHANGES quando todos os gates BPI-GATE-01..16 estiverem aceites por revisão documental e refletidos em schema/contrato/testes antes de código operacional. GO WITH CHANGES não significa deploy nem ativação de alertas: significa apenas autorização para o João escolher equipa de execução e abrir trabalho técnico controlado.

## 11. Gates e bloqueios concretos

P0 gates gerais:
1. Testes `pytest` passam no ambiente correto: `.venv/bin/python -m pytest -q`.
2. Nenhum status IMPLEMENTED sem teste/evidência de código.
3. Endpoints privados com user-scope testado para watchlists; repetir padrão em alerts/deadlines/portfolios antes de os promover a IMPLEMENTED.
4. Detalhe de marca frontend criado antes de declarar pesquisa→detalhe concluído.
5. Claims da landing devem refletir estado real antes de tráfego público.
6. Legal/privacy mínimos antes de produção pública ou prospeção/export.
7. Portal admin P0 mínimo funcional e testado: RBAC `is_superuser`, deny para não-admin, redaction, overview, users, planos/subscrições/uso, sources/imports/jobs/quality/review/audit/BPI gates.

Blockers CRITICAL BPI:
- BPI-CRIT-01: persistência/staging/versionamento BPI inexistentes. Faltam `raw.bpi_bulletins`, `raw.bpi_page_extractions`, staging/versionamento de eventos, dedupe/parser/reconciliation/supersession/quarantine explícitos, constraints/índices/FKs e unique/upsert transacional.
- BPI-CRIT-02: deadlines contraditórios `+2 meses civis` vs `+60 dias` e juridicamente não validados. Geração de deadlines/alertas BPI fica congelada por default.

Gates BPI rastreáveis, derivados da auditoria independente:

| Gate | Requisito/gate obrigatório | Rastreia para |
|---|---|---|
| BPI-GATE-01 | Congelar deadlines/alertas BPI por defeito com regra versionada `legal_status=draft|validated`, `enabled=false`, aprovador, data e base jurídica; nada cria `app.deadlines`/alertas BPI antes de validação. | FR-DEADLINE-002, BPI-CRIT-02 |
| BPI-GATE-02 | Escolher uma única semântica temporal validada para PT; remover o conflito `P2M`/meses civis vs `60 days` em contrato, código e testes. | FR-DEADLINE-002 |
| BPI-GATE-03 | Definir migrations P0 para `raw.bpi_bulletins`, `raw.bpi_page_extractions` e staging/versionamento de eventos BPI, com constraints, FKs, índices e unicidade transacional. | FR-BPI-002, FR-BPI-003, BPI-CRIT-01 |
| BPI-GATE-04 | Definir onde vivem `dedupe_key`, `parser_version`, `field_confidence`, reconciliation, supersession e quarantine; não depender apenas de JSON/raw_data. | FR-BPI-005, FR-BPI-007 |
| BPI-GATE-05 | Tornar arquivo concorrente seguro com unique constraint/upsert, `archive_version`, republicação/supersession e URLs alternativas. | FR-BPI-002 |
| BPI-GATE-06 | Reconciliar os 11 campos YAML ausentes (`change_date`, `correction_date`, `deferral_date`, `legal_notice`, `licence_scope`, `licensee_name`, `licensor_name`, `opponent_name`, `opposition_date`, `opposition_reference`, `request_date`) no contrato ou removê-los da taxonomia. | FR-BPI-005 |
| BPI-GATE-07 | Formalizar required fields por evento, incluindo expressão de recusa como `refusal_date OR legal_basis_text` se essa for a decisão; eventos inválidos são recusados/quarantined. | FR-BPI-004, FR-BPI-005 |
| BPI-GATE-08 | Corrigir exemplos JSON para serem válidos segundo o contrato, incluindo campos non-null como `id`, `bulletin_id`, `parser_name`, `raw_text_hash` e `quarantine_status` quando exigidos. | FR-BPI-005 |
| BPI-GATE-09 | Unificar source enums e event types canónicos (`inpi_bpi`/`bpi_pdf` ou decisão única documentada) e mapear/migrar tipos legacy (`publication`, `grant`, `provisional_refusal`, etc.). | FR-BPI-005 |
| BPI-GATE-10 | Definir thresholds gap-free: `score >= 0.85`, `0.65 <= score < 0.85`, `score < 0.65`, com comportamento de alerta/review/quarantine em cada faixa e runtime alinhado. | FR-BPI-007 |
| BPI-GATE-11 | Codificar ST.17/aliases como heurísticas no YAML: `match_mode`, scope obrigatório de secção, corroboradores e confidence caps. | FR-BPI-004 |
| BPI-GATE-12 | Mover `opposition_filed` para P2/disabled até existirem fixtures reais, ou justificar e alinhar todos os roadmaps. | Taxonomia BPI P2 |
| BPI-GATE-13 | Corrigir mapping de deadlines para a tabela real `app.deadlines` ou criar migration para modelo desejado com FK a `events.lifecycle_events`; não usar mapping documental divergente. | FR-DEADLINE-002 |
| BPI-GATE-14 | Reconciliar marcas por `(jurisdiction, application_number)`/registration number com constraints adequadas; matching por nome isolado é proibido. | FR-BPI-006 |
| BPI-GATE-15 | Acrescentar guards de paginação/convergência, robots recheck/kill switch, limite máximo de páginas, deteção de loops e orçamento por run; alinhar retry/backoff com `sources.yaml`. | FR-BPI-001, NFR-COST-001 |
| BPI-GATE-16 | Documentar política RGPD e custo total operacional antes de ativar prospeção, OCR ou retenção indefinida: base jurídica, roles/auditoria, retenção, encriptação/supressão, DPIA/LIA, storage/backups/OCR/review humana/observabilidade. | FR-BPI-008, NFR-GDPR-001, NFR-COST-001 |

Bloqueios atuais adicionais:
- Alertas bloqueados para IMPLEMENTED por falta de testes dedicados.
- Deadlines bloqueados para IMPLEMENTED por falta de teste endpoint/user-scope e validação de regras PT BPI.
- Billing real bloqueado por credenciais/teste controlado Stripe e decisão de planos em produção.
- Admin/ops é P0 e está bloqueado para conclusão por falta de UI, RBAC admin efetivo, endpoints agregados, audit model/API e testes deny/redaction.
- Pesquisa de alta qualidade bloqueada por decisão/implementação `pg_trgm` no endpoint e ranking.

## 12. Decisões abertas com recomendação Max-2

1. Pesquisa pública ou privada?
   - Recomendação: P0 privado por defeito; landing não deve chamar API de pesquisa sem rate limits.

2. BPI raw em tabelas próprias ou adaptar `raw.api_responses`?
   - Recomendação: tabelas próprias `BpiBulletinRaw` e `BpiPageExtraction`; PDF binário não é resposta JSON de API.

3. Âmbito exato das mutações admin?
   - Decisão: portal admin é P0. Recomendação: começar read-only; retry/replay/cancel/repair só entram depois de idempotência, audit append-only, confirmação explícita, RBAC e testes.

4. Prospeção P1 ou P0?
   - Recomendação: P1. Primeiro fechar vigilância, prazos e provenance; prospeção sem RGPD forte é risco.

5. Billing real antes de produto útil?
   - Recomendação: não. Manter mock/dev até P0 funcional e legal mínimo.

6. Relatórios/export?
   - Recomendação: P2, começar por CSV simples só depois de filtros RGPD e permissões.

7. Streamlit/React vs vanilla?
   - Recomendação: considerar substituída a referência README; código e CLAUDE atual apontam vanilla servido por FastAPI.

## 13. Plano de entrega por dependências, sem datas

P0 — Fundação operacional:
1. Corrigir documentação pública mínima: README/landing claims, quando autorizado noutra missão.
2. Fechar testes alerts e deadlines endpoint/user-scope.
3. Criar detalhe de marca frontend com provenance básico.
4. Tornar política de auth da pesquisa explícita.
5. Implementar portal admin mínimo read-only com RBAC `is_superuser`, deny tests, redaction, overview, users, planos/subscrições/uso, sources, imports, jobs, quality, review, audit e BPI gates.
6. Definir audit append-only e política para qualquer mutação admin; retry/replay/cancel/repair ficam fora até idempotência, confirmação e testes.
7. Fechar gates BPI-GATE-01..16 antes de qualquer implementação BPI operacional.
8. Só depois de GO WITH CHANGES decidido pelo João: implementar BPI raw/discovery/extraction/fixtures, parser por secção e normalização com quarantine, sem ativar deadlines/alertas por default.
9. Páginas legais mínimas.

P1 — Produto comercial controlado:
1. Portfolios/leads UI com RGPD e permissões.
2. Melhorar ranking pesquisa com `pg_trgm`/similarity.
3. Alert delivery email/Telegram testável sem envios acidentais.
4. Billing Stripe em ambiente controlado.

P2 — Expansão:
1. Relatórios/export avançados.
2. OCR e eventos BPI complexos.
3. White-label, SSO/API pública, Enterprise.
4. Calendário avançado/iCal.

## 14. Definition of Done por fase

P0 DoD:
- `.venv/bin/python -m pytest -q` verde.
- Todos os endpoints privados P0 com testes de auth e ownership.
- UI P0 navegável: login, dashboard, search, detalhe, watchlists, alerts, deadlines, settings.
- Portal admin P0 mínimo funcional e testado: `/app#/admin*` acessível só a `is_superuser`/admin, deny para anónimo/user normal, overview health, users/accounts, planos/subscrições/uso, sources/freshness, imports/source runs, jobs/queues/falhas, quality/reconciliation, review/quarantine, audit/system events e BPI gates; respostas redigidas sem password/hash/token/secrets/PII desnecessária.
- Ações admin mutáveis fora do read-only só passam DoD se forem idempotentes, auditadas append-only, confirmadas no UI, rate-limited/least privilege e cobertas por testes integração/e2e.
- BPI P0 apenas em estado GO WITH CHANGES: gates BPI-GATE-01..16 fechados, migrations/contrato/testes definidos, fixtures reais locais, raw PDF imutável, extraction por página, parser por secção, normalization, confidence/quarantine e provenance visível; deadlines/alertas BPI continuam disabled até regra legal `validated` e `enabled=true`.
- Sem claims públicos falsos sobre ingestão diária ou alertas reais.
- Legal/privacy mínimos publicados.

P1 DoD:
- Admin/ops avançado só para mutações seguras e automação adicional; o admin mínimo read-only já pertence ao P0.
- Leads/portfolios com UI, RGPD e export controlado.
- Alertas email/Telegram testados em sandbox/mocks robustos.
- Billing Stripe testado com webhooks em modo teste.
- Observabilidade e backups documentados/testados.

P2 DoD:
- Relatórios/export com permissões e auditoria.
- OCR/eventos complexos BPI com fixtures e métricas de confiança.
- Funcionalidades Enterprise só após roles, billing e segurança maduros.

## 15. Contagens

Requisitos funcionais por prioridade:
- P0: 33
- P1: 7
- P2: 1

Requisitos funcionais por estado:
- IMPLEMENTED: 5
- PARTIAL: 15
- PLANNED: 6
- BLOCKED: 10
- PLANNED/BLOCKED: 4
- DEFERRED: 0
- OPEN DECISION: 1

Requisitos não funcionais por prioridade:
- P0: 11
- P1: 2
- P2: 0

Requisitos não funcionais por estado:
- IMPLEMENTED: 2
- PARTIAL: 6
- PLANNED: 4
- BLOCKED: 0
- PLANNED/BLOCKED: 1
- DEFERRED: 0
- OPEN DECISION: 0
