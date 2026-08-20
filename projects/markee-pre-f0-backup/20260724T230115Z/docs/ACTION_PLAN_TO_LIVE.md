# ACTION PLAN TO LIVE — Markee

## 1. Cabeçalho

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Snapshot | 2026-07-24T19:44:32Z (UTC) |
| Autor | Max-2 |
| Working tree auditada | `/home/batata/projects/markee` |
| Único artefacto desta missão | `docs/ACTION_PLAN_TO_LIVE.md` |
| Âmbito | Plano executável desde o estado observado até local funcional, staging público reversível e produção live, sem executar alterações operacionais |
| Fora do âmbito desta missão | Código, testes, configuração, conteúdo, migrations, Git, deploy, DNS, credenciais, instalações e chamadas externas mutáveis |

### Fontes e regra de evidência

Contratos canónicos: `docs/SITEMAP.md` e `docs/REQUIREMENTS.md`. Foram confrontados com `docs/STATUS.md`, `docs/BACKLOG.md`, `CLAUDE.md`, `README.md`, `BRAND_MANUAL.md`, `FEATURES_RESEARCH.md`, o snapshot read-only de `contents/**`, `app/**`, `frontend/**`, `tests/**`, `alembic/**`, `docker-compose.yml`, `Dockerfile`, `pyproject.toml`, `config/bpi_event_taxonomy.yaml`, `docs/research/**`, Git, Docker/processos, base de dados e HTTP local/público.

Regras usadas:

- **Confirmado**: observado em código, teste executado, consulta read-only ou resposta HTTP desta auditoria.
- **Provável**: interpretação sustentada, mas sem prova end-to-end suficiente.
- **Inferência**: conclusão técnica explicitamente derivada de factos observados.
- **Desconhecido / UNKNOWN**: não verificado, incluindo valores/configuração de credenciais.
- **IMPLEMENTED** significa que existe código; **configured**, **validated**, **mock** e **live** são estados diferentes. Código implementado ou um contentor em execução não prova produção.
- Documentação antiga e copy não provam implementação. Dados mock nunca contam como dados reais.
- `contents/**` é um snapshot em escrita pelo Max: o conteúdo editorial final está **WIP** até auditoria independente PASS. Este plano não escreve nessa árvore.
- BPI permanece **NO-GO/BLOCKED**. A investigação, o YAML, o parser legacy e a task existente não autorizam ingestão operacional nem prazos/alertas BPI.

### Definição explícita dos três estados

1. **Local funcional**: aplicação, BD e filas executam numa máquina de desenvolvimento isolada; migrations são reproduzíveis; suites locais passam; dados mock estão identificados; não há dependência de URL pública. Não equivale a staging ou live.
2. **Staging público e reversível**: ambiente separado de produção, com URL e BD próprias, TLS, secrets não reutilizados, dados sintéticos/anonimizados, release imutável, backup/restore e rollback ensaiados, monitorização ativa e UAT. Pode ser desligado/revertido sem afetar produção.
3. **Produção live**: URL final aprovada, DNS/TLS/reverse proxy, segurança e isolamento multi-tenant validados, dados reais e respetiva proveniência, migrations controladas, backups e restore testados, observabilidade/on-call, legal/privacy/RGPD publicados, rollback provado, owner sign-off e hypercare ativo. `markee.batata.cc:8000` ou uma página que responde não satisfaz esta definição.

## 2. Executive status

### Veredicto factual atual

**Confirmado — funciona localmente:** FastAPI serve landing, SPA e API; PostgreSQL, Redis, app, worker e beat têm contentores em execução; `/`, `/app/`, `/health` e `/api/v1/health` responderam localmente; auth básica e watchlists têm testes; há modelos e separação ORM em `raw/core/events/app`; o worker responde a `celery inspect ping`.

**Confirmado — existe uma instância pública, mas não é produção live:** `https://markee.batata.cc/`, `/app/`, `/health` e `/api/v1/health` responderam 200 através de Cloudflare; HTTP redireciona para HTTPS; o certificado observado inclui `*.batata.cc`. Os SHA-256 do HTML local e público coincidiram. A ligação direta a `markee.batata.cc:8000`, HTTP e HTTPS, expirou; o porto local está ligado a `127.0.0.1:8000`. Isto prova uma publicação pública por proxy/túnel, não separação de staging nem readiness de produção.

**Confirmado — blockers CRITICAL:** 

1. **BPI pode alimentar deadlines sem source guard.** `app/services/ingestion.py:889-908` cria evento BPI `publication` com `deadline_date`; `app/tasks/calculate_deadlines.py:59-93` escolhe qualquer `publication` sem filtrar `source` e cria `app.deadlines`; `app/tasks/check_expiry.py` pode transformar deadlines em alertas. A task BPI está agendada diariamente em `app/tasks/__init__.py`. O facto de a BD observada ter 0 eventos BPI e 0 deadlines, e de tasks estarem a falhar, não é um controlo de segurança.
2. **Deadlines não têm user scope.** `app/api/deadlines.py:48-53` devolve a tabela global a qualquer utilizador autenticado; `app.deadlines` não tem `user_id`. É risco de fuga multi-tenant.
3. **Drift de migrations/BD.** O contentor reportou Alembic current `001` e head `002`; a BD tem schemas/tabelas de `002` e, simultaneamente, tabelas legacy em `public`. `app/main.py` executa `Base.metadata.create_all` no arranque. A BD não tem provenance de migration reproduzível.
4. **Secrets potencialmente incorporados na imagem.** Existe `.env` local; não existe `.dockerignore`; `Dockerfile` faz `COPY . .`; `/app/.env` está presente nos contentores app/worker/beat. Os valores não foram lidos. A imagem deve ser tratada como potencialmente comprometida e não promovida.
5. **Workers/schedules não estão operacionais.** Nas últimas 12 horas observadas, `calculate_deadlines` recebeu 10 e falhou 10; `poll_euipo` recebeu 1 e falhou 1; matching e dispatch tiveram sucessos e falhas. As falhas de deadline amostradas são `Future ... attached to a different loop`.
6. **Instância pública expõe comportamento de desenvolvimento.** Uvicorn usa `--reload`, bind mounts de código, sem restart policy, sem healthcheck app/worker/beat; defaults permitem secret de desenvolvimento e CORS `*`; `/docs` e `/openapi.json` estão públicos; não foram observados headers HSTS/CSP/X-Content-Type-Options/X-Frame-Options na resposta pública.
7. **Copy pública contém claims incompatíveis com o estado.** A landing publicada afirma monitorização contínua, leitura integral diária do BPI, `24/7`, `≤24h`, notificações email/Telegram e capacidades de planos não validadas. O snapshot editorial propõe correções, mas está WIP.

**Parcial:** API de marcas com fallback mock, matching, alertas, lifecycle, billing mock/Stripe, portfolios/prospeção, quality e frontend. Faltam gates de segurança, testes dedicados, user scope, dados reais, páginas/rotas P0 e validação operacional.

**Falta:** admin P0, detalhe de marca, legal/privacy, política RGPD/retenção/consentimento, CI/release, ambiente staging separado, imagens imutáveis, secrets seguros, backup/restore, monitoring, UAT, rollback, produção e hypercare.

### Tabela de stages

| Stage | Estado | Evidência concluída | Trabalho restante | Gate/Blocker |
|---|---|---|---|---|
| STG-00 Baseline e contenção | PARTIAL / CRITICAL | Snapshot Git/Docker/HTTP/DB/testes recolhido | Conter BPI, mock, exposição pública e imagens suspeitas | João autoriza restrição/rotação; source guard obrigatório |
| STG-01 Contratos e editorial | PARTIAL / WIP | SITEMAP/REQUIREMENTS 1.0; `contents/**` existe | Auditoria independente, claims e scope release | Max ainda escreve; João aprova contrato/editorial |
| STG-02 Segurança e data integrity | BLOCKED | JWT/bcrypt e schemas existem | Secrets, CORS, rate limits, migrations, drift, headers | CRITICAL migrations/secrets |
| STG-03 Auth, user scope e RBAC | PARTIAL / BLOCKED | Auth/watchlist ownership testado | Deadlines scope, admin RBAC, teams, sessão/recovery | CRITICAL fuga deadlines; decisões auth |
| STG-04 Dados não-BPI e reconciliação | PARTIAL | Raw/core/events/app e ingestão/versionamento existem | Fonte real validada, mock proibido, seed/reconcile | Dataset real vazio; credenciais UNKNOWN |
| STG-05 Billing e planos | PARTIAL / BLOCKED | Catálogo e caminhos mock/Stripe implementados | Decidir free beta vs Stripe, quotas e claims | Stripe real e webhooks não validados |
| STG-06 Vigilâncias, alertas e prazos | PARTIAL / BLOCKED | Watchlists implementadas; engines/tasks existem | BPI isolado, deadlines scoped, pipeline e delivery testados | CRITICAL BPI/source guard |
| STG-07 Admin P0 e observabilidade | PLANNED / BLOCKED | Health, quality e modelos parciais | UI/API admin read-only, audit, jobs/freshness | RBAC/audit ausentes |
| STG-08 Frontend, UX e conteúdo | PARTIAL | Landing/SPA responsive básica | Detail/admin/legal, claims, e2e UI, a11y | Editorial WIP; claims públicos |
| STG-09 Legal, RGPD e retenção | PLANNED / BLOCKED | Estrutura editorial WIP | Aprovação jurídica e execução técnica | GATE-JURIDICO |
| STG-10 Testes e evidence pack | PARTIAL | 146 testes recolhidos; execução isolada 142 pass/4 skip | E2E/security/perf/a11y/coverage/integration real | Sem CI; skips PG nesta execução |
| STG-11 Fundação infra/staging | PARTIAL / BLOCKED | Compose local e TLS público existem | Ambientes separados, imagens, secrets, backups, monitoring | Config atual é dev; sem restore |
| STG-12 Staging reversível e UAT | PLANNED | Nenhum ambiente separado provado | Deploy staging, smoke, UAT João, rollback drill | STG-00..11 |
| STG-13 Production readiness | PLANNED | DNS/TLS candidato observado | URL final, hardening, runbook e go/no-go | Decisões e evidence pack |
| STG-14 Go-live | PLANNED | Não iniciado | Backup, migration, canary, cutover, smoke, sign-off | Autorização explícita de produção |
| STG-15 Hypercare | PLANNED | Não iniciado | On-call, métricas, incidentes, retro | Produção live |

## 3. Arquitetura e superfície atual

### Matriz factual

