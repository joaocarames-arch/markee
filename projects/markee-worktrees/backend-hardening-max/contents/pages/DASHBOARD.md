# Dashboard

Rota: `/app#/dashboard`.
Estado: `[PARTIAL]`.
Requisitos: `FR-DASH-001`, `FR-WATCH-001..003`, `FR-ALERT-001`, `FR-DEADLINE-001`, `NFR-QUALITY-001`.
Contratos: [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md), [`../UI_BLOCKS.md`](../UI_BLOCKS.md), [`../GLOSSARY.md`](../GLOSSARY.md), [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md), [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md).

Regra de vista:

- Uma ação principal por vista: `Pesquisar marcas`. As restantes entradas de topo (`Gerir vigilâncias`, `Ver vigilâncias`, `Ver prazos`) são utilidades de navegação secundárias, sempre disponíveis a partir do `PageHeader`, nunca como segunda ação principal desta vista.
- `Terminar sessão` é utilidade global do `AppShell`, não conta como segunda ação principal desta vista.
- Proposta condicionada à `OD-10`: se aprovada, utilizadores `is_superuser` poderão ver `SourceFreshness` ligado a `/app#/admin/sources` `[PLANNED]`; os restantes perfis não verão o bloco.
- KPIs (`Vigilâncias ativas`, `Itens monitorizados`, `Alertas por rever`, `Prazos próximos`, `Fontes com dados recentes`) são leitura agregada, não ações. Drill-down a partir de cada KPI conta como segundo CTA contextual, não como ação principal da vista.

## Objetivo e decisão

O utilizador deve perceber o que precisa de atenção hoje. Decisão principal da vista: abrir a pesquisa de marcas. As restantes decisões (rever alertas, prazos, vigilâncias) pertencem a vistas dedicadas com o seu próprio CTA principal.

## H1 e intro

H1:
`Painel`

Subtítulo:
`Resumo das vigilâncias, alertas e prazos disponíveis nesta conta.`

Texto introdutório:
`Use este painel para decidir onde agir primeiro. Dados derivados de fontes ou regras parciais mostram estado, freshness e limitações. Prazos derivados de BPI continuam bloqueados — risco CRITICAL até validação dos gates BPI-GATE-01..16 (ver GLOSSARY §Deadline BPI).`

CTA primário da vista:
`Pesquisar marcas` -> `/app#/search`

Utilidades de navegação secundária (disponíveis no `PageHeader`, não substituem a ação principal):
- `Gerir vigilâncias` -> `/app#/watchlists`
- `Ver alertas` -> `/app#/alerts`
- `Ver prazos` -> `/app#/deadlines`
- `Definições` -> `/app#/settings`

## Hierarquia desktop

1. `PageHeader` com H1, subtítulo e CTA `Pesquisar marcas`.
2. `KPI/Stat` row (leitura, sem ação):
   - `Vigilâncias ativas` `[PLANNED — depende de OD-09]`
   - `Itens monitorizados`
   - `Alertas por rever`
   - `Prazos próximos`
   - `Fontes com dados recentes` `[PLANNED — depende de OD-10]` (se aprovado e houver atualização disponível, `is_superuser` poderá ter ligação a `/app#/admin/sources`)
3. Coluna principal: `AlertItem` recentes `[PLANNED — seleção depende de OD-11]` (até 5) e `DeadlineItem` próximos (até 5).
4. Coluna lateral: `SourceFreshness` por fonte e atalhos de navegação para as vistas dedicadas.

## Hierarquia mobile

1. H1 + CTA `Pesquisar` (largura total).
2. `AlertItem` por rever.
3. `DeadlineItem` próximos.
4. `WatchlistCard` resumo das vigilâncias.
5. `SourceFreshness` em bloco expansível.
6. `KPI/Stat` cards colapsáveis atrás de `Ver mais detalhes`.

## Copy por bloco

KPI `Vigilâncias ativas`:
Label `Vigilâncias ativas`
Tooltip `Listas de monitorização associadas à sua conta.`
Empty `Ainda não criou vigilâncias.` Utilidade contextual `Gerir vigilâncias` -> `/app#/watchlists`.

KPI `Itens monitorizados`:
Label `Itens monitorizados`
Tooltip `Marcas, termos e referências que estão sob vigilância.`
Empty `Sem itens em vigilância.`

KPI `Alertas por rever`:
Label `Alertas por rever`
Tooltip `Alertas disponíveis no sistema. Envio externo por email ou Telegram não é assumido como entrega real.`
Empty `Não há alertas por rever.` Utilidade contextual `Ver alertas` -> `/app#/alerts`.

KPI `Prazos próximos`:
Label `Prazos próximos`
Tooltip `Datas calculadas a partir dos dados disponíveis. Confirme prazos críticos na fonte oficial.`
Warning `Alguns prazos podem depender de regras ainda não validadas.`
Warning BPI `Prazos derivados de BPI permanecem bloqueados — risco CRITICAL até validação dos gates BPI-GATE-01..16 (ver GLOSSARY §Deadline BPI).`

KPI `Fontes com dados recentes`:
Label `Fontes com dados recentes`
Tooltip `Número de fontes com freshness dentro do limite.`
Empty `Sem dados de freshness disponíveis.`
Warning `Algumas fontes estão desatualizadas.`

