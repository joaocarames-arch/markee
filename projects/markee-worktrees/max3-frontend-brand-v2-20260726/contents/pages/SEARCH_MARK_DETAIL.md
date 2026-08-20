# Search and mark detail

Rotas:
- `/app#/search` `[PARTIAL]`.
- `/app#/marks/{application_number}` `[PLANNED]`.

Requisitos: `FR-SEARCH-001`, `FR-MARK-001`, `NFR-QUALITY-001`, `NFR-PERF-001`.
Contratos: [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md), [`../UI_BLOCKS.md`](../UI_BLOCKS.md), [`../GLOSSARY.md`](../GLOSSARY.md), [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md), [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md).

Notas de implementação:

- `/app#/search` já é servida pelo SPA atual (`frontend/dashboard/app.js`); o endpoint público `GET /api/v1/trademarks` é usado pelo frontend mas, no router backend atual, está sem requisito de JWT.
- `/app#/marks/{application_number}` é declaração de alvo P0. A API `GET /api/v1/trademarks/{application_number}` existe em `app/api/trademarks.py` mas o `frontend/dashboard/app.js` ainda não a serve em `VIEW_RENDERERS`. Implementação frontend deve entrar sem contradizer a API.
- A ação principal de `/app#/search` é submeter a pesquisa. A ação principal de `/app#/marks/{application_number}` é adicionar a marca a uma vigilância. As restantes opções são utilidades secundárias.

## Pesquisa - objetivo

Encontrar marcas relevantes por texto, jurisdição e classe. Decisão principal da vista: abrir o detalhe de uma marca ou adicionar a uma vigilância a partir do resultado.

H1:
`Pesquisa de marcas`

Subtítulo:
`Pesquise por nome, jurisdição e classe de Nice na base disponível.`

Intro:
`A pesquisa atual é funcional, mas ranking avançado e `pg_trgm` explícito ainda são trabalho parcial. Os resultados devolvidos dependem das fontes configuradas e da freshness de cada uma.`

CTA primário da vista:
`Pesquisar` -> submete `SearchForm` na própria vista (`GET /api/v1/trademarks`)

Utilidade de navegação secundária:
- `Limpar filtros` -> reset `Filters` na própria vista

Acesso ao detalhe:
- CTA contextual por resultado: `Ver detalhe` -> `/app#/marks/{application_number}` `[PLANNED]`
- Utilidade contextual por resultado: `Adicionar a vigilância` -> `/app#/watchlists`

Labels:
- `Texto da marca`
- `Jurisdição`
- `Classe de Nice`
- `Limite de resultados`

Placeholders:
- `Ex.: NovaLuz`
- `Todas as jurisdições`
- `Ex.: 35`

Ajuda contextual:
`Use nome, número ou termo distintivo. Filtros reduzem ruído, mas não garantem cobertura completa.`

Resultados:
- Título do card/tabela: `{word_mark}`
- Metadados: `Nº pedido {application_number} · {jurisdiction} · Classes {nice_classes}`
- Estado: `{status}`
- Fonte: `{source}` quando disponível

Desktop:
- Tabela quando houver muitos resultados.
- Cards para top results ou mobile.

Mobile:
- `SearchForm` acima.
- Filtros colapsáveis.
- `ResultCard` com CTA contextual no fim.

Estados da pesquisa:
- Loading: `A pesquisar marcas disponíveis.`
- Empty `no-results`: `Não encontrámos marcas para estes filtros.` Utilidade contextual `Limpar filtros`.
- Success: `{count} resultados encontrados.`
- Warning: `A pesquisa pode não incluir fontes bloqueadas ou dados ainda não reconciliados.`
- Error: `Não conseguimos concluir a pesquisa.` Utilidade contextual `Tentar novamente` (recarrega a vista).
- Permission denied: `Inicie sessão para pesquisar.` Utilidade contextual `Iniciar sessão` -> `/app#/login`.
- Stale data: `Alguns resultados podem estar desatualizados. Verifique a fonte.`

## Detalhe de marca - objetivo

Ver dados consolidados de uma marca antes de a vigiar, rever prazo ou usar como referência. Decisão principal da vista: adicionar a marca a uma vigilância. As restantes opções (voltar, criar prazo manual, exportar) são utilidades secundárias; a criação de prazo manual e o export permanecem `[PLANNED]` até a respetiva regra de produto e schema serem decididos.

H1:
`{word_mark}`

Subtítulo:
`Nº pedido {application_number} · {jurisdiction}`

Intro:
`Dados bibliográficos, classes, titulares, estado e histórico disponível, com proveniência e freshness visíveis. Esta página é alvo P0 e ainda não está servida pelo SPA atual; a sua implementação deve preservar os blocos abaixo.`

