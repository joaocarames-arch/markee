# Admin portal P0

Rotas: `/app#/admin`, `/app#/admin/overview`, `/app#/admin/users`, `/app#/admin/subscriptions`, `/app#/admin/sources`, `/app#/admin/imports`, `/app#/admin/jobs`, `/app#/admin/quality`, `/app#/admin/review`, `/app#/admin/audit`, `/app#/admin/bpi`.

Estado factual: portal admin P0 completo não está implementado. As peças backend existentes e os endpoints de qualidade/saúde não equivalem a RBAC/admin validado. Alvo: `[PLANNED/BLOCKED]`; BPI: `[BLOCKED]`, `NO-GO`, risco `CRITICAL`.

Logout atual: o browser remove localmente o JWT, limpa `state.user` e navega para `/app#/login`; não existe blacklist, revogação ou chamada ao backend. Um endpoint `POST /api/v1/auth/logout` permanece `[PLANNED]`.

Requisitos: `FR-ADMIN-001..011`, `NFR-ADMIN-SEC-001`, `NFR-ADMIN-TEST-001`, `NFR-OBS-001`, `NFR-QUALITY-001`, `NFR-IDEMP-001`.

## Regra central

O portal admin P0 é monitorização read-only por defeito. Serve para auditar plataforma, qualidade dos dados, fontes, importações, filas, planos e gates BPI. Não substitui Datadog, Stripe Dashboard ou pgAdmin.

Mutações como retry, replay, cancel, repair, accept/reject, role changes, plan changes, enable/disable source e reprocessamento de webhook ficam `[BLOCKED]` até existirem, em conjunto:
- idempotência da operação e da API;
- RBAC e testes deny/allow por role;
- confirmação explícita do utilizador;
- audit log append-only;
- redaction de secrets, tokens, headers sensíveis e PII;
- rate limit e least privilege;
- testes integração e e2e.

| Read-only P0:
| `read-only P0`: alvo da monitorização no portal admin; não existe portal admin operacional no SPA atual. Tudo o que aparece como "read-only P0" aqui é referência ao alvo, não a uma área já servida.
| `PLANNED`: alvo decidido, ainda sem contrato ou UI.
| `BLOCKED`: depende de idempotência, audit, confirmação e policy.

## Shell admin

H1:
`Admin`

Subtítulo:
`Monitorização operacional da plataforma.`

Intro:
`Veja saúde, fontes, importações, qualidade, filas, contas e gates. Ações mutáveis só aparecem quando forem seguras, auditadas e testadas.`

CTA primário:
`Atualizar estado`

CTA secundário:
`Ver BPI gates` -> `/app#/admin/bpi`

Bloco:
- `AdminOverview` com cards agregadores.
- Topbar mostra role (`superuser/admin`) e correlation_id de auditoria quando existir.
- `ErrorState` global se qualquer agregador falhar.

Permission denied:
`Não tem permissões para aceder ao portal admin.`

## Navegação admin

- `Visão geral` -> `/app#/admin/overview`
- `Utilizadores` -> `/app#/admin/users`
- `Planos e utilização` -> `/app#/admin/subscriptions`
- `Fontes` -> `/app#/admin/sources`
- `Importações` -> `/app#/admin/imports`
- `Tarefas e filas` -> `/app#/admin/jobs`
- `Qualidade` -> `/app#/admin/quality`
- `Revisão` -> `/app#/admin/review`
- `Registo de auditoria` -> `/app#/admin/audit`
- `Gates BPI` -> `/app#/admin/bpi`

Mobile:
Tabs compactas ou menu lateral colapsável; manter `Visão geral` e `Gates BPI` sempre acessíveis em dois cliques.

## Visão geral e saúde `/app#/admin/overview` `[PLANNED]`

Objetivo:
Detetar rapidamente se há incidente operacional.

H1:
`Visão geral`

Subtítulo:
`Estado geral da API, dados e processos.`

Blocos:
- `SystemHealth`: API, DB, Redis, worker, beat quando suportado.
- `SourceFreshnessTable` resumo: última atualização por fonte.
- `DataQualityMetrics`: accepted/review/quarantine, completeness/confidence.
- Lista das últimas falhas conhecidas (runs/jobs) quando endpoints existirem.

Copy obrigatória:
`A visão geral mostra os sinais operacionais disponíveis quando os endpoints existem. A ausência de métricas não significa que o sistema esteja saudável.`

