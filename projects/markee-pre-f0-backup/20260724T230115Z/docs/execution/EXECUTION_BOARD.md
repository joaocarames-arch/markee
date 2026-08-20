# EXECUTION BOARD — markee (STG-00..STG-15)

- Working directory: `/home/batata/projects/markee`
- Perfil: Max-2 (papel crítico/read-only)
- Data UTC inicial: 2026-07-24T20:47Z
- Plano canónico: `docs/ACTION_PLAN_TO_LIVE.md` (HEAD `51aa7d0e057479275df7955f1fa7c8cbdd711d4c`)
- Snapshot base: `docs/execution/STG-00_CONTAINMENT_AUDIT.md` (BLOCKED)
- Snapshot editorial: `docs/execution/STG-01_EDITORIAL_PRODUCT_SIGNOFF.md` (READY_FOR_JOAO, OPEN GATE-PRODUTO-JOAO e GATE-JURIDICO)
- Estado atual: `not_started | in_progress | blocked | ready_for_review | done`
- Sem percentagens. Cada linha indica owner funcional e gate; nunca "progresso inventado".

## 0. Leituras obrigatórias antes de mexer

- STG-00 contém o veredicto factual de contenção: BPI tecnicamente capaz (schedule, ingestion, deadlines, dispatch); checkout mock alcançável; `/api/v1/billing/plans` público; `/api/v1/trademarks` com fallback mock; imagem contém `/app/.env` (sha256 `64cf63b6…3b83`); URL pública expõe `markee.batata.cc` e `app.markee.batata.cc` via Cloudflare Tunnel sem Access policy; BD observada vazia (0 rows) — **isso não constitui controlo BPI**; backup/manifest ausentes. Ver `STG-00_CONTAINMENT_AUDIT.md`.
- STG-01 confirma auditoria independente final PASS sobre `contents/**` (13 ficheiros, hash agregado `e139b99e24777209dc9dbad89916d4620b6874f2254c0d274a96847a68e1a509`), mas **STG-01 continua READY_FOR_JOAO**: OD-01..OD-20 abertas, copy revista ainda não aplicada na landing servida, GATE-PRODUTO-JOAO e GATE-JURIDICO OPEN. Ver `STG-01_EDITORIAL_PRODUCT_SIGNOFF.md`.
- Não há overlap de writers: `contents/**` é árvore única do Max; código/config/testes/infra são árvores da Forja/Fable; auditoria/board/evidence são da Max-2; gates finais são do João.
- Toda a coluna "próxima tarefa" abaixo é **bounded** (entradas/saídas/condições de paragem). Nada do que está marcado como `not_started` foi iniciado.

## 1. Conventions

- **Owner funcional** (papel, não pessoa atribuída): `Spud` (orquestração), `Max` (conteúdo), `Max-2` (auditoria/board/evidence), `Forja`/`Fable` (código+TDD), `João` (autorização e decisão).
- **Gate**: nome curto do gate aplicável; sem gate ⇒ empty.
- **Artefacto esperado**: o que deve aparecer em `docs/execution/` ou `docs/` quando o estado avança.
- **Critérios de saída**: lista binária (sem "quase" ou "bom o suficiente").
- **Última evidência**: caminho do ficheiro/probe/observação mais recente, datada em UTC.

## 2. Tabela consolidada STG-00..STG-15

