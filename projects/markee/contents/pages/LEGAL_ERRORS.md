# Legal and errors

Rotas:
- `/privacy` `[PLANNED]`.
- `/terms` `[PLANNED]`.
- `/legal` `[PLANNED]`.
- `/404` `[PLANNED]` (decisão dedicada vs SPA: `OD-04`).
- `/500` `[PLANNED]` (decisão dedicada vs SPA: `OD-04`).

Requisitos: `NFR-LEGAL-001`, `NFR-GDPR-001`, `NFR-SEC-001`, `GATE-JURIDICO`.
Contratos: [../../docs/REQUIREMENTS.md](../../docs/REQUIREMENTS.md), [../UI_BLOCKS.md](../UI_BLOCKS.md), [../GLOSSARY.md](../GLOSSARY.md), [../CONTENT_PRINCIPLES.md](../CONTENT_PRINCIPLES.md).

## GATE-JURIDICO

As três estruturas propostas (`/privacy`, `/terms`, `/legal`) dependem de `OD-07` e partem do pressuposto `GATE-JURIDICO`: a copy só é publicada depois de revisão por profissional qualificado e aprovação explícita do João. Até essa aprovação, as páginas existem apenas como estrutura editorial e nunca devem ser promovidas como conteúdo jurídico final.

Regras:
- Páginas legais nunca usam claims absolutos (`garantido`, `sempre`, `tempo real`).
- Microcopy de monitorização aparece sempre que a página tocar em prazos, alertas, oposições, renovações ou BPI.
- Toda referência a titulares, dados de contacto ou dados judiciais inclui minimização RGPD.
- Qualquer dúvida de interpretação deve indicar `Consulte a fonte oficial ou profissional qualificado.`
- CTA `Contactar` aponta para canal ainda `[PLANNED]`; enquanto não existir canal dedicado, `Contactar` não deve ser prometido como resposta atempada.

Microcopy legal base:
`Esta informação apoia a monitorização de marcas, mas não substitui consulta da fonte oficial nem aconselhamento profissional.`

Microcopy específica BPI (quando aplicável):
`BPI permanece NO-GO/BLOCKED/CRITICAL. Estado atual inseguro: o backend pode produzir/expor dados e prazos BPI sem source guard. O estado-alvo obrigatório exige ocultação/bloqueio na UI e no backend após guard testado. Até lá, a feature não pode ser promovida nem colocada live; copy não substitui controlo técnico.`

Microcopy billing (quando aplicável):
`Esta subscrição é registada no Markee. Em modo de desenvolvimento pode não corresponder a cobrança Stripe real.`

## Meta legal comum

Meta title base:
`Markee - {Página}`

Meta description base:
`Informação legal do Markee sobre utilização, privacidade e limites da plataforma.`

Canonical base:
`https://markee.batata.cc/{path}`

## Legal pages

### `/privacy` `[PLANNED]`

H1:
`Privacidade`

Subtítulo:
`Como o Markee deve tratar dados de conta, marcas, vigilâncias e operações.`

Intro:
`Esta página explica que dados são recolhidos, finalidade, retenção, subprocessadores, direitos RGPD e contactos. A copy é aprovada por profissional qualificado antes de publicação pública.`

Blocos:
- Dados de conta (email, hash de palavra-passe, sessão JWT em localStorage).
- Dados de marcas e vigilâncias (pesquisa, watchlists, alertas, prazos).
- Dados operacionais/admin com redaction (sem password, hash, token, secrets, headers sensíveis ou PII desnecessária).
- Prospeção e minimização RGPD `[PLANNED/BLOCKED]`.
- BPI/contactos gerais: `não extrair nem expor por defeito no MVP`.
- Retenção e eliminação `[PLANNED]` — política e execução ainda não aprovadas.
- Direitos RGPD (acesso, retificação, apagamento, portabilidade, oposição).
- Subprocessadores.
- Contacto.

CTA primário:
`Contactar` -> `mailto:spud@batata.cc` `[PLANNED — depende de OD-16 e GATE-JURIDICO]`.

CTA secundário:
`Voltar` -> `history.back()` (fallback `/`) `[PLANNED/GATE-JURIDICO]`

### `/terms` `[PLANNED]`

H1:
`Termos de utilização`

Subtítulo:
`Condições para usar o Markee.`

Intro:
`Os termos cobrem conta, uso aceitável, limites de responsabilidade, planos, billing, disponibilidade, propriedade intelectual e alterações. A copy é aprovada por profissional qualificado antes de publicação pública.`

Disclaimers obrigatórios:
- `O Markee apoia monitorização e organização de informação; não substitui aconselhamento jurídico.`
- `Prazos e alertas devem ser confirmados em casos críticos.`
- `Funcionalidades em modo parcial, mock/dev ou bloqueadas não constituem compromisso operacional.`
- `A integração de billing pode operar em modo mock/dev; não usar como prova de cobrança real.`

