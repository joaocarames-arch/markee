# UI blocks

Catálogo canónico de blocos. Não é design system completo; é inventário editorial/UI para reutilização.

Campos padrão por bloco: propósito, páginas, conteúdo/props, dados/API/tabela, variants, estados, interação, permissões, responsivo, acessibilidade, dependências.

## Público

### Header/Nav
- Propósito: navegação pública e entrada no produto.
- Páginas: `/`, anchors landing.
- Conteúdo/props: logo, links, CTA `Entrar`, menu mobile.
- Dados/API/tabela: nenhum.
- Variants: desktop pill, mobile drawer.
- Estados: sticky/transparent/scrolled.
- Interação: abrir menu, saltar para anchors.
- Permissões: público.
- Responsivo: links colapsam em menu.
- Acessibilidade: `nav`, `aria-expanded`, skip link.
- Dependências: assets de logo.

### Hero
- Propósito: explicar proposta de valor e levar a `/app#/login`.
- Páginas: `/`.
- Conteúdo/props: H1, subtítulo, micro-label, CTA primário/secundário, nota de estado.
- Dados/API/tabela: nenhum.
- Variants: cinematic desktop, fallback mobile.
- Estados: loading visual, reduced motion.
- Interação: CTAs.
- Permissões: público.
- Responsivo: reduzir texto e motion.
- Acessibilidade: H1 único, contraste, motion respeita preferências.
- Dependências: BRAND tokens, scripts atuais se mantidos.

### Trust/Proof
- Propósito: provas factuais sem claims proibidos.
- Páginas: `/`, `/#motor`.
- Conteúdo/props: bullets com estado interno, evidência resumida.
- Dados/API/tabela: docs/testes como referência, não API.
- Variants: strip, cards.
- Estados: n/a.
- Interação: links para secções.
- Permissões: público.
- Responsivo: cards empilhados.
- Acessibilidade: lista semântica.
- Dependências: `SITEMAP.md`, `REQUIREMENTS.md`.

### FeatureGrid
- Propósito: apresentar capacidades por área.
- Páginas: `/#funcionalidades`.
- Conteúdo/props: título, descrição, estado interno, CTA.
- Dados/API/tabela: rotas existentes/planeadas.
- Variants: cards, painéis horizontais.
- Estados: disabled para `[BLOCKED]`.
- Interação: abrir rota/anchor.
- Permissões: público.
- Responsivo: grid -> lista.
- Acessibilidade: headings por card.
- Dependências: matriz de sitemap.

### Workflow
- Propósito: mostrar fluxo pesquisar -> vigiar -> rever -> agir.
- Páginas: `/`, `/#motor`.
- Conteúdo/props: steps, descrição, estado/fonte.
- Dados/API/tabela: nenhum direto.
- Variants: timeline horizontal/vertical.
- Estados: planned/blocked badges.
- Interação: links para rotas.
- Permissões: público.
- Responsivo: vertical mobile.
- Acessibilidade: ordered list.
- Dependências: statuses.

### DataSources
- Propósito: explicar fontes e limitações.
- Páginas: `/`, `/#motor`, `/#funcionalidades`.
- Conteúdo/props: fonte, estado, freshness copy, blockers.
- Dados/API/tabela: `core.sources`, `core.source_runs` `[PLANNED admin]` quando no produto.
- Variants: public summary, admin table link.
- Estados: active/partial/blocked/stale.
- Interação: abrir admin BPI para admins.
- Permissões: público no resumo; detalhe admin.
- Responsivo: cards.
- Acessibilidade: estado textual além de cor.
- Dependências: BPI gates.

### Pricing
- Propósito: comparar planos sem prometer billing real.
- Páginas: `/#precos`, settings.
- Conteúdo/props: nome, preço, limites, CTA, nota mock/real.
- Dados/API/tabela: `/api/v1/billing/plans`, `PLAN_META`.
- Variants: public cards, app compact.
- Estados: loading/error/mock.
- Interação: criar conta/checkout.
- Permissões: público para catálogo; checkout privado.
- Responsivo: cards empilhados.
- Acessibilidade: tabela/lista clara.
- Dependências: billing service `[PARTIAL]`.

### FAQ
- Propósito: responder objeções e limites.
- Páginas: `/`.
- Conteúdo/props: pergunta, resposta, links.
- Dados/API/tabela: nenhum.
- Variants: accordion/list.
- Estados: aberto/fechado.
- Interação: expandir.
- Permissões: público.
- Responsivo: accordion mobile.
- Acessibilidade: buttons com `aria-expanded`.
- Dependências: legal copy.

