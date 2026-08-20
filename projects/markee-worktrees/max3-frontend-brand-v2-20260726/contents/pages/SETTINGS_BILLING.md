# Settings and billing

Rota: `/app#/settings`.
Estado: `[PARTIAL]`.
Requisitos: `FR-ACCOUNT-001`, `FR-BILLING-001..003`, `NFR-SEC-001`, `NFR-LEGAL-001`.
Contratos: [../../docs/REQUIREMENTS.md](../../docs/REQUIREMENTS.md), [../UI_BLOCKS.md](../UI_BLOCKS.md), [../GLOSSARY.md](../GLOSSARY.md), [../SITEMAP_CONTENT_MATRIX.md](../SITEMAP_CONTENT_MATRIX.md).

Princípio:
- Uma ação principal por vista: `Gerir plano` é a ação principal da vista `/app#/settings`. `Terminar sessão` é utilidade global secundária presente no shell, não segunda ação principal desta vista.
- A página nunca apresenta Stripe como cobrança operacional validada.
- `BillingStatus` distingue explicitamente `mock-development`, `real-unverified`, `real-verified`, `error` e `unknown`.
- Pricing público do catálogo é separado do plano atribuído/mock e do billing futuro.
- Comportamentos dependentes de OD permanecem condicionados à aprovação do ID canónico; CTAs sem implementação real ficam planeados ou bloqueados.

## Objetivo e decisão

O utilizador deve ver dados básicos da conta, plano atual e opções disponíveis. Decisão principal da vista: gerir plano. Terminar sessão é utilidade de shell disponível em toda a aplicação.

## H1 e intro

H1:
`Definições`

Subtítulo:
`Conta, plano e sessão.`

Intro:
`Veja os dados associados à sua conta e o estado da subscrição registado no Markee. Esta página distingue plano atribuído, catálogo público e billing futuro.`

CTA principal da vista:
`Gerir plano` -> abre a secção `Plano/subscrição` em `/app#/settings`.

Utilidade global secundária (shell, não segunda ação principal desta vista):
`Terminar sessão` -> client-side: remove JWT de `localStorage` e redireciona para `/app#/login`. Backend `POST /api/v1/auth/logout` `[PLANNED]`.

## Conta

Bloco:
- `PageHeader` com H1 e utilidade `Terminar sessão` disponível no shell.

Campos:
- `Nome`
- `Email`
- `Empresa`
- `Estado da conta`
- `Perfil`

Copy:
`Estes dados identificam a sua conta no Markee. Edição de conta e palavra-passe estão fora do fluxo atual.` `[PARTIAL]`

Confirmação de logout:
`Sessão terminada neste navegador.`

Estados:
- Loading: `A carregar dados da sua conta.`
- Empty: `Não encontrámos dados de conta para este utilizador.`
- Success: `Dados da conta atualizados.`
- Warning: `Edição de conta e palavra-passe estão fora do fluxo atual.`
- Error: `Não conseguimos carregar os dados da conta.` CTA `Tentar novamente` -> recarrega a vista.
- Permission denied: `Inicie sessão para ver definições.` CTA `Iniciar sessão` -> `/app#/login`.
- Stale data: `Os dados da conta podem ter mudado desde a última sincronização.`

## Plano/subscrição

Bloco:
- `PlanSubscriptionMonitor` em modo user (compact).
- Proposta condicionada à `OD-13`: se aprovada, `BillingStatus` fica visível e separado do catálogo.

Título:
`Plano atual`

Campos:
- `Plano`
- `Estado da subscrição`
- `Limite de marcas`
- `Limite de utilizadores`
- `Limite de clientes`
- `Modo de billing`
- `Data da última sincronização` `[PLANNED — depende de OD-14]`

`BillingStatus` estados e copy:

| Estado | Copy visível |
|---|---|
| `mock-development` | `Modo de billing: desenvolvimento. Esta subscrição é registada no Markee e pode não corresponder a cobrança Stripe real.` |
| `real-unverified` | `Modo de billing: Stripe real. A última sincronização com Stripe ainda não foi verificada em produção.` |
| `real-verified` | `Modo de billing: Stripe real verificado. Última sincronização: {date}.` (só após evidência) |
| `error` | `Modo de billing: erro ao sincronizar com Stripe. Verifique configuração.` |
| `unknown` | `Modo de billing: desconhecido. A integração pode não estar configurada.` |