Blocos:
- Conta e uso aceitável.
- Planos e billing (com distinção mock/dev vs Stripe real).
- Prazos, alertas, oposições, renovações e BPI: limites e bloqueios.
- Disponibilidade e observabilidade.
- Propriedade intelectual.
- Limitação de responsabilidade.
- Alterações aos termos.
- Lei aplicável e foro.

CTA primário:
`Criar conta` -> `/app#/login` `[PLANNED/GATE-JURIDICO]`; o utilizador seleciona `Criar conta` nessa vista.

CTA secundário:
`Voltar ao início` -> `/`

### `/legal` `[PLANNED]`

H1:
`Informação legal`

Subtítulo:
`Limites da informação apresentada pelo Markee.`

Intro:
`A informação no Markee deve ser lida como apoio à monitorização, com fonte e estado visíveis sempre que aplicável. Esta página agrega referências a disclaimers específicos.`

Blocos:
- Fontes e freshness (EUIPO/TMview, INPI/BPI, mock/dev).
- Prazos e validação profissional.
- BPI NO-GO e gates BPI-GATE-01..16.
- Billing parcial/mock e `BillingStatus`.
- Contacto e canal de comunicação.

CTA primário:
`Ver privacidade` -> `/privacy`

CTA secundário:
`Ver termos` -> `/terms`

## Cookies e consentimento `[PLANNED — depende de OD-17 e GATE-JURIDICO]`

CTA de rodapé canónico:
- Label: `Cookies`.
- Ação: reabrir preferências de consentimento `[PLANNED]`.
- Estado técnico atual: a ação ainda não existe; não atribuir URL autónoma.

Contexto:
`O Markee guarda o token JWT em localStorage neste navegador para manter a sessão do utilizador autenticado. Cookies analíticos, de marketing ou de terceiros exigem consentimento explícito quando forem adicionados.`

Microcopy (a aplicar quando o banner existir):
`Usamos o armazenamento local deste navegador para manter a sua sessão. Cookies adicionais só são ativados com o seu consentimento.`

Estados:
- Sem consentimento dado: banner `Aceitar todos` / `Apenas necessários` / `Configurar`.
- Consentimento dado: banner recolhido; persistência do estado.
- Erro de consentimento: `Não conseguimos registar a sua escolha. Tente novamente.`

CTA primário (consentimento):
Estado interno: `[PLANNED — depende de OD-17]`. Copy visível: `Aceitar todos` — se aprovado e implementado, grava consentimento para todas as categorias configuradas.

CTA secundário (consentimento):
Estado interno: `[PLANNED — depende de OD-17]`. Copy visível: `Apenas necessários` — se aprovado e implementado, grava apenas preferências essenciais; o JWT permanece no armazenamento local funcional usado pelo login.

CTA terciário (consentimento):
Estado interno: `[PLANNED — depende de OD-17]`. Copy visível: `Configurar` — se aprovado e implementado, abre painel granular por categoria.

Nota editorial:
Numa vista de consentimento legal, `Aceitar`/`Recusar` constituem um par regulatório (opt-in/opt-out equivalente) e não violam a regra editorial de uma ação principal por vista; ambos precisam de destino e estado próprios e de wire-up real quando o banner existir.

## Retenção `[PLANNED]`

Contexto:
`A política de retenção e a sua execução técnica estão ainda por aprovar. O Markee não deve, nesta fase, prometer prazos concretos de retenção nem comportamento de eliminação além do que está implementado e testado.`

Microcopy segura (substitui qualquer afirmação de execução):
`Os pedidos de eliminação estão a ser desenhados. Quando aprovados, serão processados pela equipa conforme política publicada.`

Blocos (quando a política existir):
- Retenção por tipo de dado.
- Procedimento de eliminação.
- Exceções por obrigação legal.

CTA primário:
`Pedir eliminação` `[PLANNED]` — alvo: rota dedicada `/app#/settings/delete` ou canal de contacto, após política aprovada (ver `OD-18`).

CTA secundário:
`Voltar ao início` -> `/`

## Error pages and states

Estados HTTP cobertos pelo UI/servidor, conforme SITEMAP e UX:

| Estado | Comportamento | Copy visível |
|---|---|---|
| 401 Unauthorized | redirecionar para `/app#/login` com retorno seguro | `A sessão expirou. Inicie sessão novamente.` |
| 403 Forbidden | página de erro dedicada ou inline | `Não tem permissões para aceder a esta área.` |
| 404 Not Found | página dedicada `/404` ou estado SPA | `Página não encontrada. Esta rota não existe ou ainda não está disponível.` |
| 409 Conflict | estado inline em formulário | `Esta ação entrou em conflito com o estado atual. Atualize e tente novamente.` |
| 422 Unprocessable Entity | erros por campo em formulário | `Verifique os campos assinalados e tente novamente.` |
| 429 Too Many Requests | estado inline ou banner | `Muitas tentativas. Aguarde antes de voltar a tentar.` |
| 500 Internal Server Error | página dedicada `/500` ou estado SPA | `Não conseguimos carregar esta área.` |
| 503 Service Unavailable | estado de manutenção | `Serviço em manutenção. Voltaremos assim que possível.` |

