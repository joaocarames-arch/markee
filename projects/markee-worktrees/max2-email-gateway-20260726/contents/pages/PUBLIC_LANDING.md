# Public landing

Rotas: `/`, `/#funcionalidades`, `/#motor`, `/#precos`.
Estado: `[PARTIAL]`.
Requisitos: `FR-LAND-001`, `FR-BILLING-001`, `NFR-LEGAL-001`, `NFR-GDPR-001`.
Contratos: [../../docs/REQUIREMENTS.md](../../docs/REQUIREMENTS.md), [../UI_BLOCKS.md](../UI_BLOCKS.md), [../GLOSSARY.md](../GLOSSARY.md), [../SITEMAP_CONTENT_MATRIX.md](../SITEMAP_CONTENT_MATRIX.md), [../CONTENT_PRINCIPLES.md](../CONTENT_PRINCIPLES.md).

## Objetivo e decisão

O visitante deve perceber se o Markee merece uma conta para pesquisar e configurar vigilâncias. Decisão principal: entrar no produto ou abandonar.

## Meta pública

Meta title:
`Markee - monitorização de marcas em Portugal e na Europa`

Meta description:
`Pesquise marcas, organize vigilâncias e acompanhe alertas e prazos com fonte e estado visíveis. Para profissionais de PI, equipas legais e PME.`

OG title: `Markee`.
OG description: `Monitorização de marcas com fonte, proveniência e freshness visíveis.`
Canonical: `https://markee.batata.cc/`

## Hero

H1:
`Marcas sob vigilância, sem promessas no escuro.`

Subtítulo:
`O Markee ajuda a pesquisar marcas, criar vigilâncias e rever alertas e prazos com fonte, confiança e atualização dos dados à vista.`

Intro curta:
`Feito para profissionais de propriedade industrial, equipas legais e empresas que precisam de acompanhar marcas sem perder o rasto aos dados.`

CTA primário:
`Começar gratuitamente` -> `/app#/login` `[IMPLEMENTED]`

CTA secundário:
`Explorar funcionalidades` -> `/#funcionalidades` `[PARTIAL]`

Nota discreta sob CTAs:
`Algumas fontes e automações estão em validação. O estado dos dados é mostrado no produto.`

Substituições obrigatórias da landing atual (`frontend/landing/index.html`):

- "Boletim BPI lido na íntegra todos os dias · LEITURA DIÁRIA · DADOS ESTRUTURADOS" -> `Pipeline BPI operacional em NO-GO até validação dos gates BPI-GATE-01..16. Discovery, arquivo raw, extração por página e deadlines BPI continuam bloqueados.`
- "24/7 vigilância contínua" -> `Vigilância baseada em fontes configuradas. Estado e freshness visíveis por dado.`
- "≤24h da publicação ao alerta" -> `Prazos e alertas dependem da fonte e do módulo. O Markee não promete monitorização contínua nem tempos de resposta.`
- "Email cuidado ou mensagem instantânea no Telegram" -> `Alertas disponíveis no produto. O envio externo por email ou Telegram não está validado como entrega real.`
- "registos oficiais INPI · EUIPO" manter, sem implicar cobertura completa.
- "45 classes de Nice cobertas" -> `Pesquisa por classe de Nice disponível. Filtro depende do dado presente na fonte.`

Copy mobile:
- H1 mais curto: `Vigilância de marcas com fonte visível.`
- Subtítulo em 2 linhas no máximo.
- CTA primário primeiro; CTA secundário abaixo.

## Navegação pública

Links:
- `Funcionalidades` -> `/#funcionalidades`
- `Motor` -> `/#motor`
- `Preços` -> `/#precos`
- `Entrar` -> `/app#/login`

## Trust/Proof

Título:
`Feito para trabalho de PI, não para decorar dashboards.`

Bullets:
- `Pesquisa por texto, jurisdição e classe de Nice.` `[PARTIAL]`
- `Vigilâncias por conta com ownership testado.` `[IMPLEMENTED]`
- `Prazos e alertas com estado visível.` `[PARTIAL]`
- `Proveniência e qualidade como requisitos de produto.` `[PARTIAL]`

Claim seguro sobre fontes:
`O Markee trabalha com dados de marcas disponíveis nas fontes configuradas. Cada vista deve indicar fonte e atualização conhecida.`

