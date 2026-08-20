# STG-01 — Fecho de contratos e aprovação editorial

Data: 2026-07-24
Working directory: `/home/batata/projects/markee`
Âmbito: fecho documental/produto; sem alterações a código, configuração, testes, serviços, plano canónico ou `contents/**`.
Veredicto: **READY_FOR_JOAO**

## 1. Veredicto e leitura do snapshot

O STG-01 está pronto para decisão do João, não para promoção live.

O snapshot de `docs/ACTION_PLAN_TO_LIVE.md` dizia que `contents/**` estava WIP e aguardava auditoria independente. Esse facto ficou ultrapassado pelo estado observado nesta missão:

- o pacote editorial contém 13 ficheiros;
- `/tmp/max2-markee-contents-final-audit.md` reporta PASS;
- `/tmp/max2-markee-contents-final-reaudit.md` reporta FAIL intermédio por dois blockers concretos;
- `/tmp/max2-markee-contents-final-two-check.md` reporta PASS final, limitado precisamente aos dois blockers, confirmando a correcção editorial do fluxo registo→login e a separação entre risco BPI actual e estado-alvo;
- a execução local `.venv/bin/python -m pytest -q` nesta missão devolveu `144 passed, 2 skipped, 1 warning`.

Conclusão factual: **Max concluiu o pacote `contents/**` e Max-2 deu PASS final no âmbito auditado**. Isto não é aprovação do João, não é `GATE-PRODUTO-JOAO`, não é `GATE-EDITORIAL-PASS` assinado pelo João e não é `GATE-JURIDICO`. O PASS editorial independente prova coerência do pacote após a remediação; não prova que a implementação técnica esteja pronta nem que claims legais/comerciais possam ser publicados.

O código continua a vencer a copy quando há divergência. Evidência relevante:

- `/app#/watchlists` tem API/UI e testes de ownership: estado técnico local implementado, não live;
- `/app#/marks/{application_number}` tem endpoint, mas não tem view frontend dedicada;
- `/app#/admin` e subáreas continuam planeadas/bloqueadas;
- deadlines não têm user scope e o cálculo não filtra BPI por source;
- BPI continua NO-GO/BLOCKED/CRITICAL;
- billing tem caminhos mock e Stripe, mas o modo efectivo é UNKNOWN e não houve validação Stripe real;
- email e Telegram não têm entrega real validada;
- a instância pública observada é PUBLIC DEV INSTANCE, não staging separado nem produção live.

## 2. Legenda de estado e evidência

A matriz abaixo usa quatro colunas de maturidade, sempre com significado independente:

- `implemented`: existe código/rota ou copy especificada;
- `configured`: existe configuração/caminho detectável, mas não prova execução segura nem modo efectivo;
- `validated`: existe teste/evidência local suficiente para o comportamento indicado; não equivale a UAT, staging ou dados reais;
- `live`: operação de produção aprovada, com ambiente, dados, segurança, legal, observabilidade, rollback e sign-off. **Nenhuma capacidade está confirmada como live.**

`—` significa “não provado”. `I/C/V/L` na matriz são, respectivamente, implemented/configured/validated/live.

Owners abaixo são owners recomendados para a decisão ou remediação; não constituem atribuição nem aprovação.

## 3. Matriz P0: rota → requisito → copy → API/source → teste → estado → blocker → owner