CTA primário da vista:
`Adicionar a vigilância` -> `/app#/watchlists`

Utilidades de navegação secundária:
- `Voltar à pesquisa` -> `/app#/search`
- `Criar prazo manual` `[PLANNED]` -> alvo futuro `/app#/deadlines` com item pré-preenchido; sem implementação atual.
- `Exportar` `[PLANNED]` -> alvo futuro pendente de decisão de formato, permissões e RGPD.

Secções:
1. `MarkSummary`
   - `Marca`
   - `Número de pedido`
   - `Estado`
   - `Jurisdição`
   - `Classes de Nice`
   - `Titulares` com minimização de dados pessoais.
2. `ProvenanceBadge`
   - `Fonte principal`
   - `Última atualização conhecida`
   - `Confiança`
3. `Timeline` `[PLANNED/PARTIAL]`
   - `Pedido`
   - `Publicação`
   - `Concessão`
   - `Recusa`
   - `Caducidade`
   - BPI events: `[BLOCKED]` até validação dos gates BPI-GATE-01..16.

Tooltips:
- Proveniência: `Mostra de onde veio este dado e quando foi processado.`
- Confiança: `Indicador técnico de consistência. Não substitui validação profissional.`
- Freshness: `Última vez que o Markee obteve ou confirmou este dado.`
- Fonte: `Sistema ou documento de origem.`

Estados do detalhe:
- Loading: `A carregar detalhe da marca.`
- Empty: `Não há detalhe disponível para este número.`
- Success: `Detalhe carregado.`
- Warning: `Existem dados parciais ou sem reconciliação completa.`
- Error: `Não conseguimos carregar esta marca.` Utilidade contextual `Tentar novamente` (recarrega a vista).
- Permission denied: `Inicie sessão para ver detalhes de marca.` Utilidade contextual `Iniciar sessão` -> `/app#/login`.
- Stale data: `Última atualização conhecida: {date}. Confirme dados críticos na fonte oficial.`

Roteiro `mark detail` por etapas (quando implementado):
1. Match de hash `marks/{application_number}` para renderer dedicado.
2. Render `MarkSummary` com dados da API.
3. Render `ProvenanceBadge` quando `source_runs` e `parser_version` existirem.
4. Render `Timeline` com eventos `events.lifecycle_events` apenas não-BPI.
5. CTA primário `Adicionar a vigilância` abre modal de seleção de vigilância.

## Claims bloqueados

Não escrever como afirmação ativa:
- `Histórico BPI completo`.
- `Prazos de oposição garantidos`.
- `Dados em tempo real`.
- `Cobertura completa INPI/EUIPO`.

Escrever:
- `Histórico disponível nas fontes configuradas.`
- `Eventos BPI: bloqueados até validação dos gates BPI-GATE-01..16.`
- `Prazos apresentados como apoio à revisão; confirme na fonte oficial ou com profissional qualificado.`

## Questões abertas

A rota de detalhe depende de `OD-06`, definida apenas na secção canónica de [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md). Até aprovação, permanece `[PLANNED — depende de OD-06]`. A autenticação do endpoint de pesquisa exige revisão técnica separada; esta página não decide nem promete a alteração.

## Navegação relacionada

- [`../README.md`](../README.md) — convenções editoriais e taxonomia de estados.
- [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md) — princípios de redação, uma ação principal por vista e microcopy canónica.
- [`../GLOSSARY.md`](../GLOSSARY.md) — termos canónicos PT-PT/EN.
- [`../UI_BLOCKS.md`](../UI_BLOCKS.md) — blocos `SearchForm`, `Filters`, `ResultCard/Table`, `MarkSummary`, `ProvenanceBadge`, `SourceFreshness`, `ConfidenceIndicator`, `Timeline`.
- [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) — linhas `/app#/search` e `/app#/marks/{application_number}`.
- [`DASHBOARD.md`](DASHBOARD.md) — `AlertItem` e `DeadlineItem` referenciados a partir do painel.
- [`WATCHLISTS_ALERTS_DEADLINES.md`](WATCHLISTS_ALERTS_DEADLINES.md) — vista `/app#/watchlists` (destino do CTA `Adicionar a vigilância`).
- [`ADMIN_PORTAL.md`](../pages/ADMIN_PORTAL.md) — proveniência e qualidade detalhadas no portal admin.
- [`../../docs/SITEMAP.md`](../../docs/SITEMAP.md) — secção 5 (rotas frontend) e §6 (`/api/v1/trademarks`).
- [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md) — `FR-SEARCH-001`, `FR-MARK-001`, `NFR-PERF-001`.