| Stage | Título curto | Estado | Última evidência | Critical path / dependências | Próxima tarefa (bounded) | Owner | Gate | Artefacto esperado | Critérios de saída |
|---|---|---|---|---|---|---|---|---|---|
| STG-00 | Baseline congelada e contenção imediata | `blocked` | `docs/execution/STG-00_CONTAINMENT_AUDIT.md` (2026-07-24T20:47Z) | Self; alimenta STG-02..06 | Criar `tests/stg00/` com 8 failing tests (BPI source deny + kill switch + schedule off + dispatch deny + default-off). PR CRITICAL non-content. NÃO tocar runtime/schedule/imagem. | Forja/Fable | GATE-JOAO-CONTENCAO; GATE-CREDENTIALS (rotacionar antes da WP3) | `tests/stg00/test_bpi_*.py` + relatório WP1 | 8 testes verde; `grep` confirma 4+ flags BPI; `inspect scheduled` sem `parse-bpi-daily` em modo `BPI_ENABLED=False`; `.env` ausente da imagem de release; `/api/v1/billing/plans` 410 em free-beta; landing sem claims proibidos; dump baseline + MANIFEST anexados |
| STG-01 | Fecho de contratos e aprovação editorial | `ready_for_review` | `docs/execution/STG-01_EDITORIAL_PRODUCT_SIGNOFF.md` (2026-07-24) | STG-00 não bloqueia conteúdo; dependente de decisão João | João responde OD-01..OD-20 e aprova scope freeze; Max-2 aplica delta documentado no STG-01; copy anti-claims instalada na landing | Spud (orquestra), Max (copy pós-decisão), Max-2 (auditoria), Forja (claims→copy→UI→teste), João (autoridade) | GATE-PRODUTO-JOAO; GATE-EDITORIAL-PASS; GATE-JURIDICO (legal) | Decision log OD; release scope freeze assinado; landing com copy aprovada | 0 claims proibidos positivos; OD obrigatórias com owner/data; copy instalada igual ao pacote `contents/`; `/app#/settings` com `BillingStatus` correto; `MailTo provisório` se OD-16 aprovado |
| STG-02 | Segurança base e integridade de migrations/BD | `blocked` | plano §STG-02; Docker/compose lidos em STG-00 | STG-00 snapshot (BD+imagem); OD-04 (URL) | (a) migration `upgrade` zero→head com schema diff 0; (b) reconciliação current=001 vs head=002; (c) `.dockerignore` + `.env` fora; (d) startup falha com secret default/CORS wildcard/URL dev; (e) CORS allowlist; (f) rate limits; (g) headers CSP/HSTS/nosniff/frame/referrer/permissions; (h) SBOM + scan | Forja/Fable; Max-2 audita; João autoriza | GATE-BACKUP-BEFORE-MIGRATION; GATE-CREDENTIALS; GATE-SECURITY-PASS | `tests/integration/test_migrations_zero_to_head.py`; ADR migration; SBOM; scan report; redaction policy | 0 critical/high não aceites; BD vazia→head sem diff; clone atual→head sem perda; `.env`/`secret` ausente da imagem; default inseguro rejeitado em startup; 429 tests; headers conferidos |
| STG-03 | Auth, user scope, teams e RBAC | `blocked` | plano §STG-03; `app/api/auth.py`, `watchlists.py`, `deadlines.py` | STG-02; decisão OD-02 (pesquisa/detalhe); OD-07 (sessão) | Matriz rota×anónimo×userA×userB×team×superuser; deny-first tests em deadlines, alerts, portfolios, quality, billing, admin; `require_superuser` aplicado; sessão cookie+CSRF ou localStorage com mitigação CSP/XSS; redacção de PII em logs | Forja/Fable; Max-2 revê; João decide produto | GATE-AUTH-PRODUTO; GATE-RBAC-PASS | matriz rota/scope; deny tests; IDOR report; ADR sessão | user A não lê/escreve B; admin anónimo/user=401/403; inativo bloqueado em cada pedido; recovery/session policy assinada; logs sem PII |
| STG-04 | Dados reais não-BPI, seed e reconciliação | `blocked` | plano §STG-04; `app/services/euipo_service.py`, `ingestion.py` | STG-02; STG-03 scope; OD-05 (fonte/ToS); BPI excluído | (a) separar modos `mock/dev`, `staging synthetic`, `production real`; (b) contract tests sandbox/read-only; (c) cursor/retries/pagination caps; (d) kill switch por source; (e) seed só para classes/config; (f) import autorizado + reconciliation report; (g) raw partitionamento contínuo; (h) freshness/stale visível | Spud; Forja planeia; Fable executa; Max-2 valida fontes/proveniência; João autoriza custo | GATE-CRED-EUIPO/REDE; GATE-DATASET; GATE-COST se >$1 | contract; ToS review; reconciliation report; lineage; seed manifest; freshness policy | mock disabled em produção; cada registo real liga a source/run/raw/version; reexecução idempotente; orphan/failure visíveis; freshness mostrada; UAT dataset aprovado |
| STG-05 | Billing, Stripe, catálogo e quotas | `blocked` | plano §STG-05; `app/api/billing.py`, `services/billing.py`; `/api/v1/billing/plans` 200 público | STG-01 catálogo; STG-02 secrets; STG-03 ownership; STG-09 termos | João decide OD-15/OD-03 (free beta disabled vs Stripe); reconciliar `PLAN_LIMITS` com capacidade real; remover/deferir white-label/reports/SSO/API/WIPO/Telegram; `BillingStatus` inequívoco; quotas com testes concorrentes; idempotency keys + event ledger; UAT financeiro em modo test | Spud; Forja; Fable; Max-2 audita; João decide | GATE-BILLING-MODE; GATE-STRIPE-TEST; GATE-STRIPE-LIVE; GATE-LEGAL-BILLING | decision log; catálogo assinado; webhook event matrix; quota report; test receipts sem PII/secrets | 1 modo exposto; 0 claims falsos; quotas com testes concorrentes; Stripe test matrix PASS; free-beta 0 CTA cobrança acessível |
| STG-06 | Vigilâncias, matching, alertas e prazos com BPI isolado | `blocked` | plano §STG-06; `app/tasks/match_similar.py`, `calculate_deadlines.py`, `check_expiry.py`, `send_alerts.py` | STG-02/03/04; STG-00 WP1 (source deny) | (a) implementar primeiro source-deny tests do WP1; (b) feature registry de deadline rules com source/jurisdiction/version/legal_status/enabled; (c) todas BPI rules `enabled=false`; (d) corrigir ownership/user scope de deadlines; (e) corrigir worker async loop; (f) E2E não-BPI ingest→match→alert interno→read/dismiss; (g) tests alerts/deadlines (auth, ownership, sort, filter, idempotência); (h) dedupe concorrente com constraint/idempotency key; (i) `sent_at` só quando política de canais é satisfeita; (j) admin read-only de runs/matching/deadline rules/deliveries | Forja planeia; Fable executa; Max-2 valida isolamento BPI; João aprova canais | BPI NO-GO; GATE-DEADLINE-LEGAL por rule; GATE-EMAIL; GATE-TELEGRAM | rule registry; legal approvals; E2E trace; worker stability report; delivery evidence; BPI negative-proof report | 0 BPI→deadline/alert; E2E não-BPI PASS; deny multi-user PASS; worker estável em janela UAT; deadline com owner/source/rule version; delivery states correspondem a evidência |
| STG-07 | Portal admin P0 read-only, observabilidade e audit | `blocked` | plano §STG-07; `app/api/quality.py`, `services/quality.py` | STG-02/03; STG-01; STG-04/06 dados/worker | (a) contratos admin versionados redigidos: overview/users/subscriptions/sources/imports/jobs/quality/review/audit/BPI gates; (b) `require_superuser` + deny tests; (c) readiness DB/Redis/worker/beat; (d) endpoints paginados read-only; (e) heartbeat/jobs view; cancel/retry disabled; (f) audit append-only; (g) BPI NO-GO + 16 gates sem botão de ativação; (h) SPA admin + estados loading/empty/error/stale/403; (i) structured logs + correlation/request ID + métricas + alertas | Spud; Forja; Fable; Max-2 audita redaction/gates/BPI; João confirma scope | GATE-ADMIN-SCOPE; GATE-RBAC-PASS; GATE-OBSERVABILITY; GATE-COST se monitoring pago | OpenAPI admin; RBAC/redaction report; screenshots; audit schema/ADR; alert routes; operator guide | 10 domínios P0 com vista/estado; anónimo/user negados; superuser permitido; redaction tests PASS; readiness deteta dependência down; audit append-only; 0 mutações admin; BPI mostra 16/16 blocked |
| STG-08 | Frontend/UX, conteúdo, responsive e acessibilidade | `blocked` | plano §STG-08; `frontend/landing/*`, `frontend/dashboard/*`; `contents/pages/*` PASS | STG-01 (copy); STG-03..07 (APIs); STG-09 (legal) | (a) aplicar só conteúdo com auditoria PASS; (b) remover claims não comprovados; (c) detalhe de marca com proveniência e sem eventos BPI acionáveis; (d) integrar admin P0; (e) legal/error routes; (f) `BillingStatus`/`NotificationStatus`/source/rule status nos alertas/prazos; (g) validar CTAs/deep links + 404/403/500/503; (h) XSS/DOM injection + CSP; (i) self-host/pin assets; (j) mobile/tablet/desktop + a11y axe/Lighthouse/keyboard/screen reader; (k) SEO/canonical/OG só na URL final | Max (conteúdo); Forja revê arquitetura; Fable implementa; Max-2 audita claims; João UX gate | GATE-EDITORIAL-PASS; GATE-UX-JOAO; GATE-A11Y; GATE-LEGAL-PUBLISH | route screenshots; a11y report; browser matrix; content audit PASS; CTA/link report; visual baselines | todas as rotas P0 navegáveis; 0 links/CTAs mortos; 0 axe critical/serious; keyboard-only completa fluxos; 0 claims proibidos positivos; fontes/mock/freshness visíveis |
| STG-09 | Legal, RGPD, retenção, consentimento e políticas | `blocked` | plano §STG-09; `contents/pages/LEGAL_ERRORS.md`, `CONTENT_PRINCIPLES.md` | STG-01 scope; STG-04/06/07 data map | (a) controller/contacto/finalidades/bases legais/categorias; (b) mapear flows/storage/logs/backups/Stripe/email/Telegram/CDNs/monitoring como subprocessadores; (c) retenção por tabela/raw/log/backup; (d) direitos de acesso/retificação/apagamento/portabilidade/oposição + processo verificável; (e) LIA/DPIA em prospeção/BPI/contactos; (f) manter prospeção/BPI PII disabled até aprovação; (g) consentimento analytics/marketing; (h) publicar privacy/terms/legal/disclaimers/cookies/subprocessadores/versões; (i) rever billing/SLA/disponibilidade/responsabilidade por prazos/fonte oficial; (j) revisão profissional qualificado + João; (k) testar UI/backend cumprem políticas | Spud coordena DPO/jurídico; Max estrutura copy; Max-2 verifica claims/evidência; Forja mapeia execução; Fable implementa controlos; João aprova | GATE-JURIDICO; GATE-RGPD; GATE-PROSPETION; GATE-BPI-16; GATE-CONSENT; GATE-LEGAL-BILLING | RoPA/data map; retention schedule; subprocessors list; LIA/DPIA decision; legal versions; request runbook; approvals | data map cobre stores/flows; políticas versionadas e acessíveis; subprocessadores ativos listados; pedidos RGPD ensaiados E2E; retenção testada; consentimento respeitado; sign-off jurídico + João |
| STG-10 | Testes, quality gates e release evidence pack | `blocked` | plano §STG-10; `pytest` 144 passed / 2 skipped / 1 warning (venv local); execução isolada anterior 142/4/1 | STG-02..09; CI inexistente; E2E/admin/legal/security/perf/a11y gaps | (a) fixar matriz de ambientes; (b) eliminar asserts permissivos; (c) tests alerts/deadlines/portfolios/teams/billing/admin; (d) BPI negative + pipeline não-BPI E2E; (e) migration zero/clone + restore drill; (f) E2E P0 + smoke público; (g) SAST/dependency/image/secret scan + DAST em staging; (h) SLO/perf budgets; (i) a11y automatizada/manual + browser matrix; (j) coverage services ≥80%; (k) CI com artefactos imutáveis; (l) release evidence pack + revisão independente PASS | Spud; Forja; Fable; Max-2 audita; Max visual; João SLO/UAT | GATE-QA-PASS; GATE-SECURITY-PASS; GATE-PERF-SLO; GATE-A11Y; GATE-COST se DAST/perf pago | JUnit/coverage; scan reports; E2E vídeo/screenshots; perf report; a11y report; migration/restore report; test environment manifest; QA sign-off | 0 falhas; 0 skips inesperados; 0 flaky não resolvido; coverage services ≥80%; 0 critical/high não aceite; fluxos P0 E2E PASS; budgets aprovados; evidence pack completo |
| STG-11 | Fundação infra, secrets, containers, backups e monitoring | `blocked` | plano §STG-11; compose local + cloudflared | STG-02; OD-04 (URL); OD-12 (SLO/RPO/RTO); legal retention | (a) topologia local/staging/prod; (b) compose/manifests sem bind mounts/reload + imagens por digest; (c) health/readiness app/worker/beat + restart + limits; (d) secret store/injection; `.env` fora da imagem; rotação; least privilege DB/Redis; (e) DB/Redis isolados; TLS/reverse proxy/Cloudflare com origin policy; (f) migrations como job único; (g) backups encrypted DB+raw; (h) restore drill medindo RPO/RTO; (i) logs centralizados redigidos + métricas + alertas; (j) release registry + SBOM + signing/provenance; (k) documentar capacity/cost; avisar antes de >$1 | Spud; Forja; Fable; Max-2 audita; João autoriza | GATE-INFRA-COST; GATE-CREDENTIALS; GATE-BACKUP-RESTORE; GATE-MONITORING; GATE-NETWORK | architecture diagram; manifests/IaC; secret inventory sem valores; backup/restore report; monitoring matrix; cost approval; release manifest | ambientes isolados; release por digest; health/readiness todos os serviços; restore integral PASS; alerts testados; secrets scan zero; DB/Redis inacessíveis externamente; rollback image disponível; RPO/RTO aprovados e medidos |
| STG-12 | Staging público, reversível, UAT e gates do João | `not_started` | plano §STG-12; candidato `markee.batata.cc` responde | STG-00..11 gates P0; evidence pack draft | (a) URL staging aprovada + DNS/TLS + access control; BD/secrets próprios; (b) deploy imagem por digest + migration job a BD vazia; (c) environment banner + robots/noindex + checkout/live notifications off; (d) health/readiness + migrations + smoke API/UI + workers + source kill switches; (e) E2E/security/perf/a11y autorizados; (f) backup staging; rollback release anterior; restore ambiente limpo; (g) UAT por persona; (h) validar copy/legal/consent/billing mode + BPI NO-GO; (i) corrigir defects via PRs atómicos; (j) congelar release candidate + João UAT PASS | Spud agenda; Forja valida plano; Fable executa após autorização; Max-2 audita; Max valida conteúdo; João UAT | GATE-STAGING-DEPLOY; GATE-STAGING-DATA; GATE-UAT-JOAO; GATE-RELEASE-CANDIDATE | staging manifest; screenshots; test pack; restore/rollback logs; UAT script/results; defects disposition; sign-off | staging com identidade/separação; deploy from scratch PASS; rollback/restore PASS; suites/gates PASS; 0 defect P0/P1 não aceite; João UAT PASS; release digest congelado |
| STG-13 | Production readiness, DNS/TLS, reverse proxy e go/no-go | `not_started` | plano §STG-13; HTTPS 200 público | STG-12 PASS; release freeze | (a) João confirma URL final; (b) TTL/cutover/origin/tunnel/reverse proxy/cert/renewal; (c) produção isolada + secrets novos + BD target; (d) maintenance/read-only/canary + owner por passo; (e) congelar release digest + migrations + config checksum + SBOM + evidence pack; (f) backup preflight + restore target; (g) rollback triggers + schema compat + comando/owner; (h) monitoring/on-call/status/contact + hypercare rota; (i) checklist NO-GO + go/no-go meeting; (j) sign-offs João + técnico + segurança + dados + legal + operações | Spud conduz; Forja valida; Fable prepara comandos; Max-2 verifica pack; Max valida copy; João GO | GATE-PROD-READINESS; GO explícito João; DNS/TLS/rede | production change record; DNS/cutover plan; frozen manifest; sign-off matrix; rollback card; hypercare roster | checklist 100% binária PASS; release digest = staging; current=head no clone; backup/restore atual; rollback ensaiado; monitor alerts recebidos; todos sign-offs |
| STG-14 | Go-live controlado | `not_started` | plano §STG-14 | STG-13 GO assinado | (a) change window + GO João/on-call; (b) backup consistente + checksum + restore target; (c) release digest/config/secrets + kill switches BPI/channels/billing; (d) migration job único + current=head; (e) canary/read-only + readiness API/DB/Redis/worker/beat; (f) smoke auth/search real/watchlist/alert interno/deadline não-BPI/admin/legal sem ação externa indevida; (g) proxy/DNS/traffic conforme plano; (h) TLS/headers/redirects/docs policy + URL final; (i) João owner smoke + sign-off live; (j) rollback imediato se trigger | Spud; Forja; Fable (apenas comandos autorizados); Max-2 observa; João GO/ABORT | GATE-PRODUCTION-DEPLOY; GATE-DNS-CUTOVER; GATE-STRIPE-LIVE/canais se incluídos; confirmação por passo destrutivo | timestamps UTC; command outputs redigidos; migration ID; release digest; smoke results; traffic change; João sign-off ou rollback report | migration/smoke/checklist PASS; release/config = manifest; métricas dentro do SLO; 0 alert security/data; João sign-off; rollback ainda possível |
| STG-15 | Hypercare e transição para operação normal | `not_started` | plano §STG-15 | STG-14 live + monitoring | (a) roster e canais aprovados; (b) monitor availability/errors/latency/DB/Redis/queue/sources/backups/auth/billing; (c) rever alertas e logs redigidos; (d) smoke periódico + reconciliation; (e) incident severity + rollback/disable + comunicação aprovada; (f) backup seguinte + restore viability; (g) defects triaged; hotfix só TDD/PR/release; (h) feedback João/utilizadores; (i) post-launch review; (j) João encerra hypercare | Spud orquestra; Forja lidera; Fable executa fixes autorizados; Max-2 audita; Max trata conteúdo; João decide rollback/exit | GATE-HYPERCARE-EXIT João; qualquer hotfix/deploy/DNS/paid = gate próprio | hypercare log; metrics snapshot; incident/postmortem; defect backlog; runbook; exit sign-off | janela definida e concluída sem critical aberto; SLO/backup/source checks cumpridos; defects triaged; runbook atualizado; João assina exit |