| Rota P0 | Requisito canónico | Copy editorial aprovada/a aplicar | API / source of truth | Teste/evidence existente | I | C | V | L | Blocker | Owner recomendado |
|---|---|---|---|---|---|---|---|---|---|---|
| `/` e anchors públicos | FR-LAND-001; FR-BILLING-001; NFR-LEGAL-001 | `PUBLIC_LANDING.md`: proposta de valor; BPI NO-GO; sem 24/7, ≤24h, entrega email/Telegram ou cobertura completa | HTML estático `frontend/landing/index.html`; `PLAN_META`; fontes configuradas | HTTP local/público observado; sem teste frontend/editorial automatizado | Sim | Parcial | Não | Não | claims só podem ser publicados após anti-claims e implementação da copy revista; legal em falta | João para copy/scope; Forja para aplicação |
| `/app` shell | FR-AUTH-003; NFR-SEC-001 | `AUTH_ONBOARDING.md`: verificar sessão; erro/sessão expirada; logout apenas remove JWT local | `GET /api/v1/auth/me`; JWT em `localStorage` | `tests/integration/test_api.py`; HTTP observado | Sim | Parcial | Sim para auth coberta | Não | sem hardening, recuperação, rate limit e validação de ambiente | Forja; João para política de sessão |
| `/app#/login` | FR-AUTH-001..003 | Registo devolve `UserOut` sem JWT; frontend chama login automaticamente; fallback manual se falhar; sem verificação de email actual | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`; `app.users` | `tests/integration/test_api.py`; auditoria final confirmou sequência real em `frontend/dashboard/app.js:535-555` | Sim | Parcial | Sim para contrato auth | Não | password policy, rate limit, recovery/verify email e UAT ausentes | Forja; João decide OD-05 |
| `/app#/dashboard` | FR-DASH-001 | Resumo limitado ao que a fonte/API fornece; freshness e alertas só quando suportados; sem métricas inventadas | `/watchlists`, `/alerts`, `/deadlines`; `app.*`, `core.*` | Código `frontend/dashboard/app.js`; sem E2E frontend | Sim | Parcial | Não | Não | APIs de alertas/deadlines sem validação completa; deadlines inseguros; OD-09/10/11 | Forja; João decide OD-09..11 |
| `/app#/search` | FR-SEARCH-001 | Pesquisa na base disponível; ranking e fonte visíveis; mock nunca apresentado como real | `GET /api/v1/trademarks`; `core.trademarks`; EUIPO/TMview real ou fallback mock | `tests/integration/test_api.py`; endpoint usa `ILIKE` | Sim | Parcial | Parcial | Não | filtro `nice_class` não está completo segundo contrato; dados reais/credenciais UNKNOWN; OD-01 | Forja; João decide OD-01 |
| `/app#/marks/{application_number}` | FR-MARK-001 | Detalhe com proveniência/confiança; rota é alvo P0, não capacidade actual | `GET /api/v1/trademarks/{application_number}`; `core.trademarks` | Endpoint coberto na auditoria/API; view frontend ausente | Sim (API) | Não (UI) | Não | Não | falta rota/view, timeline/proveniência visível e decisão OD-06 | Forja; João decide OD-06 |
| `/app#/watchlists` | FR-WATCH-001..003 | Ownership por conta; matching explicitamente parcial até pipeline end-to-end validado | CRUD `/watchlists*`; `app.watchlists`, `app.watchlist_items`; similarity engine/tasks | `tests/integration/test_watchlists_api.py`; unit tests similarity | Sim | Parcial | Sim para CRUD/ownership | Não | matching ingestão→alerta sem E2E; quotas/validação fortes pendentes | Forja; produto valida scope |
| `/app#/alerts` | FR-ALERT-001..003 | Alertas internos disponíveis; `Envio externo não validado.`; nunca “enviado/entregue” sem prova | `/alerts*`; `app.alerts`; tasks `send_alerts`; SMTP/Telegram se configurados | Código API/frontend; não há teste dedicado de ownership/delivery | Sim | Parcial | Não | Não | pipeline e delivery não validados; BPI bloqueado; OD-08/11/12 | Forja; João decide OD-08/11/12 |
| `/app#/deadlines` | FR-DEADLINE-001..002 | Apoio à organização, não garantia jurídica; BPI/PT bloqueado até source guard, regra versionada e gates | `/deadlines`; `app.deadlines`; `events.lifecycle_events`; lifecycle engine | unit `test_lifecycle.py`; endpoint/user-scope não testado | Sim | Parcial | Não | Não | fuga multi-tenant; cálculo BPI sem source guard; sem aprovação jurídica; BPI-GATE-01/02/13 | Forja para guard/scope; João e jurídico para regra |
| `/app#/settings` | FR-ACCOUNT-001; FR-BILLING-001..003 | Plano atribuído separado do catálogo; `BillingStatus=unknown` sem data inventada; checkout desactivado até validação | `/billing/subscription`, `/billing/plans`, `/billing/checkout`, `/billing/webhook`; `app.subscriptions`; Stripe | Código frontend/API; sem testes Stripe/webhook reais | Sim | Sim (caminhos) | Não | Não | modo Stripe UNKNOWN, checkout mock possível, webhook não validado; OD-13..15 | Forja; João decide OD-13..15 |
| `/app#/admin` e `/admin/overview` | FR-ADMIN-001..002; NFR-ADMIN-SEC-001 | Portal admin é alvo read-only; ausência de métricas não significa saúde; acesso admin apenas | `/health`, `/api/v1/health`, `/quality/metrics` parcial; DB/workers/Redis | health testado; não há router/UI admin nem deny tests | Não (portal) | Parcial (health) | Não | Não | UI/API agregadas, RBAC efectivo, audit e observabilidade ausentes | Forja; João confirma scope |
| `/app#/admin/users` | FR-ADMIN-003 | Lista redigida sem password/hash/token; read-only | `app.users`, `app.subscriptions`; endpoint admin necessário | Sem endpoint/UI/testes | Não | Não | Não | Não | RBAC, redaction, paginação e deny tests | Forja |
| `/app#/admin/subscriptions` | FR-ADMIN-004 | Mock/dev versus Stripe real validado sempre distinto; não inventar MRR/receita | `app.subscriptions`; billing endpoints; Stripe | Sem admin endpoint/UI; billing real não validado | Não | Parcial | Não | Não | decisões de billing, Stripe/webhooks, RBAC e audit | Forja; João decide OD-13..15 |
| `/app#/admin/sources` e `/admin/imports` | FR-ADMIN-005..006; NFR-QUALITY-001 | Fonte, modo, freshness, run e erro redigido; sem secrets; retry/replay bloqueado | `core.sources`, `core.source_runs`, `raw.api_responses`, ingestion/tasks | Modelos/serviços parciais; sem UI/API agregada | Não | Parcial | Não | Não | endpoint admin, provenance/drill-down, idempotência e redaction | Forja |
| `/app#/admin/jobs` | FR-ADMIN-007; NFR-OBS-001 | Só mostrar estado quando API segura existir; cancelar/repetir bloqueado | Celery/Redis/tasks; API inexistente | `celery inspect ping` observado; falhas de tasks observadas; sem API/testes | Não | Sim (infra local) | Não | Não | heartbeat/API, dead-letter, idempotência, audit; workers degradados | Forja |
| `/app#/admin/quality` | FR-ADMIN-008 | Completude/confiança/proveniência/reconciliação; raw nunca como HTML | `/quality/metrics` parcial; schemas `raw/core/events/app` | endpoint existe mas policy/UI/drill-down não; schema tests | Parcial (endpoint) | Parcial | Não | Não | admin RBAC, métricas por fonte/run, redaction e testes | Forja |
| `/app#/admin/review` e `/admin/audit` | FR-ADMIN-009..010; NFR-ADMIN-SEC-001 | Quarentena redigida; audit append-only; acções mutáveis bloqueadas | `app.review_queue`; modelo audit específico não confirmado | Sem API/UI/admin tests | Não | Não | Não | Não | policy, audit append-only, RBAC, confirmação, schema e testes | Forja; João aprova policy |
| `/app#/admin/bpi` | FR-ADMIN-011; FR-BPI-001..008; BPI-GATE-01..16 | NO-GO/BLOCKED/CRITICAL; gates visíveis; “não activar ingestão, prazos ou alertas BPI” | Parser legacy/docs/YAML não são pipeline operacional; schemas BPI específicos ausentes | `test_bpi_parser.py` usa texto simulado; auditorias confirmam blockers | Parcial (legacy/docs) | Não | Não | Não | todos BPI-GATE-01..16; source guard inexistente | Forja executa após decisão; Max-2 audita; jurídico/João gates |
| `/privacy`, `/terms`, `/legal` | NFR-GDPR-001; NFR-LEGAL-001 | Conteúdo legal separado e explicitamente sujeito a `GATE-JURIDICO`; disclaimers não substituem aprovação | Estático planeado; sem rotas/ficheiros servidos actualmente | conteúdo auditado; ausência de rotas confirmada | Não | Não | Não | Não | textos legais, RGPD, retenção, consentimento e aprovação jurídica | João/jurídico |

