# Sitemap content matrix

Fonte estrutural: `../docs/SITEMAP.md`. Estados seguem a regra de `../docs/REQUIREMENTS.md`.

| Rota | Estado | Objetivo do utilizador | Mensagem principal | CTA principal | CTA secundário | Blocos |
|---|---|---|---|---|---|---|
| `/` | `[PARTIAL]` | Perceber o valor e entrar no produto | Monitorizar marcas, rever sinais relevantes e organizar prazos com fonte visível | Começar gratuitamente -> `/app#/login` | Explorar funcionalidades -> `/#funcionalidades` | Header/Nav, Hero, Trust/Proof, FeatureGrid, Workflow, DataSources, Pricing, FAQ, CTA, Footer |
| `/#funcionalidades` | `[PARTIAL]` | Avaliar capacidades | Pesquisa, vigilâncias, prazos e proveniência, distinguindo BPI bloqueado | Entrar -> `/app#/login` | Ver motor -> `/#motor` | FeatureGrid, DataSources, CTA |
| `/#motor` | `[PARTIAL]` | Entender como os dados são tratados | Similaridade e qualidade com fonte/confiança visíveis | Pesquisar no produto -> `/app#/search` | Ver preços -> `/#precos` | Workflow, Trust/Proof, DataSources |
| `/#precos` | `[PARTIAL]` | Comparar planos | Planos disponíveis; billing real não deve ser prometido como validado | Criar conta -> `/app#/login` | Ver termos -> `/terms` `[PLANNED]` | Pricing, FAQ, CTA |
| `/app` | `[IMPLEMENTED]` | Entrar na shell privada | Acesso à aplicação mediante sessão | Iniciar sessão -> `/app#/login` | Ir para painel -> `/app#/dashboard` | AppShell, LoadingSkeleton, ErrorState |
| `/app#/login` | `[IMPLEMENTED]` | Criar conta ou iniciar sessão | Entre para pesquisar, criar vigilâncias e rever alertas | Iniciar sessão -> submit `AuthForm` mode=`login` na própria vista | Criar conta -> alterna `AuthForm` mode=`register` na própria vista | AuthForm, ConfirmDialog, ErrorState |
| `/app#/dashboard` | `[PARTIAL]` | Priorizar trabalho do dia | Resumo de vigilâncias, alertas e prazos disponíveis | Pesquisar marcas -> `/app#/search` | Ver vigilâncias -> `/app#/watchlists` | AppShell, PageHeader, KPI/Stat, AlertItem, DeadlineItem, SourceFreshness, EmptyState |
| `/app#/search` | `[PARTIAL]` — visibilidade `[PLANNED — depende de OD-01]` | Encontrar marcas por texto/jurisdição/classe | Pesquisa na base disponível; ranking avançado ainda parcial | Pesquisar -> submit `SearchForm` na própria vista | Limpar filtros -> reset `Filters` na própria vista | PageHeader, SearchForm, Filters, ResultCard/Table, SourceFreshness |
| `/app#/marks/{application_number}` | `[PLANNED — depende de OD-06]` | Rever detalhe antes de agir | Dados, eventos e proveniência por marca | Adicionar a vigilância -> `/app#/watchlists` | Voltar à pesquisa -> `/app#/search` | MarkSummary, ProvenanceBadge, SourceFreshness, ConfidenceIndicator, Timeline |
| `/app#/watchlists` | `[IMPLEMENTED]` | Gerir vigilâncias e itens | Defina marcas, classes e thresholds a acompanhar | Criar vigilância -> abrir modal/POST `/api/v1/watchlists` na própria vista | Adicionar item -> abrir modal/POST `/api/v1/watchlists/{id}/items` na própria vista | WatchlistCard, SearchForm, ConfirmDialog, EmptyState |
| `/app#/alerts` | `[PARTIAL]` | Rever alertas | Alertas disponíveis no sistema; envio externo não é prometido | Marcar como lido -> POST `/api/v1/alerts/{alert_id}/read` na própria vista | Dispensar -> POST `/api/v1/alerts/{alert_id}/dismiss` na própria vista | AlertItem, Filters, EmptyState, ErrorState, NotificationStatus |
| `/app#/deadlines` | `[PARTIAL]` | Rever prazos próximos | Prazos ajudam a organizar revisão; BPI/PT legal está bloqueado até validação | Rever prazo -> drill-down `/app#/marks/{application_number} [PLANNED]` | Filtrar próximos -> query params `?upcoming_only=true` na própria vista | DeadlineItem, Timeline, SourceFreshness, EmptyState |
| `/app#/leads` | `[PLANNED]` | Explorar oportunidades | Prospeção planeada com filtros RGPD | Ver oportunidades `[PLANNED]` | Exportar `[PLANNED — depende de OD-20]` | PageHeader, Filters, ResultCard/Table, EmptyState |
| `/app#/portfolios` | `[PLANNED]` | Gerir carteiras/clientes | API parcial existe; UI dedicada planeada | Criar portfolio `[PLANNED]` | Associar marca `[PLANNED]` | PageHeader, ResultCard/Table, ConfirmDialog |
| `/app#/reports` | `[PLANNED — depende de OD-02]` | Exportar informação para cliente | Relatórios/export por decidir | Gerar export `[PLANNED — depende de OD-02]` | Voltar ao painel -> `/app#/dashboard` | EmptyState, ConfirmDialog |
| `/app#/settings` | `[PARTIAL]` | Ver conta e plano | Dados de conta e subscrição; Stripe real não validado em produção | Gerir plano -> drill-down `BillingStatus` na própria vista | Terminar sessão -> client-side: remove JWT de `localStorage` e redireciona para `/app#/login`; endpoint `POST /api/v1/auth/logout` `[PLANNED]` | PageHeader, PlanSubscriptionMonitor, UsageLimits, BillingStatus, ErrorState |
| `/app#/admin` | `[PLANNED/BLOCKED]` | Ver estado operacional | Atalho/landing do portal admin P0 read-only; deve redirecionar para `/app#/admin/overview` quando implementado | Ver visão geral -> `/app#/admin/overview` | Ver BPI gates -> `/app#/admin/bpi` | AdminOverview, SystemHealth, BpiPipelineStatus, BpiGateChecklist |
| `/app#/admin/overview` | `[PLANNED]` | Detetar incidentes | Estado API/DB/workers/freshness/falhas quando suportado | Atualizar estado -> refresh in-place | Abrir falhas -> drill-down `/app#/admin/imports` quando existir run falhada; senão listar inline na própria vista | AdminOverview, SystemHealth, DataQualityMetrics |
| `/app#/admin/users` | `[PLANNED]` | Auditar contas sem segredos | Lista redigida de contas, plano e estado | Filtrar utilizadores -> query params na própria vista | Ver detalhe read-only -> drill-down `/app#/admin/users/{user_id} [PLANNED]` | UserAccountTable |
| `/app#/admin/subscriptions` | `[PLANNED]` | Monitorizar planos/uso | Catálogo, subscrições e mock vs Stripe real | Filtrar subscrições -> query params na própria vista | Ver plano -> drill-down `/app#/admin/subscriptions/{user_id} [PLANNED]` | PlanSubscriptionMonitor, UsageLimits, BillingStatus |
| `/app#/admin/sources` | `[PLANNED]` | Ver freshness e erros de fontes | Último sucesso, volumes e erros sem secrets | Atualizar -> refresh in-place | Ver imports -> drill-down `/app#/admin/imports` filtrado pela fonte | SourceFreshnessTable |
| `/app#/admin/imports` | `[PLANNED]` | Auditar execuções de importação | Execuções, progresso, contagens e erros | Ver detalhe -> drill-down `/app#/admin/imports/{run_id} [PLANNED]` | Repetir `[BLOCKED]` | ImportRunTable, ImportRunDetail |
| `/app#/admin/jobs` | `[PLANNED/BLOCKED]` | Ver filas e falhas | Estado Celery/Redis quando API segura existir | Ver falhas -> filtro `?status=failed` na própria vista | Cancelar/repetir `[BLOCKED]` | JobQueue |
| `/app#/admin/quality` | `[PLANNED]` | Ver qualidade/reconciliação | Completude, confiança, duplicados e conflitos | Ver métricas -> drill-down interno na própria vista (detalhe de métrica) | Abrir revisão -> drill-down `/app#/admin/review` quando existirem itens retidos | DataQualityMetrics, ReconciliationSummary |
| `/app#/admin/review` | `[PLANNED/BLOCKED]` | Rever dados retidos | Fila redigida; decisões mutáveis bloqueadas | Ver detalhe -> drill-down `/app#/admin/review/{item_id} [PLANNED/BLOCKED]` | Aceitar/rejeitar `[BLOCKED]` | ReviewQueue, QuarantineDetail |
| `/app#/admin/audit` | `[PLANNED/BLOCKED]` | Rastrear eventos do sistema | Audit append-only redigido | Filtrar eventos -> query params na própria vista | Exportar `[PLANNED — depende de OD-03]` | AuditLog |
| `/app#/admin/bpi` | `[BLOCKED]` | Ver gates BPI | BPI NO-GO até gates 01..16 | Ver gates -> expande checklist na própria vista (drill-down por gate a `docs/REQUIREMENTS.md` §11) | Ativar pipeline `[BLOCKED]` | BpiPipelineStatus, BpiGateChecklist |
| `/privacy` | `[PLANNED/GATE-JURIDICO]` | Ler privacidade/RGPD | Como dados são tratados e minimizados | Contactar -> `mailto:spud@batata.cc` `[PLANNED — depende de OD-16 e GATE-JURIDICO]` | Voltar -> `history.back()` (fallback `/`) | LegalContent, Footer |
| `/terms` | `[PLANNED/GATE-JURIDICO]` | Ler termos | Condições de uso e limites de responsabilidade | Criar conta -> `/app#/login` `[PLANNED/GATE-JURIDICO]` (selecionar registo nessa vista) | Voltar ao início -> `/` | LegalContent, Footer |
| `/legal` | `[PLANNED/GATE-JURIDICO]` | Ler disclaimers | O Markee apoia monitorização; não substitui aconselhamento profissional | Ver privacidade -> `/privacy` `[PLANNED/GATE-JURIDICO]` | Ver termos -> `/terms` `[PLANNED/GATE-JURIDICO]` | LegalContent, Footer |
| `/404` | `[PLANNED — depende de OD-04]` | Recuperar de rota inválida | Página não encontrada | Voltar ao início -> `/` | Voltar ao painel -> `/app#/dashboard` | ErrorState |
| `/500` | `[PLANNED — depende de OD-04]` | Recuperar de falha | Não conseguimos carregar esta área | Tentar novamente -> repetir na própria vista | Voltar -> `history.back()` (fallback `/`) | ErrorState |