Microcopy obrigatória:
`A integração de billing existe parcialmente. Se o ambiente estiver em modo mock/dev, esta subscrição não confirma cobrança Stripe real.`

CTAs:
- `Ver planos` -> `/#precos` `[PARTIAL]`
- `Continuar para checkout` `[PLANNED — depende de OD-15]` -> possível alvo `POST /api/v1/billing/checkout`. Se aprovado, permanece desativado até validação controlada; modo efetivo `UNKNOWN`, sem Stripe real/webhooks/checkout validados ou live.
- `Sair do modo desenvolvimento` `[PLANNED]` — alvo para ambiente admin, sem implementação atual.

Warning checkout mock:
`Checkout em modo de desenvolvimento. Não use este ecrã como prova de cobrança real.`

Erro Stripe/config:
`Não conseguimos preparar o checkout neste momento.`

## Catálogo público de planos

Bloco:
- `Pricing` em formato compacto.

Tabela (estritamente factual; cada capacidade futura está marcada individualmente):

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
- Stripe: os campos `STRIPE_PRICE_*` existem em `app/core/config.py:44-47`, e os caminhos mock/real existem no código. O modo efetivo é `UNKNOWN`; Stripe real, checkout e webhooks não foram validados e não estão live. O catálogo não constitui promessa de cobrança.

Copy segura:
`Os limites apresentados vêm do catálogo configurado. Funcionalidades dependentes de módulos bloqueados não ficam automaticamente disponíveis por escolher um plano superior.`

CTA por plano:
`Criar conta` -> `/app#/login` quando o utilizador não tiver sessão; `Continuar para checkout` fica `[PLANNED — depende de OD-15]` e, se aprovado, permanece desativado até validação controlada.

## Separação entre pricing público, plano atribuído e billing futuro

- `Pricing público` (`/#precos`): catálogo público, sem claims de cobrança, sempre identificável como `catálogo Markee`.
- `Plano atribuído` (`/app#/settings`): registo do plano na conta do utilizador, vindo de `app.subscriptions`.
- `Billing futuro` (`/app#/settings` -> `Continuar para checkout`): `[PLANNED — depende de OD-15]`. O caminho `POST /api/v1/billing/checkout` existe, mas o modo efetivo é `UNKNOWN`; Stripe real, webhook e checkout não foram validados nem estão live.
- `BillingStatus` em settings e admin é um estado técnico documentado, não uma OD.

## Estados

Loading:
`A carregar definições.`

Empty:
`Não encontrámos dados de subscrição para esta conta.`

Success:
`Definições atualizadas.`

Warning:
`Billing real com Stripe não está validado neste ambiente.`

Error:
`Não conseguimos carregar as definições.` CTA `Tentar novamente` -> recarrega a vista.

Permission denied:
`Inicie sessão para ver definições.` CTA `Iniciar sessão` -> `/app#/login`.

Stale data:
`O estado da subscrição pode ter mudado desde a última sincronização.`

## Mobile

- Conta e plano em cartões separados.
- Utilidade `Terminar sessão` disponível no shell, no fim do menu, não como segunda ação principal da vista.
- Warning de billing acima de `Continuar para checkout`, se o fluxo da `OD-15` for aprovado; o botão permanece `[PLANNED — depende de OD-15]` e desativado até validação controlada.

## Admin cross-link

Se `is_superuser`:
- `Ver monitorização de planos` -> `/app#/admin/subscriptions` `[PLANNED]`

## Referências a decisões abertas

Decisões consolidadas na secção canónica em [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) (secção `Questões e propostas abertas — secção canónica`):

- `OD-13` — Apresentação visual de plano atribuído vs catálogo.
- `OD-14` — Data da última sincronização quando `BillingStatus=unknown`.
- `OD-15` — Upgrade via checkout vs contacto.

Estado técnico fora das OD: `BillingStatus` está especificado para settings e admin.

## Claims proibidos nesta área

Não afirmar:
- Stripe em produção validado.
- Cobrança confirmada sem `BillingStatus=real-verified`.
- Receção imediata de email de confirmação.
- Fatura automática por plano superior.
- `Continuar para checkout` como ação ativa antes de `BillingStatus=real-verified`.

Escrever:
- `Esta subscrição é registada no Markee.`
- `Em modo de desenvolvimento pode não corresponder a cobrança Stripe real.`
- `O modo de billing atual é: {BillingStatus}.`
