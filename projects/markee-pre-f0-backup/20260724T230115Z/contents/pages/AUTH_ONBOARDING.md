# Auth and onboarding

Rotas: `/app`, `/app#/login`.
Estados: `/app` `[IMPLEMENTED]`, `/app#/login` `[IMPLEMENTED]`.
Requisitos: `FR-AUTH-001..003`, `NFR-SEC-001`, `NFR-GDPR-001`.
Contratos: [../../docs/REQUIREMENTS.md](../../docs/REQUIREMENTS.md), [../UI_BLOCKS.md](../UI_BLOCKS.md), [../GLOSSARY.md](../GLOSSARY.md).

## Objetivo e decisão

O utilizador deve criar conta ou iniciar sessão. Decisão principal: login vs registo.

## `/app` shell gate

Título loading:
`A verificar sessão.`

Texto:
`Estamos a confirmar se já tem sessão ativa.`

Estados:
- Loading: `A verificar sessão.`
- Success: encaminhar para `/app#/dashboard`.
- Error: `Não conseguimos confirmar a sessão.` CTA `Iniciar sessão` -> `/app#/login`.
- Permission denied: `A sessão expirou ou não é válida.` CTA `Iniciar sessão novamente` -> `/app#/login`.

## `/app#/login`

H1:
`Entrar no Markee`

Subtítulo:
`Pesquise marcas, crie vigilâncias e acompanhe alertas a partir da sua conta.`

Tabs/alternância:
- `Iniciar sessão`
- `Criar conta`

### Formulário login

Labels:
- `Email`
- `Palavra-passe`

CTA primário:
`Iniciar sessão` -> `POST /api/v1/auth/login` -> encaminhar para `/app#/dashboard`.

CTA secundário:
`Criar nova conta` -> muda para o separador `Criar conta` em `/app#/login`.

Ajuda contextual:
`Use o email associado à sua conta Markee.`

Erros:
- Email vazio: `Introduza o email.`
- Palavra-passe vazia: `Introduza a palavra-passe.`
- Credenciais inválidas: `Email ou palavra-passe inválidos.`
- Utilizador inativo: `Esta conta está inativa.`
- Sessão expirada: `A sessão expirou. Inicie sessão novamente.`

Confirmação:
`Sessão iniciada.`

Destino pós-login:
`/app#/dashboard`

### Formulário registo

Labels:
- `Nome completo`
- `Empresa` `[opcional]`
- `Email`
- `Palavra-passe`

CTA primário:
`Criar conta` -> `POST /api/v1/auth/register`, que devolve `UserOut` sem JWT e não autentica por si. Após o registo, o frontend tenta automaticamente `POST /api/v1/auth/login`; se obtiver JWT, grava-o e navega para `/app#/dashboard`. Se esse login automático falhar, a conta pode já existir e o utilizador pode iniciar sessão manualmente; não há verificação de email atual.

CTA secundário:
`Já tenho conta` -> muda para o separador `Iniciar sessão` em `/app#/login`.

Ajuda contextual:
`A conta permite guardar vigilâncias, alertas e prazos associados ao seu utilizador.`

Erros:
- Email duplicado: `Já existe uma conta com este email.`
- Palavra-passe fraca: `Escolha uma palavra-passe mais segura.`
- Campos obrigatórios: `Preencha os campos obrigatórios.`
- Falha de rede: `Não conseguimos comunicar com o servidor. Tente novamente.`

Confirmação após login automático bem-sucedido:
`Conta criada com sucesso.`

Falha no login automático após registo:
`A conta pode já ter sido criada. Tente iniciar sessão.`

## Onboarding mínimo pós-registo `[PLANNED]`

Objetivo:
Criar primeira vigilância ou pesquisar primeira marca.

H1:
`Configure o essencial.`

Intro:
`Comece por pesquisar uma marca ou criar uma vigilância. Pode ajustar tudo depois.`

CTA primário:
`Pesquisar marca` -> `/app#/search`

CTA secundário:
`Criar vigilância` -> `/app#/watchlists`

## Verify-email pós-registo `[PLANNED]`

Estado atual: não existe verificação de email no produto. O campo `email_verified` não faz parte do modelo `User` atual, nem há endpoint de confirmação, nem serviço de envio configurado. Tudo o que se refere a verificação de email deve ser tratado como alvo, nunca como comportamento ativo.

Comportamento alvo (quando implementado):
- Após `POST /api/v1/auth/register`, mostrar nota `Verifique o email para ativar todas as funcionalidades.` `[PLANNED]`
- Bloqueio vs aviso não-bloqueante até verificação: `OD-05`
- Email de boas-vindas e confirmação dependem de envio real configurado; nunca prometer entrega.

Microcopy neutra no MVP:
`O Markee ainda não envia email de confirmação. Pode iniciar sessão com as credenciais que escolheu.`

## Mobile

- Mostrar uma tab de cada vez.
- Colocar erro diretamente abaixo do campo.
- CTA em largura total.
- Texto legal compacto abaixo do formulário.

## Microcopy segurança

- `Nunca mostramos a sua palavra-passe.`
- `Terminar sessão remove o token deste navegador.`
- `Não partilhe credenciais por email ou chat.`
- `O token JWT é guardado em localStorage neste navegador. Limpar dados do navegador termina a sessão.`

## Estados

Loading: `A autenticar.` / `A criar conta.`
Empty: não aplicável.
Success: `Sessão iniciada.` / `Conta criada.`
Warning: `Está a usar um ambiente de desenvolvimento.` quando aplicável.
Error: `Não foi possível concluir o pedido.`
Permission denied: `Não tem acesso a esta conta.`
Stale data: não aplicável.