### CTA
- Propósito: ação final contextual.
- Páginas: públicas e empty states.
- Conteúdo/props: título, texto, CTA primário/secundário.
- Dados/API/tabela: rotas.
- Variants: public/app/admin warning.
- Estados: normal/disabled/blocked.
- Interação: navegar.
- Permissões: conforme rota.
- Responsivo: largura total mobile.
- Acessibilidade: label específico.
- Dependências: matriz CTA.

### Footer
- Propósito: links finais, legal e marca.
- Páginas: públicas/legais.
- Conteúdo/props: logo, links, disclaimers curtos.
- Dados/API/tabela: nenhum.
- Variants: public/legal.
- Estados: n/a.
- Interação: links.
- Permissões: público.
- Responsivo: colunas -> lista.
- Acessibilidade: landmark footer.
- Dependências: páginas legais `[PLANNED]`.

## Produto

### AppShell
- Propósito: layout privado, sidebar/topbar/router.
- Páginas: `/app#/*`.
- Conteúdo/props: nav, user, role, active route, top actions.
- Dados/API/tabela: `/api/v1/auth/me`.
- Variants: user/admin.
- Estados: loading/auth error.
- Interação atual: terminar sessão remove localmente o JWT de `localStorage`, limpa `state.user` e navega para `/app#/login`. Não existe revogação no backend. Endpoint de logout: `[PLANNED]`.
- Permissões: autenticado; admin só `is_superuser`.
- Responsivo: sidebar colapsável/bottom nav.
- Acessibilidade: landmarks, foco visível.
- Dependências: auth `[IMPLEMENTED]`.

### PageHeader
- Propósito: título, contexto e ação principal.
- Páginas: todas as privadas.
- Conteúdo/props: H1, subtítulo, badges de estado, CTA.
- Dados/API/tabela: nenhum direto.
- Variants: normal/admin/warning.
- Estados: stale/warning.
- Interação: CTA.
- Permissões: conforme página.
- Responsivo: CTA abaixo do título.
- Acessibilidade: H1 único.
- Dependências: copy de página.

### KPI/Stat
- Propósito: resumir números acionáveis.
- Páginas: dashboard/admin overview.
- Conteúdo/props: label, valor, delta, estado, tooltip.
- Dados/API/tabela: watchlists/alerts/deadlines/quality `[PARTIAL]`.
- Variants: normal/warning/stale.
- Estados: loading/empty/error.
- Interação: abrir lista filtrada.
- Permissões: privado/admin.
- Responsivo: grid -> cards.
- Acessibilidade: não depender só da cor.
- Dependências: endpoints por área.

### SearchForm
- Propósito: recolher critérios de pesquisa/adicionar item.
- Páginas: search, watchlists.
- Conteúdo/props: q, jurisdiction, nice_class, submit/reset.
- Dados/API/tabela: `/api/v1/trademarks`, watchlist item API.
- Variants: compact/full.
- Estados: loading/validation/error.
- Interação: submit, limpar.
- Permissões: autenticado.
- Responsivo: campos empilhados.
- Acessibilidade: labels e erros por campo.
- Dependências: search API `[PARTIAL]`.

### Filters
- Propósito: reduzir listas densas.
- Páginas: search, alerts, deadlines, admin tables.
- Conteúdo/props: filtros, sort, pagination.
- Dados/API/tabela: query params quando existirem; admin APIs `[PLANNED]`.
- Variants: inline/drawer.
- Estados: applied/empty.
- Interação: aplicar/limpar.
- Permissões: conforme página.
- Responsivo: drawer mobile.
- Acessibilidade: fieldsets.
- Dependências: API filtering.

### ResultCard/Table
- Propósito: mostrar resultados/listas.
- Páginas: search, leads, portfolios, admin.
- Conteúdo/props: columns/card fields, actions, status.
- Dados/API/tabela: `/trademarks`, `/portfolios*`, admin APIs `[PLANNED]`.
- Variants: card/table/dense.
- Estados: loading/empty/error/stale.
- Interação: abrir detalhe, sort, paginate.
- Permissões: privado/admin.
- Responsivo: table -> cards.
- Acessibilidade: table headers, row actions com labels.
- Dependências: dados de rota.