Notas:

- `/app#/marks/{application_number}` é declaração de alvo P0. No estado atual `frontend/dashboard/app.js` apenas conhece `/dashboard`, `/search`, `/watchlists`, `/alerts`, `/deadlines`, `/settings`. Detalhe deve ser implementado sem contradizer a API `GET /api/v1/trademarks/{application_number}` que já existe.
- `/app#/admin` e `/app#/admin/overview` partilham copy. Em MVP, `/app#/admin` deve redirecionar para `/app#/admin/overview`.
- `/app#/admin/subscriptions` acrescenta `BillingStatus` para distinguir mock vs Stripe real.
- `/app#/alerts` adiciona `NotificationStatus` para não prometer envio externo.
- `/app#/dashboard` poderá adicionar `SourceFreshness` para atualização visível sem exigir abertura do detalhe, se a OD-10 for aprovada.

## Questões e propostas abertas — secção canónica

Esta é a única secção canónica para OD-01..OD-20. Todas continuam por decidir pelo João. Fora daqui, páginas e blocos referenciam apenas o ID e condicionam qualquer comportamento à respetiva aprovação. Cada entrada separa pergunta, proposta (quando existe) e impacto.

- `OD-01` — Pergunta: pesquisa pública ou privada? Proposta: privada em P0. Impacto: controla autenticação e exposição de titulares, classes e proveniência. Estado: `[OPEN DECISION]`.
- `OD-02` — Pergunta: que formato, permissões e salvaguardas RGPD usar em relatórios/exportação? Proposta: nenhuma fechada. Impacto: `/app#/reports` não pode exportar até definição. Estado: `[OPEN DECISION]`.
- `OD-03` — Pergunta: permitir exportação de auditoria/admin em que formato e com que permissões? Proposta: deferir até existir audit append-only e RBAC. Impacto: exportação permanece bloqueada. Estado: `[OPEN DECISION]`.
- `OD-04` — Pergunta: usar páginas 404/500 dedicadas ou estados SPA? Proposta: dedicadas para 404/500 e inline para os restantes erros. Impacto: determina rotas e recuperação. Estado: `[OPEN DECISION]`.
- `OD-05` — Pergunta: verificação de email bloqueante ou apenas aviso? Proposta: nenhuma enquanto o serviço não existir. Impacto: condiciona acesso pós-registo. Estado: `[OPEN DECISION]`.
- `OD-06` — Pergunta: detalhe de marca em hash ou path real? Proposta: manter hash. Impacto: afeta deep links e router. Estado: `[OPEN DECISION]`.
- `OD-07` — Pergunta: conteúdo legal combinado ou em três páginas? Proposta: três páginas. Impacto: condiciona sitemap e publicação sujeita a GATE-JURIDICO. Estado: `[OPEN DECISION]`.
- `OD-08` — Pergunta: manter referências visíveis a email/Telegram? Proposta: manter texto neutro sem prometer entrega. Impacto: condiciona `NotificationStatus` e copy pública. Estado: `[OPEN DECISION]`.
- `OD-09` — Pergunta: qual o âmbito do KPI `Vigilâncias ativas`? Proposta: por utilizador autenticado. Impacto: define agregação e isolamento. Estado: `[OPEN DECISION]`.
- `OD-10` — Pergunta: quem vê `SourceFreshness` no dashboard? Proposta: apenas `is_superuser`. Impacto: condiciona composição do dashboard e ligação admin. Estado: `[OPEN DECISION]`.
- `OD-11` — Pergunta: que janela usar nos alertas recentes? Proposta: não-lidos, com fallback de sete dias. Impacto: altera seleção e ordenação. Estado: `[OPEN DECISION]`.
- `OD-12` — Pergunta: mostrar `NotificationStatus` sempre ou apenas com canal configurado? Proposta: mostrar sempre enquanto não houver entrega validada. Impacto: altera todos os itens de alerta. Estado: `[OPEN DECISION]`.
- `OD-13` — Pergunta: como separar plano atribuído e catálogo? Proposta: separação visual na mesma página. Impacto: condiciona hierarquia de settings. Estado: `[OPEN DECISION]`.
- `OD-14` — Pergunta: o que mostrar como data quando `BillingStatus=unknown`? Proposta: `Sincronização indisponível`, sem data fictícia. Impacto: condiciona o campo de sincronização. Estado: `[OPEN DECISION]`.
- `OD-15` — Pergunta: upgrade por checkout ou contacto? Proposta: manter checkout desativado até validação real. Impacto: condiciona CTA e fluxo de upgrade. Estado: `[OPEN DECISION]`.
- `OD-16` — Pergunta: que canal usar em `Contactar` nas páginas legais? Proposta: `mailto:spud@batata.cc` enquanto não houver canal dedicado. Impacto: condiciona CTAs legais. Estado: `[OPEN DECISION]`.
- `OD-17` — Pergunta: quando apresentar banner de consentimento? Proposta: apenas se existirem cookies analíticos, de marketing ou de terceiros. Impacto: condiciona banner e reabertura de preferências. Estado: `[OPEN DECISION]`.
- `OD-18` — Pergunta: que destino usar para pedidos de eliminação? Proposta: rota dedicada ou canal de contacto, ainda sem escolha. Impacto: CTA permanece planeado até política aprovada. Estado: `[OPEN DECISION]`.
- `OD-19` — Pergunta: thresholds de atualização globais ou por fonte? Proposta: valores comuns com eventual configuração por fonte. Impacto: define estados e alertas de atualização. Estado: `[OPEN DECISION]`.
- `OD-20` — Pergunta: que formato, permissões e salvaguardas RGPD usar na exportação de leads? Proposta: nenhuma fechada. Impacto: exportação permanece planeada. Estado: `[OPEN DECISION]`.