| Superfície | Estado | Implemented/configured/validated/live | Evidência e lacuna principal |
|---|---|---|---|
| Landing `/` | PARTIAL | Implemented; publicamente servida; não validada editorialmente | `frontend/landing/*`, `app/main.py`; claims falsos e CDNs externos |
| Dashboard `/app` hash SPA | PARTIAL | Implemented; validado por HTTP, sem E2E | `frontend/dashboard/*`; rotas atuais: dashboard/search/watchlists/alerts/deadlines/settings/login |
| Detalhe de marca | PLANNED | API implemented; UI ausente | `app/api/trademarks.py`; target `/app#/marks/{application_number}` |
| Backend FastAPI `/api/v1` | PARTIAL | Implemented; health HTTP validado; não hardened | `app/api/__init__.py`; docs/OpenAPI públicos |
| Auth | PARTIAL | Register/login/me implemented e testados | Sem política de password, rate limit, verify/recovery/MFA; token em localStorage; inactive não revalidado em `/me` |
| Pesquisa | PARTIAL | Endpoint implemented; público; fallback mock | `app/api/trademarks.py`; `ILIKE`, sem filtro `nice_class` apesar do contrato; mock pode parecer real |
| Watchlists | IMPLEMENTED no âmbito atual | API/UI e ownership testados | `tests/integration/test_watchlists_api.py`; falta quota/validação forte/classes/pipeline E2E |
| Alertas internos | PARTIAL | API/service/task implemented; não validated end-to-end | Sem testes dedicados; sem provenance UI; delivery sem prova |
| Deadlines | BLOCKED / CRITICAL | API/engine/task implemented; inseguro | Global sem user scope; regra BPI não isolada; task falha em runtime |
| Email/Telegram | PARTIAL/UNVERIFIED | Código configured por env; estado de credenciais UNKNOWN | Sem envio controlado; `sent_at` pode ser marcado mesmo com delivery skipped |
| Billing/Stripe | PARTIAL | Mock implemented; caminho real unverified; não live | Checkout UI ativo; webhook sem testes; catálogo inclui features não entregues |
| Portfolios/prospeção | PARTIAL | API/service implemented; UI/testes integração incompletos | Team scope provável no código; RGPD e permissões por validar |
| Admin | PLANNED/BLOCKED P0 | Não implemented como portal | `/quality/metrics` exige apenas auth, não admin; `is_superuser` existe sem router/admin UI |
| BPI | BLOCKED / NO-GO | Parser/task legacy implemented e beat configured; pipeline novo não implemented | Faltam BPI-GATE-01..16; agendamento contradiz NO-GO |
| EUIPO | PARTIAL | Cliente OAuth/mock implemented; modo efetivo e credenciais UNKNOWN | BD real observada vazia; `core.sources/source_runs/raw` sem registos |
| PostgreSQL | PARTIAL / CRITICAL | Em execução; schemas ORM presentes; migration state inválido | current `001`, head `002`, duplicados `public` e schemas novos |
| Workers/Celery/Redis | PARTIAL / DEGRADED | Em execução e ping responde; schedules falham | Falhas async loop; sem health/heartbeat productizado/dead-letter |
| Containers | LOCAL DEV | Configured e running; não release-grade | `--reload`, mounts, tags mutáveis, sem restart; app/worker/beat sem healthcheck |
| Publicação atual | PUBLIC DEV INSTANCE | HTTPS acessível; não staging separado; não live | URL pública espelha local; sem evidence pack, backups, legal, rollback ou sign-off |
| Backups/restore | PLANNED | Não confirmado | Nenhum script/política/drill observado |
| Observabilidade/audit | PARTIAL/PLANNED | Liveness simples; logs Docker | Sem DB readiness, métricas, alerting, audit append-only, on-call |

### Fluxo de dados observado

- EUIPO: beat → `poll_euipo` → serviço OAuth ou mock → `raw.api_responses` → ingestão/versionamento → `core.trademarks`.
- BPI legacy: beat diário → download/parser → `core.documents`/eventos → `events.lifecycle_events`; este fluxo está **NO-GO** e deve ficar tecnicamente impossível em staging/produção.
- Matching: `core.trademarks` + `app.watchlists/items` → `app.alerts`.
- Prazos: `core.trademarks` + qualquer evento `publication` → `app.deadlines`; falta source/legal guard e user ownership.
- Delivery: alertas pendentes → email/Telegram quando configurados; sem validação de entrega real.
- Frontend: assets vanilla servidos pelo mesmo FastAPI; JWT em localStorage; chamadas same-origin a `/api/v1`.

## 4. Stages completos até live

### STG-00 — Baseline congelada e contenção imediata

**Objetivo:** impedir que o estado público/development e o risco BPI criem dano enquanto o produto é corrigido.

**Estado atual factual:** PARTIAL/CRITICAL. O snapshot está recolhido, mas beat agenda BPI/deadlines; a landing pública tem claims falsos; registo e checkout mock estão publicamente alcançáveis; não há ambiente separado.

**Evidência já concluída:** Git HEAD `51aa7d0`; `git status` com `contents/**`, contratos e BPI untracked; HTTP local/público; `app/tasks/__init__.py`; `app/tasks/calculate_deadlines.py`; `app/services/ingestion.py`; BD com 0 users/trademarks/events/deadlines; logs de workers; imagem contém `/app/.env`.

**Tarefas restantes:**

1. Abrir issue/PR CRITICAL não-content para teste falhante que prove que evento `source=inpi_bpi` nunca cria `app.deadlines` nem alertas.
2. Introduzir kill switch explícito e default-off para discovery/download/parse/ingest BPI e remover a schedule BPI de ambientes não autorizados.
3. Bloquear por código o source BPI no cálculo de deadlines e no dispatch; não depender de worker avariado ou BD vazia.
4. Decidir com João se a instância pública atual fica access-restricted/maintenance até STG-12; não executar sem autorização.
5. Desativar checkout/upgrade e identificar mock na UI até STG-05.
6. Impedir dados mock em qualquer ambiente público; se não houver fonte real, mostrar `dados indisponíveis`.
7. Registar hashes da release e inventário sem secrets; marcar imagens atuais como não promovíveis.
8. Preservar um dump/manifest read-only da BD antes de qualquer correção futura.

**Dependências/pré-condições:** nenhuma para os testes/guards; restrição pública e rotação de secrets exigem João.

**Responsável recomendado:** Spud orquestra; Forja (GPT-5.6 Sol) planeia/revê/valida; Claude Code CLI `claude-fable-5` executa TDD; Max-2 revê evidência BPI; Max não é tocado em `contents/**`; João autoriza acesso público e rotação.

**Paralelizável vs critical path:** guard BPI, bloqueio mock e inventário podem correr em paralelo em trees distintos. A contenção BPI e preservação de baseline são o primeiro critical path; não esperar pela revisão editorial.

**Stop conditions:** qualquer teste mostra evento BPI a criar deadline/alerta; schedule BPI ativa; mock apresentado como real; imagem com secret é promovida; não existe snapshot recuperável.

**Gates/autorização:** GATE-JOAO-CONTENCAO para restringir URL/serviços; GATE-CREDENTIALS para rotação sem imprimir valores; BPI continua NO-GO independentemente do resultado.

**Critérios de aceitação mensuráveis:** testes source-deny passam; 0 schedules BPI em staging/produção; 0 caminhos que transformam source BPI em deadline/alerta; checkout e mock não são apresentados como operação real; release candidate não contém `.env`.

**Checks futuros:** `pytest` dirigido aos testes BPI/deadline; `celery -A app.tasks inspect scheduled`; inspeção de schedule; `docker run --rm <image> sh -c 'test ! -e /app/.env'`; queries de lineage BPI→deadline. Não executar com imagem/tag de produção sem gate.

**Artefactos/evidência:** testes regressão, decisão de contenção, manifest da BD, inventário de schedules, relatório de scan da imagem, ADR de BPI disabled.

**Riscos e rollback:** restringir acesso afeta utilizadores atuais — contagem observada é 0, mas confirmar novamente. Rollback da contenção apenas depois dos guards PASS. Rotação invalida sessões/integrações; manter procedimento de reconfiguração seguro.

**Esforço:** M; pressupõe alterações pequenas mas cross-cutting e sem dados reais a migrar.

### STG-01 — Fecho de contratos e aprovação editorial

**Objetivo:** congelar o scope P0/live e garantir que copy, rotas e estados refletem implementação real.

**Estado atual factual:** PARTIAL/WIP. `docs/SITEMAP.md` e `docs/REQUIREMENTS.md` são canónicos; `contents/**` está a ser corrigido pelo Max e não tem auditoria independente PASS.

**Evidência já concluída:** contratos 1.0; matriz editorial e páginas em `contents/**`; inconsistências confirmadas em `README.md`, `CLAUDE.md` e landing publicada.

**Tarefas restantes:**

1. Aguardar o Max terminar `contents/**`; não criar segundo writer.
2. Fazer auditoria independente route→requisito→copy→API→teste.
3. Resolver decisões OD-01..OD-16 da secção 6 aplicáveis ao P0.
4. Congelar release scope: BPI excluído e disabled; prospeção/export/Enterprise deferidos salvo decisão explícita contrária.
5. Definir catálogo de capacidades `implemented/configured/validated/live` por ambiente.
6. Corrigir contratos apenas numa missão autorizada se a auditoria encontrar contradição real.
7. Aprovar mensagens legalmente sensíveis e anti-claims.
8. Obter sign-off editorial e de produto do João.

**Dependências/pré-condições:** conclusão do writer Max; STG-00 não precisa esperar.

**Responsável recomendado:** Spud orquestra; Max conclui conteúdo/multimodal; Max-2 faz auditoria crítica; Forja valida implementabilidade; João aprova scope e copy.

**Paralelizável vs critical path:** inventário técnico e testes podem avançar; não editar `contents/**` em paralelo. O freeze de scope precede billing, frontend final, legal e UAT.

**Stop conditions:** claims ativos sem evidência; rota alvo sem owner/estado; BPI vendido como operacional; Stripe/email/Telegram/admin apresentados como live; duas pessoas a escrever a mesma árvore.

**Gates/autorização:** GATE-EDITORIAL-PASS, GATE-PRODUTO-JOAO, GATE-JURIDICO para copy legal.

**Critérios de aceitação mensuráveis:** 100% das rotas P0 têm requisito, estado, CTA e fonte de dados; 0 claims proibidos positivos; todas as open decisions têm decisão, owner ou defer explícito; auditoria independente PASS assinada.

**Checks futuros:** diff read-only dos contratos/conteúdo; pesquisa de anti-claims; matriz automatizada de links/rotas; comparação OpenAPI→SITEMAP.

**Artefactos/evidência:** relatório editorial PASS/FAIL, decision log, release scope, capability matrix e sign-off João.

**Riscos e rollback:** scope creep atrasa segurança; rollback é regressar ao último contrato assinado, não reintroduzir copy antiga.

**Esforço:** M; pressupõe snapshot Max concluído e sem reescrita integral.

### STG-02 — Segurança base e integridade de migrations/BD

**Objetivo:** criar uma fundação reproduzível e sem secrets/defaults de desenvolvimento.

**Estado atual factual:** BLOCKED/CRITICAL. Migration current/head diverge; existem tabelas duplicadas; `.env` está na imagem; CORS e secret têm defaults inseguros; app faz `create_all`; não há rate limit ou headers de segurança provados.

