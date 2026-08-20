# Watchlists, alerts and deadlines

Rotas:
- `/app#/watchlists` `[IMPLEMENTED]`.
- `/app#/alerts` `[PARTIAL]`.
- `/app#/deadlines` `[PARTIAL]`.

Requisitos: `FR-WATCH-001..003`, `FR-ALERT-001..003`, `FR-DEADLINE-001..002`, `NFR-QUALITY-001`.
Contratos: [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md), [`../UI_BLOCKS.md`](../UI_BLOCKS.md), [`../GLOSSARY.md`](../GLOSSARY.md), [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md), [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md).

Princípios comuns a estas três vistas:

- Uma ação principal por vista: `Criar vigilância` (`/app#/watchlists`), `Marcar como lido` (`/app#/alerts`), `Rever prazo` (`/app#/deadlines`). As restantes opções (utilidades de navegação, utilidades de shell como `Terminar sessão`) são secundárias e não substituem a ação principal.
- Cada vista declara sempre todos os estados: `loading`, `empty`, `success`, `warning`, `error`, `stale`, `permission denied`.
- `NotificationStatus` aparece sempre que um alerta sugere canal externo, com texto neutro `Envio externo não validado.`
- `SourceFreshness`, `ProvenanceBadge`, `ConfidenceIndicator` e `DeadlineItem` aparecem sempre que a vista mostrar fonte, run, confiança ou data.
- Prazos derivados de BPI são classificados como `CRITICAL` (ver GLOSSARY §Deadline BPI): o `app/tasks/calculate_deadlines.recalculate_all` pode produzir `Deadline` de oposição para o último `LifecycleEvent.event_type == "publication"` sem filtrar source. BPI permanece NO-GO/`[BLOCKED]` até source guard, migration para `enabled`/`legal_status`, testes e regra legal versionada (`BPI-GATE-01`, `BPI-GATE-02`, `BPI-GATE-13`). Estado atual inseguro: o backend pode produzir e expor prazos BPI sem source guard. Estado-alvo obrigatório: UI e backend devem ocultá-los/bloqueá-los depois de um guard testado. Até lá, a feature BPI não pode ser promovida nem colocada live; copy não substitui controlo técnico.
- `EmptyState` cobre `first-use`, `no-results`, `in-progress`, `no-data-yet`, `blocked`, `rate-limited` e `redacted` quando aplicável.
- Email e Telegram estão individualmente marcados `[PLANNED]` como canal de envio externo: não existe envio real validado, configuração controlada nem entrega provada. A UI não promete entrega por estes canais.

## Vigilâncias `/app#/watchlists` `[IMPLEMENTED]`

Objetivo:
Criar e gerir listas de marcas, termos, classes e jurisdições a acompanhar. Decisão principal da vista: criar uma vigilância nova. As restantes decisões (adicionar item, editar, eliminar) são utilidades com destino próprio.

H1:
`Vigilâncias`

Subtítulo:
`Organize marcas, termos, classes e jurisdições que quer acompanhar.`

Intro:
`Cada vigilância pertence à sua conta. Use thresholds e classes para reduzir ruído. Thresholds mais altos diminuem falsos positivos, mas podem esconder semelhanças relevantes. O motor de matching é parcial até pipeline end-to-end estar validado.`

CTA primário da vista:
`Nova vigilância` -> abre modal/POST `/api/v1/watchlists` na própria vista.

Utilidade contextual de cada vigilância:
- `Adicionar item` -> abre modal/POST `/api/v1/watchlists/{id}/items` na própria vista.
- `Editar` -> abre modal/PUT `/api/v1/watchlists/{id}` na própria vista.
- `Eliminar` -> abre `ConfirmDialog` destrutivo e chama DELETE `/api/v1/watchlists/{id}`.

Blocos:
- `WatchlistCard` por vigilância (compact/expanded, estados `active`/`inactive`/`loading`/`error`).
- `SearchForm` compacto para adicionar item por texto/jurisdição/classe.
- `ConfirmDialog` destrutivo para eliminar vigilância e itens.
- `EmptyState` variantes `first-use`, `no-results`, `in-progress`, `rate-limited`, `redacted`.

Campos de formulário:
- `Nome da vigilância`
- `Limiar de similaridade`
- `Peso fonético`
- `Peso de classes`
- `Jurisdições`
- `Marca ou termo`
- `Classes de Nice`
- `Notas`

Ajuda contextual:
`Um limiar mais alto reduz falsos positivos, mas pode esconder semelhanças relevantes. O motor de matching é parcial até pipeline end-to-end estar validado.`