### MarkSummary
- Propósito: resumo de marca.
- Páginas: mark detail, result detail snippets.
- Conteúdo/props: word_mark, application_number, status, jurisdiction, classes, holders.
- Dados/API/tabela: `/api/v1/trademarks/{application_number}`, `core.trademarks`.
- Variants: compact/full.
- Estados: partial/stale/error.
- Interação: adicionar a vigilância.
- Permissões: autenticado.
- Responsivo: grid -> stack.
- Acessibilidade: listas semânticas para classes/holders.
- Dependências: detail UI `[PLANNED]`.

### ProvenanceBadge
- Propósito: indicar rasto da fonte.
- Páginas: mark detail, alerts, deadlines, admin quality.
- Conteúdo/props: source, run_id, document/page, parser_version, confidence.
- Dados/API/tabela: raw/core/events/app, source_runs; BPI-specific `[BLOCKED]`.
- Variants: source-only/full/warning.
- Estados: unknown/stale/quarantine.
- Interação: tooltip; admin drill-down quando permitido.
- Permissões: básico para user, detalhe para admin.
- Responsivo: badge compacto.
- Acessibilidade: texto expandido acessível.
- Dependências: provenance fields `[PARTIAL]`.

### SourceFreshness
- Propósito: mostrar atualização conhecida.
- Páginas: dashboard, search/detail, admin sources.
- Conteúdo/props: source, last_success_at, status, age.
- Dados/API/tabela: `core.source_runs`, admin freshness API `[PLANNED]`.
- Variants: badge/table row.
- Estados: fresh/stale/unknown/error.
- Interação: abrir fonte/admin.
- Permissões: user summary/admin full.
- Responsivo: compact badge.
- Acessibilidade: texto de estado.
- Dependências: source_runs.

### ConfidenceIndicator
- Propósito: explicar qualidade técnica.
- Páginas: mark detail, alerts, quality, review.
- Conteúdo/props: score, band, explanation.
- Dados/API/tabela: confidence service, review_queue.
- Variants: score/band/text only.
- Estados: high/review/quarantine/unknown.
- Interação: tooltip.
- Permissões: conforme dado.
- Responsivo: badge.
- Acessibilidade: label textual.
- Dependências: thresholds; BPI thresholds `[BLOCKED]` até gate 10.

### Timeline
- Propósito: eventos por data.
- Páginas: mark detail, deadlines.
- Conteúdo/props: event_type, date, source, confidence, deadline.
- Dados/API/tabela: `events.lifecycle_events`, `app.deadlines`.
- Variants: vertical/compact.
- Estados: partial/blocked/stale.
- Interação: abrir evento/detalhe.
- Permissões: autenticado.
- Responsivo: vertical.
- Acessibilidade: ordered list.
- Dependências: events; BPI events `[BLOCKED]`.

### WatchlistCard
- Propósito: gerir uma vigilância e itens.
- Páginas: watchlists, dashboard summary.
- Conteúdo/props: name, thresholds, jurisdictions, items, actions.
- Dados/API/tabela: `/watchlists`, `/watchlists/{id}/items`, `app.watchlists`, `app.watchlist_items`.
- Variants: compact/expanded.
- Estados: active/inactive/loading/error.
- Interação: edit, delete, add/remove item.
- Permissões: owner.
- Responsivo: card stack.
- Acessibilidade: confirm destructive actions.
- Dependências: watchlists API `[IMPLEMENTED]`.

### AlertItem
- Propósito: rever alerta.
- Páginas: dashboard, alerts.
- Conteúdo/props: title, body, type, status, source, confidence, created_at.
- Dados/API/tabela: `/alerts`, `app.alerts`.
- Variants: unread/read/dismissed.
- Estados: loading/empty/stale.
- Interação: mark read, dismiss.
- Permissões: owner.
- Responsivo: card.
- Acessibilidade: buttons com labels.
- Dependências: alerts API `[PARTIAL]`.

### DeadlineItem
- Propósito: rever prazo.
- Páginas: dashboard, deadlines, mark detail.
- Conteúdo/props: mark, type, date, days_remaining, rule_status, source.
- Dados/API/tabela: `/deadlines`, `app.deadlines`.
- Variants: upcoming/overdue/blocked.
- Estados: warning/error/stale.
- Interação: abrir marca/fonte.
- Permissões: owner.
- Responsivo: card.
- Acessibilidade: data em texto.
- Dependências: deadlines API `[PARTIAL]`; BPI deadlines `[BLOCKED]`.