Estados técnicos fora da lista OD (não são decisões de produto):

- `/app#/admin` como alias — estado técnico documentado: `/app#/admin` redireciona para `/app#/admin/overview` (ver linha 23 e nota 2); não é decisão aberta.
- BPI no filtro de prazos vencidos — estado-alvo obrigatório: ocultar prazos BPI após source guard testado. Estado atual: o backend pode produzi-los/expô-los; até correção, BPI permanece NO-GO/BLOCKED/CRITICAL e não pode ser promovido/live. Não é uma OD.
- Dismiss idempotency — DOCUMENTADO: já implementado em `app/api/alerts.py:89-100` (atribuição `is_dismissed=True`); é gate técnico, não decisão de produto.
- `BillingStatus` em settings vs admin — estado técnico documentado: matriz, `UI_BLOCKS.md` e a própria página exigem ambos.
- Heartbeat sem API — DOCUMENTADO: capacidade fica `[PLANNED/BLOCKED]`; UI não pode mostrar heartbeat sem API segura.
- Drill-down BPI para REQUIREMENTS ou página interna — estado técnico documentado: destino `docs/REQUIREMENTS.md` §11 (ver `BpiGateChecklist` em `UI_BLOCKS.md` e `pages/ADMIN_PORTAL.md`).

## Navegação relacionada

