# Slice email gateway — status: PASS

Data: 2026-07-26 (UTC). Branch `max2/email-gateway-20260726`, base `c9d20f7`.

## Âmbito entregue

Verificação de email de conta: registo cria conta não verificada e despacha
email de verificação via gateway tipado (`memory` em dev/teste, `smtp` em
produção); login bloqueia contas não verificadas; `POST /verify` consome o
token; `POST /resend-verification` reemite com rate limit.

- `app/services/email.py` — gateway (envelope tipado, backends async,
  allowlist de remetentes, rejeição de header injection, STARTTLS, timeout,
  fail-closed fora de development/test).
- `app/services/email_templates.py` — templates PT-PT (texto + HTML) e
  minting de URL apenas contra allowlist de bases.
- `app/services/email_verification.py` — tokens aleatórios (32 bytes,
  base64url), persistidos apenas como SHA-256, TTL, single-use, revogação de
  tokens pendentes na reemissão, rate limit por utilizador/hora.
- `app/services/email_verification_dispatch.py` — emissão + envio + registo
  de auditoria (`email_deliveries`).
- `app/api/auth.py` — `/register` (resposta constante, enumeration-safe),
  `/verify` (idempotente, erro genérico único), `/resend-verification`
  (enumeration-safe, 429 quando excede o limite), `/login` (403 para não
  verificados).
- `alembic/versions/003_email_verification.py` — colunas em `app.users` +
  tabelas `app.email_verification_tokens` / `app.email_deliveries`,
  reversível.

## Gates (executados nesta worktree, código final)

1. Testes targeted da feature: `56 passed`.
2. `python -m pytest tests/unit tests/integration`: `190 passed, 2 skipped`.
3. Suite completa `python -m pytest -q`: `330 passed, 2 skipped`.
4. `ruff check --select E4,E7,E9,F` nos paths alterados: limpo. (O ruff 0.16
   disponível no ambiente aplica por omissão um rule-set mais lato que o
   config do repo e assinala também código pré-existente não tocado; a
   baseline canónica do repo é o default clássico.)
5. `python -m compileall` nos paths alterados: OK.
6. Alembic offline (sem BD): chain `001 → 002 → 003 (head)`; `upgrade
   002:003 --sql`, `downgrade 003:002 --sql` e `upgrade base:head --sql`
   geram o DDL esperado, com `UNIQUE (token_hash)` e sem coluna de plaintext.
7. Invariantes de segurança: hash-only at rest, nenhum token em logs ou
   respostas, TTL/single-use/revogação/rate-limit testados, register/resend
   enumeration-safe, verify idempotente, SMTP com TLS/timeout/allowlist/
   rejeição de header injection/fail-closed. Secret scan do diff: limpo
   (apenas passwords de fixture em testes).
8. `git diff --check` e `git diff --cached --check`: limpos.
