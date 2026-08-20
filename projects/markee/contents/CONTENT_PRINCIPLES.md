# Content principles

## Voz

O Markee fala em português europeu, com tom profissional, claro e direto. Deve soar como uma ferramenta de trabalho para PI, não como marketing vazio.

Usar:

- frases curtas;
- verbos de ação: pesquisar, rever, adicionar, marcar, filtrar, exportar quando existir;
- explicações objetivas de fonte, confiança e freshness;
- tratamento neutro/profissional: "a sua marca", "a sua vigilância", "a sua conta".

Evitar:

- "revolucionário", "360º", "mais inteligente", "definitivo", "garantido", "tempo real", "cobertura completa";
- entusiasmo artificial;
- promessas jurídicas absolutas;
- "IA" como argumento vago.

## Terminologia canónica

- Produto: `Markee` em texto normal; logótipo pode usar `markee`.
- `Marca`, `pedido de marca`, `registo`, `classe de Nice`, `jurisdição`.
- `Vigilância` para watchlist no UI; `watchlist` apenas em docs técnicos.
- `Alerta` para evento que pede atenção; `notificação` apenas para envio por canal.
- `Prazo` para datas de ação; nunca "deadline garantido".
- `Fonte`, `proveniência`, `confiança`, `atualização dos dados`; `freshness` apenas como termo técnico.
- `Revisão` e `quarentena` para dados que não devem entrar automaticamente no core.
- Identificadores técnicos (rotas, endpoints, nomes de tabela, `gate_id`) ficam em inglês quando necessário (`POST /api/v1/alerts/{id}/read`, `BPI-GATE-01`, `app.watchlists`).

## Uma ação principal por vista

Regra editorial padrão:

- Cada vista privada ou pública tem exatamente uma ação principal inequívoca. As restantes opções são utilidades secundárias (navegação contextual, refresh, abertura de detalhe) e nunca substituem a ação principal.
- A ação principal é a única que responde à pergunta "o que é que esta vista me deixa fazer agora?". Em `/app#/search` é `Pesquisar`; em `/app#/marks/{application_number}` é `Adicionar a vigilância`; em `/app#/watchlists` é `Nova vigilância`; em `/app#/alerts` é `Marcar como lido`; em `/app#/deadlines` é `Rever prazo`; em `/app#/settings` é `Gerir plano`; em `/app#/dashboard` é `Pesquisar marcas`.
- Utilidades de shell global (`Terminar sessão`, navegação lateral, refresh de página) não contam como segunda ação principal.
- Quando uma vista tiver dois candidatos a ação principal, a copy deve promover só um e degradar os restantes a utilidades com destino explícito.

Exceção regulatória — pares de consentimento:

- Uma vista de consentimento legal (ex.: banner de cookies) pode apresentar duas opções equivalentes em peso regulatório: `Aceitar todos` e `Apenas necessários`. Estas opções constituem um par de opt-in/opt-out equivalente, são regulatórias e não violam a regra de uma ação principal por vista.
- O par deve ser documentado como `par de consentimento` e ambas as opções precisam de destino e estado próprios (estado `Aceitar` grava consentimento para todas as categorias; `Apenas necessários` grava apenas essenciais; `Configurar` é terceira opção granular). Esta exceção é a única permitida pela regra.
- A exceção aplica-se apenas a fluxos de consentimento legal claramente identificados como tais. Não deve ser invocada para "resolver" dois CTAs fortes numa mesma vista de produto.

## Marcadores internos canónicos

`[IMPLEMENTED]`, `[PARTIAL]`, `[PLANNED]`, `[BLOCKED]`, `[OPEN DECISION]` são marcas internas e nunca aparecem ao utilizador final.

- `[OPEN DECISION]` é estritamente para decisões reais de produto ainda em aberto (ex.: privacidade vs pública na pesquisa, formato de export, política de retenção). Não usar para features simplesmente planeadas, que devem ser `[PLANNED]`, nem para gates dependentes de validação, que devem ser `[BLOCKED]`.
- Quando a copy de utilizador precisar de expor estado, usar linguagem natural:
  - `Ainda não operacional` em vez de `[PLANNED]`.
  - `Bloqueado por validação` em vez de `[BLOCKED]`.
  - `Modo de desenvolvimento` em vez de `[PARTIAL]`.
  - `Decisão em aberto` em vez de `[OPEN DECISION]`.
- O `NotificationStatus` distingue os sub-estados de canal externo: `not-configured`, `configured-mock`, `configured-real-unverified`, `configured-real-verified`. Só o último é válido após envio real provado; nunca usar `enviado` ou `entregue` sem evidência.