### Conclusão da matriz

A matriz satisfaz o rastreio documental de todas as superfícies P0 do contrato. Não satisfaz, por si só, os critérios técnicos de implementação. O maior desvio é entre “rota alvo” e “rota servida”: detalhe de marca, admin e legais têm copy contratual, mas não são capacidades implementadas. A única capacidade P0 com validação substancial é auth básica e CRUD de watchlists; isso não autoriza live.

## 4. Capability matrix por ambiente

Estado de referência: `local` é desenvolvimento isolado; `public-dev` é a instância pública observada e não é staging; `staging` e `prod` não têm evidência de ambiente separado.

| Capacidade | local | public-dev | staging | prod | Regra de release |
|---|---|---|---|---|---|
| Auth | I/C/V parcial; testes auth | I observado; não hardened | Não provado | Não provado | permitido apenas com hardening, rate limit, secret seguro e UAT |
| Search | I/V parcial; fallback mock possível | I público/SPA; mock pode existir | Não provado | Não provado | mock identificado; sem fonte real não apresentar resultados como reais |
| Watchlists | I/V CRUD e ownership | I publicado, sem UAT | Não provado | Não provado | P0 candidato após user-scope e smoke |
| Alerts internos | I parcial; sem E2E | I parcial | Não provado | Não provado | mostrar apenas estado interno; sem claim de delivery |
| Deadlines | I mas BLOCKED/CRITICAL | I exposto com risco de scope/BPI | Não promover | Não promover | disabled por release policy até guards e user-scope técnicos; não confiar em copy |
| BPI | legacy I; NO-GO | potencialmente agendado/risco; NÃO | NÃO activar | NÃO activar | excluir e desactivar tecnicamente; BPI-GATE-01..16 OPEN/BLOCKED |
| Admin | não implementado | não implementado | não provado | não provado | deferir até RBAC, audit, APIs e deny tests |
| Billing/Stripe | mock I; real C UNKNOWN | checkout/catálogo alcançável; não live | não provado | não provado | excluir checkout; catalogar sem claim de cobrança |
| Email | caminho C por env; delivery UNKNOWN | não validado | não provado | não provado | não dizer enviado/entregue |
| Telegram | caminho C por env; delivery UNKNOWN | não validado | não provado | não provado | não dizer enviado/entregue |
| Portfolios | API parcial I; UI não | não vender como capacidade completa | não provado | não provado | deferir P1; sem leads públicos |
| Legal | copy planeada; rotas ausentes | não provado | não provado | não provado | sem publicação live antes de GATE-JURIDICO |
| Mock data | fallback existe; identificável | risco de parecer real | proibido sem label inequívoco | proibido | mock nunca se apresenta como real; sem dado real: “dados indisponíveis” |
| Real data | BD observada sem provenance real suficiente; credenciais UNKNOWN | não provado | não provado | não provado | exige source/run/freshness/provenance e validação independente |