### EmptyState
- Propósito: recuperação canónica quando não há dados, tarefa em curso, dados ainda não disponíveis, funcionalidade bloqueada, limite de chamadas excedido ou conteúdo redigido por política.
- Páginas: todas as listas, dashboards, áreas admin e páginas legais.
- Conteúdo/props: title, body, CTA principal (ação única da vista), ícone/ilustração opcional.
- Dados/API/tabela: nenhum direto; pode referenciar endpoint quando relevante para explicar ausência.
- Variants (lista canónica completa):
  - `first-use`: primeira utilização, sugere criar/começar.
  - `no-results`: pesquisa sem matches, sugere refinar.
  - `no-permission`: utilizador sem role, sugere contactar admin.
  - `in-progress`: tarefa a correr, sugere aguardar.
  - `no-data-yet`: dados ainda não disponíveis, com data prevista.
  - `blocked`: funcionalidade bloqueada, link para admin/detalhe.
  - `rate-limited`: limite de chamadas excedido, CTA para reduzir ritmo.
  - `redacted`: dados redigidos por política, explicar sem expor.
- Estados: empty/in-progress/blocked.
- Interação: CTA principal (único) por vista; navegação contextual via link secundário inline.
- Permissões: conforme página.
- Responsivo: central/inline.
- Acessibilidade: mensagem textual, `aria-live=polite` quando muda dinamicamente, estado textual além de cor.
- Dependências: copy de página; CTAs matrix.

### ErrorState
- Propósito: falhas recuperáveis.
- Páginas: todas.
- Conteúdo/props: title, body, retry, secondary.
- Dados/API/tabela: erro seguro redigido.
- Variants: inline/full-page/permission.
- Estados: error/403/404/500.
- Interação: retry/navigate.
- Permissões: n/a.
- Responsivo: full width.
- Acessibilidade: `role=alert` quando apropriado.
- Dependências: error handling.

### LoadingSkeleton
- Propósito: feedback durante fetch.
- Páginas: todas.
- Conteúdo/props: label, skeleton shape.
- Dados/API/tabela: n/a.
- Variants: card/table/page.
- Estados: loading.
- Interação: none.
- Permissões: n/a.
- Responsivo: adaptar layout.
- Acessibilidade: `aria-busy`, texto visível.
- Dependências: n/a.

### ConfirmDialog
- Propósito: confirmar ações destrutivas/mutáveis.
- Páginas: watchlists, future admin, billing.
- Conteúdo/props: title, body, confirmLabel, cancelLabel, risk.
- Dados/API/tabela: depende da ação.
- Variants: destructive/billing/admin-mutation.
- Estados: open/loading/error.
- Interação: confirm/cancel.
- Permissões: conforme ação.
- Responsivo: modal full-width mobile.
- Acessibilidade: focus trap, ESC, labels.
- Dependências: mutações seguras; admin mutações `[BLOCKED]`.

## Admin P0

### AdminOverview
- Propósito: resumo operacional read-only.
- Páginas: `/app#/admin`, `/app#/admin/overview`.
- Conteúdo/props: health summary, freshness, failures, quality counts.
- Dados/API/tabela: `/health`, `/api/v1/health`, `/api/v1/quality/metrics`, admin aggregator `[PLANNED]`.
- Variants: normal/degraded/blocked.
- Estados: loading/empty/error/stale.
- Interação: refresh, drill-down.
- Permissões: admin/superuser.
- Responsivo: stats -> list.
- Acessibilidade: status text.
- Dependências: admin RBAC `[PLANNED/BLOCKED]`.

### SystemHealth
- Propósito: saúde API/DB/Redis/workers.
- Páginas: admin overview.
- Conteúdo/props: service, status, last_heartbeat, message.
- Dados/API/tabela: `/health`, `/api/v1/health`, worker/job API `[PLANNED/BLOCKED]`.
- Variants: service card/table.
- Estados: ok/degraded/down/unknown.
- Interação: refresh.
- Permissões: admin.
- Responsivo: table -> cards.
- Acessibilidade: não usar só cor.
- Dependências: observability endpoints.

### UserAccountTable
- Propósito: listar contas sem secrets.
- Páginas: `/app#/admin/users`.
- Conteúdo/props: email, name, company, active, is_superuser, plan, dates.
- Dados/API/tabela: `app.users`, `app.subscriptions`, admin API `[PLANNED]`.
- Variants: dense/paginated.
- Estados: loading/empty/error.
- Interação: filter/sort/detail read-only.
- Permissões: admin.
- Responsivo: horizontal scroll/cards.
- Acessibilidade: table headers.
- Dependências: redaction/RBAC tests.