**Evidência já concluída:** `app/main.py`, `app/core/config.py`, `app/core/security.py`, `alembic/**`, `Dockerfile`, `docker-compose.yml`; `alembic current=001`, `heads=002`; inspeção de schemas/tabelas; `/app/.env present` sem leitura de valores.

**Tarefas restantes:**

1. Criar teste de migration `upgrade` de BD vazia até head e schema diff zero.
2. Explicar e reconciliar current `001` vs objetos `002`; inventariar dados em schemas `public/raw/core/events/app`.
3. Desenhar migration corretiva idempotente; nunca apagar duplicados antes de reconciliação e backup.
4. Remover `Base.metadata.create_all` do arranque fora de testes/dev.
5. Criar `.dockerignore`; excluir `.env`, `.git`, caches, testes/dados desnecessários; rebuild sem cache e scan.
6. Rotacionar todos os secrets que possam ter entrado na imagem; não reutilizar entre local/staging/prod.
7. Fazer startup falhar se secret/default inseguro, CORS wildcard ou URL dev forem usados em staging/prod.
8. Definir CORS allowlist; adicionar rate limits para auth/search/webhook; limitar payloads/timeouts.
9. Definir headers CSP/HSTS/nosniff/frame/referrer/permissions no edge/app; adaptar CDNs ou self-host assets.
10. Rever OpenAPI/docs públicos, erros, logging/redaction e dependências/lock/SBOM.
11. Executar SAST, dependency/image scan e teste de permissões do utilizador não-root/read-only filesystem quando viável.

**Dependências/pré-condições:** STG-00 snapshot; backup antes de migration corretiva; decisões de URL/CORS.

**Responsável recomendado:** Spud; Forja Sol desenha/revê; Claude Code CLI executa TDD/migrations/containers; Max-2 audita drift e evidência; João autoriza rotação e downtime se necessário.

**Paralelizável vs critical path:** imagem/secrets/headers pode avançar em paralelo com desenho de migration, em branches separadas. Reconciliar BD e secrets é critical path para staging.

**Stop conditions:** migration destrutiva sem backup/restore; secret aparece em logs/diff; current != head; schema diff não explicado; fallback dev aceite em staging/prod; vulnerabilidade critical/high sem decisão documentada.

**Gates/autorização:** GATE-BACKUP-BEFORE-MIGRATION, GATE-CREDENTIALS, GATE-SECURITY-PASS, aprovação João para downtime.

**Critérios de aceitação mensuráveis:** BD vazia chega a único head; BD clone atual chega ao mesmo schema sem perda; 0 tabelas legacy não justificadas; 0 `.env`/secret na imagem; produção recusa defaults; scans sem critical/high não aceites; headers e rate limits testados; docs públicas conforme decisão.

**Checks futuros:** `alembic current`, `alembic heads`, `alembic upgrade head`, `alembic check`; schema-only dump diff; `docker history --no-trunc`; scan da imagem/SBOM; HTTP header tests; testes 429; secret scanning. Usar clones, nunca primeiro na BD live.

**Artefactos/evidência:** ADR migration, plano de reconciliação, dumps checksummed, teste upgrade/rollback, SBOM, scan reports, rotation record sem valores e security checklist.

**Riscos e rollback:** migration pode perder/duplicar dados. Estratégia expand/verify/contract, backup consistente, restore drill e downgrade apenas se comprovadamente seguro.

**Esforço:** L; pressupõe BD observada vazia, mas exige confirmar novamente antes de agir.

### STG-03 — Auth, user scope, teams e RBAC

**Objetivo:** provar isolamento por utilizador/equipa e least privilege em todas as rotas.

**Estado atual factual:** PARTIAL/BLOCKED. Auth e watchlists estão testados; deadlines são globais; trademarks são públicos; quality é acessível a qualquer auth; admin não existe; portfolios não têm suite de integração dedicada.

**Evidência já concluída:** `app/api/auth.py`, `watchlists.py`, `deadlines.py`, `portfolios.py`, `quality.py`, modelos User/Team; testes auth/watchlists.

**Tarefas restantes:**

1. Criar matriz rota×anónimo×user A×user B×team member×superuser.
2. Escrever deny-first tests para deadlines, alerts, portfolios, quality, billing e futura admin.
3. Modelar ownership de deadlines através de portfolio/watchlist/user ou entidade explícita; migrar sem ambiguidade.
4. Exigir scope correto em pesquisa/detalhe conforme OD-02 e rate limit no modo público, se escolhido.
5. Criar dependency `require_superuser/admin`; aplicar a todas as rotas admin/quality sensíveis.
6. Definir roles de team e operações permitidas; testar convite/remoção apenas se entrarem no P0.
7. Validar `is_active` em cada pedido autenticado, não só login; definir revogação/rotação de sessão.
8. Definir política de password, recovery, verificação de email e MFA/admin conforme OD-07.
9. Decidir armazenamento de sessão: cookie HttpOnly/SameSite+CSRF ou aceitar formalmente localStorage com mitigação CSP/XSS.
10. Redigir respostas e logs sem PII/secrets.

**Dependências/pré-condições:** STG-02 migrations/security; decisão de pesquisa e teams.

**Responsável recomendado:** Spud; Forja Sol modela threats/RBAC; Claude Code CLI executa TDD; Max-2 faz adversarial review; João decide produto/auth.

**Paralelizável vs critical path:** testes alerts/portfolios podem correr em paralelo; modelação de deadline ownership e admin dependency não devem ter writers concorrentes nos mesmos routers/models. Deadline scope é critical path.

**Stop conditions:** user A lê/escreve dados de B; user normal acede admin/quality operacional; conta inativa mantém acesso; token/PII aparece em resposta/log; política auth sem decisão.

**Gates/autorização:** GATE-AUTH-PRODUTO, GATE-RBAC-PASS, GATE-EMAIL se recovery/verify for ativado.

**Critérios de aceitação mensuráveis:** matriz completa com deny/allow automatizado; 0 endpoint privado sem dependency; deadlines retornam apenas recursos autorizados; admin anónimo/user=401/403 e superuser=200; contas inativas bloqueadas; recovery/session policy aprovada.

**Checks futuros:** pytest dirigido a auth/scope; OpenAPI security inspection; testes IDOR/BOLA; sessão expirada/revogada; análise de logs redigidos.

**Artefactos/evidência:** threat model, RBAC matrix, testes deny/allow, ADR de sessão e relatório IDOR.

**Riscos e rollback:** migration de ownership pode esconder dados válidos. Mapear, reconciliar, bloquear órfãos em quarantine e manter rollback de leitura read-only.

**Esforço:** L; pressupõe P0 sem RBAC fino além de user/team/superuser.

### STG-04 — Dados reais não-BPI, migration, seed e reconciliação

**Objetivo:** garantir que produção usa dados reais, rastreáveis e reconciliados, sem fallback sintético silencioso.

**Estado atual factual:** PARTIAL. Infra raw/core/events/app e versionamento existem; BD observada tem 0 trademarks/raw/source_runs; pesquisa com query e BD vazia devolve mock EUIPO; credenciais reais e qualidade da fonte são UNKNOWN.

**Evidência já concluída:** `app/services/euipo_service.py`, `ingestion.py`, `raw_responses.py`, modelos/migration `002`, testes ingestion/confidence/schemas.

**Tarefas restantes:**

1. Decidir fonte P0 real e termos de uso: EUIPO/TMview/API e âmbito PT/EU; BPI excluído.
2. Separar modos `mock/dev`, `staging synthetic` e `production real`; produção deve falhar/mostrar indisponível sem fonte.
3. Obter credenciais autorizadas sem as colocar em código/logs; fazer sandbox/read-only contract tests.
4. Definir cursor, retries, pagination caps, rate/cost limits, kill switch e source freshness.
5. Corrigir partições raw de forma contínua e testada para datas futuras.
6. Criar seed mínimo apenas para classes/configuração; dados de marca reais entram por import versionado, não seed inventado.
7. Executar import em staging com amostra autorizada e reconciliation report: processed/new/updated/failed/duplicates/orphans.
8. Validar constraints fortes por `(jurisdiction, application_number)`/registration number e provenance.
9. Definir initial load/backfill, checkpoint e reexecução idempotente.
10. Definir resposta quando fonte está stale/down e impedir mock fallback.
11. Aprovar dataset inicial e freshness observada antes de UAT.

**Dependências/pré-condições:** STG-02 migration; STG-03 scope; credenciais/rede autorizadas; legal da fonte.

**Responsável recomendado:** Spud; Forja Sol planeia pipeline; Claude Code CLI executa; Max-2 valida fontes/ausências/provenance; João autoriza credenciais, rede e dataset.

**Paralelizável vs critical path:** contract tests e desenho de reconciliation paralelos; import real só após migration e credential gate. É critical path para um produto de pesquisa útil.

**Stop conditions:** dados mock sem label; fonte/ToS UNKNOWN; import não idempotente; perda de raw/provenance; taxa de erro sem explicação; BPI entra no pipeline.

**Gates/autorização:** GATE-CRED-EUIPO/REDE; qualquer custo externo esperado acima de $1 exige aviso e autorização João; GATE-DATASET; BPI NO-GO.

**Critérios de aceitação mensuráveis:** produção tem mock disabled; cada registo real liga a source/run/raw/version; reexecução da mesma janela não duplica; reconciliação contabiliza todos os input records; failures ficam visíveis/replayáveis; freshness é apresentada; dataset UAT aprovado.

**Checks futuros:** contract tests sandbox; import dry-run/clone; queries de contagem por layer/source/run; checks de idempotência e orphan; comparação hash/version; sem chamadas reais antes do gate.

**Artefactos/evidência:** source contract, ToS review, run/reconciliation report, sample lineage, seed manifest, data quality report e sign-off dataset.

**Riscos e rollback:** API muda ou bloqueia; parar no kill switch, preservar cursor/raw, reverter release e não apagar versões.

**Esforço:** L; assume uma fonte API autorizada e BPI fora do live.

### STG-05 — Billing, Stripe, catálogo e quotas sem claims falsos

**Objetivo:** escolher e validar um modo comercial coerente: free/private beta sem cobrança ou Stripe real controlado.

**Estado atual factual:** PARTIAL/BLOCKED. Catálogo e endpoints existem; checkout mock está ativo no UI; webhook e Stripe real não foram testados; feature flags incluem capacidades não implementadas; quotas não são globalmente impostas.

**Evidência já concluída:** `app/api/billing.py`, `app/services/billing.py`, `frontend/dashboard/app.js:1186-1295`, `PLAN_META`, `PLAN_LIMITS`; credenciais não inspecionadas.

**Tarefas restantes:**

