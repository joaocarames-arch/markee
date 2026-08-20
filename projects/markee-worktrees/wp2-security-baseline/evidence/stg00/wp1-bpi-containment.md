# STG00-WP1 — BPI Containment — Evidence Report

- Worktree: `/home/batata/projects/markee-worktrees/stg00-bpi-containment`
- Branch: `stg00-bpi-containment` (base `51aa7d0e057479275df7955f1fa7c8cbdd711d4c`)
- Venv: `/home/batata/projects/markee/.venv` (existing; nothing installed)
- Date (UTC): 2026-07-24
- Status: **NOT DEPLOYED. BPI NO-GO remains in force.** This branch changes
  code and tests only, inside the dedicated worktree. No deploy, restart,
  image rebuild, live schedule edit, Cloudflare change, live-DB write,
  migration, secret read, push or PR was performed. The running public-dev
  stack still executes the old image with the old schedule until a gated
  deployment (Gate João) happens.

## 1. What was implemented

One central typed policy (`app/core/source_policy.py::SourcePolicy`,
built from `app/core/config.py` settings) is consulted by every stage:
beat schedule, `parse_bpi` task, `ingest_bpi_events`, deadline
recalculation, alert generation and alert dispatch. Defaults are
fail-closed: `BPI_ENABLED=False`, `BPI_SCHEDULE_ENABLED=False`,
`BPI_INGESTION_ALLOWED=False`, `BPI_DENY_SOURCES=["inpi_bpi", "BPI"]`
(the registry name and the label the parser stamps on lifecycle events).
While `BPI_ENABLED` is off, the BPI labels stay denied even if the deny
list is emptied.

## 2. RED→GREEN table (all runs executed in this session, in the worktree)

| # | Behavior | Test file (tests/stg00/) | RED evidence | GREEN evidence | Commit |
|---|---|---|---|---|---|
| 1 | Settings default-off; deny includes `inpi_bpi` | `test_bpi_kill_switch_default_off.py` (6 tests) | `6 failed in 0.20s` (fields/module absent) | `6 passed` | `d7e3c38` |
| 2 | Beat schedule excludes `parse-bpi-daily` when disabled; non-BPI entries remain | `test_bpi_beat_schedule_disabled.py` (6 tests) | collection `ImportError: build_beat_schedule` | `6 passed` | `3a845b9` |
| 3 | Ingestion early-exits disabled: zero lifecycle events, zero review-queue rows | `test_bpi_source_deny_ingestion.py::test_bpi_event_not_ingested_when_disabled` | `3 failed in 2.16s` (events were ingested; `skipped_disabled` absent) | `3 passed` | `886f184` |
| 4 | `parse_bpi` task early-exits before download/DB | same file, `test_parse_bpi_task_early_exits_when_disabled` | AssertionError raised from spy: "BPI download attempted while BPI is disabled" | `3 passed` | `886f184` |
| 5 | Deadline recalculation creates zero BPI deadlines (denied trademark source and denied publication events) | `test_bpi_source_deny_deadlines.py` (3 tests) | `3 failed in 3.74s` (`recalculate_deadlines` absent; deadlines would be created) | `3 passed` | `e69754f` |
| 6 | Alert creation denies BPI-rooted trademarks; non-BPI unaffected | `test_bpi_source_deny_alerts.py` (3 tests) | `2 failed, 1 passed` (alerts were created for BPI trademarks; non-BPI already green) | `3 passed` | `d8d2265` |
| 7 | Dispatch blocks pending BPI-rooted alerts; adapters never invoked; non-BPI still dispatched | `test_bpi_dispatch_deny.py` (3 tests) | `3 failed in 2.45s` (dispatch delivered / adapters would be hit) | `3 passed` | `5475ec7` |
| 8 | Hourly deadline task stays usable for authorized sources; explicit enablement only representable locally, never runtime | `test_non_bpi_sources_still_create_deadlines`, `TestEnablementIsLocalOnly` (schedule), `test_bpi_ingestion_works_when_explicitly_enabled` | covered inside the RED runs of rows 2/3/5 above | green in the same files | `3a845b9`/`886f184`/`e69754f` |

Notes on RED honesty: rows 2 and 8 (schedule/enablement) failed as a
collection-time ImportError, which is the red state for an API that did
not exist; `test_non_bpi_alerts_still_created` (row 6) was green at
first run — it is a non-regression guard, not a new behavior.

## 3. Final verification runs

| Command | Result |
|---|---|
| `pytest tests/stg00 -v` | **24 passed** in 11.11s, 0 failed, 0 skipped |
| `pytest -q` (full repo suite) | **168 passed, 2 skipped, 1 warning** in 36.66s |
| `python -m compileall app tests/stg00` | OK |
| `git diff --check 51aa7d0e..HEAD` | clean (no whitespace errors) |
| Secret scan of delta (grep for password/secret/token/key/PEM/sk_live/AKIA patterns) | no matches beyond preexisting settings field names; no values |
| `git status --short` | clean working tree |