## Funcionalidades

Título:
`O essencial para acompanhar marcas.`

Blocos:
1. Pesquisa de marcas `[PARTIAL]`
   - Texto: `Pesquise por nome, jurisdição e classe. O detalhe dedicado com timeline e proveniência é alvo P0.`
   - CTA: `Pesquisar no produto` -> `/app#/search`
2. Vigilâncias `[IMPLEMENTED]`
   - Texto: `Crie listas de marcas/termos e acompanhe itens por conta.`
   - CTA: `Criar vigilância` -> `/app#/watchlists`
3. Alertas `[PARTIAL]`
   - Texto: `Reveja alertas disponíveis no produto, marque como lidos ou dispense. Envio externo por canal não deve ser assumido como validado.`
   - CTA: `Ver alertas` -> `/app#/alerts`
4. Prazos `[PARTIAL]`
   - Texto: `Organize datas de revisão. Prazos críticos devem ser confirmados na fonte oficial ou por profissional qualificado.`
   - CTA: `Ver prazos` -> `/app#/deadlines`
5. BPI `[BLOCKED]`
   - Texto: `O pipeline BPI automatizado está em NO-GO até fechar os gates técnicos e jurídicos BPI-GATE-01..16.`
   - CTA: `Ver estado BPI` -> `/app#/admin/bpi` `[BLOCKED/admin]`

Capacidades não operacionais (a não vender como ativas):
- Envio de alertas por email `[PLANNED]` — serviço de notificação por email não está configurado nem validado como entrega real.
- Envio de alertas por Telegram `[PLANNED]` — bot e canal de envio não estão integrados como operação corrente.
- Analytics de produto `[PLANNED]` — métricas de uso agregadas não estão expostas no produto.
- White-label `[PLANNED]` — personalização de marca não está disponível no produto.
- Cobertura WIPO `[BLOCKED]` — fora do escopo operacional atual; apenas EUIPO/TMview e INPI/BPI (BPI NO-GO) são alvos.
- API pública completa `[BLOCKED]` — a API atual serve o produto; acesso Enterprise/API externo é P2, não P0.

## Motor

Título:
`Dados úteis precisam de rasto.`

Texto:
`O Markee combina pesquisa, normalização e indicadores de qualidade. Quando um dado depende de fonte, run ou regra parcial, a interface deve mostrar essa condição.`

Microcopy:
- Proveniência: `Fonte e rasto do dado.`
- Confiança: `Indicador técnico, não validação jurídica.`
- Freshness: `Última atualização conhecida pelo Markee.`

Copy específica BPI:
`O parser BPI atual é referência de investigação. Estado atual inseguro: o backend pode produzir/expor dados e prazos BPI sem source guard. O estado-alvo obrigatório exige ocultação/bloqueio na UI e no backend após guard testado. BPI permanece NO-GO/BLOCKED/CRITICAL e não pode ser promovido nem colocado live; copy não substitui controlo técnico.`

## Fontes de dados

Título:
`Fontes com estado, não fé.`

Copy:
`EUIPO/TMview e INPI/BPI têm granularidades diferentes. O Markee deve preservar essas diferenças em vez de fingir equivalência.`

BPI visible copy permitida:
`BPI automatizado: bloqueado até validação de arquivo raw, extração por página, normalização, reconciliação, quarantine e regra jurídica de prazos.`

EUIPO copy:
`EUIPO/TMview via OAuth2; em ausência de credenciais válidas cai para modo mock e a copy nunca promete leitura em tempo real.`

## Preços

Título:
`Planos simples para começar.`

Catálogo (referência canónica de preços: `PLAN_META` em `frontend/dashboard/app.js:37`; limites por plano: `PLAN_LIMITS` em `app/services/billing.py:18`; campos `STRIPE_PRICE_*` existentes em `app/core/config.py:44-47`; o modo efetivo é `UNKNOWN` e checkout/webhooks Stripe reais não foram validados).