Estados:
- Loading: `A verificar saúde operacional.`
- Empty: `Ainda não há métricas agregadas.`
- Warning: `Algumas integrações não expõem heartbeat seguro.`
- Error: `Não conseguimos carregar a visão geral de administração.` CTA `Tentar novamente`.
- Stale data: `Métricas sem atualização desde {date}.`

Read-only P0:
- `Atualizar estado` (refresh manual).
- Filtros por janela temporal.

Bloqueado:
- `Reiniciar worker`.
- `Limpar fila`.
- `Forçar sync`.
- Qualquer mutação sobre workers, Redis ou DB.

## Utilizadores/contas `/app#/admin/users` `[PLANNED]`

Objetivo:
Auditar contas, estado e plano sem expor segredos.

H1:
`Utilizadores`

Subtítulo:
`Contas registadas e estado básico.`

Bloco:
- `UserAccountTable` densa com redaction obrigatória (`email` redigível quando necessário, sem password/hash/token).

Colunas:
- `Email` (redigível).
- `Nome`.
- `Empresa`.
- `Ativo/inativo`.
- `is_superuser`.
- `Plano resumido`.
- `Criado em / atualizado em`.

Ajuda:
`Palavras-passe, hashes, tokens, secrets e cabeçalhos sensíveis nunca aparecem nesta tabela.`

Read-only P0:
- Filtrar, ordenar, paginar.
- Abrir detalhe read-only com `app.subscriptions` resumido.
- Drill-down para `/app#/admin/subscriptions` por utilizador.

Bloqueado:
- Ativar/desativar utilizador.
- Alterar perfil.
- Reset password.
- Impersonar sessão.

## Planos/subscrições/utilização `/app#/admin/subscriptions` `[PLANNED]`

Objetivo:
Ver catálogo, subscrições e consumo sem confundir mock com cobrança real.

H1:
`Planos e utilização`

Subtítulo:
`Catálogo, subscrições e limites registados.`

Blocos:
- `PlanSubscriptionMonitor` em modo admin (lista paginada).
- `UsageLimits` por subscrição quando existirem contagens (`max_marks`, `max_users`, `max_clients`).
- `BillingStatus` por subscrição com `Modo de billing`, `Estado checkout`, `Estado webhook` e data da última sincronização.

Copy obrigatória:
`Mostrar claramente se billing está em modo mock/dev ou Stripe real validado.`

Não inventar:
- MRR.
- Receita.
- Churn.
- Pagamentos confirmados.
- Webhook receipts além do que está registado.

Read-only P0:
- Filtrar por plano, estado (`active`/`trialing`/`past_due`/`canceled`/`unknown`).
- Drill-down por subscrição com `BillingStatus` detalhado.

Bloqueado:
- Alterar plano manualmente.
- Reprocessar webhook.
- Emitir reembolso.
- Forçar `real-verified` em `BillingStatus`.

## Fontes/atualização dos dados `/app#/admin/sources` `[PLANNED]`

Objetivo:
Saber que fontes estão configuradas, quando atualizaram e que erros tiveram.

H1:
`Fontes`

Subtítulo:
`Atualização, volumes e último erro por fonte.`

Bloco:
- `SourceFreshnessTable` com labels visíveis: `Fonte`, `Modo/ativo`, `Último sucesso`, `Estado de atualização`, `Volumes por camada`, `Último erro` (redigido).

Copy:
`Secrets, tokens, headers sensíveis e payloads perigosos ficam redigidos.`

Read-only P0:
- Filtrar por estado `fresh`/`stale`/`failed`/`unknown`.
- Drill-down por fonte para `ImportRunTable` quando existir run.

Bloqueado:
- Enable/disable source.
- Alterar configuração (`urls`, `rate_limit`, `parser_version`).
- Forçar run.
- Editar secrets.

## Importações/execuções da fonte `/app#/admin/imports` `[PLANNED]`

Objetivo:
Auditar execuções de ingestão/importação.

H1:
`Importações`

Subtítulo:
`Execuções por fonte, janela, duração, contagens e erros.`

Blocos:
- `ImportRunTable` densa.
- `ImportRunDetail` (drawer/página) com metadados, parser_version, contagens e erros redigidos.

Colunas da tabela:
- `ID da execução`
- `Fonte`
- `Estado`
- `Janela`
- `Início/fim/duração`
- `Processados/novos/atualizados/falhados`
- `Analisador/versão` quando disponível
- `Último erro redigido`

Detalhe:
`Mostra contagens, erros e ligações para raw/reconciliation quando existirem.`

