# Full audit progress

## Phase 0 — baseline

- Audit ID: `allie21-full-audit-2026-11-14`
- Repository: `ErpeUser/Allie21_Chess_Live_Studio`
- Baseline/current main commit: `15464e24278f540e081d07c067e20d4cc0d076e8`
- Root tree: `c4ecfe3a93f71dfc96d96f117300d0bc74d3f026`
- Deterministic inventory: 144 blobs, 19 trees, `truncated=false`.
- Required instruction files were read; historical `AGENT_PROGRESS.md` remains preserved context, not proof of current coverage.
- Audit branch: `audit/full-repository-2026-11-14`.
- Latest audit source-fix commit: `8f4335a8f10177aa80c2abf76c55fe9999de1b13`.

## Completed review blocks

- Configuration, shell hooks, workflow YAML, root launch/update scripts, `config.json`, and `pyproject.toml` were read in full. No confirmed defect was found in this static pass; actions are SHA-pinned and Windows release remains workflow-dispatch only.
- Documentation/version finding AUDIT-0002 is fixed; current claims are 11.2.24/11.2.24.0 and old evidence is labeled historical.
- Backend audit found exactly one confirmed defect, AUDIT-0003. The overlay-settings access gate was added and the regression was observed RED before the fix and GREEN after it. The changed Python files compile.
- Viewer audit found AUDIT-0004: idle private status failed open. The viewer now preserves backend availability and capture-exclusion flags. The focused/full viewer reliability file is GREEN at 15/15.
- Baseline CI/Security failures remain infrastructure blockers because all jobs fail before steps and logs are unavailable.

## Current blockers

- CI/Security runs 43571741050/43571740981, 43625326792/43625326785, and latest PR runs 43628346970/43628346976 failed before any job step; all job `steps` are null and connector log downloads return `BlobNotFound`.
- Branch-protection read returned 403; branch object reports `protected=false` and no required status checks.
- Windows onedir/EXE, Edge/Playwright, DPI/HWND, OBS/getDisplayMedia, and real capture acceptance are NOT_EXECUTED.

## Resume point

Re-read the fixed `viewer/index.html` interval 180–259 and the static-review interval 260–572, then resume stable file order at line 573. The browser manifest/options/background/connection/update/worker-status files, userscript sections after line 260, relevant browser/viewer/overlay/pairing/extension/release tests, and all 11 `tools/` scripts had no additional confirmed defect. Full repository coverage is not complete; remaining viewer lines and any unrecorded test intervals still require checkpointed review.

## Finding status

- AUDIT-0002 — FIXED (documentation/version reconciliation).
- AUDIT-0003 — FIXED (overlay-settings authorization gate; HTTP regression 4/4 and compile checks).
- AUDIT-0004 — FIXED (idle private overlay status; viewer reliability 15/15).
- AUDIT-0001 — BLOCKED (CI/Security infrastructure/log availability).


## Additional completed review blocks

- All 43 test files were read fully at the baseline; no additional confirmed defect was found. The current-blob regression additions in `tests/test_http_offline.py` and `tests/test_viewer_reliability.js` remain covered by focused tests.
- All top-level backend Python files, all vendored Allie Python files, opening TSVs, engine/openings README files, and the vendor SHA-256 manifest were read and validated. The eight vendored file hashes match the manifest; no new defect was found.
- Browser files and all 11 tool scripts were read fully. Path, version, manifest, atomic-update, and release checks are internally consistent; no new defect was found.
- AUDIT-0005 corrected `docs/superpowers/README.md`, which incorrectly exposed the 11.2.22 finalization plan as active.

## Resume point

The next unreviewed inventory block begins at `ALLIE_ANALYSE_IST.md` line 1. Remaining work includes the two large analysis documents, changelog/license/source-license/example data, binary assets, final current-blob coverage reconciliation, and the full locked/platform verification gates.


## Documentation and data review

- The two large analysis documents, dated historical audit reports, licensing files, example PGN, opening tables, and historical Superpowers plans/specs were read completely. The dated blocker statements remain preserved historical evidence; they were not reclassified as current runtime defects.
- Opening tables contain the expected three-field tabular schema and complete ECO coverage; opening hashes and the vendored Allie SHA-256 manifest match the fetched contents.
- `docs/superpowers/README.md` was corrected under AUDIT-0005 so the 11.2.22 plan is explicitly archived rather than presented as active.
- Binary icon assets were checked as metadata-only inventory items; they contain no text-line audit surface.

## Resume point

The full 144-file inventory is now covered: source, tests, documentation, data, browser, tools, lockfile, and binary metadata. No files remain INVENTORIED. Remaining work is the locked test suite, platform-specific validation, remote CI/log recovery, and final current-blob/PR publication checks.


## Inventory coverage complete

- `uv.lock` was read structurally across all 1,374 physical lines. The project record is 11.2.24 with Python 3.12; all twelve project dependency pins match `pyproject.toml`, registry sources are used consistently, and no Git/path source was found.
- The 144-file manifest now has no `INVENTORIED` entries. Binary icons are recorded as metadata-only because they have no text-line surface.
- Static review found no additional confirmed defect beyond AUDIT-0002 through AUDIT-0005. AUDIT-0001 remains an infrastructure blocker until GitHub Actions exposes executable logs.

## Validation gates still open

- Run the exact locked unittest, pytest, Node, Ruff, Mypy, version, and diff checks in a complete checkout.
- Execute Windows onedir/EXE, Edge/Playwright, DPI/HWND, OBS/getDisplayMedia, and real capture acceptance on the required platform.
- Recheck CI/Security after the connector/GitHub log availability issue is resolved, then decide whether the draft PR can leave Draft state.


## CI rerun evidence

- The failed PR-triggered jobs were rerun as requested: CI `43633388763` and Security `43633388757`.
- The reruns reproduced the same infrastructure condition: all five jobs completed as failures with `steps: null`, and every job-log request returned `BlobNotFound`.
- AUDIT-0001 remains BLOCKED on GitHub Actions log availability; no source-level failure was inferred.


## Coverage reconciliation

- The three instruction files were line-counted and added to current-blob coverage: `AGENTS.md` 58, `AGENT_TASK.md` 217, and `AGENT_PROGRESS.md` 207 lines.
- The two icon files are binary metadata-only items with no text-line coverage interval.
- Coverage now has entries for all 144 manifest paths; 139 text files have line intervals, three instruction files have explicit instruction intervals, and two binary assets are recorded as metadata-only.
- Manual version-contract assertions passed for application/lock/MV3/userscript versions and the unchanged extension key; the direct extension ID is derived from that key and is unchanged from baseline.