## 3. Critical path

### Até staging

`STG-00 contenção` → `STG-02 migrations/secrets` → `STG-03 scope/RBAC` → `STG-04 dados reais sem mock` → `STG-06 core com BPI isolado` → `STG-07 admin/obs` → `STG-08/09 frontend+legal` → `STG-10 evidence pack` → `STG-11 infra/restore` → `STG-12 staging/UAT`.

STG-01 fecha scope antes da integração final. STG-05 bifurca: free beta disabled (M) ou Stripe validado (L); não bloqueia staging se checkout inacessível e copy correta.

### Até produção

`STG-12 PASS` → `STG-13 readiness/go-no-go` → `STG-14 cutover` → `STG-15 hypercare`.

BPI operacional exige os 16 `BPI-GATE-01..16`, novo schema/raw archive/extraction/parser/reconciliation/quarantine, fixtures reais e aprovação legal. Default: **BPI excluído e tecnicamente disabled**.

### Paralelização sem dois writers na mesma árvore

- `contents/**` é árvore única do Max; ninguém mais escreve até auditoria PASS.
- Imagem/infra/segurança podem avançar em paralelo com suites de API em worktrees distintas.
- Legal drafting pode correr com engenharia; publicação espera data map final.
- Tests alerts/portfolios/billing separados por módulo; partilhas em `app/models/**`, `alembic/**`, `app/tasks/__init__.py` e `frontend/dashboard/app.js` são serializadas.
- Um único writer operacional para migration/deploy/DNS.

