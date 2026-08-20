# Glossary

## Produto e navegação

Markee — plataforma SaaS de monitorização de marcas para Portugal e Europa.

Landing — página pública `/` com proposta de valor, funcionalidades, motor, preços e CTA.

Aplicação — SPA privada em `/app`, com navegação por hash.

Portal admin P0 — área `/app#/admin*` para `superuser/admin`. Estado atual: alvo decidido, mas implementação `[PLANNED/BLOCKED]`; as peças backend existentes não formam ainda um portal operacional. Tudo o que aparece como "portal admin" deve ser lido como planeado e nunca como já entregue.

## Dados de marca

Marca — sinal distintivo registado ou pedido junto de uma jurisdição.

Pedido de marca — submissão ainda em ciclo de exame/publicação/concessão.

Número de pedido — identificador usado na rota `/app#/marks/{application_number}` e na API de detalhe (`GET /api/v1/trademarks/{application_number}`).

Classe de Nice — classificação internacional de produtos/serviços.

Jurisdição — âmbito da marca, por exemplo PT/INPI ou EU/EUIPO.

Titular — pessoa ou entidade associada à marca. Minimizar dados pessoais no UI conforme `NFR-GDPR-001`.

## Monitorização

Vigilância — conjunto de marcas/termos/classes/jurisdições que o utilizador quer acompanhar.

Item de vigilância — marca, termo ou referência dentro de uma vigilância.

Alerta — registo interno que pede revisão do utilizador. Envio por canal externo é notificação e não deve ser assumido como operacional.

Notificação — envio por email, Telegram ou outro canal externo. Estado atual: envio por email `[PLANNED]` e envio por Telegram `[PLANNED]` individualmente; não há configuração controlada nem entrega real validada para nenhum dos dois.

Email — canal de envio externo. Estado atual: `[PLANNED]`. UI nunca promete entrega, mesmo quando o utilizador indique o seu endereço.

Telegram — canal de envio externo via bot. Estado atual: `[PLANNED]`. UI nunca promete entrega enquanto o bot não estiver integrado e o envio não estiver validado.

Prazo — data de ação ou revisão calculada. Não é garantia jurídica.

## Qualidade e proveniência

Fonte — origem do dado: EUIPO/TMview, INPI/BPI, base interna ou simulação/desenvolvimento quando aplicável.

Proveniência — rasto que liga um dado à fonte, run, parser, payload/documento e data conhecida.

Freshness — atualidade do dado no Markee, normalmente "último sucesso" ou "última atualização conhecida".

Confiança — score/estado técnico de qualidade ou reconciliação. Não equivale a certeza legal.

Revisão — fila de dados que precisam de validação humana ou técnica antes de aceitação.

Quarentena — estado para dados que não podem entrar automaticamente no core por baixa confiança, conflito ou contrato incompleto.

Reconciliação — processo de ligar dados de fontes diferentes à mesma entidade sem fusões perigosas.

## BPI

BPI — Boletim da Propriedade Industrial do INPI. Valor para prova de publicação, páginas, secções e excertos.

NO-GO BPI — decisão atual: pipeline BPI operacional está bloqueado até gates `BPI-GATE-01..16`.

Gate BPI — condição técnica/legal/documental obrigatória antes de permitir execução operacional. Lista concreta em [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) (secção 11 / entradas `BPI-GATE-01..16`) e [`../docs/SITEMAP.md`](../docs/SITEMAP.md) secção 5.1. Detalhe canónico de cada gate vive em [`pages/ADMIN_PORTAL.md`](pages/ADMIN_PORTAL.md) § `BpiGateChecklist` (16 entradas).

Deadline BPI — prazo derivado de evento BPI. Estado atual: `[BLOCKED]` — BPI NO-GO. Falha de segurança/contrato CRITICAL: o `app/tasks/calculate_deadlines.recalculate_all` (ver `app/tasks/calculate_deadlines.py:59-93`) cria `Deadline` de oposição para o último `LifecycleEvent.event_type == "publication"` sem filtrar a fonte, e `app/services/ingestion.py:889-908` produz `LifecycleEvent` com `deadline_date` para eventos BPI `publication`. Não existem `enabled`/`legal_status` no modelo `events.lifecycle_events` nem em `app.deadlines` (`app/models/lifecycle.py`). BPI permanece NO-GO/BLOCKED e não pode ser considerado seguro até existirem: source guard (filtrar source em BPI/PT legal), model fields/migration (`enabled`, `legal_status`), testes e regra legal versionada. A UI não pode corrigir o backend; até lá, prazos BPI são apresentados como `Bloqueado até validação da regra legal.` e a UI nunca os apresenta como ativos.

Estágio BPI — uma das fases de pipeline: discovery, raw archive PDF, extraction por página, parsing P0, normalization, reconciliation, confidence/quarantine, RGPD/custo e deadlines/alertas. Cada estágio está `[BLOCKED]` independentemente.

GO WITH CHANGES — não é deploy nem ativação; é autorização para o João escolher equipa de execução e abrir trabalho técnico controlado, apenas quando os 16 gates BPI estiverem fechados.

## Billing

