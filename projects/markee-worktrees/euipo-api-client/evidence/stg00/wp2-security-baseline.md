# STG00-WP2 — Security Baseline — Evidence Report

- Worktree: `/home/batata/projects/markee-worktrees/wp2-security-baseline`
- Branch: `wp2-security-baseline` (base `51aa7d0e057479275df7955f1fa7c8cbdd711d4c`)
- Reference (read-only): `stg00-bpi-containment` at `0a5e9282b56d0dc940334e56382f9e207890a821`
- Authoritative handoff: `/tmp/markee-spud-handoff-2026-07-24/PROMPT-SPUD-MARKEE-MASTER-v2.md`,
  `REVIEW-MARKEE-2026-07-24.md`, `markee-fixes-2026-07-24.patch`
- Date (UTC): 2026-07-24
- Status: **NOT DEPLOYED. BPI NO-GO remains in force.** This WP only
  applies the security-baseline patch and merges the WP1 BPI
  containment branch inside the worktree. No deploy, restart, image
  rebuild, live schedule edit, Cloudflare change, live-DB write,
  migration, secret read, push or PR was performed. The running
  public-dev stack still executes the old image with the old schedule
  until a gated deployment (Gate João) happens.

## 1. What was implemented

Five classes of fix, all with dedicated regression tests:

1. **Multi-tenant containment on `/deadlines`** — the list endpoint now
   returns only deadlines whose trademark is linked to the
   authenticated user via the user's own `Alert` rows
   (`app/api/deadlines.py`). Interim fix pending the
   `monitored_marks` redesign (delegated to STG-03 in the master
   prompt).
2. **Celery loop lifecycle** — `run_async` now disposes the SQLAlchemy
   async engine inside the same loop it was created in, fixing the
   `Future attached to a different loop` failure observed in 10/10
   `calculate_deadlines` runtime runs (`app/tasks/__init__.py`,
   `app/core/database.py` engine).
3. **Mock fallback honesty** — `/trademarks` search and detail fallback
   to the EUIPO service is now gated by `ENABLE_MOCK_FALLBACK`
   (default `False`), and mock records are prefixed with `MOCK/`
   (`app/api/trademarks.py`, `app/core/config.py`).
4. **Config fail-fast + exposure hardening** — `Settings` adds
   `ENVIRONMENT`, `DB_CREATE_ALL_ON_STARTUP`, `ENABLE_MOCK_FALLBACK`
   and a `_validate` guard that refuses to boot with the dev
   `SECRET_KEY`, wildcard CORS, mock fallback or `create_all` outside
   development. `/docs`, `/redoc` and `/openapi.json` are turned off
   outside development; baseline security headers are attached to
   every response; CORS defaults replace `*`. `.dockerignore` keeps
   `.env`, `.git`, tests, docs and editorial sources out of the image
   (`app/core/config.py`, `app/main.py`, `docker-compose.yml`,
   `.dockerignore`).
5. **Auth and RBAC** — `get_current_user` rejects inactive users
   with 403 (deactivated tokens stop working immediately);
   `/quality/metrics` requires `is_superuser`; `tests/integration/
   test_api.py` was ported from `passlib` to `app.core.security`
   (`passlib` was removed in commit `962116e`).

## 2. Patch provenance

- `git apply --check markee-fixes-2026-07-24.patch` against
  `51aa7d0` → exit 0 (clean three-way context).
- `git apply markee-fixes-2026-07-24.patch` → exit 0.
- Patch source: `/tmp/markee-spud-handoff-2026-07-24/markee-fixes-2026-07-24.patch`
  (758 lines, 28 259 bytes). Per the authoritative review
  (`REVIEW-MARKEE-2026-07-24.md`), the patch is the artefact of the
  Max/-2 review and implements fixes FIX-01..FIX-06 against the
  remaining 5 CRITICAL blockers.

## 3. RED → GREEN table (all runs executed in this session, in the worktree)