### Ordem recomendada de commits/PRs/releases

1. Tests CRITICAL BPI source-deny + kill switch/schedule off.
2. Tests/fix deadline ownership e auth scope.
3. Migration reconciliation/current=head + remover `create_all` fora dev.
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

Cada commit atómico, TDD, suite verde, sem misturar content/migration/infra não relacionados. Não promover o working tree atual com artefactos untracked diretamente.

## 4. Decisões abertas que afetam o board

`OD-01..OD-16` (plano §6) e `OD-17..OD-20` (STG-01 editorial) continuam **OPEN**. Default se João não decidir: **fail-closed** (não activar capacidade dependente, não publicar claim, não ampliar scope).

Mapa OD→stage (recomendação Max-2):

- OD-01 (scope live e BPI) → STG-01/00/06 — recomenda live P0 sem BPI; BPI disabled/NO-GO.
- OD-02 (pesquisa/detalhe público/privado) → STG-03/08 — recomenda privado em P0.
- OD-03 (free beta vs Stripe) → STG-05 — recomenda free beta até core/legal estável; checkout off.
- OD-04 (URL final e URLs staging/prod) → STG-11/13 — separar; não chamar à atual URL produção por defeito.
- OD-05 (fonte real e dataset inicial) → STG-04 — recomenda EUIPO/TMview autorizada, BPI excluído.
- OD-06 (teams/portfolios/roles no P0) → STG-03/08 — limitar ao necessário.
- OD-07 (sessão, password, verify/recovery, MFA admin) → STG-03 — política antes de staging; admin MFA recomendado.
- OD-08 (email/Telegram no live) → STG-06/11 — ambos deferred salvo sandbox+delivery PASS.
- OD-09 (catálogo, quotas e features por plano) → STG-05 — só vender capacidades validadas.
- OD-10 (controller/contacto/base legal/retenção/subprocessadores) → STG-09 — decisão com profissional qualificado.
- OD-11 (analytics, consentimento e CDNs) → STG-08/09 — sem analytics não essencial; self-host/pin assets.
- OD-12 (SLO, RPO, RTO, on-call, hypercare window) → STG-11/15 — quantificar e ensaiar.
- OD-13 (admin audit export e mutações admin) → STG-07 — export deferred; mutações fora P0.
- OD-14 (relatórios/export/prospeção) → STG-04/06/08 — deferred após RGPD.
- OD-15 (dados de staging) → STG-12 — sintéticos/anonimizados.
- OD-16 (BPI futuro) → STG-00/06 — só após 16/16 gates e novo GO WITH CHANGES.
- OD-17..OD-20 (STG-01) — banner consentimento, pedidos eliminação, thresholds atualização, export de leads — todas com default fail-closed, nenhuma implementada sem decisão.