Plano — tier comercial disponível no catálogo do Markee. O frontend expõe `PLAN_META` em [`../frontend/dashboard/app.js`](../frontend/dashboard/app.js) (~linha 37) com labels PT-PT e preços mensais. O backend tem `PLAN_LIMITS` em [`../app/services/billing.py`](../app/services/billing.py) e os Stripe price IDs por configuração (`settings.STRIPE_PRICE_*`). Catálogo atual: `Free` €0, `Individual` €5, `Pro` €29, `Profissional` €99, `Enterprise` €249.

Subscrição — estado do plano associado à conta. Tabela `app.subscriptions`.

Stripe real — cobrança/processamento validado por Stripe em ambiente controlado. Os caminhos mock e real existem no código; modo efetivo `UNKNOWN`. Stripe real, checkout e webhooks não foram validados e não estão live.

Mock/dev billing — caminho de desenvolvimento que simula checkout/subscrição. A sua existência no código não prova que seja o modo efetivo; o UI só o identifica após evidência controlada.

Checkout — `POST /api/v1/billing/checkout`. Em modo mock devolve estrutura; em modo real exige Stripe e webhook. Estado atual: `[PARTIAL]`, sem cobrança real validada em produção.

Webhook — `POST /api/v1/billing/webhook`. Recebe eventos Stripe; verifica assinatura e atualiza `app.subscriptions`. Estado atual: `[PARTIAL]`, sem teste dedicado nem evento real recebido.

BillingStatus — bloco UI canónico que distingue explicitamente `mock-development`, `real-unverified`, `real-verified`, `error`, `unknown`. Nunca apresenta `real-verified` sem evidência validada em produção.

## Roles e admin

Utilizador — qualquer conta autenticada. Sem acesso ao portal admin.

Admin — role operacional para `/app#/admin*`. Em P0 mapeado para `app.users.is_superuser`. Autorização efetiva no router admin ainda `[PLANNED]`.

Superuser — flag `app.users.is_superuser`. Usado como gate de admin até política RBAC fina existir.

RBAC — role-based access control. `NFR-ADMIN-SEC-001` exige deny/allow tests, redaction, least privilege, rate limit e auditoria.

Audit — registo append-only de ações admin. Modelo/tabela/API ainda não confirmados.

Read-only P0 — modo-alvo do portal admin. No estado atual não existe portal admin operacional; tudo o que aparece como "read-only P0" é referência ao alvo, não a uma área já servida pelo SPA.

Mutação admin — qualquer ação admin que escreve (retry/replay/cancel/repair, accept/reject, enable/disable, role changes, plan changes). Não inclui refresh manual nem leitura.

Redaction — remoção de password, hash, token, secrets, headers sensíveis e PII desnecessária antes de devolver dados por uma rota admin.

## Estados internos e marcadores

`[IMPLEMENTED]` — existe código e teste local para o comportamento essencial.

`[PARTIAL]` — existe parte funcional, mas falta UI, teste, integração real, contrato ou política.

`[PLANNED]` — alvo decidido, sem implementação suficiente.

`[BLOCKED]` — depende de decisão, schema, validação legal, credencial ou gates.

`[OPEN DECISION]` — decisão real de produto ainda em aberto; não usar para features simplesmente planeadas ou bloqueadas, que devem ser marcadas `[PLANNED]` ou `[BLOCKED]` respetivamente.

## Navegação relacionada

- [`README.md`](README.md) — convenções editoriais e taxonomia de estados.
- [`UI_BLOCKS.md`](UI_BLOCKS.md) — blocos canónicos `WatchlistCard`, `AlertItem`, `DeadlineItem`, `NotificationStatus`, `ProvenanceBadge`, `SourceFreshness`, `ConfidenceIndicator`, `BillingStatus`, `BpiGateChecklist`.
- [`SITEMAP_CONTENT_MATRIX.md`](SITEMAP_CONTENT_MATRIX.md) — matriz rota → blocos; cobre as 32 entradas frontend.
- [`CONTENT_PRINCIPLES.md`](CONTENT_PRINCIPLES.md) — princípios de redação, tom, terminologia canónica e microcopy.
- [`pages/PUBLIC_LANDING.md`](pages/PUBLIC_LANDING.md) — terminologia exposta na landing pública.
- [`pages/AUTH_ONBOARDING.md`](pages/AUTH_ONBOARDING.md) — `AuthForm`, sessão e copy de autenticação.
- [`pages/DASHBOARD.md`](pages/DASHBOARD.md) — KPI e blocos do painel.
- [`pages/SEARCH_MARK_DETAIL.md`](pages/SEARCH_MARK_DETAIL.md) — `MarkSummary`, `ProvenanceBadge`, `Timeline`.
- [`pages/WATCHLISTS_ALERTS_DEADLINES.md`](pages/WATCHLISTS_ALERTS_DEADLINES.md) — vigilâncias, alertas, prazos e `NotificationStatus`.
- [`pages/SETTINGS_BILLING.md`](pages/SETTINGS_BILLING.md) — `BillingStatus` e catálogo público de planos.
- [`pages/LEGAL_ERRORS.md`](pages/LEGAL_ERRORS.md) — `LegalContent`, `ErrorState`, `EmptyState`.
- [`pages/ADMIN_PORTAL.md`](pages/ADMIN_PORTAL.md) — 10 domínios admin P0 e `BpiGateChecklist` com 16 gates detalhados.
- [`../docs/SITEMAP.md`](../docs/SITEMAP.md) — sitemap canónico de rotas (fonte estrutural).
- [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) — estados, requisitos FR/NFR e gates BPI.