### PlanSubscriptionMonitor
- Propósito: monitorizar planos/subscrições.
- Páginas: settings, admin subscriptions.
- Conteúdo/props: plan, status, mode mock/real, limits, user.
- Dados/API/tabela: `/billing/plans`, `/billing/subscription`, `app.subscriptions`, admin API `[PLANNED]`.
- Variants: user/admin.
- Estados: mock/real/unknown/error.
- Interação: checkout/filter.
- Permissões: owner/admin.
- Responsivo: cards/table.
- Acessibilidade: estado textual.
- Dependências: billing `[PARTIAL]`.

### UsageLimits
- Propósito: mostrar limites e consumo.
- Páginas: settings, admin subscriptions.
- Conteúdo/props: max_marks, max_users, max_clients, used counts when available.
- Dados/API/tabela: `app.subscriptions`; usage API `[PLANNED]`.
- Variants: progress/list.
- Estados: unknown/near-limit/over-limit.
- Interação: none/filter admin.
- Permissões: owner/admin.
- Responsivo: list.
- Acessibilidade: texto além de barra.
- Dependências: usage counts `[PLANNED]`.

### SourceFreshnessTable
- Propósito: listar freshness por fonte.
- Páginas: admin sources/overview.
- Conteúdo/props: source, enabled/mode, last_success, volumes, last_error.
- Dados/API/tabela: `core.sources`, `core.source_runs`, `raw.api_responses`, admin API `[PLANNED]`.
- Variants: summary/full.
- Estados: fresh/stale/failed/unknown.
- Interação: filter/drill-down.
- Permissões: admin.
- Responsivo: table -> cards.
- Acessibilidade: status text.
- Dependências: redaction.

### ImportRunTable
- Propósito: listar runs.
- Páginas: admin imports.
- Conteúdo/props: run_id, source, status, window, counts, duration.
- Dados/API/tabela: `core.source_runs`, admin API `[PLANNED]`.
- Variants: dense.
- Estados: running/success/failed/partial.
- Interação: open detail.
- Permissões: admin.
- Responsivo: horizontal scroll.
- Acessibilidade: table headers.
- Dependências: source_runs.

### ImportRunDetail
- Propósito: detalhe read-only da run.
- Páginas: admin imports.
- Conteúdo/props: metadata, parser_version, errors redacted, raw/reconciliation links.
- Dados/API/tabela: source_runs/raw/reconciliation `[PLANNED]`.
- Variants: drawer/page.
- Estados: loading/error/stale.
- Interação: close/open links.
- Permissões: admin.
- Responsivo: full page mobile.
- Acessibilidade: headings.
- Dependências: admin detail endpoint.

### JobQueue
- Propósito: filas, workers e falhas.
- Páginas: admin jobs.
- Conteúdo/props: queue, status, heartbeat, running, failed, dead-letter.
- Dados/API/tabela: Celery/Redis API `[PLANNED/BLOCKED]`.
- Variants: queue cards/table.
- Estados: unknown/running/failed/stale.
- Interação: refresh; cancel/retry disabled.
- Permissões: admin.
- Responsivo: cards.
- Acessibilidade: status text.
- Dependências: secure job API.

### DataQualityMetrics
- Propósito: métricas de qualidade.
- Páginas: admin overview/quality.
- Conteúdo/props: completeness, confidence, accepted/review/quarantine, duplicates/conflicts.
- Dados/API/tabela: `/api/v1/quality/metrics`, review_queue, raw/core/events/app.
- Variants: stats/table.
- Estados: loading/empty/error.
- Interação: drill-down.
- Permissões: admin.
- Responsivo: grid -> list.
- Acessibilidade: labels claros.
- Dependências: quality endpoint `[PLANNED/PARTIAL]`.

### ReconciliationSummary
- Propósito: conflitos e duplicados.
- Páginas: admin quality.
- Conteúdo/props: source, field, conflict_count, duplicate_count, affected records.
- Dados/API/tabela: reconciliation tables/API `[PLANNED]`.
- Variants: summary/detail.
- Estados: ok/warning/blocked.
- Interação: filter/open review.
- Permissões: admin.
- Responsivo: table.
- Acessibilidade: status text.
- Dependências: reconciliation schema.