Confirmações:
- `Vigilância criada.`
- `Vigilância atualizada.`
- `Vigilância eliminada.`
- `Item adicionado à vigilância.`
- `Item removido.`

`ConfirmDialog` de eliminação:
- Título: `Eliminar vigilância?`
- Texto: `Esta ação remove a vigilância e os seus itens desta conta. Não pode ser revertida.`
- CTA destrutivo: `Eliminar vigilância`
- CTA secundário: `Cancelar`

Estados:
- Loading: `A carregar vigilâncias.`
- Empty `first-use`: `Ainda não há vigilâncias.` Utilidade contextual `Criar vigilância` (mesmo destino que o CTA principal).
- Empty `no-results`: `Não encontrámos marcas para os filtros. Tente alargar a pesquisa.`
- Success: `Vigilância guardada.`
- Warning: `Matching automático é parcial até pipeline end-to-end estar validado.`
- Error: `Não conseguimos carregar as vigilâncias.` Utilidade contextual `Tentar novamente` (recarrega a vista).
- Permission denied: `Inicie sessão para gerir vigilâncias.` Utilidade contextual `Iniciar sessão` -> `/app#/login`.
- Stale data: `A lista pode não refletir alterações recentes.`

Filtragem:
- Filtro por estado (`active`/`inactive`).
- Pesquisa por nome de vigilância.
- Ordenação por criação e última atualização.

Mobile:
- `WatchlistCard` em stack vertical.
- `ConfirmDialog` em largura total.
- CTA primário no topo, utilidades abaixo.

## Alertas `/app#/alerts` `[PARTIAL]`

Objetivo:
Rever alertas registados no Markee e limpar a fila. Decisão principal da vista: marcar como lido. As restantes decisões (dispensar, abrir a marca/vigilância associada) são utilidades com destino próprio.

H1:
`Alertas`

Subtítulo:
`Reveja sinais que podem precisar da sua atenção.`

Intro:
Estado interno dos canais: `[PLANNED]`. Copy visível: `Os alertas listados existem no Markee. Não há envio externo validado, configuração controlada nem entrega provada. A interface mostra o estado disponível e não promete entrega.`

CTA primário da vista:
`Marcar como lido` -> POST `/api/v1/alerts/{alert_id}/read` na própria vista.

Utilidades contextuais por `AlertItem`:
- `Dispensar` -> POST `/api/v1/alerts/{alert_id}/dismiss` na própria vista.
- `Ver marca` -> `/app#/marks/{application_number}` `[PLANNED]`.
- `Ver vigilância` -> `/app#/watchlists`.

Blocos:
- `AlertItem` com proveniência, confiança e freshness (`unread`/`read`/`dismissed`).
- `Filters` por estado, tipo de alerta, vigilância e data.
- Proposta condicionada à `OD-12`: se aprovada, `NotificationStatus` fica sempre visível enquanto a entrega externa não for validada.
- `ProvenanceBadge` por alerta com `source`, `run_id`, `document/page`, `parser_version`.
- `SourceFreshness` por alerta quando houver run conhecida.
- `ConfidenceIndicator` por alerta com banda `high`/`review`/`quarantine`/`unknown`.
- `EmptyState` `first-use`, `no-results`, `no-data-yet`, `blocked`, `redacted`.
- `ErrorState` `inline` ou `full-page` quando a fila não carrega.

Conteúdo de cada `AlertItem`:
- `Título`
- `Resumo`
- `Tipo`
- `Fonte`
- `Confiança`
- `Criado em`
- `Estado: por rever / lido / dispensado`
- `NotificationStatus` (texto neutro: `Envio externo não validado.`)

Tooltips:
- Fonte: `Fonte ou processo que originou este alerta.`
- Confiança: `Score técnico; reveja a fonte antes de agir.`
- Freshness: `Última atualização conhecida relacionada com este alerta.`
- Proveniência: `Indica a origem do dado e o caminho até à fonte usada pelo Markee.`

Filtros:
- `Todos`
- `Por rever`
- `Tipo de alerta`
- `Vigilância`
- `Data`

Confirmações:
- `Alerta marcado como lido.`
- `Alerta dispensado.`

Estados:
- Loading: `A carregar alertas.`
- Empty `first-use`: `Não há alertas por rever.`
- Empty `no-data-yet`: `Os alertas dependem da próxima ronda de processamento.` Utilidade contextual `Ver freshness` -> `/app#/dashboard`.
- Empty `blocked`: `Alertas derivados de BPI continuam bloqueados até validação dos gates BPI-GATE-01..16.`
- Success: `Lista de alertas atualizada.`
- Warning: `Alertas derivados de BPI continuam bloqueados até validação dos gates BPI-GATE-01..16.`
- Warning `stale`: `Pode haver alterações posteriores na fonte.`
- Error: `Não conseguimos carregar os alertas.` Utilidade contextual `Tentar novamente` (recarrega a vista).
- Permission denied: `Inicie sessão para ver alertas.` Utilidade contextual `Iniciar sessão` -> `/app#/login`.
- Stale data: `Última atualização conhecida: {date}. A fonte pode ter alterações posteriores.`