`configured` não significa “activo”: campos de configuração, caminhos de serviço e schedules não provam modo efectivo, credenciais válidas, entrega ou segurança.

## 5. Release scope freeze proposto

Aplicar somente depois da aprovação do João; esta missão não aplica o freeze.

### Incluído no release candidato

1. Landing e auth apenas com copy anti-claims aprovada.
2. Dashboard limitado a dados efetivamente disponíveis e com estados `loading/empty/warning/error/stale/permission denied`.
3. Pesquisa apenas com indicação explícita da fonte e do modo mock/real; sem ranking/cobertura prometidos sem evidência.
4. CRUD de watchlists, com ownership testado.
5. Alertas internos apenas; sem promessa de envio externo.
6. Prazos apenas depois de corrigidos source guard, user scope e regras; até lá, a superfície deve ser bloqueada/indisponível, não uma lista “operacional”.
7. Admin, detalhe de marca, portfolios, export, legais e recovery como `deferred` até implementação e validação próprias.

### Excluído/disabled

- BPI: ingestão, parsing operacional, eventos, prazos e alertas BPI. O parser legacy, YAML, investigação ou uma task agendada não são autorização.
- Checkout/upgrade Stripe: disabled até testes controlados de checkout, assinatura de webhook, idempotência, catálogo e decisão comercial.
- Email/Telegram: disabled como claims de entrega; qualquer canal interno de teste deve estar explicitamente marcado e isolado.
- Prospeção/exportação de contactos/listas gerais: deferred por RGPD, custo e falta de UI/policy.
- Enterprise/API pública, SSO, WIPO, white-label, analytics e relatórios complexos: deferred.

