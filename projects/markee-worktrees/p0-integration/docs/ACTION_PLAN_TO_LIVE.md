# ACTION PLAN TO LIVE — Markee

## 1. Cabeçalho e mandato

| Campo | Valor |
|---|---|
| Versão | 2.0 |
| Mandato | PROMPT-SPUD-MARKEE-MASTER-v2.md, versão 2.1, 2026-07-24 |
| Autor | Max-2 — planeador/auditor |
| Repositório de trabalho | `/home/batata/projects/markee-worktrees/max2-action-plan-v2` |
| Branch desta missão | `max2-action-plan-v2` |
| HEAD esperado | `51aa7d0e057479275df7955f1fa7c8cbdd711d4c` |
| Âmbito | Planeamento, board de execução e auditoria documental apenas |
| Fora do âmbito | Código de produto, testes de runtime, BD, Docker, deploy, rede, secrets, conteúdo e decisões de gate |

Este documento substitui o plano v1.0. A fonte de verdade é o master v2.1; o review de 2026-07-24 e o corpus de planeamento são evidência histórica/read-only, não autorização para executar operações.

## 2. Regra de evidência

Cada afirmação usa uma destas classes:

- **Confirmado** — observado directamente no código, Git, artefacto, teste ou probe identificável.
- **Provável** — suportado por evidência parcial, sem prova suficiente para fechar o estado.
- **Inferência** — conclusão técnica derivada de factos observados; não é prova de execução.
- **UNKNOWN** — não observado ou não demonstrado.

Estados independentes e não intercambiáveis: `IMPLEMENTED` ≠ `configured` ≠ `validated` ≠ `live`. Um teste local não prova staging ou produção. Um contentor em execução não prova release. `mock` nunca conta como real, fonte oficial, entrega ou monitorização.

Stop conditions globais: suite vermelha em master; secret impresso em log, diff, commit ou evidence; alteração pública fora de WP autorizado; regra `draft` a gerar prazo/alerta; dados mock apresentados como reais; evidência insuficiente apresentada como validação/live; migration destrutiva sem backup/restore comprovado; conflito agente/plano/realidade não escalado ao João.

SPUD despacha e reporta. Max executa WPs atribuídos, com TDD, suite dedicada, suite completa e `python -m compileall app` antes do commit final. Max-2 planeia, mantém estes dois documentos, audita e emite `PASS`, `PASS WITH NOTES` ou `FAIL`. Sol + Claude Code CLI Fable 5 fazem exclusivamente o polish visual da F5, segundo D5. Max-2 não escreve código de produto.

Um `FAIL` volta ao Max para correcção; há no máximo 2 loops Max→Max-2. Depois do segundo FAIL, ou perante conflito/decisão de produto, escala-se ao João. Só o João pode parar nos GATE-J1..J5.

## 3. Decisões fixadas pelo João

- **D1 — Ownership de deadlines: opção A.** Criar `app.monitored_marks (user_id, trademark_id, origin, created_at)`, alimentada pelo matching (`origin=match`) e pelo pin manual (`origin=manual`). O scoping interino via alertas é substituído.
- **D2 — Programa BPI: GO WITH CHANGES.** Trabalho técnico controlado nos BPI-GATE-01..16 está autorizado; activação runtime não está autorizada. Kill switch permanece OFF até GATE-J4.
- **D3 — Rotação de secrets e rebuild de imagens autorizados.** Executar no WP4/F1, sem valores em output.
- **D4 — Billing: free beta até staging validado.** Stripe real sai do critical path; catálogo e claims têm de reflectir esta decisão.
- **D5 — Divisão de frontend.** Max/Max-2 fazem estrutura, APIs, dados, lógica e UI funcional sem polish. UI cinemática, efeitos, micro-interacções e polish final são feitos na F5 por Sol + Claude Code CLI Fable 5 sobre estrutura validada. Esta decisão não é reescrita nem transferida para Max.

Restrição operacional desta noite: Forja está 100% dedicada ao Instituto. Apenas Max e Max-2 podem trabalhar no Markee. Assim, execução visual F5 fica **PARKED/BLOCKED para este overnight run**; não é atribuída a Max e D5 mantém-se intacta.

## 4. Gates humanos — únicos pontos de paragem