### ReviewQueue
- Propósito: fila de revisão/quarantine.
- Páginas: admin review.
- Conteúdo/props: item, source, reason, confidence, status, created_at.
- Dados/API/tabela: `app.review_queue`, admin API `[PLANNED]`.
- Variants: dense.
- Estados: empty/loading/error.
- Interação: open detail; decisions disabled.
- Permissões: admin.
- Responsivo: cards/table.
- Acessibilidade: table headers.
- Dependências: policy/audit for mutations `[BLOCKED]`.

### QuarantineDetail
- Propósito: detalhe redigido de item em quarantine.
- Páginas: admin review.
- Conteúdo/props: payload excerpt redacted, reason, source/run, confidence.
- Dados/API/tabela: review_queue/raw tables.
- Variants: drawer/page.
- Estados: blocked/error.
- Interação: close; accept/reject disabled.
- Permissões: admin.
- Responsivo: full page mobile.
- Acessibilidade: headings, safe text rendering.
- Dependências: redaction.

### AuditLog
- Propósito: eventos append-only.
- Páginas: admin audit.
- Conteúdo/props: timestamp, actor, action, resource, result, correlation_id.
- Dados/API/tabela: audit table/API `[PLANNED/BLOCKED]`.
- Variants: table.
- Estados: empty/loading/error.
- Interação: filter; export (ver `OD-03` em [`SITEMAP_CONTENT_MATRIX.md`](SITEMAP_CONTENT_MATRIX.md)).
- Permissões: admin.
- Responsivo: horizontal scroll.
- Acessibilidade: table headers.
- Dependências: audit model.

### BpiPipelineStatus
- Propósito: estado NO-GO do pipeline BPI.
- Páginas: admin BPI.
- Conteúdo/props: stage, status, blocker, requirement.
- Dados/API/tabela: docs/gates; planned BPI tables `[BLOCKED]`.
- Variants: stage cards/table.
- Estados: blocked/planned.
- Interação: open gate detail.
- Permissões: admin.
- Responsivo: cards.
- Acessibilidade: status text.
- Dependências: BPI-GATE-01..16.

### BpiGateChecklist
- Propósito: checklist canónico dos 16 gates BPI com estado e decisão.
- Páginas: `/app#/admin/bpi`.
- Conteúdo/props: `gate_id`, `requirement`, `status` (`blocked`/`accepted`/`rejected`), `evidence_link`, `owner_decision`.
- Dados/API/tabela: `docs/REQUIREMENTS.md` §11; future gate API `[PLANNED]`.
- Variants: compact/full.
- Estados: blocked/accepted/rejected.
- Interação: filter por status; drill-down por gate para evidência em `docs/REQUIREMENTS.md` §11.
- Permissões: admin.
- Responsivo: accordion.
- Acessibilidade: headings por gate; estado textual além de cor; foco visível ao expandir.
- Dependências: gates fechados antes de GO WITH CHANGES.

Entradas canónicas (16 gates, cada um `Decisão: [BLOCKED]`):
- `BPI-GATE-01` - congelar deadlines/alertas BPI por defeito.
- `BPI-GATE-02` - uma única semântica temporal PT.
- `BPI-GATE-03` - migrations `raw.bpi_bulletins` e `raw.bpi_page_extractions`.
- `BPI-GATE-04` - dedupe_key, parser_version, field_confidence, supersession, quarantine.
- `BPI-GATE-05` - arquivo concorrente seguro com unique/upsert.
- `BPI-GATE-06` - reconciliar 11 campos YAML em falta.
- `BPI-GATE-07` - required fields por evento, incluindo expressão de recusa.
- `BPI-GATE-08` - corrigir exemplos JSON inválidos.
- `BPI-GATE-09` - unificar source enums e event types canónicos.
- `BPI-GATE-10` - thresholds gap-free 0.85/0.65/0.
- `BPI-GATE-11` - ST.17/aliases como heurísticas YAML.
- `BPI-GATE-12` - mover `opposition_filed` para P2/disabled.
- `BPI-GATE-13` - corrigir mapping de deadlines para `app.deadlines`.
- `BPI-GATE-14` - reconciliar por `(jurisdiction, application_number)`.
- `BPI-GATE-15` - guards de paginação, robots, kill switch, orçamento.
- `BPI-GATE-16` - política RGPD e custo total operacional.

Nota: as 16 entradas detalhadas (com `requirement`, `evidence_link`, `owner_decision`) vivem em [`pages/ADMIN_PORTAL.md`](pages/ADMIN_PORTAL.md) § `BpiGateChecklist` (16 gates) e são a fonte canónica única. Este bloco UI referencia-as, não as duplica.