## Regras de claims

Copy pública só pode afirmar o que o estado permite:

- `[IMPLEMENTED]`: pode ser afirmado como disponível.
- `[PARTIAL]`: dizer que está disponível com limitações ou em modo parcial quando necessário.
- `[PLANNED]`: só como "planeado" ou "em preparação", nunca como funcionalidade ativa.
- `[BLOCKED]`: explicar o bloqueio quando relevante; não vender como ativo.
- `[OPEN DECISION]`: não prometer; esperar decisão de produto.

Claims proibidos sem implementação/teste:

- ingestão BPI diária operacional;
- leitura integral diária do BPI;
- cobertura completa INPI/EUIPO;
- prazos juridicamente garantidos;
- Stripe real em produção validado;
- alertas enviados por email;
- alertas enviados por Telegram;
- dados em tempo real;
- ausência de falsos positivos/negativos;
- monitorização contínua 24/7;
- serviço diário automático sem visibilidade de freshness.

Claims proibidos apenas em contexto positivo/ativo. Em contexto negativo, proibição, substituição ou disclaimer, podem aparecer como parte da explicação (ex.: "Não prometemos cobertura completa INPI/EUIPO; cada vista deve indicar fonte e atualização conhecida.").

Formulações seguras:

- "Pesquisa marcas registadas na base disponível."
- "Mostra a fonte e a data conhecida dos dados."
- "Os prazos ajudam a organizar revisão; confirme datas críticas com fonte oficial ou profissional qualificado."
- "BPI automatizado: bloqueado até validação dos gates técnicos e jurídicos BPI-GATE-01..16."
- Estado interno: `[PLANNED]`. Copy visível: "O envio externo por email e Telegram não está validado como entrega real."

## CTAs e destinos

- Todo o CTA visível ao utilizador deve ter destino explícito: rota hash, rota path, endpoint, `mailto:`, `history.back()` ou estado marcado individualmente como `[PLANNED]`/`[BLOCKED]`.
- CTAs que abrem uma subsecção da própria vista descrevem-na sem inventar uma rota nova.
- `Tentar novamente` recarrega a vista atual; nunca aponta para uma rota diferente sem justificação.
- `Iniciar sessão` aponta para `/app#/login`.
- `Voltar` usa `history.back()` com fallback `/` ou `/app#/dashboard` consoante o contexto.
- `Contactar` aponta para `mailto:spud@batata.cc` quando o canal dedicado não existir; o alvo de canal dedicado está `[PLANNED]`.

## Informação, monitorização e recomendação

Separar sempre, em qualquer copy pública:

- **Informação**: dados de marca (texto, número, jurisdição, classes, titulares, estado). Factual, datada, com fonte.
- **Monitorização**: vigilâncias, alertas, freshness, alterações detetadas. Sublinha que o Markee observa e regista, não interpreta juridicamente.
- **Recomendação**: sugerir revisão, confirmar na fonte, falar com profissional qualificado. Nunca instruções de "deve fazer X" sobre prazos, oposições, renovações ou caducidades.

Microcopy legal base (usar quando a página tocar em prazos, alertas, oposições, renovações ou BPI):
`Esta informação apoia a monitorização de marcas, mas não substitui consulta da fonte oficial nem aconselhamento profissional.`

Microcopy específica BPI (sempre que BPI aparecer, mesmo como bloqueado):
`Pipeline BPI operacional em NO-GO até validação dos gates BPI-GATE-01..16. Estado atual: o backend pode produzir/expor dados e prazos BPI sem source guard. Estado-alvo obrigatório: UI e backend devem ocultar/bloquear após guard testado. Até lá, a feature não pode ser promovida nem colocada live; copy não substitui controlo técnico.`

Microcopy específica billing (sempre que checkout/subscription aparecer):
`Esta subscrição é registada no Markee. Em modo de desenvolvimento pode não corresponder a cobrança Stripe real.`

Microcopy específica admin (sempre que uma área admin for mencionada):
`O portal admin é monitorização read-only P0. Ações mutáveis exigem idempotência, audit, confirmação e testes.`

## Estados internos vs copy pública

Os marcadores `[IMPLEMENTED]`, `[PARTIAL]`, `[PLANNED]`, `[BLOCKED]`, `[OPEN DECISION]` nunca aparecem ao utilizador final. Servem para:

- distinguir copy segura versus copy ambiciosa;
- identificar áreas que exigem disclaimers;
- alimentar a matriz SITEMAP_CONTENT_MATRIX e o UI_BLOCKS.

Quando a copy de utilizador precisar de expor estado, usar linguagem natural (ver "Marcadores internos canónicos").

