# Independent audit — STG00-WP2 security baseline

Date: 2026-07-24 UTC
Auditor: Max-2
Verdict: **PASS WITH NOTES**

## Audited revisions and topology

- Master/base: `51aa7d0e057479275df7955f1fa7c8cbdd711d4c`.
- WP2 security patch: `189345be07cff6fb1e4074fd3546360204ac0ab5`.
- WP1 tip integrated: `0a5e9282b56d0dc940334e56382f9e207890a821`.
- Integration merge: `c17637c8f74eb3f6b7bf584bba29dd053accf736`, parents `189345b` and `0a5e928`.
- WP2 evidence/branch HEAD audited: `42e4b884f9bc521ef613f2d9f8db86849d5eddd2`.
- Audit-plan baseline: `88b5de291dc626f1636df91bcf56d57c93ee2ead`.

Topology and status were independently inspected. `wp2-security-baseline` was clean before and after verification. The audit branch was clean before these audit edits. No push, merge to master, deploy, Docker, network or database administration was performed.

## Scope and implementation findings

Confirmed:

1. Delta from master is limited to the 11-file WP2 security patch, the WP1 containment commits/tests/evidence, the explicit integration merge and WP2 evidence. No unrelated product, migration, frontend, billing, editorial or future-WP file was found.
2. `app/tasks/__init__.py` preserves both required sides: `build_beat_schedule()` adds `parse-bpi-daily` only when `policy.bpi_schedule_active`, and `run_async()` awaits `engine.dispose()` in `_wrapped()` before closing its event loop.
3. The BPI kill switch remains default OFF and the directed WP1 suite validates schedule, ingestion, deadline, alert and dispatch denial.
4. WP2 introduced no new secret default. Existing development defaults remain; non-development validation rejects the development secret sentinel, wildcard CORS, mock fallback and startup `create_all`. Docs/OpenAPI are disabled outside development.
5. Trademark mock fallback is default OFF, forbidden outside development, opt-in only in development and returned records are labelled `MOCK/`.
6. Outbound effects were not exercised. The WP1 outbound-delivery change is containment only: denied-source alerts are blocked before adapters. No general outbound HTTP client redesign was introduced.
7. Health responses carry `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy`, covered by the directed tests.
8. No Alembic/schema change, monitored-marks redesign, billing/frontend work or general `sent_at` redesign was introduced. WP1 necessarily references `sent_at` only to ensure blocked BPI alerts remain unsent.
9. Secret-value scan found names/references and development/test sentinels only; no operational secret value was identified. Relevant names: `DATABASE_URL`, `DB_PASSWORD`, `SECRET_KEY`, `EUIPO_API_CLIENT_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SMTP_PASSWORD`, `TELEGRAM_BOT_TOKEN`.

## Evidence validation

`evidence/stg00/wp2-security-baseline.md` was checked line-by-line against Git, code and independent commands. Its topology, file classification, behaviour descriptions, test totals, compile result, diff-check result, clean status and deferrals are materially accurate.

Notes on wording/evidence:

- The report says the merge had no conflicts, while the merge commit message calls `app/tasks/__init__.py` a “conflict resolution”. Git records the resulting merge but does not preserve enough metadata to independently prove whether an interactive conflict occurred. The resulting code is correct; this is documentary ambiguity, not a product blocker.
- The report states a dependency was installed during worker verification. This audit installed nothing and used the existing environment.
- Literal development/test sentinel examples occur in code and evidence; they are not operational credentials, but future evidence should prefer names or `<redacted-dev-sentinel>` where the exact literal is unnecessary.

## Independent verification at `42e4b88`

Serial canonical runs, existing environment only:

- `python -m pytest tests/ -q`: **178 passed, 2 skipped** in 38.54s.
- `python -m pytest tests/stg00 -q`: **24 passed** in 9.20s.
- `python -m pytest tests/integration/test_security_fixes.py -q`: **9 passed** in 5.05s.
- `python -m compileall -q app`: exit 0.
- `git diff --check` for aggregate `51aa7d0..42e4b88` and separately for WP2 patch, WP1 tip, integration merge and evidence commit: all exit 0.

Audit note: an initial attempt ran the three pytest commands concurrently. Those runs interfered through the shared PostgreSQL test schemas and produced schema/create-drop and transaction errors. Re-running the prescribed commands serially gave the clean results above. This exposes test-environment non-isolation under concurrent invocations, but does not invalidate the canonical serial suite or WP2 behaviour.

## Deferred and operational state

Correctly parked: image rebuild and development-sentinel rotation at WP4/D3; Alembic 001/002/live drift at WP3/GATE-J1; absent `ruff`/`mypy`; monitored-marks at WP6; delivery-honesty redesign at WP7.

State separation: changes are **IMPLEMENTED** and independently validated locally. They are not merged to master, not validated in staging, not deployed and not proven live. BPI runtime activation remains unauthorized and OFF.

## Authorization

**PASS WITH NOTES.** No blocker ID is raised. Merge of WP2 plus its integrated WP1 history into master is authorized, and that merge may close F0. This audit does not perform the merge or closure.

Binary authorization: **YES**.
