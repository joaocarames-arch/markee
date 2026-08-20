# EXECUTION BOARD — Markee v2.0

Data de auditoria: 2026-07-24 (UTC)
Plano: `docs/ACTION_PLAN_TO_LIVE.md`
Mandato: `PROMPT-SPUD-MARKEE-MASTER-v2.md` v2.1
Worktree: `/home/batata/projects/markee-worktrees/max2-action-plan-v2`
Branch: `max2-action-plan-v2`
Baseline: master `51aa7d0e057479275df7955f1fa7c8cbdd711d4c` (`51aa7d0`)
Corpus de origem: `/home/batata/projects/markee` — read-only; untracked planning corpus preservado.

## Convenções

Evidência: `Confirmado`, `Provável`, `Inferência`, `UNKNOWN`. Estados `IMPLEMENTED`, `validated` e `live` são independentes; mock nunca é real. `not_started` não implica trabalho executado. `Max` executa; `Max-2` planeia/audita; `SPUD` orquestra. A camada visual F5 pertence a Sol + Claude Code CLI Fable 5 por D5, não a Max.

Owner/gate não constituem aprovação. Só João pode parar nos GATE-J1..J5. Um FAIL pode regressar ao Max no máximo duas vezes; depois escala ao João.

## Gate register — cada gate humano exactamente uma vez

| Gate | Ponto de paragem do João | Estado factual |
|---|---|---|
| GATE-J1 | Autorizar migration na BD real após dry-run/backup/restore | UNKNOWN / OPEN |
| GATE-J2 | Aprovar claims editoriais antes de publicar copy nova | UNKNOWN / OPEN |
| GATE-J3 | Validar cada regra de prazo com base legal | UNKNOWN / OPEN |
| GATE-J4 | Activar BPI em runtime após BPI-GATE-01..16 aceites | UNKNOWN / OPEN; kill switch OFF |
| GATE-J5 | Go/no-go de produção após UAT em staging | UNKNOWN / OPEN |

## Execution board