| # | Behavior | Test file | RED evidence | GREEN evidence | Commit |
|---|---|---|---|---|---|
| 1 | `/deadlines` returns only the user's deadlines (no global leak) | `tests/integration/test_security_fixes.py::test_deadlines_scoped_to_user` and `::test_deadlines_empty_for_user_without_alerts` | master returned `Deadline` rows unfiltered; query had no `where` clause (audit §CRITICAL #2) | `2 passed` | `189345b` |
| 2 | `get_current_user` rejects inactive users with 403 | `test_get_current_user_rejects_inactive` | master returned the user (no `is_active` check) | `1 passed` | `189345b` |
| 3 | EUIPO mock fallback off by default; on enable, records are labelled `MOCK/` | `test_search_no_mock_fallback_by_default`, `test_search_mock_fallback_labelled_when_enabled`, `TestTrademarkEndpoints::test_list_trademarks_empty_db_no_fallback_by_default`, `::test_list_trademarks_empty_db_with_fallback` | master always hit the mock service when DB row count was 0 and produced records with no `MOCK/` prefix | `4 passed` | `189345b` |
| 4 | `/quality/metrics` requires `is_superuser` | `test_quality_metrics_forbidden_for_regular_user` | master returned the metrics payload to any authenticated user (`Audit CRITICAL #4`) | `1 passed` | `189345b` |
| 5 | `_validate` refuses to boot outside development with dev-grade security | `test_production_refuses_dev_secret`, `test_production_refuses_wildcard_cors_and_mock`, `test_development_accepts_dev_defaults` | pre-patch `Settings` had no `ENVIRONMENT`/`ENABLE_MOCK_FALLBACK`/`DB_CREATE_ALL_ON_STARTUP` and no `_validate`; module-level `settings = get_settings()` was unguarded | `3 passed` | `189345b` |
| 6 | `test_api.py` no longer imports `passlib` | `tests/integration/test_api.py::TestAuthEndpoints::test_login_success` (and 13 others) | baseline: `1 error` (`ImportError: passlib`, missing module) caused by commit `962116e` removing passlib; collection-time `error` for the whole file | `14 passed` (whole file) | `189345b` |

The 9 dedicated security tests cover FIX-01..FIX-05; FIX-06 is the
broken-baseline regression restored by the patch.

## 4. Final verification runs

| Command | Result |
|---|---|
| `pytest tests/integration/test_security_fixes.py -v` | **9 passed** in 5.08s |
| `pytest tests/stg00 -v` | **24 passed** in 9.35s (WP1 baseline, expected) |
| `pytest tests/integration/test_api.py -v` | **14 passed** in 2.31s (FIX-06 restored) |
| `pytest tests/ -q` (full repo suite) | **178 passed, 2 skipped** in 38.42s; no new skips, no warnings escalated |
| `python -m compileall -q app` | OK (exit 0, no syntax errors) |
| `git diff --check 51aa7d0..HEAD` | clean (no whitespace errors) |
| `git status --short` after merge | clean working tree |
| `pytest tests/stg00 -v` (post-merge re-run) | **24 passed** in 9.35s |

Pre-patch baseline (master `@51aa7d0`): suite collection errored on
`tests/integration/test_api.py` because of the passlib import;
after the patch + dep install (`email-validator==2.3.0` was
declared in `requirements.txt` but missing from the venv —
environmental, not patch-induced), 154 passed + 2 skipped. Post-merge
final: 178 passed + 2 skipped (154 + 24 WP1 tests). Net of WP2: 9
dedicated tests + 1 baseline (`test_api.py`) restored + self-contained
fixes to the rest of the suite.

## 5. Merge and conflict resolution