## Blocos adicionais

### NotificationStatus
- Propósito: mostrar ao utilizador que o envio externo não é claim operacional.
- Páginas: `/app#/alerts`, settings.
- Conteúdo/props: texto `Envio externo não validado`, ícone neutro, link para settings.
- Dados/API/tabela: nenhum direto; refleja estado do alert service.
- Variants: alert-detail, settings-row.
- Estados: not-configured, configured-mock, configured-real-unverified, configured-real-verified.
- Interação: abrir settings para configurar canal.
- Permissões: autenticado.
- Responsivo: card compacto.
- Acessibilidade: estado textual além de cor; nunca usar "enviado" sem confirmação real.
- Dependências: alert service `[PARTIAL]`; SEM envio real validado.

### BillingStatus
- Propósito: mostrar ao utilizador se a subscrição é mock/dev ou Stripe real validado.
- Páginas: `/app#/settings`, `/app#/admin/subscriptions`.
- Conteúdo/props: `Modo de billing`, `Estado checkout`, `Estado webhook`, data da última sincronização.
- Dados/API/tabela: `app.subscriptions`, billing service `[PARTIAL]`.
- Variants: user compact, admin detail.
- Estados: mock-development, real-unverified, real-verified, error, unknown.
- Interação: nenhum (read-only); settings admin drill-down.
- Permissões: owner/admin.
- Responsivo: card.
- Acessibilidade: estado textual; nunca prometer cobrança sem validação.
- Dependências: Stripe real validado `[PARTIAL]`.

## Blocos transversais (auth, legal)

### AuthForm
- Propósito: formulários de autenticação (login, registo, recuperação) com validação, mensagens acessíveis e estados visíveis.
- Páginas: `/app#/login`, modais de sessão expirada, future recover/verify-email.
- Conteúdo/props:
  - `mode`: `login` | `register` | `recover` | `verify-email`.
  - `fields`: por mode — `login` (`email`, `password`); `register` (`email`, `password`, `full_name`, `company_name` opcional); `recover` (`email`); `verify-email` (`code`).
  - `submitLabel`: texto do CTA principal.
  - `secondaryCta`: par secundário (`Criar conta` quando `mode=login`; `Iniciar sessão` quando `mode=register`).
  - `legalLink`: ligação a `/terms [PLANNED]` e `/privacy [PLANNED]`.
- Dados/API/tabela: `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `POST /api/v1/auth/recover [PLANNED]`, `POST /api/v1/auth/verify [PLANNED]`; `app.users`.
- Variants: compact (modal) | full (página `/app#/login`).
- Estados: idle | loading | validation-error | submit-error (credenciais, rede, servidor) | success | rate-limited.
- Interação: submit por Enter; validação por campo; mensagens de erro junto ao campo; CTA secundário alterna entre `Iniciar sessão` e `Criar conta` consoante `mode`.
- Permissões: público.
- Responsivo: campos empilhados largura total mobile.
- Acessibilidade: `aria-describedby` por campo de erro, `aria-invalid` quando inválido, `autocomplete` adequado (`email`, `current-password`, `new-password`), foco visível, label por input, skip para CTA secundário, anunciar sucesso via `aria-live=polite`.
- Status/CTA:
  - `login`: submit `Iniciar sessão` -> sucesso grava JWT e redireciona para `/app#/dashboard`.
  - `register`: submit `Criar conta` -> `POST /api/v1/auth/register` devolve `UserOut`, sem JWT, e não autentica por si; o frontend tenta de seguida `POST /api/v1/auth/login`, grava o JWT e navega para `/app#/dashboard` se essa segunda chamada tiver sucesso. Se o login automático falhar, a conta pode já existir e o utilizador pode iniciar sessão manualmente. Verificação de email: `[PLANNED — depende de OD-05]`.
  - `recover`: submit `Enviar pedido` -> sucesso mostra estado neutro "Se a conta existir, recebe instruções".
  - erro de credenciais: copy neutra, sem confirmar existência de conta.
- Dependências: auth `[IMPLEMENTED]`; recover/verify `OD-05`.

### LegalContent
- Propósito: renderização de páginas legais (privacidade, termos, disclaimers) com copy PT-PT, âncoras internas e referência a data de versão.
- Páginas: `/privacy`, `/terms`, `/legal`.
- Conteúdo/props:
  - `slug`: `privacy` | `terms` | `legal`.
  - `version`: data ISO da última revisão (`YYYY-MM-DD`).
  - `sections[]`: `{id, title, body}` com âncoras internas.
  - `lastUpdatedLabel`: copy "Última revisão: {date}".