Read-only P0:
- Filtrar por fonte, estado, janela temporal.
- Abrir detalhe com erros redigidos.

Bloqueado:
- `Repetir`/`Reexecutar` até existirem idempotência, auditoria, confirmação e política.

## Tarefas/filas/falhas `/app#/admin/jobs` `[PLANNED/BLOCKED]`

Objetivo:
Ver filas, processos e falhas sem permitir cancelamento inseguro.

H1:
`Tarefas e filas`

Subtítulo:
`Estado dos processos assíncronos quando houver API segura.`

Bloco:
- `JobQueue` com labels visíveis `Fila`, `Estado`, `Sinal de atividade`, `Em execução`, `Falhadas`, `Mensagens não processadas`.

Copy:
`Sem API segura de filas, esta área só pode mostrar estado agregado ou ficar bloqueada.`

Read-only P0 (quando implementado):
- Visualizar filas e sinal de atividade dos processos.
- Visualizar mensagens não processadas em agregado.

Bloqueado:
- Cancelar tarefa.
- Repetir tarefa.
- Limpar mensagens não processadas.
- Reencaminhar mensagem.

## Qualidade dos dados/reconciliação `/app#/admin/quality` `[PLANNED]`

Objetivo:
Ver qualidade, conflitos e dados que precisam de revisão.

H1:
`Qualidade dos dados`

Subtítulo:
`Completude, confiança, proveniência e reconciliação.`

Blocos:
- `DataQualityMetrics` com labels visíveis `Completude`, `Confiança`, `Aceites`, `Em revisão`, `Em quarentena`, `Duplicados` e `Conflitos`.
- `ReconciliationSummary` por fonte e campo.
- Links para `ReviewQueue` quando houver itens retidos.

Copy:
`Conteúdos brutos não devem ser renderizados como HTML. Mostrar excertos redigidos e metadados seguros.`

Read-only P0:
- Filtrar por fonte, run, campo.
- Ver detalhe de reconciliation read-only.

Bloqueado:
- `Reparar`/`Reconciliar` automaticamente.
- Alterar thresholds.
- Mover item entre filas.

## Revisão/quarentena `/app#/admin/review` `[PLANNED/BLOCKED]`

Objetivo:
Ver itens retidos por baixa confiança, conflito ou contrato incompleto.

H1:
`Revisão e quarentena`

Subtítulo:
`Itens que não devem entrar automaticamente nos dados principais.`

Blocos:
- `ReviewQueue` densa.
- `QuarantineDetail` (painel/página) com conteúdo redigido, motivo, execução e confiança.

Colunas da tabela:
- `Item`
- `Fonte/execução`
- `Tipo`
- `Confiança`
- `Motivo`
- `Criado em`
- `Estado`

Detalhe:
`Conteúdo redigido, origem, motivo da quarentena/revisão, confiança e ligação à execução.`

Read-only P0:
- Filtrar por estado, fonte, banda de confiança.
- Abrir detalhe redigido.

Bloqueado:
- `Aceitar`/`Rejeitar`/`Reparar`/`Reexecutar` até existirem política, auditoria, confirmação e testes.

## Auditoria/eventos do sistema `/app#/admin/audit` `[PLANNED/BLOCKED]`

Objetivo:
Rastrear eventos administrativos e operacionais críticos.

H1:
`Registo de auditoria`

Subtítulo:
`Eventos append-only redigidos.`

Bloco:
- `AuditLog` tabela com `timestamp`, `actor`, `action`, `resource`, `result`, `correlation_id`, `IP/user-agent` (redigidos quando necessário).

Copy:
`O registo de auditoria não permite edição nem eliminação através da interface. Eventos são append-only e redigidos quando necessário.`

Read-only P0 (quando implementado):
- Filtrar por actor, ação, recurso, janela temporal.
- Drill-down por correlation_id.

Bloqueado:
- `Exportar auditoria` até decisão RGPD/segurança.
- Editar/apagar eventos.
- Reordenar entradas.

## Pipeline/gates BPI `/app#/admin/bpi` `[BLOCKED]`

Objetivo:
Mostrar claramente que BPI operacional está em NO-GO e o que falta.

H1:
`Pipeline BPI`

Subtítulo:
`NO-GO até validação dos gates BPI.`

Intro:
`O analisador legado e a investigação documental não autorizam pipeline operacional. Descoberta, arquivo PDF bruto, extração por página, normalização, reconciliação, quarentena e prazos BPI continuam bloqueados até BPI-GATE-01..16.`