| WP | Fase | Owner | Pré-requisitos | Branch/worktree | Evidence path | Estado actual | Veredicto de auditoria | Gate | Próxima acção bounded |
|---|---|---|---|---|---|---|---|---|---|
| WP2 | F0 Baseline | Max; SPUD | master 51aa7d0; WP1 containment | audited history integrated in master: merge `ebd15a1`, WP2 head `42e4b884f9bc521ef613f2d9f8db86849d5eddd2` | `evidence/stg00/wp2-security-baseline.md`; independent audit: `evidence/stg00/wp2-security-baseline-audit.md` | `IMPLEMENTED`; validated locally; integrated in master; not staging or live; F0 closed locally | `PASS WITH NOTES` — scope/topology/behaviours verified; canonical suite 178 passed, 2 skipped; directed suites 24/24 and 9/9 | — | F0 closed; start F1/WP3 only; no runtime BPI activation |
| WP3 | F1 Fundação | Max; Max-2 audita | WP2 PASS; inventário de drift; backup; dry-run | branch por WP; a criar | `evidence/f1/wp3-migrations.md` | `not_started` | `UNKNOWN` | GATE-J1 | produzir dry-run, prova BD vazia e plano reversível; parar para João |
| WP4 | F1 Fundação | Max; SPUD | WP2 PASS; autorização D3; inventário sem valores | branch por WP; a criar | `evidence/f1/wp4-secrets-images.md` | `not_started` | `UNKNOWN` | — | rotacionar sem valores em output, rebuild e provar ausência de `.env` |
| WP5 | F1 Fundação | Max; Max-2 audita | WP2 PASS; WP4; segredos externos | branch por WP; a criar | `evidence/f1/wp5-staging-compose.md` | `not_started` | `UNKNOWN` | — | preparar compose staging e fail-fast; documentar backup/restore |
| WP6 | F2 Produto | Max; Max-2 audita | WP3; WP2; D1 | branch por WP; a criar | `evidence/f2/wp6-monitored-marks.md` | `not_started` | `UNKNOWN` | — | implementar ownership D1 e testes multi-tenant; não usar alertas como scope |
| WP7 | F2 Produto | Max; Max-2 audita | WP6; canais em fake | branch por WP; a criar | `evidence/f2/wp7-honest-delivery.md` | `not_started` | `UNKNOWN` | — | cobrir success/failed/skipped; sem rede real e sem claim delivery |
| WP8 | F2 Produto | Max; Max-2 audita | WP3; WP6; RBAC base | branch por WP; a criar | `evidence/f2/wp8-admin-rbac.md` | `not_started` | `UNKNOWN` | — | entregar admin read-only, BPI state visible/disabled e audit log |
| WP9 | F2 Produto | Max; Max-2 audita | WP6; auth hardening | branch por WP; a criar | `evidence/f2/wp9-mark-detail-auth.md` | `not_started` | `UNKNOWN` | — | entregar detalhe estrutural, rate limits e sessão de 24h/refresh |
| WP10 | F3 BPI | Max; Max-2 audita | WP3; D2; contrato BPI | branch por WP; a criar | `evidence/f3/wp10-bpi-contract-schema.md` | `not_started` | `UNKNOWN` | — | schema raw/provenance/quarantine e fixtures reais; não activar runtime |
| WP11 | F3 BPI | Max; Max-2 audita | WP10; kill switch OFF; fixtures | branch por WP; a criar | `evidence/f3/wp11-bpi-pipeline.md` | `not_started` | `UNKNOWN` | — | construir cinco estágios em replay; verificar rate limit e quarantine |
| WP12 | F3 BPI | Max; Max-2 audita; jurídico para regra | WP10; taxonomia; dossier legal | branch por WP; a criar | `evidence/f3/wp12-deadline-rules.md` | `not_started` | `UNKNOWN` | GATE-J3 | propor semântica única e manter `draft` incapaz de criar prazos/alertas |
| WP13 | F3 BPI | Max; Max-2 | WP10–WP12; BPI-GATE-01..16 | branch por WP; a criar | `evidence/f3/wp13-bpi-gates.md` | `not_started` | `UNKNOWN` | GATE-J4 | auditar gates item a item; report consolidado; não activar antes de J4 |
| WP14 | F4 Editorial | Max; Max-2 audita; SPUD | D4; capacidades evidenciadas | branch por WP; `contents/**` do Max | `evidence/f4/wp14-editorial.md` | `not_started` | `UNKNOWN` neste worktree | GATE-J2 | claim→capability matrix; remover claims não provadas; preparar sign-off |
| WP15 | F4 Legal/RGPD | Max; SPUD; validação jurídica externa | WP6–WP14 conforme dados; data map | branch por WP; a criar | `evidence/f4/wp15-legal-rgpd.md` | `not_started` | `UNKNOWN` | — | preparar páginas/policies, retenção, consentimento e export/delete; sem declarar aprovação |
| WP-UI1 | F5 UI | Sol + Claude Code CLI Fable 5; Max-2 audita | WP8/WP9 estrutural; WP14 + GATE-J2 | branch visual dedicado; a criar | `evidence/f5/wp-ui1-landing-brand.md` | `parked/blocked overnight` | `UNKNOWN` | — | não iniciar esta noite; SPUD só agenda após disponibilidade de Sol/Fable e handoff aprovado |
| WP-UI2 | F5 UI | Sol + Claude Code CLI Fable 5; Max-2 audita | WP8/WP9; APIs estáveis; WP-UI1 | branch visual dedicado; a criar | `evidence/f5/wp-ui2-dashboard-admin.md` | `parked/blocked overnight` | `UNKNOWN` | — | não iniciar esta noite; polish sem alteração de API; auditoria E2E depois |
| WP16 | F6 Staging/UAT | Max; SPUD; João UAT | WP2–WP15; UI final; compose staging | release branch/tag futura; UNKNOWN | `evidence/f6/wp16-staging-uat.md` | `not_started` | `UNKNOWN` | GATE-J5 | deploy staging só com evidence pack; smoke, rollback/restore drill e guião UAT |
| WP17 | F7 Produção | Max; SPUD; João | WP16 PASS; GATE-J5 | release imutável; UNKNOWN | `evidence/f7/wp17-go-live.md` | `not_started` | `UNKNOWN` | — | preparar canary/cutover/runbook; não executar sem J5 |
| WP18 | F7 Hypercare | Max; SPUD; Max-2 audita | WP17 live comprovado | release operacional; UNKNOWN | `evidence/f7/wp18-hypercare.md` | `not_started` | `UNKNOWN` | — | recolher métricas duas semanas, incident log e retro; só depois propor saída |

## Estado de branches e evidência

| Item | Estado |
|---|---|
| master | F0 integrated; current HEAD is the controlled integration tip; planning/source provenance committed separately |
| WP1 | `stg00-bpi-containment`, `0a5e928` confirmado pelo handoff/review |
| WP2 | audited at `42e4b884f9bc521ef613f2d9f8db86849d5eddd2`; WP1 integrated by merge `c17637c8f74eb3f6b7bf584bba29dd053accf736`; merged to master by `ebd15a1`; independently audited `PASS WITH NOTES`; not staging or live |
| F0/F1 | F0 closed locally after controlled merge; F1/WP3 next and not started; GATE-J1 remains the next human gate after the WP3 report |
| Esta board/plano | canonical planning/status documents; no product code |
| Staging/produção | UNKNOWN; URL pública histórica não prova staging nem live |

## Stop conditions e reporting

Parar e escalar ao SPUD/João se houver suite vermelha, secret exposto, alteração não autorizada, mock como real, `draft` a gerar alertas, migration sem backup, ou divergência de ownership/mandato. No fecho de cada fase o SPUD reporta WPs, veredictos, blockers, próximo gate e decisões exclusivamente de João. Nenhuma despesa externa superior a $1 sem aviso prévio.

Handoff WP2: Max deve entregar commit exacto, diff, evidence report, suites `pytest`, `tests/stg00`, `tests/integration/test_security_fixes.py`, `python -m compileall app`, resolução do conflito em `app/tasks/__init__.py`, `git diff --check`, branch limpa e ausência de secrets. Max-2 audita execução no commit indicado; não aceita inferência de “passou noutro lugar”, mock como real ou qualquer claim de validated/live sem prova específica.