`NotificationStatus`:
- Texto canónico: `Envio externo não validado.`
- Estados visíveis: `not-configured`, `configured-mock`, `configured-real-unverified`, `configured-real-verified` (este último só depois de envio real provado).
- Email como canal: `[PLANNED]` — sem configuração controlada nem entrega real validada.
- Telegram como canal: `[PLANNED]` — sem bot integrado nem entrega real validada.
- Utilidade contextual: `Configurar canal` -> `/app#/settings` quando existir configuração.
- Nunca escrever `Enviado` ou `Entregue` sem evidência validada.

Mobile:
- Lista em `AlertItem` cards verticais.
- Ações de leitura e dispensa em fila acessível sem modal.
- Filtros em `Filters` drawer colapsável.

## Prazos `/app#/deadlines` `[PARTIAL]`

Objetivo:
Rever datas próximas e priorizar validação. Decisão principal da vista: rever o prazo. As restantes decisões (abrir detalhe da marca, confirmar fora do Markee) são utilidades com destino próprio.

H1:
`Prazos`

Subtítulo:
`Datas de revisão associadas às suas marcas e eventos disponíveis.`

Intro:
`Os prazos ajudam a organizar trabalho. Não são garantia jurídica e devem ser confirmados na fonte oficial ou com profissional qualificado em casos críticos. Prazos derivados de BPI são classificados como `CRITICAL` (ver GLOSSARY §Deadline BPI) e permanecem bloqueados até validação dos gates BPI-GATE-01..16.`

CTA primário da vista:
`Rever prazo` -> drill-down `/app#/marks/{application_number}` `[PLANNED]` quando existir a rota de detalhe; caso contrário, foco na secção `DeadlineItem` correspondente.

Utilidades contextuais por `DeadlineItem`:
- `Ver marca` -> `/app#/marks/{application_number}` `[PLANNED]`.
- `Filtrar próximos` -> query params `?upcoming_only=true` na própria vista.

Blocos:
- `DeadlineItem` por prazo (`upcoming`, `overdue`, `blocked`).
- `Timeline` compacta por marca quando houver eventos.
- `SourceFreshness` por prazo quando existir run conhecida.
- `Filters` por tipo, jurisdição, vencidos, próximos.
- `EmptyState` `first-use`, `no-data-yet`, `blocked`.
- `ErrorState` para falhas de carregamento.

Conteúdo de cada `DeadlineItem`:
- `Marca`
- `Tipo de prazo`
- `Data`
- `Dias restantes`
- `Fonte/regra`
- `Estado da regra: draft / validated` quando aplicável
- `ProvenanceBadge` quando a run estiver disponível
- `ConfidenceIndicator` quando a regra for parcial

Filtros:
- `Próximos`
- `Todos`
- `Tipo de prazo`
- `Jurisdição`
- `Vencidos`

Tooltip de prazo:
`Data calculada a partir dos dados disponíveis. Confirme prazos críticos na fonte oficial ou com profissional qualificado.`

Warnings obrigatórios:
- BPI/PT oposição: `Bloqueado até regra legal versionada e validada.` (referência: `BPI-GATE-01`, `BPI-GATE-02`, `BPI-GATE-13`).
- Freshness vencida: `Freshness da fonte ultrapassou o limite definido.`
- Conflito legal de semântica temporal PT: `Conflito de semântica temporal PT por resolver.` (referência: `BPI-GATE-02`).

Estados:
- Loading: `A carregar prazos.`
- Empty `first-use`: `Não há prazos próximos.`
- Empty `no-data-yet`: `Os prazos dependem da próxima ronda de processamento.` Utilidade contextual `Ver freshness` -> `/app#/dashboard`.
- Empty `blocked`: `Prazos derivados de BPI são classificados como `CRITICAL` (ver GLOSSARY §Deadline BPI) e permanecem bloqueados até validação dos gates BPI-GATE-01..16.`
- Success: `Prazos atualizados.`
- Warning: `Alguns prazos dependem de regras parciais ou fontes desatualizadas.`
- Warning `stale`: `Última atualização conhecida: {date}. Confirme antes de agir.`
- Error: `Não conseguimos carregar os prazos.` Utilidade contextual `Tentar novamente` (recarrega a vista).
- Permission denied: `Inicie sessão para ver prazos.` Utilidade contextual `Iniciar sessão` -> `/app#/login`.
- Stale data: `Última atualização conhecida: {date}. Confirme antes de agir.`