## Acessibilidade e legibilidade

- H1 único por página.
- CTAs com labels concretos: "Pesquisar marcas", "Criar vigilância", "Rever prazo".
- Não usar cor como único indicador de estado.
- Ícones com texto ou `aria-label`.
- Erros junto ao campo e resumo no topo quando o formulário falha.
- Loading com texto útil, não só skeleton.
- Empty states com utilidade contextual de recuperação (não segunda ação principal).
- Tabelas com cabeçalhos, ordenação explícita e paginação legível.
- Contraste WCAG AA em todo o texto visível.
- Hierarquia de headings respeitada em páginas legais.

## Microcopy por estado

Loading:

- "A carregar dados da sua conta."
- "A pesquisar marcas disponíveis."
- "A verificar estado das fontes."

Empty:

- "Ainda não há vigilâncias."
- "Não encontrámos resultados para estes filtros."
- "Não há alertas por rever."

Success:

- "Vigilância criada."
- "Alerta marcado como lido."
- "Marca adicionada à vigilância."

Warning:

- "Dados possivelmente desatualizados. Verifique a fonte antes de agir."
- "Este prazo depende de regra ainda não validada."

Error:

- "Não conseguimos carregar estes dados. Tente novamente."
- "A sessão expirou. Inicie sessão novamente."

Permission denied:

- "Não tem permissões para aceder a esta área."

Stale data:

- "Última atualização conhecida: {date}. A fonte pode ter alterações posteriores."

BPI bloqueado:

- "Pipeline BPI operacional em NO-GO/BLOCKED/CRITICAL. Estado atual: o backend pode produzir/expor dados e prazos BPI sem source guard; o estado-alvo exige ocultação/bloqueio após guard testado. Até lá, não promover nem colocar live."

## Tooltips canónicas

Proveniência:
"Indica a origem do dado e o caminho até à fonte usada pelo Markee."

Confiança:
"Estimativa técnica sobre a qualidade/consistência do dado. Não é validação jurídica."

Fonte:
"Sistema ou documento de onde o dado foi obtido."

Atualização dos dados:
"Mostra quando esta fonte foi atualizada pela última vez no Markee."

Prazo:
"Data calculada a partir dos dados disponíveis. Confirme prazos críticos na fonte oficial."

Revisão/quarentena:
"Dados enviados para revisão porque a confiança, o contrato ou a reconciliação não permitem aceitação automática."

Plano/subscrição:
"Mostra o plano registado no Markee. Em desenvolvimento pode não corresponder a cobrança Stripe real."

## Navegação relacionada

- [`README.md`](README.md) — convenções editoriais e taxonomia de estados.
- [`GLOSSARY.md`](GLOSSARY.md) — termos canónicos PT-PT/EN, marcadores internos e papéis.
- [`UI_BLOCKS.md`](UI_BLOCKS.md) — blocos públicos, produto e admin P0; lista canónica de blocos reutilizáveis.
- [`SITEMAP_CONTENT_MATRIX.md`](SITEMAP_CONTENT_MATRIX.md) — matriz rota → blocos, com 32 entradas frontend.
- [`pages/PUBLIC_LANDING.md`](pages/PUBLIC_LANDING.md) — landing e âncoras públicas.
- [`pages/AUTH_ONBOARDING.md`](pages/AUTH_ONBOARDING.md) — `AuthForm`, sessão e copy de autenticação.
- [`pages/DASHBOARD.md`](pages/DASHBOARD.md) — uma ação principal (`Pesquisar marcas`) e respetivos blocos.
- [`pages/SEARCH_MARK_DETAIL.md`](pages/SEARCH_MARK_DETAIL.md) — uma ação principal por vista (search e mark detail).
- [`pages/WATCHLISTS_ALERTS_DEADLINES.md`](pages/WATCHLISTS_ALERTS_DEADLINES.md) — uma ação principal por vista (criar vigilância / marcar lido / rever prazo).
- [`pages/SETTINGS_BILLING.md`](pages/SETTINGS_BILLING.md) — `BillingStatus` e claims de billing.
- [`pages/LEGAL_ERRORS.md`](pages/LEGAL_ERRORS.md) — `LegalContent`, `ErrorState` e microcopy legal.
- [`pages/ADMIN_PORTAL.md`](pages/ADMIN_PORTAL.md) — 10 domínios admin P0 e `BpiGateChecklist` com 16 gates.
- [`../docs/SITEMAP.md`](../docs/SITEMAP.md) — sitemap canónico de rotas (fonte estrutural).
- [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) — estados, requisitos FR/NFR e gates BPI.