- [`README.md`](README.md) — convenções editoriais e taxonomia de estados.
- [`UI_BLOCKS.md`](UI_BLOCKS.md) — catálogo canónico de blocos referenciados nesta matriz.
- [`CONTENT_PRINCIPLES.md`](CONTENT_PRINCIPLES.md) — princípios de redação e tom.
- [`GLOSSARY.md`](GLOSSARY.md) — termos canónicos PT-PT/EN.
- [`pages/PUBLIC_LANDING.md`](pages/PUBLIC_LANDING.md) — landing pública (`/`, `/#funcionalidades`, `/#motor`, `/#precos`).
- [`pages/AUTH_ONBOARDING.md`](pages/AUTH_ONBOARDING.md) — `/app#/login` e blocos `AuthForm`.
- [`pages/DASHBOARD.md`](pages/DASHBOARD.md) — `/app#/dashboard`.
- [`pages/SEARCH_MARK_DETAIL.md`](pages/SEARCH_MARK_DETAIL.md) — `/app#/search` e `/app#/marks/{application_number}`.
- [`pages/WATCHLISTS_ALERTS_DEADLINES.md`](pages/WATCHLISTS_ALERTS_DEADLINES.md) — `/app#/watchlists`, `/app#/alerts`, `/app#/deadlines`.
- [`pages/SETTINGS_BILLING.md`](pages/SETTINGS_BILLING.md) — `/app#/settings`.
- [`pages/LEGAL_ERRORS.md`](pages/LEGAL_ERRORS.md) — `/privacy`, `/terms`, `/legal`, `/404`, `/500` e blocos `LegalContent`/`ErrorState`.
- [`pages/ADMIN_PORTAL.md`](pages/ADMIN_PORTAL.md) — portal admin P0 (10 domínios, 16 gates BPI).
- [`../docs/SITEMAP.md`](../docs/SITEMAP.md) — sitemap canónico de rotas (fonte estrutural).
- [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) — estados, requisitos FR/NFR e gates BPI.
- [`../docs/STATUS.md`](../docs/STATUS.md) — estado atual dos entregáveis.