## 5. Gates ativos (resumo)

| Gate | Tipo | Bloqueia |
|---|---|---|
| GATE-BPI-NO-GO | técnico/legal | ingestão/deadline/alerta BPI |
| GATE-CREDENTIALS | autorização | usar/alterar credenciais |
| GATE-CRED-EUIPO | credencial/rede | chamada/import real |
| GATE-STRIPE-TEST/LIVE | financeiro | checkout/cobrança live |
| GATE-EMAIL / GATE-TELEGRAM | canal | envio externo |
| GATE-RGPD / GATE-JURIDICO | legal | produção pública, prospeção/export |
| GATE-STAGING | técnico | deploy staging |
| GATE-UAT-JOAO | produto | freeze release |
| GATE-BACKUP-RESTORE | operação | migration/deploy produção |
| GATE-DNS-TLS | rede | cutover DNS/traffic |
| GATE-PRODUCTION | owner | deploy/cutover live |
| GATE-HYPERCARE-EXIT | owner | encerrar hypercare |
| GATE-COST | financeiro | serviço/rede paga se >$1 |
| GATE-JOAO-CONTENCAO | operacional | restrição URL/serviços |
| GATE-EDITORIAL-PASS / GATE-PRODUTO-JOAO | editorial/produto | publicação copy |