```
*   c17637c merge(stg00-bpi-containment): WP1 BPI containment + kill switch
|\
| * 0a5e928 docs(evidence): STG00-WP1 BPI containment evidence report
| * 5475ec7 feat(dispatch): block BPI-rooted pending alerts before any delivery
| * d8d2265 feat(alerts): suppress alert creation for denied-source trademarks
| * e69754f feat(deadlines): deny BPI-rooted trademarks and publication events
| * 886f184 feat(ingestion): early-exit BPI ingestion and parse task when disabled
| * 3a845b9 feat(tasks): gate parse-bpi-daily out of the beat schedule by policy
| * d7e3c38 feat(config): add default-off BPI kill switch and central source policy
* | 189345b fix(security): apply security baseline review (FIX-01..06)
|/
* 51aa7d0 test: cover watchlist API endpoints (base)
```

- `git merge --no-ff stg00-bpi-containment` reported **no conflicts**.
- The two sides touched `app/tasks/__init__.py` in distinct regions:
  WP1 replaced the static `beat_schedule` dict with a
  `build_beat_schedule(policy)` factory and added the
  `from app.core.source_policy import SourcePolicy, get_source_policy`
  import; WP2 rewrote `run_async` to wrap the coroutine in
  `_wrapped()` that calls `engine.dispose()` before the loop closes.
  The merge cleanly preserves both.
- Inspecting the merged `app/tasks/__init__.py` shows
  `beat_schedule=build_beat_schedule()` (WP1 default-off) and the
  WP2 `run_async` with `_wrapped()` / `engine.dispose()` intact.
- No other conflict surface was touched; the rest of the merge is
  the disjoint, additive changes of WP1 (new `app/core/source_policy.py`,
  edits to `app/tasks/{parse_bpi,calculate_deadlines,check_expiry,
  match_similar,send_alerts}.py`, `app/services/{ingestion,alerts}.py`,
  `tests/unit/test_ingestion.py` fixture, new `tests/stg00/*`,
  `evidence/stg00/wp1-bpi-containment.md`).

## 6. Files (delta vs. base `51aa7d0`)

New:
- `.dockerignore`
- `app/core/source_policy.py` (from WP1)
- `app/services/alerts.py` (from WP1)
- `tests/integration/test_security_fixes.py` (WP2)
- `tests/stg00/__init__.py`, `tests/stg00/factories.py`,
  `tests/stg00/test_bpi_*.py` (6 files from WP1)
- `evidence/stg00/wp1-bpi-containment.md` (from WP1)

Modified by WP2 only:
- `app/api/auth.py` (inactive-user 403 in `get_current_user`)
- `app/api/deadlines.py` (user-scoped query)
- `app/api/quality.py` (superuser guard)
- `app/api/trademarks.py` (mock fallback gate + `nice_class` filter)
- `app/core/config.py` (`ENVIRONMENT`, `DB_CREATE_ALL_ON_STARTUP`,
  `ENABLE_MOCK_FALLBACK`, CORS default, `_validate`)
- `app/main.py` (`create_all` opt-in, `/docs` gated, security headers)
- `app/tasks/__init__.py` (`run_async` lifecycle)
- `docker-compose.yml` (restart, healthcheck, `UVICORN_EXTRA`,
  `ENVIRONMENT`/`DB_CREATE_ALL_ON_STARTUP`/`ENABLE_MOCK_FALLBACK`
  env wiring)
- `tests/integration/test_api.py` (`passlib` → `app.core.security`)

Modified by WP1 only: `app/core/config.py` (BPI settings),
`app/tasks/parse_bpi.py`, `app/tasks/calculate_deadlines.py`,
`app/tasks/check_expiry.py`, `app/tasks/match_similar.py`,
`app/tasks/send_alerts.py`, `app/services/ingestion.py`,
`tests/unit/test_ingestion.py`.

Modified by both (merged): `app/tasks/__init__.py`,
`app/core/config.py`.

## 7. Verification of fail-fast / security behavior (live synthetic run)

Each snippet below runs against the merged tree; results are
reproducible from the worktree.