| Gate | Decisão exclusiva do João | Condição de entrada |
|---|---|---|
| GATE-J1 | Autorizar execução da migration na BD real | dry-run, inventário de drift, backup/restore e reversibilidade documentados |
| GATE-J2 | Sign-off editorial das claims antes de copy nova publicada | matriz claim→capacidade validada, sem claims falsas |
| GATE-J3 | Validar cada regra de prazo | `draft`→`validated`, base legal citada, aprovador e data; sem alertas antes disso |
| GATE-J4 | Activar BPI em runtime | BPI-GATE-01..16 aceites pelo Max-2; kill switch OFF até aqui |
| GATE-J5 | Go/no-go de produção | UAT em staging separado, evidence pack e rollback/restore provados |

Nenhum gate é decidido por este plano, Max, Max-2 ou SPUD. Os antigos gates de routing/decisões locais são superseded apenas quando contradizem D1–D5 ou GATE-J1..J5; os factos históricos são preservados nos materiais de evidência.

## 5. Estado factual de partida

- **Confirmado:** o baseline master `51aa7d0` foi integrado com WP1/WP2 auditados e com o plano/board/auditoria canónicos; o corpus de planeamento/source foi preservado e será committed como provenance separado.
- **Confirmado:** WP1 tem branch/worktree `stg00-bpi-containment` em `0a5e928`.
- **Confirmado:** a auditoria independente autorizou o merge com veredicto `PASS WITH NOTES`; os resultados independentes são preservados em `evidence/stg00/wp2-security-baseline-audit.md`.
- **Confirmado:** F0 está fechado localmente; F1/WP3 é o próximo trabalho e permanece `not_started`; GATE-J1 continua o próximo gate humano após o relatório WP3.
- **UNKNOWN:** migrations, runtime, BD, Docker, staging, produção e gates. Não são promovidos por inferência. BPI runtime permanece OFF.

## 6. Fases e work packages

### F0 — Baseline imediato

**WP2 — Security baseline.** Concluído e integrado em master através da história auditada WP1/WP2. Auditoria independente: `PASS WITH NOTES`, sem blocker; F0 fechado localmente. Implementado/validado localmente não significa staging/live. BPI runtime permanece OFF.

### F1 — Fundação segura

**WP3 — Migrations.** Inventariar drift real (`alembic current`/`heads` e tabelas legacy), produzir script idempotente/reversível, `pg_dump` schema `public`, prova em BD vazia sem `create_all`; dry-run para GATE-J1, depois execução autorizada.

**WP4 — Secrets e imagens.** Rodar SECRET_KEY, DB_PASSWORD e credenciais SMTP/Telegram/EUIPO existentes; só registar `rotated: yes`. Rebuild de todas as imagens com `.dockerignore`; provar ausência de `.env` na imagem e invalidar tokens activos. Nenhum valor em logs, commits ou reports.

**WP5 — Staging compose.** Criar compose de staging sem bind mounts, `UVICORN_EXTRA=""`, `ENVIRONMENT=staging`, flags dev desligadas, secrets externos, healthchecks/restart em todos os serviços, DB/Redis próprios, fail-fast para secret dev e backup/restore ensaiado.

### F2 — Produto correcto

**WP6 — monitored_marks (D1).** Modelo/migration; matching escreve `monitored_marks`; pin/unpin; `GET /deadlines` scoped pela tabela; isolamento multi-tenant. Remover scoping interino via alertas.

**WP7 — Delivery honesto.** `sent_at` apenas depois de delivery real bem-sucedida em pelo menos um canal; skipped/failed em `alert_deliveries` sem `sent_at`; cobrir sucesso, falha SMTP e credenciais ausentes com fakes sem rede.

**WP8 — Admin P0 + RBAC.** Router `/api/v1/admin/*` read-only para superuser; jobs/freshness, quality, review queue e BPI gates visíveis com acções disabled; UI estrutural; audit log de acessos.

**WP9 — Detalhe de marca + auth hardening.** UI estrutural `/app#/marks/{application_number}`, política de password, rate limits em login e pesquisa pública, token de 24h com refresh ou re-login.

### F3 — Programa BPI, sequência estrita