### Regras fail-closed

- Capacidade não `validated` fica indisponível ou explicitamente marcada como não disponível; não fica escondida atrás de copy optimista.
- Capacidade `mock` tem label persistente de mock/dev. Mock nunca é “fonte oficial”, “dados reais” ou “monitorização”.
- Nenhum claim público sem evidence pack correspondente: rota, runtime, teste, source/run e ambiente.
- Nenhuma data legal, freshness, entrega, cobertura, SLA ou “tempo real” é inventada.
- Nenhuma promoção de local/public-dev para staging/prod enquanto STG-00..STG-11 não fecharem os respectivos gates.
- BPI permanece disabled mesmo que a BD esteja vazia ou o worker esteja avariado; uma falha de execução não é um controlo.

## 6. OD-01..OD-20 — decisões do João

Todas continuam **OPEN**. As recomendações são propostas de produto, não decisões aplicadas. Se João não decidir, o default é **fail-closed**: não activar a capacidade dependente, não publicar o claim e não ampliar o scope.

| ID | Pergunta | Opções | Recomendação fundamentada | Default se sem decisão | Impacto/custo/dependência | Escolha curta para aprovação |
|---|---|---|---|---|---|---|
| OD-01 | Pesquisa pública ou privada? | pública; privada | Privada em P0: reduz exposição e alinha SPA com dados de conta; endpoint actual é público no backend e precisa de revisão | bloquear pesquisa sem sessão | auth, endpoint scope, deny tests, UX pública | `OD-01: privada em P0` |
| OD-02 | Formato/permissões/salvaguardas de relatórios? | CSV; PDF; ambos; deferir | Deferir: não há rota/export nem política de dados | não criar export | implementação, RGPD, storage e testes de permissão | `OD-02: deferir relatórios/export` |
| OD-03 | Export de auditoria? | não; CSV; JSON; ambos | Deferir até audit append-only, redaction e RBAC | export bloqueado | audit schema, PII, rate limit, revisão legal | `OD-03: sem export até audit+RGPD` |
| OD-04 | 404/500 dedicadas ou SPA? | páginas dedicadas; estados SPA; híbrido | Híbrido: 404/500 dedicadas, erros de domínio inline; recupera melhor sem duplicar UI | mostrar estado seguro sem nova rota | routing, templates, E2E e a11y | `OD-04: híbrido` |
| OD-05 | Verificação de email bloqueante ou aviso? | bloqueante; aviso; sem funcionalidade | Sem funcionalidade no MVP actual, com texto neutro; não há campo/serviço | não bloquear nem prometer email | serviço email, recovery, modelo, RGPD | `OD-05: sem verificação no MVP; sem claim` |
| OD-06 | Detalhe em hash ou path real? | hash; path real | Hash: preserva router vanilla existente e reduz mudança P0; view continua por implementar | não publicar deep link | frontend router, E2E, provenance | `OD-06: manter hash` |
| OD-07 | Legal combinado ou três páginas? | combinado; `/privacy`+`/terms`+`/legal` | Três páginas: separa privacidade, termos e disclaimer e já está refletido no pacote | não publicar páginas legais | redação jurídica, rotas, links, GATE-JURIDICO | `OD-07: três páginas` |
| OD-08 | Manter referências visíveis a email/Telegram? | remover; mencionar neutro; prometer por plano | Mencionar neutro, sempre “envio externo não validado”; evita apagar informação sem criar claim | ocultar capacidade externa | copy, NotificationStatus, delivery evidence | `OD-08: texto neutro, sem promessa` |
| OD-09 | Âmbito do KPI “Vigilâncias activas”? | por user; por team; global | Por utilizador autenticado: único âmbito seguro com modelos/testes actuais | KPI indisponível | query scope, dashboard aggregation, auth | `OD-09: por utilizador` |
| OD-10 | Quem vê SourceFreshness? | todos; admins; ninguém | Apenas admin/superuser até existir endpoint e política de freshness utilizável | ocultar bloco | RBAC, API sources, UX e observabilidade | `OD-10: só admin/superuser` |
| OD-11 | Janela de alertas recentes? | não-lidos; 7 dias; ambos; configurável | Não-lidos, fallback de sete dias: corresponde a trabalho pendente sem perder contexto | não mostrar “recentes” agregados | query, ordenação, testes e dashboard | `OD-11: não-lidos; fallback 7 dias` |
| OD-12 | NotificationStatus sempre ou só com canal configurado? | sempre; canal configurado; nunca | Sempre, enquanto entrega não validada: impede inferência de entrega | ocultar canais e mostrar apenas alertas internos | componente, estados de delivery e copy | `OD-12: sempre, neutro` |
| OD-13 | Separar plano atribuído e catálogo? | mesma área; cartões separados; admin só | Cartões separados na settings: evita confundir preço com subscrição efectiva | não misturar catálogo e plano | UI, billing state e suporte a unknown | `OD-13: cartões separados` |
| OD-14 | Data quando BillingStatus unknown? | esconder; “não disponível”; última observada | `Sincronização indisponível`, sem data fictícia: estado honesto e barato | não mostrar data | UI state, webhook/sync evidence | `OD-14: Sincronização indisponível` |
| OD-15 | Upgrade por checkout ou contacto? | checkout; contacto; nenhum | Nenhum checkout público até Stripe real controlado; contacto só após canal aprovado | checkout disabled e sem CTA comercial activo | Stripe test mode, webhook, billing policy e custo | `OD-15: checkout desactivado até validação` |
| OD-16 | Canal de Contactar legal? | mailto; formulário; nenhum | `mailto:spud@batata.cc` provisório, sujeito a aprovação e sem promessa de SLA | remover CTA de contacto | legal, recepção/retenção e ownership | `OD-16: mailto provisório, sujeito a jurídico` |
| OD-17 | Quando banner de consentimento? | sempre; só cookies não essenciais; nunca | Só com analytics/marketing/terceiros: minimiza fricção e respeita finalidade | não apresentar banner sem cookies que o exijam | inventário cookies, CMP/preferências, jurídico | `OD-17: apenas cookies não essenciais` |
| OD-18 | Destino de pedidos de eliminação? | rota dedicada; mailto/formulário; backoffice | Deferir escolha até política RGPD/retention; não inventar endpoint | pedido bloqueado com contacto não publicado | backend, verificação identidade, audit e retenção | `OD-18: deferir; sem endpoint inventado` |
| OD-19 | Thresholds de atualização globais ou por fonte? | globais; por fonte; híbridos | Híbrido: defaults globais e override por fonte após dados de freshness; reduz complexidade P0 | não mostrar freshness threshold operacional | modelação, source registry, observabilidade | `OD-19: globais com override futuro por fonte` |
| OD-20 | Formato/permissões/salvaguardas de export de leads? | CSV; PDF; ambos; nenhum | Nenhum P0; prospeção/export fica deferred por RGPD, custo e falta de UI | export bloqueado | policy RGPD, minimização, audit, quotas e storage | `OD-20: sem export P0` |