| Plano | Preço | Limite marcas | Limite clientes | Notas |
|---|---|---|---|---|
| Free | €0/mês | 1 marca | - | EUIPO+INPI, alertas de renovação `[PLANNED]`, email `[PLANNED]` |
| Individual | €5/mês | 5 marcas | - | alertas de similaridade, oposição, email `[PLANNED]` |
| Pro | €29/mês | 100 marcas | - | fonética PT, Telegram `[PLANNED]`, analytics básico `[PLANNED]` |
| Profissional | €99/mês | 500 marcas | multi-cliente `[PLANNED]` | prospeção `[PLANNED]`, multi-cliente `[PLANNED]`, white-label `[PLANNED]` |
| Enterprise | €249/mês | ilimitado | - | API completa `[BLOCKED]`, SSO `[BLOCKED]`, WIPO `[BLOCKED]` |

Notas por capacidade:
- `email` / `Telegram` em todos os planos: envio externo `[PLANNED]`, sem validação de entrega real.
- `analytics`: `[PLANNED]`, ainda não exposto como capacidade.
- `prospeção`, `multi-cliente`, `white-label`: `[PLANNED]`, UI dedicada e configuração por definir.
- `API completa`, `SSO`, `WIPO` no plano Enterprise: `[BLOCKED]`, fora do escopo operacional atual.
- Stripe: os caminhos mock e real de checkout/webhook existem no código; modo efetivo `UNKNOWN`. Stripe real, webhooks e checkout não foram validados e não estão live. O catálogo não constitui promessa de cobrança.

Nota obrigatória:
`A integração de billing existe parcialmente. O checkout pode operar em modo mock/dev; esta subscrição é registada no Markee e pode não corresponder a cobrança Stripe real.`

CTA por plano:
`Criar conta` -> `/app#/login`

Microcopy de plano:
`Limites e funcionalidades podem depender do estado técnico e legal de cada módulo. Escolher um plano superior não desbloqueia automaticamente módulos bloqueados.`

## FAQ

P: `O Markee substitui aconselhamento jurídico?`
R: `Não. O Markee apoia pesquisa e monitorização, mas decisões críticas devem ser confirmadas com fonte oficial ou profissional qualificado.`

P: `O BPI já está automatizado?`
R: `Não como pipeline operacional P0. O BPI está em NO-GO, bloqueado e classificado como risco CRITICAL até fechar os gates BPI-GATE-01..16.`

P: `Os alertas são enviados por email ou Telegram?`
R: `Não como entrega real validada. Notificações externas estão planeadas; o produto mostra os alertas internamente mas não promete envio por canal externo.`

P: `Os planos cobram via Stripe?`
R: `Ainda não como cobrança validada. Existem caminhos mock/parciais de checkout, e o `BillingStatus` deve distinguir explicitamente esse cenário.`

P: `O que é "freshness"?`
R: `É a data da última vez que o Markee obteve ou confirmou um dado. Não é garantia de cobertura completa.`

P: `Posso fazer prospeção?`
R: `A prospeção para profissionais de PI está planeada com filtros RGPD. UI dedicada e export ainda não existem.`

P: `Existe API pública?`
R: `Não em P0. A API atual é para uso interno do produto. Acesso Enterprise/API externo é P2 e está bloqueado no estado atual.`

## Footer legal

CTAs de rodapé `[PLANNED/GATE-JURIDICO]`:
- `Privacidade` -> `/privacy`.
- `Termos` -> `/terms`.
- `Cookies` -> reabrir preferências de consentimento `[PLANNED]`; a ação técnica ainda não existe e não há URL autónoma.

## Informação, monitorização, recomendação

Secção de rodapé da landing (quando implementação suportar):

- **Informação**: dados de marca com fonte e freshness.
- **Monitorização**: vigilâncias, alertas, freshness.
- **Recomendação**: confirmar prazos críticos na fonte oficial ou com profissional qualificado.

Microcopy legal base:
`Esta informação apoia a monitorização de marcas, mas não substitui consulta da fonte oficial nem aconselhamento profissional.`

## Estados

Loading: `A preparar a página.`
Empty: não aplicável.
Success: `Conta criada. Pode configurar a sua primeira vigilância.`
Warning: `Algumas automações dependem de validação técnica/legal.`
Error: `Não conseguimos carregar esta secção.`
Permission denied: não aplicável em rota pública.
Stale data: `Informação comercial ou técnica pode ter mudado desde a última atualização.`

## Mobile

- H1 curto no topo.
- CTAs em largura total.
- Ancoragem de secção colapsa em separador sticky.
- Disclaimer legal visível mas discreto.