**WP10 — Contrato/schema.** Implementar `docs/research/BPI_DATA_CONTRACT.md`: PDF raw imutável com SHA-256/metadados HTTP, extracção por página, eventos com proveniência, confidence e quarantine; migrations e fixtures dos 7 PDFs reais amostrados.

**WP11 — Pipeline de cinco estágios.** `discover → archive → extract → parse → normalize/reconcile`; parse por secção, dedupe/matching/quarantine, rate limit ≤5 req/min, um PDF de cada vez, backoff e User-Agent identificável. Kill switch; testes apenas replay de fixtures.

**WP12 — Regras de prazo versionadas.** `rule_id`, versão, estado `draft|validated`, `legal_basis`, `approved_by`, `approved_at`; resolver semanticamente `+2 meses civis` vs `+60 dias` e preparar dossier para GATE-J3. `draft` nunca cria prazo/alerta.

**WP13 — Aceitação BPI.** Max-2 audita BPI-GATE-01..16 item a item; consolida report para GATE-J4. Se J4 for aceite, activação faseada: arquivo/ingestão sem alertas, uma semana de observação, drift/quarantine report, depois apenas regras `validated`.

### F4 — Conteúdo, legal e claims

**WP14 — Editorial.** Max finaliza `contents/**`; cada claim pública mapeia a capacidade validada. Proibir 24/7, ≤24h e leitura integral diária BPI enquanto não provados. Max-2 audita claim-a-claim; GATE-J2; copy aprovada só é implementada na F5.

**WP15 — Legal/RGPD.** Privacidade, termos, retenção, consentimento, minimização de prospecção, base legal, registo de tratamento e export/delete (arts. 15/17) na API. GATE-J3 aplica-se às regras jurídicas de prazo; publicação legal depende de aprovação competente.

### F5 — UI cinemática e polish

**WP-UI1 — Landing e brand.** Sol + Claude Code CLI Fable 5; copy de GATE-J2; brand manual, efeitos, performance LCP <2.5s, bundles locais, AA e reduced motion.

**WP-UI2 — Dashboard/admin.** Sol + Fable 5; loading/empty/error, transições, data-viz e polish sem alterar contratos API. Max-2 audita regressão E2E e claims aprovadas.

Estado nesta noite: ambos `parked/blocked`; Forja está dedicada ao Instituto. Não atribuir visual a Max. D5 permanece.

### F6 — Staging, UAT e ensaio

**WP16 — Deploy staging.** Release imutável, migrations via script, smoke, health/5xx alerting, rollback drill cronometrado, restore provado e guião UAT João: registo→watchlist→match→alerta→deadline→admin. GATE-J5.

### F7 — Produção e hypercare

**WP17 — Go-live.** URL final, DNS/TLS, backup pré-migration, canary/cutover, smoke e sign-off, apenas após GATE-J5.

**WP18 — Hypercare.** Duas semanas de métricas diárias (tasks, quarantine, deliveries, 5xx), incident log e retro com dívida técnica.

## 7. Ordem de execução

F0 → F1 (`WP3→WP4→WP5`) → F2/F3 em paralelo após WP6/WP10 poderem avançar → F4 → F5 → F6 → F7. Nenhuma fase posterior abre com FAIL pendente no mesmo track. Handoff F4→F5: SPUD entrega OpenAPI de dev, brand manual, copy aprovada e rotas/ecrãs estruturais.

## 8. Limitações e handoff de auditoria WP2

Para auditar WP2 após Max terminar, exigir do SPUD/Max: branch e commit exactos; diff limitado ao patch/WP1 e sem código não relacionado; `evidence/stg00/wp2-security-baseline.md`; saída datada de `pytest` da suite completa, `tests/stg00` e `tests/integration/test_security_fixes.py`; `python -m compileall app`; resolução explícita do conflito de `app/tasks/__init__.py`; `git diff --check`; estado limpo. Max-2 deve confirmar que os testes foram executados no commit indicado, que mock não é real, que IMPLEMENTED/validated/live não foram confundidos, e que nenhum secret aparece. Emitir PASS/PASS WITH NOTES/FAIL. Dois FAIL loops no máximo; depois escalar João.

Este plano não afirma merge, validação, staging, live ou qualquer gate. Não contém valores secretos nem executa operações mutáveis.