## 7. Decisões obrigatórias para P0 vs deferíveis

### Obrigatórias antes de fechar P0

- OD-01: acesso à pesquisa e exposição de dados.
- OD-04: tratamento de erros públicos e privados.
- OD-05: comportamento pós-registo/verify-email, mesmo que seja “não existe no MVP”.
- OD-06: contrato do detalhe de marca.
- OD-08, OD-11, OD-12: claims e selecção de alertas.
- OD-09: isolamento do KPI.
- OD-10: visibilidade de freshness.
- OD-13, OD-14, OD-15: billing sem confundir mock com cobrança.
- OD-07, OD-16, OD-17, OD-18: legais, consentimento e pedidos RGPD; não publicar sem `GATE-JURIDICO`.
- decisão explícita de scope freeze: BPI disabled; deadlines inseguros não são P0 live; admin só após implementação.

### Podem ser deferidas sem bloquear o núcleo técnico mínimo

- OD-02 e OD-03: relatórios e export de auditoria.
- OD-18, se a superfície legal não for publicada e o mecanismo de contacto ficar fora do release.
- OD-19: thresholds avançados por fonte, mantendo o default seguro sem claim.
- OD-20: export de leads e prospeção.

“Deferir” tem de ficar registado como fora do release; não significa deixar o CTA activo.