## 6. Próximas ações imediatas (esta semana)

Ordem proposta; nenhuma executada por esta missão.

1. **João** decide `GATE-JOAO-CONTENCAO` e `GATE-CREDENTIALS` (STG-00 WP3+rotação). `GATE-COST` não aplicável.
2. **Forja/Fable** abre worktree `stg00-bpi-containment`; cria `tests/stg00/` com 8 failing tests; PR CRITICAL non-content; **não** toca `contents/**`, runtime, schedules, imagem ou BD.
3. **Max-2** (esta missão) acompanha revisão de evidência pós-implementação de WP1, sem promover estados por inferência.
4. **Spud** regista em `docs/execution/DECISION_LOG.md` (a criar) a resposta de João a OD-01..OD-20 e a autorização de contenção/rotação; **não** criar conteúdo novo de produto.
5. **Max** mantém-se em standby pós-`contents/**` PASS; nenhuma segunda escrita até aplicação da copy aprovada (STG-01 delta).
6. **Forja/Fable** abre worktrees paralelas `stg00-mock-checkout`, `stg00-image-secrets`, `stg00-baseline-db` após WP1 red.

## 7. Limitações e honestidade

- Não li valores de `.env`, tokens, segredos, JWT ou PII. Presenças confirmadas via `test -e`/`env` truncado a 2 chars.
- Não toquei código, config, testes, runtime, schedules, migrations, imagens, contentores, DNS, backup ou BD.
- Não fiz `git add`, `git commit`, `git push`, `docker build`, `docker pull`, `docker compose up/down/restart`, `celery …` mutável, `alembic`, `pg_dump`, `psql` write, `apt`, `pip install`, `npm`.
- Estados `not_started` não foram iniciados. Nenhum item do board foi promovido por inferência.
- Conteúdo editorial marcado como PASS vem de `STG-01_EDITORIAL_PRODUCT_SIGNOFF.md`; STG-01 mantém-se **READY_FOR_JOAO**, com OD-01..OD-20 abertas e GATE-PRODUTO-JOAO/GATE-JURIDICO ainda por assinar. **Não** confundir PASS editorial com aprovação de live.
- `inspect scheduled` "empty" durante a STG-00 não é prova de schedule desativada. Schedule está carregada no worker/beat; o que falta é gate/flag/test.
- BD observada vazia é facto, mas **não** é controlo BPI. O pipeline BPI pode inserir eventos a qualquer batida.
- Backup/manifest ausentes. STG-00 recomenda dump antes de qualquer correção; **não** foi produzido nesta missão.
- URLs `markee.batata.cc` e `app.markee.batata.cc` estão live; este board não as altera nem restringe.
- Nenhum cost >$1 é recomendado. `GATE-COST` continua OPEN e exige autorização antes de qualquer despesa.