- Dados/API/tabela: conteúdo versionado em `contents/pages/PUBLIC_LANDING.md` copy-fonte e storage `[PLANNED]`; nenhum endpoint dinâmico no P0.
- Variants: longform (uma coluna larga) | compact (sumário + âncoras).
- Estados: loading (apenas em variant dinâmica) | empty `[PLANNED]` | stale.
- Interação:
  - `LegalContent` é renderização de páginas legais com CTAs próprios por rota, conforme matriz. A exceção regulatória de `Aceitar`/`Recusar` aplica-se apenas a banner de consentimento, nunca a `/terms` como CTA principal.
  - Ações legais `[PLANNED/GATE-JURIDICO]`: `Contactar` -> `mailto:spud@batata.cc` `[PLANNED — depende de OD-16]`; em `/privacy`, `Voltar` -> `history.back()` com fallback `/`.
- Permissões: público.
- Responsivo: tipografia fluida; largura máxima legível.
- Acessibilidade: headings hierárquicos, skip para conteúdo, `lang=pt-PT`, links com label claro, contraste WCAG AA, semântica de lista para enumerados.
- Status/CTA:
  - `/privacy` `[PLANNED/GATE-JURIDICO]`: principal `Contactar` -> `mailto:spud@batata.cc` `[PLANNED — depende de OD-16]`; secundário `Voltar` -> `history.back()` (fallback `/`).
  - `/terms` `[PLANNED/GATE-JURIDICO]`: principal `Criar conta` -> `/app#/login` (selecionar registo nessa vista); secundário `Voltar ao início` -> `/`. **Não usar `Aceitar`/`voltar` como CTA principal de `/terms`**; isso só pertence a banner de consentimento.
  - `/legal` `[PLANNED/GATE-JURIDICO]`: principal `Ver privacidade` -> `/privacy`; secundário `Ver termos` -> `/terms`.
  - Footer: `Cookies` -> ação `[PLANNED]` para reabrir preferências de consentimento; a ação técnica ainda não existe e não tem URL autónoma.
- Dependências: copy final em `pages/PUBLIC_LANDING.md`; storage versionado `[PLANNED]`.

## Navegação relacionada

- [`README.md`](README.md) — convenções editoriais e taxonomia de estados.
- [`CONTENT_PRINCIPLES.md`](CONTENT_PRINCIPLES.md) — princípios de redação e tom.
- [`GLOSSARY.md`](GLOSSARY.md) — termos canónicos PT-PT/EN.
- [`SITEMAP_CONTENT_MATRIX.md`](SITEMAP_CONTENT_MATRIX.md) — matriz rota → blocos aqui definidos.
- [`pages/PUBLIC_LANDING.md`](pages/PUBLIC_LANDING.md) — blocos públicos em uso na landing.
- [`pages/AUTH_ONBOARDING.md`](pages/AUTH_ONBOARDING.md) — uso de `AuthForm`.
- [`pages/LEGAL_ERRORS.md`](pages/LEGAL_ERRORS.md) — uso de `LegalContent`, `ErrorState`, `EmptyState`.
- [`pages/DASHBOARD.md`](pages/DASHBOARD.md) — uso de `KPI/Stat`, `AlertItem`, `DeadlineItem`, `SourceFreshness`.
- [`pages/SEARCH_MARK_DETAIL.md`](pages/SEARCH_MARK_DETAIL.md) — uso de `SearchForm`, `ResultCard/Table`, `MarkSummary`.
- [`pages/WATCHLISTS_ALERTS_DEADLINES.md`](pages/WATCHLISTS_ALERTS_DEADLINES.md) — uso de `WatchlistCard`, `AlertItem`, `DeadlineItem`.
- [`pages/SETTINGS_BILLING.md`](pages/SETTINGS_BILLING.md) — uso de `PlanSubscriptionMonitor`, `UsageLimits`, `BillingStatus`.
- [`pages/ADMIN_PORTAL.md`](pages/ADMIN_PORTAL.md) — uso de todos os blocos `Admin P0`, `BpiPipelineStatus`, `BpiGateChecklist`, `ReviewQueue`, `QuarantineDetail`, `AuditLog`.
- [`../docs/SITEMAP.md`](../docs/SITEMAP.md) — sitemap canónico de rotas.
- [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) — requisitos funcionais e não-funcionais referenciados nos blocos.
