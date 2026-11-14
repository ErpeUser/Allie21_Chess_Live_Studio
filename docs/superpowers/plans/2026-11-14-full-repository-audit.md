# Allie 2.1 Full Repository Audit Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Execute a resumable four-role audit of every file in `ErpeUser/Allie21_Chess_Live_Studio`, applying validated fixes with tests, commits, and CI evidence while preserving the product and security contracts in the supplied audit specification.

**Architecture:** Establish an immutable `main` baseline, then audit independent subsystems in stable path order. Store deterministic inventory, coverage intervals, findings, decisions, and resumable checkpoints under `docs/full-audit/`. When a confirmed finding appears, stop scanning, record its original blob/line/fingerprints, add a focused regression test, make the smallest root-cause fix, verify it, publish through a guarded branch/PR or fast-forward, recheck changed ranges, and resume.

**Tech Stack:** Python 3.12/uv, FastAPI/Uvicorn/Pydantic, python-chess/chess-tcn, PyTorch/Transformers/Allie vendor, Stockfish, Manifest V3 JavaScript, embedded viewer HTML/CSS/JS, PowerShell/CMD, GitHub Actions.

**Spec:** `Eingefügter Text(10).txt` supplied in this conversation plus repository instructions in `AGENTS.md`, `README_DE.md`, `SECURITY.md`, `VERSIONEN.md`, `AGENT_TASK.md`, `AGENT_PROGRESS.md`, and `docs/UPDATE_PIPELINE_DE.md`.

## Global Constraints

- Audit the actual `main` tree; verify `truncated=false`; record commit and blob SHAs.
- Preserve Allie as primary analysis for complete histories and the documented Stockfish roles.
- Never invent PGN history, castling rights, en-passant rights, or automatic chess moves.
- Preserve `127.0.0.1` binding, capability/instance authentication, origin/host checks, request limits, capture exclusion, extension ID/key, and stale-result/session gates.
- Preserve portable Windows onedir layout and non-destructive updater behavior.
- Do not change model weights, pinned revisions, vendored provenance, or `uv.lock` without a concrete compatibility finding and full validation.
- Keep application/userscript pairing and independent MV3 versioning aligned with `tools/check_versions.py`.
- Treat sleeping MV3 workers as normal; report unavailable Windows/Edge checks as `NOT_EXECUTED` or `BLOCKED`.
- Never claim completion, a fix, a commit, or passing tests without fresh evidence.

## Review Focus

- Partial/FEN-only history must suppress invented concrete moves and preserve legal-state uncertainty.
- Late async responses, leases, and render frames must not overwrite newer sessions.
- Private mode must fail closed for native capture exclusion and browser HUD visibility.
- Portable bundles must contain the complete locked runtime without global-package leakage.
- CI/security failures with missing logs are operational blockers, not guessed source defects.

### Task 0: Baseline and persistent audit state

**Files:** `docs/superpowers/plans/2026-11-14-full-repository-audit.md`, `docs/full-audit/{manifest,checkpoint,coverage,findings,decisions,progress}.*`

- [ ] Verify repository identity, default branch, permissions, HEAD, branch state, open PRs/issues, and workflow status.
- [ ] Read required instruction/progress docs and distinguish historical claims from current requirements.
- [ ] Build sorted 144-file inventory with classification, blob SHA, size, and line-count fields where readable.
- [ ] Initialize checkpoint and coverage without overwriting historical progress; record current CI infrastructure blocker.
- [ ] Commit audit state on a review branch and read back the branch tip.

### Task 1: Backend/session audit

**Files:** `backend/*.py`, relevant Python tests.

- [ ] Read every file in stable bounded blocks and record four-role coverage.
- [ ] For each confirmed bug, record a finding before editing, reproduce it, add a regression test, apply a minimal root-cause fix, and run focused tests.
- [ ] Reconcile changed-file coverage from diff and content fingerprints.

### Task 2: Model, openings, and dependency audit

**Files:** `backend/vendor/**`, `backend/openings/**`, `pyproject.toml`, `uv.lock`, model/hash/config files, dependency tests.

- [ ] Validate vendor hashes, model loading contracts, TSV/PGN/CSV schemas, and legal data.
- [ ] Compare declared and locked versions against Python 3.12, Windows packaging, Allie, and Stockfish compatibility; do not blind-upgrade.
- [ ] Apply only tested parser/dependency changes, updating the lockfile only when required.

### Task 3: Browser and viewer audit

**Files:** `browser/**`, `viewer/index.html`, browser/DOM/geometry/reliability tests.

- [ ] Read full browser and embedded viewer code, including inline CSS/JS.
- [ ] Run available static/Node/browser checks; mark real Edge/Playwright/DPI/capture gates honestly.
- [ ] Fix confirmed lifecycle, geometry, storage, security, and stale-frame findings with focused regressions; recheck MV3 identity/version invariants.

### Task 4: Windows tooling and CI/security audit

**Files:** `tools/**`, root scripts, `.github/**`, maintenance/release docs/tests.

- [ ] Read scripts/workflows line by line and record current run IDs and missing-log evidence.
- [ ] Test launcher, maintenance, build, version, release-smoke, and security paths available locally; reserve Windows-only checks for Windows runners.
- [ ] Preserve workflow-dispatch release boundaries and non-destructive updates.

### Task 5: Cross-cutting verification and publication

- [ ] Run the exact `AGENTS.md` locked unittest, pytest, Node, Ruff, Mypy, version, and diff checks after source changes.
- [ ] Recheck all changed files and dependent callers; update coverage/checkpoints from actual diffs.
- [ ] Publish through guarded fast-forward/PR, read back resulting `main` SHA, and inspect CI jobs/logs.
- [ ] Mark a file `VERIFIED` only when current-blob interval union covers every relevant line; document all remaining blockers.