1. João decide OD-03: free/private beta com checkout removido ou cobrança Stripe.
2. Reconciliar preços, limits e features com capacidade real; remover/deferir white-label, reports, SSO/API/WIPO/Telegram não validados.
3. Expor `BillingStatus` inequívoco; nunca redirecionar mock como se checkout tivesse sucedido.
4. Implementar/testar quotas nos writes relevantes, incluindo concorrência e downgrade.
5. Se free beta: ocultar preços/checkout ou marcar catálogo futuro e impedir POST checkout em ambiente público.
6. Se Stripe: criar produtos/preços em modo teste, allowlist de redirect URLs, idempotency keys e event ledger.
7. Testar assinatura, replay, ordem, duplicados e todos os eventos necessários; não confiar só em `checkout.session.completed`.
8. Definir impostos/faturação/cancelamento/reembolso/dunning e termos antes de live pago.
9. Fazer UAT financeiro em modo teste; separar chaves test/live.
10. Autorizar live keys e uma transação controlada apenas no cutover aprovado.

**Dependências/pré-condições:** STG-01 catálogo; STG-02 secrets; STG-03 ownership; STG-09 termos; Stripe apenas com credenciais.

**Responsável recomendado:** Spud; Forja Sol revê state machine/webhooks; Claude Code CLI executa/testa; Max-2 audita claims; João decide modo e autoriza Stripe/custos.

**Paralelizável vs critical path:** quotas/catálogo podem avançar em paralelo com legal. Stripe não bloqueia live se João aprovar free beta e todos os caminhos de cobrança forem disabled.

**Stop conditions:** preço compra feature inexistente; webhook sem assinatura/idempotência; mock parece pagamento; live key em staging/log; quota contornável; legal financeiro ausente.

**Gates/autorização:** GATE-BILLING-MODE, GATE-STRIPE-TEST, GATE-STRIPE-LIVE, GATE-LEGAL-BILLING. Stripe live é ação paga/mutável e exige João.

**Critérios de aceitação mensuráveis:** exatamente um modo exposto; 0 claims falsos; quotas têm testes concorrentes; modo Stripe tem webhook suite/replay PASS e reconciliação com Stripe test; modo free tem 0 endpoint/CTA de cobrança acessível.

**Checks futuros:** testes unit/integration webhook; Stripe CLI/test mode apenas após gate; reconciliação de subscriptions; smoke de redirect allowlist; teste downgrade/quota.

**Artefactos/evidência:** decisão comercial, catálogo assinado, webhook event matrix, test receipts sem PII/secrets, quota report e billing sign-off.

**Riscos e rollback:** cobrança indevida. Rollback: feature flag global de checkout, suspender novos checkouts, preservar ledger e reconciliar antes de qualquer reembolso.

**Esforço:** M para free beta; L para Stripe pago. Estimativas alternativas, sem data prometida.

### STG-06 — Vigilâncias, matching, alertas e prazos com BPI isolado

**Objetivo:** tornar o core P0 multi-tenant e verificável, mantendo BPI tecnicamente incapaz de gerar ações.

**Estado atual factual:** PARTIAL/BLOCKED/CRITICAL. Watchlists CRUD funciona; matching/alerts/deadlines existem; faltam E2E e tests alerts/deadline; deadline global e BPI source guard ausente; tasks degradadas.

**Evidência já concluída:** `app/api/watchlists.py`, `alerts.py`, `deadlines.py`; `app/tasks/match_similar.py`, `calculate_deadlines.py`, `check_expiry.py`, `send_alerts.py`; testes similarity/lifecycle/watchlists.

**Tarefas restantes:**

1. Implementar primeiro os source-deny/legal-status tests de STG-00.
2. Criar feature registry de deadline rules com source, jurisdiction, version, legal_status, enabled, approver/date/basis.
3. Manter todas as regras BPI `enabled=false`; proibir criação, listagem acionável e dispatch.
4. Corrigir ownership/user scope dos deadlines e orphan handling.
5. Corrigir worker async loop e provar tasks repetidas sem falha/leak.
6. Criar pipeline E2E não-BPI: ingest real fixture → match → alert interno → read/dismiss.
7. Criar tests dedicados de alerts e deadlines: auth, ownership, sorting, filtering, idempotência.
8. Rever dedupe concorrente com constraint/idempotency key, não só query de 24 horas.
9. Corrigir semantics de delivery: `sent_at` só quando política de canais é satisfeita; `skipped/failed/sent` por delivery.
10. Decidir email/Telegram; se deferred, dispatch externo off e UI mostra alerta interno.
11. Validar apenas regras não-BPI com revisão jurídica apropriada; prazos críticos levam disclaimer/fonte.
12. Criar métricas e admin read-only de runs/matching/deadline rules/deliveries.

**Dependências/pré-condições:** STG-02/03/04; GATE-JURIDICO para regras; canal externo opcional.

**Responsável recomendado:** Spud; Forja Sol planeia rules/lineage e revê; Claude Code CLI executa TDD; Max-2 valida isolamento BPI e regra/fonte; Max ajusta copy após gate; João aprova canais/regras.

**Paralelizável vs critical path:** tests alerts e correção worker podem correr em paralelo; deadline ownership/source registry tocam models/migrations e devem ser serializados. Isolamento BPI é critical path absoluto.

**Stop conditions:** qualquer BPI cria deadline/alerta; deadline cruza users; task falha numa repetição; duplicate alerts em corrida; delivery `skipped` aparece como enviado; prazo sem source/rule version.

**Gates/autorização:** BPI permanece NO-GO; GATE-DEADLINE-LEGAL por rule; GATE-EMAIL e GATE-TELEGRAM individuais; rede real só após autorização.

**Critérios de aceitação mensuráveis:** 0 BPI→deadline/alert; E2E não-BPI PASS; deny tests multi-user PASS; execução repetida idempotente; worker/beat healthy durante janela UAT aprovada; cada deadline tem owner, source e rule version; delivery states correspondem a evidência.

**Checks futuros:** pytest E2E pipeline; Celery eager/integration e repeated-run; query lineage source→event→deadline→alert; teste de corrida; sandbox SMTP/Telegram somente com gate.

**Artefactos/evidência:** rule registry, legal approvals, E2E trace, worker stability report, delivery evidence e BPI negative-proof report.

**Riscos e rollback:** alertas errados podem causar dano jurídico. Kill switches por rule/source/channel, desativação imediata, preservar audit e reclassificar dados sem os apagar.

**Esforço:** XL; assume BPI excluído e apenas rules não-BPI estritamente aprovadas.

### STG-07 — Portal admin P0 read-only, observabilidade e audit

**Objetivo:** operar a plataforma sem acesso direto à BD e sem mutações admin inseguras.

**Estado atual factual:** PLANNED/BLOCKED. Health é só liveness; quality existe para qualquer user autenticado; modelos source_runs/review_queue existem; não há UI/admin router/audit model/jobs API.

**Evidência já concluída:** requisitos FR-ADMIN-001..011; `contents/pages/ADMIN_PORTAL.md` WIP; `app/api/quality.py`; `app/services/quality.py`; modelos sources/source_runs/review_queue; Docker logs.

**Tarefas restantes:**

1. Definir contratos admin versionados e redigidos: overview, users, subscriptions, sources, imports, jobs, quality, review, audit, BPI gates.
2. Aplicar `require_superuser` e deny tests antes de expor dados.
3. Implementar readiness DB/Redis/worker/beat, freshness e failures sem secrets.
4. Criar endpoints paginados read-only para users/subscriptions/sources/runs/quality/review.
5. Criar heartbeat/jobs view segura; cancel/retry ficam disabled.
6. Criar audit append-only para acessos/admin events/config/release; definir retenção/redaction.
7. Mostrar BPI NO-GO e 16 gates sem botão de ativação.
8. Implementar SPA admin e estados loading/empty/error/stale/403.
9. Adicionar structured logs, correlation/request ID, métricas e alertas operacionais.
10. Testar paginação, filtros, performance, redaction, raw payload escaping e least privilege.

**Dependências/pré-condições:** STG-02/03; contratos STG-01; dados/worker STG-04/06.

**Responsável recomendado:** Spud; Forja Sol define API/observabilidade; Claude Code CLI implementa; Max-2 audita redaction/gates/BPI; Max só copy após freeze; João aprova vista P0.

**Paralelizável vs critical path:** backend admin e wireframes podem correr em paralelo em trees distintos; UI só integra após contratos. Portal mínimo é critical path por contrato P0.

**Stop conditions:** user normal vê admin; raw HTML/payload perigoso renderizado; secret/PII desnecessária; mutação admin disponível; health verde sem distinguir UNKNOWN; BPI ativável.

**Gates/autorização:** GATE-ADMIN-SCOPE, GATE-RBAC-PASS, GATE-OBSERVABILITY, qualquer serviço pago de monitoring requer aprovação de custo.

**Critérios de aceitação mensuráveis:** 10 domínios P0 têm vista/estado; anónimo/user negados; superuser permitido; redaction tests PASS; readiness deteta dependência down; audit é append-only; 0 mutações admin; BPI mostra 16/16 gates como blocked até mudança autorizada.

**Checks futuros:** API integration/IDOR tests; axe/E2E admin; fault injection em staging; log/metric query; mutation scan; XSS payload fixtures.

**Artefactos/evidência:** OpenAPI admin, RBAC/redaction report, dashboard screenshots, audit schema/ADR, alert routes e operator guide.

**Riscos e rollback:** admin expõe PII/infra. Feature flag admin, retirar rota no proxy, preservar audit e usar ferramentas infra externas temporariamente.

**Esforço:** XL; portal completo P0 em 10 domínios, ainda que read-only.

### STG-08 — Frontend/UX, conteúdo, responsive e acessibilidade

**Objetivo:** entregar todas as rotas P0 com copy factual, interação testável e WCAG AA.

**Estado atual factual:** PARTIAL. Landing e SPA existem; sem detalhe/admin/legal; sem testes frontend; landing pública contradiz contracts; checkout mock ativo; assets dependem de CDNs.

**Evidência já concluída:** `frontend/landing/*`, `frontend/dashboard/*`, `BRAND_MANUAL.md`; snapshot `contents/**`; HTTP e hashes local/público.

**Tarefas restantes:**

1. Aplicar apenas conteúdo com auditoria independente PASS; não copiar WIP cegamente.
2. Remover claims públicos não comprovados e distinguir fonte/freshness/mock/blocked.
3. Implementar detalhe de marca com provenance e sem eventos BPI acionáveis.
4. Integrar admin P0; implementar legal/error routes conforme decisões.
5. Corrigir settings com `BillingStatus`; checkout disabled conforme STG-05.
6. Mostrar `NotificationStatus`, source/rule status e disclaimers nos alertas/prazos.
7. Validar todos os CTAs e deep links; definir 404/403/500/503.
8. Rever XSS/DOM injection e CSP; `innerHTML` só com escape/templating seguro.
9. Self-host/pin assets ou aprovar CDNs com SRI/CSP/privacy; adicionar fallback.
10. Testar mobile/tablet/desktop e browsers aprovados; reduced motion e sem JS crítico.
11. Executar axe/Lighthouse/manual keyboard/screen reader; corrigir contrast/focus/labels/headings.
12. Adicionar SEO/canonical/OG apenas na URL final aprovada.