Regras por tipo:
- Renovação `[PARTIAL]`: regra lifecycle engine, com `ConfidenceIndicator`.
- Oposição PT e caducidade por falta de pagamento `[BLOCKED]`: permanecem NO-GO/BLOCKED/CRITICAL. Estado atual inseguro: não existe feature flag nem source guard que garanta o congelamento. Estado-alvo obrigatório: a ingestão e exposição BPI só podem ser ativadas após migration, source guard, validação dos BPI-GATE-01..16 e testes.
- Grace period `[PARTIAL]`: visível quando lifecycle devolve dados consistentes.

Mobile:
- `DeadlineItem` em stack vertical com data e urgência em primeiro lugar.
- Filtros em drawer colapsável.
- CTA `Rever prazo` em largura total no rodapé do card.

## Estados comuns às três vistas

Loading: skeleton de página ou de lista com texto visível.
Empty: `EmptyState` com utilidade contextual de recuperação.
Success: confirmação textual discreta.
Warning: copy sobre regras parciais ou freshness vencida.
Error: `ErrorState` com `Tentar novamente` na própria vista.
Permission denied: redirecionar para `/app#/login`.
Stale data: mostrar `Última atualização conhecida: {date}`.

## Claims proibidos nesta área

Não afirmar:
- alertas enviados ou entregues por email;
- alertas enviados ou entregues por Telegram;
- prazos derivados de BPI operacionais;
- prazos de oposição PT juridicamente garantidos;
- monitorização contínua automática;
- deteção sem falsos positivos/negativos;
- leitura diária do BPI;
- cobertura completa.

Escrever:
- Estado interno do envio externo: `[PLANNED]`. Copy visível: `Alertas disponíveis no produto; o envio externo por email ou Telegram não está validado como entrega real.`
- `Prazos derivados de BPI bloqueados até validação dos gates BPI-GATE-01..16.`
- `Confirme prazos críticos na fonte oficial ou com profissional qualificado.`

## Questões abertas

As decisões de produto são definidas apenas na secção canónica de [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md). Ver `OD-11` e `OD-12`; a seleção de alertas e a visibilidade de `NotificationStatus` permanecem condicionadas à aprovação. O bloqueio BPI e a idempotência de dispensa são controlos técnicos, não novas OD.

## Navegação relacionada

- [`../README.md`](../README.md) — convenções editoriais e taxonomia de estados.
- [`../CONTENT_PRINCIPLES.md`](../CONTENT_PRINCIPLES.md) — princípios de redação, uma ação principal por vista e microcopy canónica.
- [`../GLOSSARY.md`](../GLOSSARY.md) — termos canónicos PT-PT/EN (vigilância, alerta, prazo, notificação, BPI).
- [`../UI_BLOCKS.md`](../UI_BLOCKS.md) — blocos `WatchlistCard`, `AlertItem`, `DeadlineItem`, `NotificationStatus`, `SourceFreshness`, `ProvenanceBadge`, `ConfidenceIndicator`, `EmptyState`, `ErrorState`.
- [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) — linhas `/app#/watchlists`, `/app#/alerts`, `/app#/deadlines`.
- [`DASHBOARD.md`](DASHBOARD.md) — KPI `Vigilâncias ativas`, `Alertas por rever` e `Prazos próximos` derivam destas vistas.
- [`SEARCH_MARK_DETAIL.md`](SEARCH_MARK_DETAIL.md) — CTA `Adicionar a vigilância` aponta para `/app#/watchlists`; `/app#/marks/{application_number}` é destino da utilidade `Ver marca`.
- [`SETTINGS_BILLING.md`](SETTINGS_BILLING.md) — `NotificationStatus` com ligação a `/app#/settings` para configurar canal.
- [`ADMIN_PORTAL.md`](../pages/ADMIN_PORTAL.md) — fila de revisão e qualidade em `/app#/admin/review` `[PLANNED/BLOCKED]` e `/app#/admin/quality` `[PLANNED]`.
- [`../../docs/SITEMAP.md`](../../docs/SITEMAP.md) — secção 5 (rotas frontend) e §6 (rotas API watchlists/alerts/deadlines).
- [`../../docs/REQUIREMENTS.md`](../../docs/REQUIREMENTS.md) — `FR-WATCH-*`, `FR-ALERT-*`, `FR-DEADLINE-*`, gates BPI.