CTA primário:
`Ver checklist de gates`

CTA secundário:
`Voltar à visão geral` -> `/app#/admin/overview`

Blocos:
- `BpiPipelineStatus` com cards por estágio (`discovery`, `raw archive PDF`, `extraction por página`, `parsing P0`, `normalization`, `reconciliation`, `confidence/quarantine`, `RGPD/custo`, `deadlines/alertas BPI`).
- `BpiGateChecklist` com as 16 entradas canónicas.

Estágios:
- Discovery `[BLOCKED]`
- Raw archive PDF `[BLOCKED]`
- Extraction por página `[BLOCKED]`
- Parsing P0 `[BLOCKED]`
- Normalization `[BLOCKED]`
- Reconciliation `[BLOCKED]`
- Confidence/quarantine `[BLOCKED]`
- RGPD/custo `[BLOCKED]`
- Deadlines/alertas BPI `[BLOCKED]`

### `BpiGateChecklist` (16 gates)

Lista canónica a apresentar no UI. Cada entrada tem `gate_id`, `requirement`, `status`, `evidence_link`, `owner_decision`.

- `BPI-GATE-01` - congelar deadlines/alertas BPI por defeito com regra versionada `legal_status=draft|validated`, `enabled=false`, aprovador, data e base jurídica; nada cria `app.deadlines`/alertas BPI antes de validação. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11. Decisão: `[BLOCKED]`.
- `BPI-GATE-02` - escolher uma única semântica temporal validada para PT; remover o conflito `+2 meses civis` vs `+60 dias` em contrato, código e testes. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; auditoria BPI CRITICAL. Decisão: `[BLOCKED]`.
- `BPI-GATE-03` - definir migrations P0 para `raw.bpi_bulletins`, `raw.bpi_page_extractions` e staging/versionamento de eventos BPI, com constraints, FKs, índices e unicidade transacional. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-002`, `FR-BPI-003`. Decisão: `[BLOCKED]`.
- `BPI-GATE-04` - definir onde vivem `dedupe_key`, `parser_version`, `field_confidence`, reconciliation, supersession e quarantine; não depender apenas de JSON/`raw_data`. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-005`, `FR-BPI-007`. Decisão: `[BLOCKED]`.
- `BPI-GATE-05` - tornar arquivo concorrente seguro com unique constraint/upsert, `archive_version`, republicação/supersession e URLs alternativas. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-002`. Decisão: `[BLOCKED]`.
- `BPI-GATE-06` - reconciliar os 11 campos YAML ausentes (`change_date`, `correction_date`, `deferral_date`, `legal_notice`, `licence_scope`, `licensee_name`, `licensor_name`, `opponent_name`, `opposition_date`, `opposition_reference`, `request_date`) no contrato ou removê-los da taxonomia. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-005`. Decisão: `[BLOCKED]`.
- `BPI-GATE-07` - formalizar required fields por evento, incluindo expressão de recusa como `refusal_date OR legal_basis_text` se essa for a decisão; eventos inválidos são recusados/quarantined. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-004`, `FR-BPI-005`. Decisão: `[BLOCKED]`.
- `BPI-GATE-08` - corrigir exemplos JSON para serem válidos segundo o contrato, incluindo campos non-null como `id`, `bulletin_id`, `parser_name`, `raw_text_hash` e `quarantine_status` quando exigidos. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-005`. Decisão: `[BLOCKED]`.
- `BPI-GATE-09` - unificar source enums e event types canónicos (`inpi_bpi`/`bpi_pdf` ou decisão única documentada) e mapear/migrar tipos legacy (`publication`, `grant`, `provisional_refusal`, etc.). Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-005`. Decisão: `[BLOCKED]`.
- `BPI-GATE-10` - definir thresholds gap-free: `score >= 0.85`, `0.65 <= score < 0.85`, `score < 0.65`, com comportamento de alerta/review/quarantine em cada faixa e runtime alinhado. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-007`. Decisão: `[BLOCKED]`.
- `BPI-GATE-11` - codificar ST.17/aliases como heurísticas no YAML: `match_mode`, scope obrigatório de secção, corroboradores e confidence caps. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-004`. Decisão: `[BLOCKED]`.
- `BPI-GATE-12` - mover `opposition_filed` para P2/disabled até existirem fixtures reais, ou justificar e alinhar todos os roadmaps. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11. Decisão: `[BLOCKED]`.
- `BPI-GATE-13` - corrigir mapping de deadlines para a tabela real `app.deadlines` ou criar migration para modelo desejado com FK a `events.lifecycle_events`; não usar mapping documental divergente. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-DEADLINE-002`. Decisão: `[BLOCKED]`.
- `BPI-GATE-14` - reconciliar marcas por `(jurisdiction, application_number)`/registration number com constraints adequadas; matching por nome isolado é proibido. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-006`. Decisão: `[BLOCKED]`.
- `BPI-GATE-15` - acrescentar guards de paginação/convergência, robots recheck/kill switch, limite máximo de páginas, deteção de loops e orçamento por run; alinhar retry/backoff com `sources.yaml`. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-001`, `NFR-COST-001`. Decisão: `[BLOCKED]`.
- `BPI-GATE-16` - documentar política RGPD e custo total operacional antes de ativar prospeção, OCR ou retenção indefinida: base jurídica, roles/auditoria, retenção, encriptação/supressão, DPIA/LIA, storage/backups/OCR/review humana/observabilidade. Estado: `blocked`. Evidência: `docs/REQUIREMENTS.md` §11; `FR-BPI-008`, `NFR-GDPR-001`, `NFR-COST-001`. Decisão: `[BLOCKED]`.