**Dependências/pré-condições:** STG-01; APIs STG-03..07; legal STG-09 para páginas finais.

**Responsável recomendado:** Spud; Max fornece conteúdo/multimodal aprovado; Forja Sol revê arquitetura/segurança; Claude Code CLI implementa e testa; Max-2 audita claims; João faz UX gate.

**Paralelizável vs critical path:** landing e shell podem avançar separadamente; content writer único em `contents/**`; integração UI serializa por ficheiro. Claims públicos e rotas P0 são critical path UAT.

**Stop conditions:** claim sem evidence; CTA dead/mock; keyboard trap; axe critical/serious; BPI ativo; preço inclui feature ausente; CDN impede core UI ou viola política.

**Gates/autorização:** GATE-EDITORIAL-PASS, GATE-UX-JOAO, GATE-A11Y, GATE-LEGAL-PUBLISH.

**Critérios de aceitação mensuráveis:** todas as rotas P0 navegáveis; 0 links/CTAs mortos; 0 axe critical/serious; keyboard-only completa fluxos P0; layouts passam viewports aprovados; 0 claims proibidos positivos; fontes/mock/freshness visíveis.

**Checks futuros:** Playwright/Cypress ou framework decidido; axe; Lighthouse; link checker; visual regression; CSP report-only→enforce em staging.

**Artefactos/evidência:** route screenshots, a11y report, browser matrix, content audit PASS, CTA/link report e visual baselines.

**Riscos e rollback:** regressão visual ou CSP quebra CDNs. Release de assets versionada; rollback do bundle/static; não relaxar CSP sem risk acceptance.

**Esforço:** XL; inclui detalhe/admin/legal e suites frontend ainda ausentes.

### STG-09 — Legal, RGPD, retenção, consentimento e políticas

**Objetivo:** cumprir obrigações públicas e implementar políticas, não apenas publicá-las.

**Estado atual factual:** PLANNED/BLOCKED. Estruturas WIP existem; não há páginas públicas finais, política aprovada, delete/export, retenção, consentimento ou lista de subprocessadores confirmada.

**Evidência já concluída:** `contents/pages/LEGAL_ERRORS.md`, `CONTENT_PRINCIPLES.md`; modelos contêm dados de conta, titulares, representatives, client email e prospeção.

**Tarefas restantes:**

1. Identificar controller, contacto privacy, finalidades, bases legais e categorias de dados.
2. Mapear flows, storage, logs, backups, Stripe/email/Telegram/CDNs/monitoring como subprocessadores potenciais.
3. Decidir e documentar retenção por tabela/raw/log/backup; implementar jobs/testes de execução e legal hold.
4. Definir direitos de acesso, retificação, apagamento, portabilidade e oposição; implementar processo verificável.
5. Fazer LIA/DPIA quando aplicável, em especial prospeção/BPI/contactos/monitorização sistemática.
6. Manter prospeção/export e BPI PII disabled até aprovação.
7. Definir consentimento para analytics/marketing; não pedir consentimento para o estritamente necessário de forma enganosa.
8. Publicar privacy, terms, legal/disclaimers, cookies/storage, subprocessadores e versões/aceitação.
9. Rever billing, SLA/disponibilidade, responsabilidade por prazos e fonte oficial.
10. Obter revisão de profissional qualificado e aprovação João.
11. Testar que UI e backend cumprem as políticas publicadas.

**Dependências/pré-condições:** STG-01 scope; decisões integrations; data map STG-04/06/07.

**Responsável recomendado:** Spud coordena profissional jurídico/DPO adequado; Max estrutura copy; Max-2 verifica claims/evidência; Forja Sol mapeia execução; Claude Code CLI implementa controlos; João aprova publicação.

**Paralelizável vs critical path:** data mapping e drafting podem correr com engenharia; publicação só após arquitetura final. Gate legal é critical path para staging com UAT externa e produção.

**Stop conditions:** política promete execução inexistente; base legal UNKNOWN; subprocessador ativo não listado; prospeção/BPI PII ativa; pedido RGPD sem owner; páginas não aprovadas.

**Gates/autorização:** GATE-JURIDICO, GATE-RGPD, GATE-PROSPETION, GATE-BPI-16, GATE-CONSENT, GATE-LEGAL-BILLING.

**Critérios de aceitação mensuráveis:** data map cobre todos os stores/flows; políticas versionadas e acessíveis; todos os subprocessadores ativos listados; pedidos RGPD ensaiados end-to-end; retenção testada; consentimento respeitado; sign-off jurídico e João.

**Checks futuros:** data inventory; tests delete/export/retention/consent; crawl legal links; backup deletion limitations review; DPIA/LIA checklist.

**Artefactos/evidência:** RoPA/data map, retention schedule, subprocessors list, LIA/DPIA decision, legal versions, request runbook e approvals.

**Riscos e rollback:** política incorreta cria exposição. Retirar feature/processing afetado, não ocultar incidente; versionar e notificar alterações conforme aconselhamento.

**Esforço:** L; depende de revisão externa e decisões, sem estimar calendário.

### STG-10 — Testes, quality gates e release evidence pack

**Objetivo:** transformar a release numa conclusão reproduzível com evidência independente.

**Estado atual factual:** PARTIAL. Execução isolada desta auditoria: `142 passed, 4 skipped, 1 warning` em 9.60s, forçando PostgreSQL indisponível e sem cache; total 146. Os contratos registam execução anterior em venv com PostgreSQL: `144 passed, 2 skipped`. A execução atual não valida PG live. Não há testes E2E frontend, admin, billing, alertas dedicados, deadline endpoint/scope, security, performance ou a11y.

**Evidência já concluída:** `tests/unit/*`, `tests/integration/test_api.py`, `test_watchlists_api.py`, `test_schemas.py`; `tests/e2e` só contém `__init__.py`; `pyproject.toml` sem configuração de coverage/CI observada.

**Tarefas restantes:**

1. Fixar matriz de ambientes: unit, integration PG clone, API, worker, E2E browser, security, perf, a11y, migration/restore.
2. Eliminar asserts permissivos (`status in (...)`) e dependências antigas de passlib no teste.
3. Adicionar tests de alerts, deadlines/scope, portfolios/teams, billing/webhook/quotas, admin/RBAC/redaction.
4. Adicionar BPI negative tests e pipeline não-BPI E2E.
5. Testar migrations de zero e clone, downgrade apenas se suportado, backup/restore e data reconciliation.
6. Criar E2E dos fluxos P0 e smoke público.
7. Executar SAST/dependency/image/secret scan e DAST em staging autorizado.
8. Definir SLO/performance budgets com João e medir search/API/jobs em dataset representativo.
9. Executar a11y automatizada/manual e responsive/browser matrix.
10. Medir coverage de services contra mínimo canónico de 80%; não declarar atingido antes do relatório.
11. Criar CI com artefactos imutáveis; nenhum deploy após falha/skip inesperado.
12. Montar release evidence pack e revisão independente PASS.

**Dependências/pré-condições:** implementações STG-02..09; staging para DAST/perf/E2E externo.

**Responsável recomendado:** Spud; Forja Sol define/revê quality gates; Claude Code CLI executa TDD/suites; Max-2 audita evidência e contradições; Max valida conteúdo visual; João aprova SLO/UAT.

**Paralelizável vs critical path:** suites por domínio em paralelo sem writers no mesmo test module; evidence pack agrega no fim. Migration/security/BPI/scope tests são critical path.

**Stop conditions:** qualquer falha; skip inesperado; flaky retry a esconder erro; coverage abaixo do contrato sem risk acceptance; security critical/high; E2E P0/a11y/perf gate falha; ambiente de teste toca produção.

**Gates/autorização:** GATE-QA-PASS, GATE-SECURITY-PASS, GATE-PERF-SLO, GATE-A11Y; DAST/rede/custos apenas autorizados.

**Critérios de aceitação mensuráveis:** 0 falhas; 0 skips inesperados; 0 flaky não resolvido; coverage services ≥80% conforme contrato; 0 security critical/high não aceite; todos os fluxos P0 E2E PASS; budgets aprovados cumpridos; evidence pack completo.

**Checks futuros:** CI test commands pinados; `pytest`; coverage; browser E2E; axe; k6/Locust decidido; scanners; migration/restore scripts. Nunca apontar DAST/load para produção sem gate.

**Artefactos/evidência:** JUnit/coverage, scan reports, E2E vídeo/screenshots, perf report, a11y report, migration/restore report, test environment manifest e QA sign-off.

**Riscos e rollback:** testes verdes com fixtures irreais. Exigir PG, dataset representativo, negative cases e rastreabilidade requisito→teste.

**Esforço:** XL; gaps de várias classes de teste.

### STG-11 — Fundação de infra, secrets, containers, backups e monitoring

**Objetivo:** construir staging/produção reproduzíveis e separados a partir de release imutável.

**Estado atual factual:** PARTIAL/BLOCKED. Compose local funciona; app só em loopback e Cloudflare dá HTTPS público; configuração é dev e sem separação, imagens pinadas por tag `latest`, mounts/reload, restart=no; sem backup/restore/monitoring provado.

**Evidência já concluída:** `docker-compose.yml`, `Dockerfile`, inspect de cinco contentores, DNS/TLS/HTTP, imagens, health db/redis e worker ping.

**Tarefas restantes:**

1. Definir topologia local/staging/prod, hosts/contas/redes/DB/storage e ownership.
2. Criar compose/manifests por ambiente sem bind mounts/reload e com imagens por digest.
3. Adicionar healthchecks/readiness app/worker/beat; restart policies e resource limits.
4. Criar secret store/injection; imagens e backups sem `.env`; rotação e least privilege DB/Redis.
5. Isolar DB/Redis de rede pública; TLS/reverse proxy/Cloudflare com origin policy aprovada.
6. Implementar migrations como job único antes da app; nunca `create_all` nem múltiplos writers.
7. Implementar backups encrypted para DB e artefactos raw necessários; retenção conforme legal.
8. Executar restore para ambiente vazio e medir RPO/RTO; João aprova objetivos quantificados.
9. Implementar logs centralizados/redigidos, métricas, alertas, uptime e disk/cert/queue/backup checks.
10. Definir release registry, SBOM, signing/provenance, cleanup e rollback image.
11. Documentar capacity/cost; avisar antes de qualquer despesa >$1.

**Dependências/pré-condições:** STG-02; decisões URL/SLO/RPO/RTO; legal retention.

**Responsável recomendado:** Spud; Forja Sol desenha/revê infra; Claude Code CLI executa IaC/manifests; Max-2 audita evidência; João autoriza recursos, secrets, custos e rede.