The 2 skips and 1 warning are the preexisting baseline (144 passed /
2 skipped / 1 warning before WP1; 144 + 24 new = 168). No new skips.

Tests ran against the dedicated `markee_test` database on the compose
PostgreSQL server (existing test infrastructure; schemas created and
dropped per test). The live `markee` database was not touched.

## 4. Commits (Conventional, atomic, oldest first)

| Commit | Scope |
|---|---|
| `d7e3c38` | feat(config): default-off kill switch + central `SourcePolicy` |
| `3a845b9` | feat(tasks): `build_beat_schedule()` gates `parse-bpi-daily` by policy |
| `886f184` | feat(ingestion): `ingest_bpi_events` early-exit + `parse_bpi` task skip |
| `e69754f` | feat(deadlines): `recalculate_deadlines` denies BPI trademarks/events |
| `d8d2265` | feat(alerts): creation deny for denied-source trademarks |
| `5475ec7` | feat(dispatch): `dispatch_pending` blocks BPI-rooted alerts pre-adapter |

Files touched: `app/core/config.py`, `app/core/source_policy.py` (new),
`app/tasks/__init__.py`, `app/tasks/parse_bpi.py`,
`app/tasks/calculate_deadlines.py`, `app/tasks/check_expiry.py`,
`app/tasks/match_similar.py`, `app/tasks/send_alerts.py`,
`app/services/ingestion.py`, `app/services/alerts.py`,
`tests/stg00/*` (new), `tests/unit/test_ingestion.py` (fixture only).

## 5. Design decisions and factual limitations

- **"BPI-rooted" operational definition:** (a) lifecycle events whose
  `source` label is denied (`BPI`/`inpi_bpi`, case-insensitive); (b)
  trademarks whose `core.sources` ingest source name is denied. A mixed
  trademark (EUIPO record with a historical BPI event) keeps its non-BPI
  behavior; its BPI events cannot create deadlines (event filter) and no
  new BPI events can be ingested (kill switch).
- **No migration / no new columns.** The invariant is implementable with
  existing schema (`Trademark.ingest_source_id` → `core.sources.name`,
  `LifecycleEvent.source`). `Source.is_enabled` exists but was not
  repurposed — runtime rows are data, not policy, and the kill switch
  must not depend on DB state.
- **Return shapes:** `BPIIngestSummary` gained `skipped_disabled`
  (additive); `parse_bpi` disabled-skip reuses the existing
  `{"status": "skipped", "reason": ...}` shape; dispatch summary gained
  `blocked`. The audit's suggested `queued_for_review=N` on disabled
  ingestion was NOT adopted: queueing writes rows, and disabled mode
  must write zero rows.
- **Preexisting test adaptation (assertion-preserving):**
  `tests/unit/test_ingestion.py::TestBPIEventIngestion` gained an
  autouse fixture that monkeypatches explicit enablement, because those
  4 tests exercise ingestion mechanics that are now default-off. No
  assertion was changed or relaxed. This is the "minimal shared fixture
  change" allowed by the WP1 brief.
- **Celery task refactors:** `recalculate_deadlines(db)` and
  `dispatch_pending(db)` were extracted from their task bodies so tests
  drive them on the fixture session; the task entrypoints and registered
  names are unchanged.
- **Blocked alerts are dismissed** (`is_dismissed=True`, `sent_at` never
  set, zero `alert_deliveries` rows) so they leave the pending queue
  without external effect. No historical data is deleted.
- **Lint/type limitation:** `[tool.ruff]` config exists in
  `pyproject.toml` but ruff (and mypy) are not installed in the existing
  venv; installing was out of scope. Performed instead:
  `compileall` (pass), full pytest suite (pass), `git diff --check`
  (pass).
- **Enablement remains gated:** tests prove local config can represent
  enablement (`build_beat_schedule` with an enabled policy contains
  `parse-bpi-daily`; ingestion works under monkeypatched enablement) and
  that this never mutates the registered default schedule. Any real
  enablement requires João's gate plus deployment — neither happened.
- **Not claimed:** nothing here disables the schedule in the running
  public-dev stack. `celery inspect` against the live beat was not run
  (read-only runtime is out of WP1 scope). Containment becomes effective
  in runtime only after a gated deploy of this branch.

## 6. Verdict

All 8 required behaviors are covered by red-first tests now green;
directed suite 24/24; full suite 168 passed with no new skips; scope,
whitespace and secret scans clean; working tree clean.

**NOT DEPLOYED. BPI NO-GO.**