## 8. Gates

### GATE-EDITORIAL-PASS

Estado de evidência: PASS independente no pacote actual, suportado pelos três relatórios `/tmp` e pelo inventário de 13 ficheiros. Falta registo formal do sign-off do João.

### GATE-PRODUTO-JOAO

Estado: OPEN. João tem de aprovar as escolhas curtas OD relevantes, o scope freeze e o veredicto de publicação. Nenhuma recomendação desta ficha o substitui.

### GATE-JURIDICO

Estado: OPEN/BLOCKED. Não existe aprovação jurídica provada para `/privacy`, `/terms`, `/legal`, RGPD, prazos/oposição BPI, retenção, prospeção, consentimento, disclaimers ou claims de responsabilidade. BPI-GATE-01/02/13 continuam dependentes de regra jurídica versionada, aprovador, data e base jurídica.

### Gate anti-claims

Estado: OPEN para publicação. O pacote editorial passou a auditoria, mas a landing actualmente servida no código foi observada com claims incompatíveis. A copy revista só pode ser aplicada após a aprovação e depois de teste/diff que prove zero claims proibidos no artefacto público.

## 9. Checklist binária de sign-off editorial/produto

Cada item precisa de `SIM` por João/owner e evidência identificável. O estado actual é indicado entre parênteses; não é uma aprovação.