**Paralelizável vs critical path:** observabilidade e manifests podem avançar em paralelo; secret rotation, migration job e backup/restore têm ordem. Restore PASS é critical path staging/produção.

**Stop conditions:** shared secret/DB entre staging/prod; `.env` na imagem; tag mutável no deploy; sem restore; porta DB/Redis pública; app sem readiness; backup não cifrado; custo sem autorização.

**Gates/autorização:** GATE-INFRA-COST, GATE-CREDENTIALS, GATE-BACKUP-RESTORE, GATE-MONITORING, GATE-NETWORK.

**Critérios de aceitação mensuráveis:** ambientes isolados; release por digest; health/readiness de todos os serviços; restore integral PASS; alerts testados; secrets scan zero; DB/Redis inacessíveis externamente; rollback image disponível; RPO/RTO aprovados e medidos.

**Checks futuros:** `docker compose config`; image digest/SBOM/signature; health probes; firewall/socket checks; backup checksum/restore drill; alert test; não imprimir env.

**Artefactos/evidência:** architecture diagram, manifests/IaC, secret inventory sem valores, backup/restore report, monitoring matrix, cost approval e release manifest.

**Riscos e rollback:** hardening pode impedir startup; testar em staging, manter release anterior/dump compatível e rollback automatizado.

**Esforço:** XL; parte do proxy existe, mas não há prova dos restantes controlos.

### STG-12 — Staging público, reversível, UAT e gates do João

**Objetivo:** validar a release candidata num ambiente público separado sem tocar produção.

**Estado atual factual:** PLANNED. A URL pública atual espelha o local e não prova staging separado/reversível.

**Evidência já concluída:** candidato `markee.batata.cc` responde, mas sem environment identity, BD separada, release manifest, restore/rollback ou UAT.

**Tarefas restantes:**

1. Provisionar URL staging aprovada, DNS/TLS e access control; usar BD/secrets próprios.
2. Deployar imagem por digest e migration job a BD vazia; carregar dados sintéticos/anonimizados.
3. Publicar environment banner e impedir robots/indexing/checkout/live notifications.
4. Executar health/readiness, migrations, smoke API/UI, workers e source kill switches.
5. Executar suites E2E/security/perf/a11y autorizadas.
6. Fazer backup staging; executar rollback para release anterior; executar restore para ambiente limpo.
7. Fazer UAT por persona: novo user, PI, team se P0, superuser/admin.
8. Validar copy/legal/consent/billing mode e BPI NO-GO no UI/admin.
9. Corrigir defects via PRs atómicos; redeploy desde zero, sem hotfix manual.
10. Congelar release candidate e obter João UAT PASS.

**Dependências/pré-condições:** STG-00..11 gates P0; evidence pack draft.

**Responsável recomendado:** Spud agenda/orquestra; Forja Sol valida plano/release; Claude Code CLI executa deploy staging após autorização; Max-2 audita; Max valida conteúdo; João executa/aprova UAT.

**Paralelizável vs critical path:** UAT por áreas pode decorrer em paralelo após deploy; fixes têm um writer por tree e regressão total. Staging PASS precede production readiness.

**Stop conditions:** staging partilha BD/secret com produção; dados pessoais reais não autorizados; rollback/restore falha; BPI/checkout/channel externo ativa; defect P0/security; UAT sem João.

**Gates/autorização:** GATE-STAGING-DEPLOY, GATE-STAGING-DATA, GATE-UAT-JOAO, GATE-RELEASE-CANDIDATE.

**Critérios de aceitação mensuráveis:** staging tem identidade/separação; deploy from scratch PASS; rollback e restore PASS; todas as suites/gates PASS; 0 defect P0/P1 não aceite; João UAT PASS; release digest congelado.

**Checks futuros:** DNS/TLS/headers; release endpoint/version; migration current=head; smoke/E2E; worker health; backup/restore/rollback; robots/noindex; BPI negative check.

**Artefactos/evidência:** staging manifest, screenshots, test pack, restore/rollback logs, UAT script/results, defects disposition e sign-off.

**Riscos e rollback:** staging público pode ser confundido com live. Access control, banner/noindex; rollback imediato para digest anterior ou desligar rota.

**Esforço:** L; pressupõe STG-11 concluído.

### STG-13 — Production readiness, DNS/TLS, reverse proxy e go/no-go

**Objetivo:** converter o release candidate aprovado num plano de produção binário.

**Estado atual factual:** PLANNED. DNS/TLS Cloudflare do candidato existe, mas URL final é OPEN DECISION; faltam hardening, environment separation, legal, backups e sign-offs.

**Evidência já concluída:** HTTPS 200, HTTP→HTTPS, certificado observado válido no instante da auditoria; direct `:8000` inacessível externamente; public/local HTML iguais.

**Tarefas restantes:**

1. João confirma URL final e se `markee.batata.cc` deixa de ser dev/staging.
2. Definir TTL/cutover/origin/tunnel/reverse proxy e certificado/renewal monitoring.
3. Preparar produção isolada, secrets novos e BD vazia/target reconciliada.
4. Definir maintenance/read-only/canary strategy e owner por passo.
5. Congelar release digest, migrations, config checksum, SBOM e evidence pack.
6. Criar backup preflight e confirmar restore target.
7. Definir rollback triggers, compatibilidade de schema e comando/owner.
8. Validar monitoring/on-call/status/contact e hypercare rota.
9. Executar checklist NO-GO e reunião go/no-go.
10. Obter sign-offs João, técnico, segurança, dados, legal e operações.

**Dependências/pré-condições:** STG-12 PASS e release freeze.

**Responsável recomendado:** Spud conduz go/no-go; Forja Sol valida tecnicamente; Claude Code CLI prepara comandos sem executar antes do gate; Max-2 verifica pack; Max valida copy; João é autoridade GO.

**Paralelizável vs critical path:** DNS plan, on-call e final pack em paralelo; nenhuma mudança de produção antes de todos os sign-offs. Sequência final é serial.

**Stop conditions:** qualquer checklist NO-GO; final URL/owner desconhecido; TTL/rollback não definido; backup/restore stale; release mudou após UAT; certificado/monitoring não coberto.

**Gates/autorização:** GATE-PROD-READINESS e GO explícito João; DNS/TLS/rede são ações externas mutáveis separadas.

**Critérios de aceitação mensuráveis:** checklist 100% binária PASS; release digest igual ao staging; current=head no clone; backup/restore atual; rollback ensaiado; monitor alerts recebidos; todos os sign-offs registados.

**Checks futuros:** compare digests/config schemas; DNS/TLS/header probes; smoke read-only; backup freshness/checksum; alert route test; final evidence verification.

**Artefactos/evidência:** production change record, DNS/cutover plan, frozen manifest, sign-off matrix, rollback card e hypercare roster.

**Riscos e rollback:** DNS/cache e schema incompatível. TTL planeado, blue/green/canary se suportado, migrations backward-compatible e origin anterior preservada.

**Esforço:** M; preparação, não desenvolvimento P0.

### STG-14 — Go-live controlado

**Objetivo:** executar o cutover com backup, canary, smoke, observabilidade e rollback imediato.

**Estado atual factual:** PLANNED; esta missão não executa deploy/DNS.

**Evidência já concluída:** nenhuma de produção final; apenas probes da instância pública atual.

**Tarefas restantes:**

1. Abrir change window e confirmar GO João/on-call.
2. Confirmar backup consistente, checksum e restore target.
3. Confirmar release digest/config/secrets e kill switches BPI/channels/billing.
4. Executar migration job único; confirmar current=head e invariants.
5. Subir canary/read-only; validar readiness API/DB/Redis/worker/beat.
6. Executar smoke auth/search real/watchlist/alert interno/deadline não-BPI/admin/legal sem gerar ação externa indevida.
7. Alterar proxy/DNS/traffic conforme plano e observar métricas/logs.
8. Confirmar TLS/headers/redirects/docs policy e URL final.
9. João faz owner smoke e sign-off live.
10. Se trigger ocorre, parar tráfego novo e executar rollback; preservar evidência.

**Dependências/pré-condições:** STG-13 GO assinado.

**Responsável recomendado:** Spud orquestra e comunica internamente; Forja Sol valida cada checkpoint; Claude Code CLI executa comandos autorizados; Max-2 observa/evidencia; João dá GO/ABORT.

**Paralelizável vs critical path:** observação por várias pessoas em paralelo; backup→migration→canary→traffic é estritamente serial, um writer operacional.

**Stop conditions:** backup/restore não confirmado; migration falha; current!=head; readiness ou smoke falha; error/latency fora do SLO aprovado; fuga scope; BPI/channel/billing inesperado; perda de observabilidade.

**Gates/autorização:** GATE-PRODUCTION-DEPLOY, GATE-DNS-CUTOVER, GATE-STRIPE-LIVE/canais apenas se incluídos, confirmação por passo destrutivo.

**Critérios de aceitação mensuráveis:** migration/smoke/checklist PASS; release e config correspondem ao manifest; métricas dentro do SLO aprovado; 0 alert de segurança/dados; João sign-off; rollback ainda possível.

**Checks futuros:** comandos do runbook da secção 8; probes externos de duas origens; smoke automatizado; query invariants; observability dashboard.

**Artefactos/evidência:** timestamps UTC, command outputs redigidos, migration ID, release digest, smoke results, traffic change, João sign-off ou rollback report.

**Riscos e rollback:** erro sob tráfego real. Triggers automáticos/manuais, rollback para digest/origin anterior; restore apenas quando rollback de app/schema não basta e com aprovação.

**Esforço:** M; janela operacional com equipa e pré-condições completas.

### STG-15 — Hypercare e transição para operação normal

**Objetivo:** detetar regressões pós-live, responder e fechar a release com evidência.

**Estado atual factual:** PLANNED; owner/on-call/SLO ainda OPEN DECISION.

**Evidência já concluída:** health/logs básicos apenas; insuficientes para hypercare.

**Tarefas restantes:**

1. Ativar roster e canais de incidentes aprovados; não prometer entrega neste terminal.
2. Monitorizar availability, errors, latency, DB/Redis, queue/jobs, source freshness, backups, auth abuse e billing/delivery se ativos.
3. Rever alertas e logs em cadência aprovada; redigir PII/secrets.
4. Executar smoke periódico e reconciliation de dados/Stripe/channels conforme scope.
5. Aplicar incident severity, rollback/disable feature e comunicação aprovada.
6. Confirmar backup seguinte e restore viability.
7. Registar defects; hotfix só por TDD/PR/release, sem edição manual live.
8. Obter feedback João/utilizadores e validar claims.
9. Fazer post-launch review, fechar riscos aceites e atualizar runbook.
10. João encerra hypercare e transfere para operação normal.

**Dependências/pré-condições:** STG-14 live e monitoring.

**Responsável recomendado:** Spud orquestra; Forja Sol lidera validação técnica; Claude Code CLI executa fixes autorizados; Max-2 audita incidentes/dados/claims; Max trata conteúdo; João decide rollback e encerramento.