Warning visível:
`Não ativar ingestão, prazos ou alertas BPI a partir deste ecrã.`

Bloqueado:
- Ativar pipeline.
- Processar boletim.
- Gerar prazos.
- Libertar quarentena.

## Estados globais admin

Loading:
`A carregar dados administrativos.`

Empty:
`Ainda não há dados para esta vista.`

Success:
`Dados administrativos atualizados.`

Warning:
`Algumas métricas dependem de endpoints ainda planeados.`

Error:
`Não conseguimos carregar esta área admin.` CTA `Tentar novamente`.

Permission denied:
`Não tem permissões para aceder ao portal admin.`

Stale data:
`Última atualização conhecida: {date}. Pode haver estado operacional mais recente fora do Markee.`

## Questões abertas

As questões de produto são definidas apenas pelos IDs canónicos em [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md). Esta página não cria nem reabre decisões. Ver `OD-03` e `OD-19`; qualquer comportamento dependente permanece condicionado à respetiva aprovação.

## Navegação relacionada

- [`../README.md`](../README.md) — convenções editoriais e taxonomia de estados.
- [`../UI_BLOCKS.md`](../UI_BLOCKS.md) — catálogo canónico de blocos referenciados (Admin P0, `BpiPipelineStatus`, `BpiGateChecklist`, `ReviewQueue`, `QuarantineDetail`, `AuditLog`).
- [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) — matriz rota → blocos, inclui os 10 domínios admin.
- [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md) — princípios de redação e tom.
- [`../GLOSSARY.md`](../GLOSSARY.md) — termos canónicos PT-PT/EN.
- [`../pages/PUBLIC_LANDING.md`](PUBLIC_LANDING.md) — landing pública.
- [`../pages/AUTH_ONBOARDING.md`](AUTH_ONBOARDING.md) — `/app#/login` e bloco `AuthForm`.
- [`../pages/DASHBOARD.md`](DASHBOARD.md) — `/app#/dashboard`.
- [`../pages/WATCHLISTS_ALERTS_DEADLINES.md`](WATCHLISTS_ALERTS_DEADLINES.md) — `/app#/watchlists`, `/app#/alerts`, `/app#/deadlines`.
- [`../pages/SETTINGS_BILLING.md`](SETTINGS_BILLING.md) — `/app#/settings` e billing.
- [`../pages/LEGAL_ERRORS.md`](LEGAL_ERRORS.md) — `/privacy`, `/terms`, `/legal`, `/404`, `/500`.
- [`../../docs/SITEMAP.md`](../../docs/SITEMAP.md) — sitemap canónico de rotas.
- [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md) — requisitos `FR-ADMIN-*`, `NFR-ADMIN-*`, `NFR-OBS-001`, `NFR-QUALITY-001`, `NFR-IDEMP-001` e §11 (gates BPI).
- [`../../docs/STATUS.md`](../../docs/STATUS.md) — estado atual dos entregáveis.
- [`../../docs/SCHEMA_DESIGN.md`](../../docs/SCHEMA_DESIGN.md) — schemas `core.sources`, `core.source_runs`, `app.subscriptions`, `app.review_queue`, etc.
- [`../../docs/BACKLOG.md`](../../docs/BACKLOG.md) — backlog operacional.