Microcopy de manutenção:
`Serviço em manutenção. Algumas áreas podem estar temporariamente indisponíveis.`

Microcopy stale (jurídico):
`Este conteúdo pode estar desatualizado. Confirme a versão mais recente antes de tomar decisões com base nele.`

### `/404` `[PLANNED]` (decisão dedicada vs SPA: `OD-04`)

H1:
`Página não encontrada`

Subtítulo:
`Esta rota não existe ou ainda não está disponível.`

CTA primário:
`Voltar ao início` -> `/`

CTA secundário:
`Voltar ao painel` -> `/app#/dashboard`

Ajuda:
`Se chegou aqui por uma hiperligação interna, a rota pode estar planeada mas ainda não implementada.`

Estados:
- Loading: `A preparar o conteúdo.`
- Empty: `Sem conteúdo relacionado com este caminho.`
- Error: `Não conseguimos gerar a página de erro.` CTA `Tentar novamente` -> recarrega a rota atual.
- Stale data: `Esta página de erro pode ter sido atualizada.`

### `/500` `[PLANNED]` (decisão dedicada vs SPA: `OD-04`)

H1:
`Não conseguimos carregar esta área`

Subtítulo:
`Ocorreu uma falha técnica.`

CTA primário:
`Tentar novamente` -> recarrega a rota atual.

CTA secundário:
`Voltar ao painel` -> `/app#/dashboard`

Ajuda:
`Se a falha persistir, registe a hora e a ação que tentou executar.`

Estados:
- Loading: `A tentar de novo.`
- Error: `A falha persistiu. Tente mais tarde.`
- Stale data: `Esta página de erro pode ter sido atualizada.`

### 503 manutenção

H1:
`Serviço em manutenção`

Subtítulo:
`Estamos a trabalhar para restabelecer o serviço.`

CTA primário:
`Tentar novamente` -> recarrega a rota atual.

CTA secundário:
`Voltar ao painel` -> `/app#/dashboard`

Ajuda:
`Algumas áreas podem estar temporariamente indisponíveis. Pedimos desculpa pelo incómodo.`

### 401/403 inline

- 401: estado inline + redirecionamento suave para `/app#/login`.
- 403: estado inline em `ErrorState` com `Permission denied`.

### 409/422/429 inline

- 409: `ConfirmDialog` ou `ErrorState` com copy contextual.
- 422: erros por campo, resumo no topo do formulário.
- 429: banner `Muitas tentativas. Aguarde antes de voltar a tentar.` com ETA quando existir.

## Estados comuns

Loading:
`A carregar conteúdo.`

Empty:
`Ainda não há conteúdo publicado para esta página.`

Success:
`Conteúdo carregado.`

Warning:
`Este conteúdo precisa de revisão legal antes de produção pública.` (referência `GATE-JURIDICO`).

Error:
`Não conseguimos carregar esta página.`

Permission denied:
`Não tem permissões para aceder a esta área.`

Stale data:
`Este conteúdo pode estar desatualizado. Confirme a versão antes de publicar.`

## Acessibilidade e recuperação

- Cada página legal tem um único H1.
- Hierarquia de headings respeitada.
- Contraste mínimo AA.
- Texto `role=alert` em mensagens de erro urgentes.
- Erros por campo com `aria-describedby` e mensagem junto ao input.
- Resumo de erros no topo do formulário quando houver mais do que um campo em falha.
- Acessibilidade de `ErrorState`: `role=alert` quando crítico; texto alternativo a cor.

## Referências a decisões abertas

Decisões consolidadas na secção canónica em [`../SITEMAP_CONTENT_MATRIX.md`](../SITEMAP_CONTENT_MATRIX.md) (secção `Questões e propostas abertas — secção canónica`):

- `OD-04` — Páginas de erro dedicadas vs estados SPA.
- `OD-07` — Legal combinada vs três páginas.
- `OD-16` — Canal `Contactar` em `/privacy`/`/terms`/`/legal`.
- `OD-17` — Presença de banner de consentimento.
- `OD-18` — Rota/contacto para pedido de eliminação.

## Claims proibidos nesta área

Não afirmar:
- Cookies técnicos de sessão como já implementados.
- Conformidade jurídica total sem aprovação documentada.
- Garantia de privacidade absoluta.
- Retenção zero em todos os dados.
- Resposta atempada a pedidos RGPD sem SLA definido.
- Política e execução de retenção como comportamento ativo.
- Subprocessadores sem lista aprovada.