**Paralelizável vs critical path:** monitorização por domínios em paralelo; um único release writer. Incidente critical interrompe roadmap e torna-se critical path.

**Stop conditions:** incidente security/data/legal; backups falham; source stale sem aviso; errors/SLO breach persistente; BPI/feature blocked ativa; owner ausente. Considerar rollback/maintenance.

**Gates/autorização:** GATE-HYPERCARE-EXIT João; qualquer hotfix/deploy/DNS/paid service exige gate próprio.

**Critérios de aceitação mensuráveis:** janela de hypercare definida e concluída sem incidente critical aberto; SLO/backup/source checks cumpridos; defects triaged; runbook atualizado; João assina exit.

**Checks futuros:** dashboards/alerts; scheduled smoke; backup verification; reconciliation queries; incident log review.

**Artefactos/evidência:** hypercare log, metrics snapshot, incident/postmortem records, defect backlog, updated runbook e exit sign-off.

**Riscos e rollback:** normalizar incidentes por fadiga. Roster/thresholds claros, escalamento e autoridade ABORT do João.

**Esforço:** M; intensidade operacional, duração decidida por risco e não inventada aqui.

## 5. Critical path

### Até staging

`STG-00 contenção` → `STG-02 migrations/secrets` → `STG-03 scope/RBAC` → `STG-04 dados reais sem mock` → `STG-06 core com BPI isolado` → `STG-07 admin/obs` → `STG-08/09 frontend+legal` → `STG-10 evidence pack` → `STG-11 infra/restore` → `STG-12 staging/UAT`.

STG-01 fecha scope antes da integração final. STG-05 segue uma bifurcação: free beta disabled (M) ou Stripe validado (L); não precisa bloquear staging se checkout estiver tecnicamente inacessível e a copy estiver correta.

### Até produção

`STG-12 PASS` → `STG-13 readiness/go-no-go` → `STG-14 cutover` → `STG-15 hypercare`.

Se João exigir BPI operacional, o critical path expande com **todos** `BPI-GATE-01..16`, novo schema/raw archive/extraction/parser/reconciliation/quarantine, fixtures reais e aprovação legal. Até lá, live só é admissível com BPI excluído e tecnicamente disabled.

### Paralelização sem dois writers no mesmo tree

- Max termina `contents/**`; ninguém mais escreve nessa árvore até auditoria PASS.
- Segurança de imagem/infra pode correr em paralelo com suites de API, em branches/worktrees distintas.
- Legal drafting pode correr com engenharia, mas publicação espera data map final.
- Testes de alerts, portfolios e billing podem ser separados por módulos; alterações partilhadas em `app/models/**`, `alembic/**`, `app/tasks/__init__.py` e `frontend/dashboard/app.js` são serializadas.
- Um único writer operacional para migration/deploy/DNS.

### Ordem recomendada de commits/PRs/releases

1. Tests CRITICAL BPI source-deny + kill switch/schedule off.
2. Tests/fix deadline ownership e auth scope.
3. Migration reconciliation/current=head + remover create_all fora dev.
4. Image/secrets/config hardening e `.dockerignore`.
5. Worker event-loop stability + health/readiness.
6. Dados real-vs-mock e provenance/reconciliation.
7. Alerts/delivery/idempotência tests/fixes.
8. Admin backend RBAC/redaction/audit.
9. Billing decision, quotas e Stripe ou disable.
10. Frontend P0 por rota, sem content WIP concorrente.
11. Legal/retention/consent execution.
12. E2E/security/perf/a11y/CI.
13. Infra staging/backups/restore/monitoring.
14. Release candidate staging + UAT fixes atómicos.
15. Production manifest/cutover; depois hypercare releases.

Cada commit é atómico, TDD, suite verde e sem misturar content/migration/infra não relacionados. Não promover o working tree atual com artefactos untracked diretamente.

## 6. Gates e decisões

### Decisões de produto abertas, únicas e deduplicadas

| ID | Tipo | Decisão | Recomendação Max-2 | Owner/gate |
|---|---|---|---|---|
| OD-01 | Produto | Scope live e BPI | Live P0 sem BPI; BPI disabled/NO-GO | João / GATE-PRODUTO |
| OD-02 | Produto/segurança | Pesquisa/detalhe públicos ou privados | Privados P0; público só com rate limit e contrato | João+Forja |
| OD-03 | Comercial | Free/private beta ou Stripe pago | Free beta até core/legal estável; checkout off | João / GATE-BILLING-MODE |
| OD-04 | Produto/infra | URL final e URLs staging/prod | Separar; não chamar à atual URL produção por defeito | João |
| OD-05 | Dados | Fonte real e dataset inicial | EUIPO/TMview autorizada, BPI excluído | João+Max-2 |
| OD-06 | Produto | Teams/portfolios e roles no P0 | Limitar ao necessário; user/team/admin explícitos | João |
| OD-07 | Segurança/produto | Sessão, password, verify/recovery e MFA admin | Política antes de staging; admin MFA recomendado | João+Forja |
| OD-08 | Produto | Email e Telegram no live | Ambos deferred salvo sandbox+delivery PASS | João |
| OD-09 | Comercial | Catálogo, quotas e features por plano | Só vender capacidades validated | João |
| OD-10 | Legal | Controller/contacto/base legal/retenção/subprocessadores | Decisão com profissional qualificado | João/jurídico |
| OD-11 | Privacy/frontend | Analytics, consentimento e CDNs | Sem analytics não essencial até consent; self-host/pin assets | João+Forja |
| OD-12 | Operação | SLO, RPO, RTO, on-call e hypercare window | Quantificar e ensaiar antes de live | João+Forja |
| OD-13 | Admin | Audit export e mutações admin | Export deferred; mutações fora P0 | João |
| OD-14 | Produto | Relatórios/export/prospeção | Deferred após RGPD | João |
| OD-15 | Dados | Dados de staging | Sintéticos/anonimizados, nunca clone PII sem autorização | João/DPO |
| OD-16 | BPI futuro | Prosseguir gates/execução | Só após 16/16 gates e novo GO WITH CHANGES | João |

### Gates técnicos e ações bloqueadas

| Gate | Tipo | Condição | Ação bloqueada até PASS |
|---|---|---|---|
| GATE-BPI-NO-GO | Técnico/legal | Source deny, schedule off; 16 gates continuam blocked | Ingestão/deadline/alerta BPI |
| GATE-CREDENTIALS | Autorização | Secret store, rotação, redaction | Usar/alterar credenciais |
| GATE-CRED-EUIPO | Credencial/rede | Fonte/ToS/custo aprovados | Chamada/import real |
| GATE-STRIPE-TEST/LIVE | Financeiro | Modo, legal, test evidence; live separado | Checkout/cobrança live |
| GATE-EMAIL | Canal | Config, privacy, sandbox e delivery PASS | Envio email |
| GATE-TELEGRAM | Canal | Bot/chat/privacy e delivery PASS | Envio Telegram |
| GATE-RGPD/JURIDICO | Legal | Políticas e execução aprovadas | Produção pública, prospeção/export |
| GATE-STAGING | Técnico | STG-00..11 PASS | Deploy staging |
| GATE-UAT-JOAO | Produto | UAT binário PASS | Freeze release |
| GATE-BACKUP-RESTORE | Operação | Restore recente PASS | Migration/deploy produção |
| GATE-DNS-TLS | Rede | URL, proxy, cert/renewal/rollback aprovados | Cutover DNS/traffic |
| GATE-PRODUCTION | Owner | Evidence pack completo e GO João | Deploy/cutover live |
| GATE-HYPERCARE-EXIT | Owner | Critérios operacionais cumpridos | Encerrar hypercare |
| GATE-COST | Financeiro | Aviso/autor. João se custo esperado >$1 | Serviço/rede paga |

Nenhum valor de credencial deve entrar em docs, outputs, commits ou screenshots. Configured é UNKNOWN até teste seguro; não inferir Stripe/email/Telegram por existirem variáveis.

## 7. Plano de testes e evidência

### Suites atuais verificadas e gaps

| Área | Evidência atual | Gap de release |
|---|---|---|
| Unit | lifecycle, similarity, fonética PT, BPI parser simulado, ingestion, confidence, prospection | Legal/source rules, races, worker stability, billing |
| API integration | health/auth/trademarks com mocks; watchlists com DB real/fallback | Alerts, deadlines scope, portfolios, billing, admin, quality RBAC |
| Schema integration | metadata e PG checks | Migration current=head/zero/clone; execução atual saltou 4 PG checks |
| E2E | Diretório vazio funcionalmente | Todos os fluxos browser P0 |
| Security | Auth básico/ownership watchlists | IDOR global, rate limit, CSRF/XSS/CSP, admin, scans/DAST |
| Performance | Nenhuma suite observada | Search/matching/jobs/API com dataset representativo |
| A11y/responsive | Código tem semântica parcial | axe/manual/browser/visual |
| Infra/data | HTTP/Docker/DB read-only | deploy from zero, backup/restore, rollback, alerts |

Quality gates por stage:

- STG-00: negative proof BPI e mock.
- STG-02: migration/security/image/secrets PASS.
- STG-03: auth/scope matrix PASS.
- STG-04: source contract, idempotência e reconciliation PASS.
- STG-05: free-disabled ou Stripe test matrix PASS.
- STG-06: E2E non-BPI e workers stable PASS.
- STG-07: admin deny/redaction/readiness/audit PASS.
- STG-08/09: E2E UI, a11y, claims e legal execution PASS.
- STG-10: suite agregada, coverage e scans PASS.
- STG-11/12: deploy/restore/rollback/staging UAT PASS.
- STG-13/14: release identity, smoke e go-live checklist PASS.

### Release evidence pack obrigatório

1. Release commit/digest, config schema/checksum e SBOM.
2. Decision log e scope, incluindo BPI disabled e billing/channel modes.
3. JUnit, coverage, E2E, a11y, performance e security reports.
4. Migration zero/clone/current=head e reconciliation reports.
5. Data lineage/source/freshness evidence; mock disabled.
6. RBAC/user-scope/redaction/IDOR report.
7. Backup checksum, restore drill e rollback drill.
8. Staging manifest, HTTP/TLS/headers/smoke and UAT evidence.
9. Legal/RGPD versions, approvals e subprocessors.
10. Monitoring/on-call/alert-route evidence.
11. Go/no-go sign-offs e production change record.
12. Hypercare plan/exit criteria.

## 8. Deploy/runbook resumido — NÃO EXECUTADO

### Preflight

1. Confirmar GO, release digest, evidence pack e ausência de writers paralelos.
2. Confirmar BPI/channel/billing feature flags no modo aprovado sem mostrar values.
3. Confirmar secrets via presence/metadata, nunca dump.
4. Confirmar health do ambiente atual, espaço, DB connections, queue e source freshness.
5. Confirmar backup target/restore owner e rollback release.