`SourceFreshness` (cards por fonte):
- por fonte: nome, último sucesso, idade, Estado de atualização.
- estados: `fresh`, `stale`, `unknown`, `error`.
- Proposta condicionada à `OD-10`: se aprovada, ligação contextual `[PLANNED]` para `/app#/admin/sources` apenas para `is_superuser`.

`AlertItem` recentes `[PLANNED — depende de OD-11]`:
- até 5 itens, lista compacta.
- cada item abre `/app#/marks/{application_number}` `[PLANNED]` quando existe; enquanto essa rota não existir, o item mostra estado apenas.
- `NotificationStatus` visível em cada item com texto `Envio externo não validado.`
- utilidade `Ver todos` -> `/app#/alerts`.

`DeadlineItem` próximos:
- até 5 itens, ordenados por data.
- cada item mostra estado da regra (`draft`/`validated`) quando aplicável.
- utilidade `Ver todos` -> `/app#/deadlines`.

`WatchlistCard` resumo:
- até 5 vigilâncias em modo compacto.
- utilidade `Ver todas` -> `/app#/watchlists`.

## Estados

Loading:
`A carregar o painel.`

Empty global:
`Ainda não há dados suficientes para resumir.`
Utilidade contextual `Gerir vigilâncias` -> `/app#/watchlists`

Empty `first-use`:
`Bem-vindo ao Markee. Comece por pesquisar uma marca ou criar uma vigilância.`
CTA principal `Pesquisar marcas` -> `/app#/search`
Utilidade `Gerir vigilâncias` -> `/app#/watchlists`

Success:
`Painel atualizado.`

Warning:
`Alguns dados dependem de fontes parciais ou regras em validação.`

Error:
`Não conseguimos carregar o painel.`
Utilidade contextual `Tentar novamente` -> recarrega a vista

Permission denied:
`Inicie sessão para ver o painel.`
Utilidade contextual `Iniciar sessão` -> `/app#/login`

Stale data:
`Última atualização conhecida: {date}. Reveja a fonte antes de agir.`

BPI bloqueado:
`Estado atual inseguro: o backend pode produzir/expor prazos BPI sem source guard. Estado-alvo obrigatório: UI e backend devem ocultá-los/bloqueá-los após guard testado. BPI permanece NO-GO/BLOCKED/CRITICAL e não pode ser promovido nem colocado live; a copy não substitui controlo técnico.`

## Microcopy crítica

Proveniência:
`A origem do dado deve estar visível no detalhe.`

Confiança:
`Score técnico de qualidade; não é decisão jurídica.`

Fonte:
`Fonte configurada no Markee, com estado quando conhecido.`

Freshness:
`Última vez que o Markee obteve ou confirmou este dado.`

Prazo:
`Use como apoio à revisão; confirme datas críticas na fonte oficial ou com profissional qualificado.`

Notificação:
`Envio externo por email ou Telegram não está validado como entrega real.`

## Anti-claims

Não pintar:
- `Alertas por rever` como `Enviados` ou `Entregues`.
- `Prazos próximos` como `Garantidos` ou `Prazos legais`.
- `Fontes com dados recentes` como `Cobertura completa`.
- `KPI` como `Stock em tempo real` ou semelhante.
- O dashboard como oferecendo `leitura diária` ou `24/7`.
- Prazos derivados de BPI como operacionais.

## Referências a decisões abertas

Decisões consolidadas na secção canónica em [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) (secção `Questões e propostas abertas — secção canónica`):

- `OD-09` — Scope de KPI `Vigilâncias ativas`.
- `OD-10` — Visibilidade de `SourceFreshness` (Estado de atualização) no dashboard.
- `OD-11` — Profundidade temporal de alertas recentes.

## Navegação relacionada

- [`../README.md`](../README.md) — convenções editoriais e taxonomia de estados.
- [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md) — princípios de redação, uma ação principal por vista e microcopy canónica.
- [`../GLOSSARY.md`](../GLOSSARY.md) — termos canónicos PT-PT/EN.
- [`../UI_BLOCKS.md`](../UI_BLOCKS.md) — blocos `AppShell`, `PageHeader`, `KPI/Stat`, `AlertItem`, `DeadlineItem`, `SourceFreshness`, `EmptyState`.
- [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) — linha `/app#/dashboard` com objetivo, mensagem, CTA principal e blocos.
- [`WATCHLISTS_ALERTS_DEADLINES.md`](WATCHLISTS_ALERTS_DEADLINES.md) — detalhe de vigilâncias, alertas e prazos.
- [`SEARCH_MARK_DETAIL.md`](SEARCH_MARK_DETAIL.md) — pesquisa e detalhe de marca.
- [`SETTINGS_BILLING.md`](SETTINGS_BILLING.md) — definições, plano e `BillingStatus`.
- [`ADMIN_PORTAL.md`](../pages/ADMIN_PORTAL.md) — `/app#/admin/sources` `[PLANNED]` e restante portal admin P0.
- [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md) — `FR-DASH-001`, `FR-WATCH-*`, `FR-ALERT-001`, `FR-DEADLINE-001`.
- [`../../docs/SITEMAP.md`](../../docs/SITEMAP.md) — secção 5 (rotas frontend) e §5.1 (subnavegação admin).