- [ ] Contratos `SITEMAP.md` e `REQUIREMENTS.md` são a fonte única (actualmente: SIM, sem alteração nesta missão).
- [ ] Pacote editorial tem exactamente 13 ficheiros (SIM, confirmado pela auditoria final).
- [ ] Auditoria independente final PASS está arquivada (SIM, `/tmp/max2-markee-contents-final-two-check.md`).
- [ ] OD-01..OD-20 continuam abertas até resposta do João (SIM).
- [ ] João aprovou as OD obrigatórias (NÃO).
- [ ] João aprovou o scope freeze (NÃO).
- [ ] BPI está tecnicamente disabled, não apenas descrito como disabled (NÃO; blocker STG-00/06).
- [ ] Nenhum deadline BPI pode chegar à tabela/alerta sem source guard testado (NÃO; código actual contradiz).
- [ ] Deadlines têm user scope testado (NÃO).
- [ ] Pesquisa está no âmbito de acesso aprovado e mock é identificado (NÃO; OD-01 e implementação pendentes).
- [ ] Detalhe de marca P0 existe em UI e tem E2E (NÃO).
- [ ] Admin P0 tem RBAC, redaction, audit e deny tests (NÃO).
- [ ] Checkout e webhooks Stripe foram validados em ambiente controlado ou estão disabled (disabled proposto; validação NÃO).
- [ ] Email/Telegram têm delivery evidence, ou não são claims públicos (delivery NÃO; anti-claim SIM no pacote).
- [ ] Páginas legais e política RGPD foram aprovadas (NÃO; GATE-JURIDICO OPEN).
- [ ] Copy pública instalada coincide com o pacote revisto (NÃO provado; landing actual tem claims antigos).
- [ ] Todos os claims públicos têm source/runtime/test evidence (NÃO).
- [ ] Ambiente public-dev foi impedido de parecer staging/prod (NÃO; remediar fora deste STG).
- [ ] UAT do João passou em staging separado (NÃO existe evidence de staging).
- [ ] Sign-off final do produto foi registado com data, owner e commit/release candidate (NÃO).

Resultado binário actual: **NÃO APROVADO PARA RELEASE/LIVE**. Resultado do STG-01 documental: **READY_FOR_JOAO**.

## 10. Delta exacto a aplicar depois da decisão

Esta secção é uma lista de trabalho posterior. Nenhum item foi aplicado nesta missão.

1. Registar a resposta do João para OD-01..OD-20, preservando os IDs e marcando cada uma como approved/deferred/rejected.
2. Actualizar apenas os documentos/artefactos permitidos pela decisão: matriz canónica, copy dependente e release manifest; não reabrir alternativas já decididas.
3. Aplicar a copy fail-closed do pacote à landing e às vistas que tenham claims antigos; remover BPI diário, 24/7, ≤24h, entrega email/Telegram e claims de cobertura.
4. Desactivar BPI por código/configuração e schedule em ambientes não autorizados; introduzir source-deny para deadlines/alertas e testes de regressão.
5. Remover/disable checkout público e qualquer CTA que pareça cobrança real até STG-05 produzir evidence Stripe controlada.
6. Tornar todas as superfícies mock explicitamente mock/dev e substituir dados não reais por `dados indisponíveis` quando não houver proveniência real.
7. Implementar user scope de deadlines e testes de isolamento antes de apresentar prazos como capacidade P0.
8. Implementar detalhe de marca, admin P0, legais e respectivos testes apenas se permanecerem no scope aprovado.
9. Revalidar API/source/teste/estado por linha da matriz; actualizar `implemented/configured/validated/live` sem promover estados por inferência.
10. Executar auditoria anti-claims sobre o artefacto efectivamente servido, não apenas sobre `contents/**`.
11. Obter `GATE-JURIDICO`, `GATE-PRODUTO-JOAO` e sign-off de release antes de qualquer staging público ou produção.
12. Produzir evidence pack de staging separado, UAT, rollback e autorização operacional em STG-12..14.

## 11. Limitações e estado factual final

Não foram lidos `.env` nem valores de secrets. Não houve rede, deploy, Git commit/push, serviços, alterações públicas ou alterações fora do ficheiro autorizado. A validação executada foi local e real: `.venv/bin/python -m pytest -q` → `144 passed, 2 skipped, 1 warning`. Essa suite não cobre E2E frontend, staging, Stripe real, delivery email/Telegram, BPI operacional, admin P0, legal approval ou produção.

Confirmação de escopo: antes da escrita, `git status --short` mostrava apenas o estado pré-existente untracked (`config/bpi_event_taxonomy.yaml`, `contents/`, `docs/ACTION_PLAN_TO_LIVE.md`, `docs/REQUIREMENTS.md`, `docs/SITEMAP.md`, `docs/research/`). O único path autorizado a criar nesta missão é este relatório; após a escrita deve permanecer inalterado qualquer outro path.