Checks template read-only: `git rev-parse HEAD`; `docker image inspect $RELEASE_IMAGE`; `docker compose -f $PROD_COMPOSE config --services`; `alembic current`; `alembic heads`; probes `/health`/readiness; queries de invariants. Variáveis são placeholders do runbook, sem valores secretos.

### Backup e migration

1. Colocar em maintenance/read-only se o plano o exigir.
2. Criar backup consistente cifrado e checksum; copiar para storage aprovado.
3. Validar restore target disponível.
4. Executar migration uma vez com release image; nunca pela app concorrente.
5. Confirmar current=head, schema invariants, contagens e órfãos.

Futuro mutável, só com gate: `pg_dump`/ferramenta aprovada; `alembic upgrade head`. Não executar rollback Alembic automaticamente se migration não for backward-compatible.

### Canary, health e smoke

1. Subir release sem tráfego ou em canary.
2. Readiness deve cobrir API, DB, Redis e workers; liveness isolada não chega.
3. Smoke: landing/legal; register/login/me conforme modo; search real; watchlist; alerta interno; deadline não-BPI scoped; settings billing mode; admin superuser e deny user.
4. Confirmar BPI 0 execução/0 output, channels e Stripe conforme scope.
5. Observar logs/metrics e só depois aumentar tráfego.

### Observabilidade

Vigiar errors/latency/traffic, DB/Redis, worker/beat heartbeat, failed/retried jobs, source freshness, data reconciliation, backup status, auth abuse, billing/webhooks e deliveries se ativos. Ausência de métrica é UNKNOWN, não saudável.

### Rollback

Triggers: migration/smoke/readiness falha; SLO breach; security/data leakage; BPI/feature bloqueada ativa; perda de monitoring. Parar tráfego novo, desligar feature/canal, repor release anterior por digest. Se schema backward-compatible, manter DB e app anterior; se não, seguir restore aprovado com perda/RPO explicitamente aceite. Preservar logs/audit e abrir incidente.

### Restore

Restaurar para ambiente limpo, verificar checksum, migrations, invariants e smoke antes de apontar tráfego. Restore não é sinónimo de backup criado; só um drill PASS conta.

## 9. Go-live checklist binária

Estado inicial de todos os itens: `[ ]` até prova no evidence pack.

| Check | Owner | Prova esperada |
|---|---|---|
| [ ] Scope/decisions P0 assinados; BPI excluído/disabled | João | Decision log |
| [ ] Editorial independente PASS, sem claims falsos | Max-2/Max | Audit report |
| [ ] CRITICAL BPI source guard e schedule off | Forja | Negative tests/config evidence |
| [ ] Deadlines e todos os endpoints user-scoped | Forja | RBAC/IDOR suite |
| [ ] Alembic current=head, sem drift/duplicados não justificados | Forja | Migration report/schema diff |
| [ ] BD target reconciliada e backup preflight | Forja | Counts/reconciliation/checksum |
| [ ] Imagem sem `.env`/secrets, por digest, SBOM/scan PASS | Forja | Image scan/manifest |
| [ ] Defaults dev, reload, mounts e CORS wildcard ausentes | Forja | Config tests/manifest |
| [ ] Rate limits, headers, docs policy e error redaction PASS | Forja | Security tests/HTTP evidence |
| [ ] Fonte real autorizada; mock disabled; freshness visível | Max-2/Forja | Source contract/lineage |
| [ ] Workers/beat stable e observáveis | Forja | Stability/heartbeat report |
| [ ] Billing modo aprovado; Stripe disabled ou validated | João/Forja | Billing decision/test pack |
| [ ] Email/Telegram disabled ou delivery validated individualmente | João/Forja | Channel evidence |
| [ ] Admin P0 read-only/RBAC/redaction/audit PASS | Forja/Max-2 | Admin test pack |
| [ ] Rotas P0/frontend responsive/a11y PASS | Max/Forja | E2E/a11y/visual pack |
| [ ] Privacy/terms/legal/RGPD/retention aprovados e implementados | Jurídico/João | Versioned approvals/tests |
| [ ] Suite total, coverage, security, perf e E2E PASS | Forja/Max-2 | QA pack |
| [ ] Staging separado deploy-from-zero PASS | Forja | Staging manifest |
| [ ] Backup restore e rollback drill PASS | Forja | Drill reports |
| [ ] URL final, DNS/TLS/proxy/renewal monitoring PASS | Forja/João | External probes/change plan |
| [ ] Monitoring/on-call/hypercare owners ativos | Spud/João | Roster/alert test |
| [ ] UAT João PASS no digest final | João | Signed UAT |
| [ ] GO produção explícito e change window aberta | João | Change record |
| [ ] Owner smoke pós-cutover PASS | João/Forja | Production smoke/sign-off |

### Critérios NO-GO inequívocos

É **NO-GO** se qualquer checklist estiver por provar ou se ocorrer um destes pontos: BPI pode gerar deadline/alerta; fuga multi-tenant; current!=head/schema drift; secrets/defaults dev na release; mock parece real; worker critical falha; backup/restore/rollback ausente; legal/RGPD não aprovado; claims falsos; suite/security/a11y/perf gate falha; staging não separado; monitoring/on-call ausente; digest mudou após UAT; João não deu GO.

## 10. Próximas 10 ações

1. **Spud delega à Forja um PR TDD CRITICAL exclusivamente em `app/tasks`, `app/services`, config de schedules e testes:** provar e bloquear BPI→deadlines/alerts, com BPI default-off. Não tocar `contents/**`.
2. **Spud pede à Forja o plano de reconciliação Alembic/BD:** explicar current `001` vs head `002`, tabelas `public` duplicadas e `create_all`; primeiro em clone e com backup.
3. **Spud delega testes/fix de user scope de deadlines e matriz IDOR:** nenhum utilizador pode ler deadlines globais; incluir alerts/portfolios/quality.
4. **João decide contenção da URL pública atual:** access restriction/maintenance até os blockers CRITICAL passarem; nenhuma mudança sem autorização explícita.
5. **Forja corrige supply/secrets da imagem:** `.dockerignore`, excluir `.env`, rebuild/scan, rotação autorizada e fail-fast de defaults dev; não mostrar valores.
6. **Forja estabiliza Celery/async DB:** reproduzir `attached to a different loop`, corrigir e provar runs repetidas de todos os schedules não-BPI.
7. **João decide scope comercial P0:** free beta com checkout off ou Stripe; BPI continua excluído; email/Telegram disabled por defeito.
8. **Depois de o Max terminar, Max-2 faz auditoria independente PASS/FAIL de `contents/**`:** claims, CTAs, estados, rotas e 16 gates; nenhum writer concorrente antes disso.
9. **Forja implementa separação mock/real e contract test da fonte autorizada:** produção sem fallback sintético, com lineage/freshness e reconciliation.
10. **Spud abre o programa de staging por workstreams sem overlap:** admin P0, frontend P0, legal/RGPD, testes/evidence e infra/backup; integrar só depois dos PRs 1–6 verdes.

## 11. Resumo final

O Markee **não é produção live**. É um MVP técnico local com uma cópia development exposta publicamente por HTTPS. Auth/watchlists e partes da ingestão/API/UI existem, mas os blockers de BPI, user scope, migrations, secrets/imagem, workers, dados reais, claims, admin, legal, testes, backup/restore e operação impedem classificação como staging controlado ou produção.

O Markee só pode ser chamado **live** quando: (a) BPI estiver excluído e tecnicamente incapaz de gerar deadlines/alertas, ou todos os gates futuros tiverem sido fechados; (b) isolamento, migrations, dados reais e segurança passarem; (c) billing/channels corresponderem exatamente ao modo aprovado; (d) admin, frontend, legal/RGPD e evidence pack estiverem completos; (e) staging separado passar deploy, restore, rollback e UAT; e (f) o digest final for lançado na URL final com TLS/DNS/monitoring, GO explícito do João e hypercare.

## 12. Registo de validação desta missão

### Comandos read-only executados (resumo)

- Git: `git status --short --branch`, `git log -12 --oneline`, `git diff --stat`, `git diff --name-status`, `git ls-files --others --exclude-standard`.
- Runtime: `docker container ls`, `docker compose ps --format json`, `docker inspect` sem env, `ps`, `ss -ltnp`.
- HTTP/DNS/TLS: `curl` local e público para `/`, `/app/`, `/health`, `/api/v1/health`, `/docs`, `/openapi.json`; `getent ahostsv4`; `openssl s_client`/`x509`; SHA-256 de HTML local vs público.
- Migrations/BD: `alembic current`, `alembic heads`; queries `psql` read-only de schemas, tabelas, counts, source/events/deadlines.
- Workers: `celery inspect ping/active/reserved`; leitura e agregação redigida de `docker logs`.
- Testes: `PYTHONDONTWRITEBYTECODE=1` e PostgreSQL deliberadamente indisponível → `.venv/bin/python -m pytest -q -p no:cacheprovider`.
- Integridade da missão: manifest SHA-256 pre-write dos ficheiros Git tracked/untracked e comparação pós-write; status/diff final.

### Resultados-chave da validação

- Testes nesta auditoria: `142 passed, 4 skipped, 1 warning`; os 4 skips resultam do isolamento deliberado de PostgreSQL. Não substitui a execução PG anterior documentada nem o gate futuro.
- Local e público responderam; HTML de landing e app coincidiu por SHA-256; `markee.batata.cc:8000` não respondeu externamente, enquanto HTTPS standard respondeu.
- Alembic: current `001`, head `002` — FAIL de readiness.
- Runtime data observada: 0 users, 0 trademarks, 0 raw responses, 0 watchlists, 0 alerts, 0 review items, 0 BPI events e 0 deadlines.
- Só este documento foi escrito pelas ferramentas desta missão: o audit trail de escrita reporta apenas `docs/ACTION_PLAN_TO_LIVE.md`. A comparação de manifests detetou uma alteração concorrente em `contents/SITEMAP_CONTENT_MATRIX.md` durante a missão; esse ficheiro pertence ao trabalho WIP do Max e não foi escrito por Max-2. Assim, a autoria desta missão está confirmada pelo audit trail, enquanto o working tree global não permaneceu imóvel.

### Limitações

- Não foram lidos valores de `.env`, tokens, passwords ou headers secretos; estado das integrações reais é UNKNOWN.
- Não foram executadas chamadas autenticadas EUIPO/INPI/Stripe/email/Telegram, deploys, migrations, writes à BD, DNS ou alterações de processos.
- Não foi executada suite contra PostgreSQL nesta missão para evitar writes persistentes; os checks PG foram read-only.
- O snapshot `contents/**` pode mudar após esta auditoria porque o Max está a trabalhar nele.
- Responder 200 por HTTPS prova reachability no instante da consulta, não disponibilidade futura, segurança ou produção.
- O SHA-256 deste próprio ficheiro é reportado externamente após a escrita final para evitar auto-referência impossível. Linhas e bytes são igualmente calculados após validação final.