## 8. Hashes before/after

- Hash before (snapshot `docs/execution/` antes desta missão):

```
784a587a22d54f6498154a2107ca581da6a770bfd514d6777d0be638d2b15d1a  docs/execution/STG-01_EDITORIAL_PRODUCT_SIGNOFF.md
```

- Hash after (estado canónico do ficheiro no disco, calculado em 2026-07-24T20:55Z, fim desta missão). Este é o hash que deve ser comparado com `sha256sum docs/execution/EXECUTION_BOARD.md` para verificação independente:

```
ee8e89c4bda6860c807cbdabbc4859af81694ed78bc1a4ca434478dcc11ae2c2  docs/execution/EXECUTION_BOARD.md
```

- Hash after do relatório STG-00 (estado canónico no disco):

```
b790589764f6786fd115d13e7bbf629ee26b8453394a817dd62390d2cb9903c1  docs/execution/STG-00_CONTAINMENT_AUDIT.md
```

- Diff vs estado pré-missão: apenas dois paths novos (`docs/execution/STG-00_CONTAINMENT_AUDIT.md`, `docs/execution/EXECUTION_BOARD.md`). Nenhum ficheiro pré-existente foi tocado.
- Apenas dois ficheiros novos em `docs/execution/`:
  1. `docs/execution/STG-00_CONTAINMENT_AUDIT.md`.
  2. `docs/execution/EXECUTION_BOARD.md` (este).
- Nenhum outro path foi criado, alterado ou removido.

## 9. Anexos

### A.1 Mapa state→owner

| Estado | Owner típico | Próximo estado natural |
|---|---|---|
| not_started | Spud agenda | in_progress |
| in_progress | Forja/Fable executa | ready_for_review |
| ready_for_review | Max-2 audita | blocked (re-trabalha) ou done |
| blocked | João/owner explícito | in_progress quando desbloqueado |
| done | Max-2 assina evidência | só regressão ou novo gate |

### A.2 Anti-claims operacionais (sempre)

- Nada é "live" sem `live` na matriz e sem UAT do João em staging separado.
- Nada é "seguro" sem `GATE-SECURITY-PASS` assinado e evidência recente.
- Nada é "validado" só por `pytest` local; suites têm de incluir PG clone, E2E browser, perf, a11y, scans.
- Nada é "real" sem source/run/provenance; mock/dev nunca apresentado como real.
- Nada é "entregue" sem delivery evidence; canais externos continuam deferred por default.
- Nada é "oficial" sem GATE-JURIDICO; prazos/oposição BPI são NO-GO por default.
- Nada é "produção" sem staging PASS + João UAT + checklist NO-GO 100% PASS.