| # | Check | Observed effect |
|---|---|---|
| 1 | `Settings(ENVIRONMENT='production', SECRET_KEY='dev-secret-change-me', CORS_ORIGINS=['https://markee.pt'])` → `_validate(...)` | `RuntimeError: Unsafe configuration for ENVIRONMENT=production: SECRET_KEY is the development default` |
| 2 | `Settings(ENVIRONMENT='staging', SECRET_KEY='x'*64, CORS_ORIGINS=['*'], ENABLE_MOCK_FALLBACK=True, DB_CREATE_ALL_ON_STARTUP=True)` → `_validate(...)` | `RuntimeError: Unsafe configuration for ENVIRONMENT=staging: CORS_ORIGINS contains '*'; ENABLE_MOCK_FALLBACK must be False; DB_CREATE_ALL_ON_STARTUP must be False` |
| 3 | `Settings(ENVIRONMENT='development')` → `_validate(...)` | objects identical (`is`), no exception |
| 4 | `get_source_policy().bpi_schedule_active` (default settings) | `False` — BPI schedule not in the registered beat |
| 5 | `GET /health` (via FastAPI `TestClient`) | `200`; headers: `x-content-type-options: nosniff`, `x-frame-options: DENY`, `referrer-policy: strict-origin-when-cross-origin` |

## 8. Design decisions and factual limitations

- **No migrations.** No Alembic revision was added; the patch is
  schema-neutral. The drift between `alembic current 001` and `head
  002` + legacy tables in the live `public` schema remains for
  GATE-J1 (WP3).
- **No `sent_at` redesign.** The patch does not touch `Alert.sent_at`
  or `app/services/alerts.py::send_alerts`; that delivery-honesty
  work is delegated to WP7 in the master prompt.
- **No live deployment / no runtime enablement.** The kill switch is
  the same WP1 default-off policy; BPI ingestion, alerts, deadlines
  and dispatch all remain denied in this branch's runtime
  (`SourcePolicy.is_source_allowed('INPI', 'BPI') is False` with
  default settings). `parse-bpi-daily` is absent from the registered
  beat schedule. Real enablement still requires GATE-J4 (João).
- **Image rebuild claim deferred.** The `.dockerignore` change is
  present in source, but the images already built against the old
  context remain compromised — the authorized rebuild is part of
  the secrets rotation (WP4, D3) and is **not** in this WP.
- **Secret rotation deferred.** No secret was read, no value is
  referenced in this report. The `SECRET_KEY` in the worktree
  defaults to the dev sentinel; the validation guard simply makes
  the dev sentinel unacceptable outside development.
- **No `app/core/source_policy.py` overlap.** That module is
  introduced by WP1 and is referenced by the merged tasks module
  but was not touched by the WP2 patch.
- **Pre-existing venv gap.** `email-validator==2.3.0` is declared
  in `requirements.txt` but was missing from the active venv
  (`/home/batata/.hermes/hermes-agent/venv`); installed to permit
  test collection. Lint/type tooling (`ruff`, `mypy`) is not
  installed — out of scope, mirroring the WP1 limitation.
- **BPI NO-GO preserved.** The patch does not touch `SourcePolicy`,
  `BPI_ENABLED`, `BPI_SCHEDULE_ENABLED`, `BPI_DENY_SOURCES` or any
  ingestion/parse/deadline/dispatch gating. The WP1 evidence
  (`evidence/stg00/wp1-bpi-containment.md`) remains accurate.

## 9. Verdict

All 6 required behaviors (FIX-01..FIX-06) are covered by
red-then-green tests now green; directed suite 9/9 + 24/24 stg00
+ 14/14 test_api.py restored; full suite 178 passed, 2 skipped, no
new skips; merge had no conflicts; targeted `app/tasks/__init__.py`
preserves both WP1 conditional `beat_schedule`/kill-switch
containment and WP2 `run_async` lifecycle with `engine.dispose()`;
working tree clean.

**NOT DEPLOYED. BPI NO-GO.**
