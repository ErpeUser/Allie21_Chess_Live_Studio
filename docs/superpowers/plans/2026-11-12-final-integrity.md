# Final Integrity and UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a tested final Allie21 build with distinct opening selections, tactical hint bubbles, honest loading/readiness, duplicate EXE protection, and stale native-session cleanup.

**Architecture:** Keep the current Allie-first backend contract and add small fields (`opening_selection`, `tactical_hints`) to the existing result. Render those fields through the existing viewer, userscript, and native message list. Harden readiness and launcher lifecycle without changing capture or analysis ownership.

**Tech Stack:** Python 3.12, FastAPI, python-chess, existing vanilla HTML/JS viewer and MV3 userscript, Windows ctypes mutex, unittest/pytest and Node tests.

**Spec:** `docs/superpowers/specs/2026-11-12-final-integrity-design.md`

## Global Constraints

- Preserve real game history; never fabricate moves or turn rights.
- Preserve arrow colors: own `#16c784/#7ee2b8`, opponent `#ef3340/#ff9299`, pre-move `#2f80ed`.
- Keep Allie first; Stockfish remains only the existing objective/FEN/fallback path.
- Private mode remains fail-closed and the default; no browser HUD fallback in private mode.
- Do not add runtime dependencies or modify model weights/lock resolution.
- Report Windows/DPI/capture tests as blocked when no Windows environment is available.

## Review Focus

- A chosen opening must be visible for both colors even when the board’s ECO opening is unchanged; test payload and all three clients.
- A missing history must never produce arrows; test existing suppression while allowing informational bubbles.
- A model object during warmup or failed warmup must not make `/health` ready; test `loading` and `failed` phases.
- Two launches racing on a free port must be rejected by the mutex; test guard behavior on the host and static Windows contract.
- A delayed overlay update after stop must be ignored; test the reset/retired-session boundary.

### Task 1: Readiness and startup lifecycle

**Files:**
- Modify: `backend/service_status.py`
- Modify: `backend/live_server.py`
- Create: `tests/test_service_status_contract.py`

- [ ] Add failing tests for `loading`/`failed` with a non-null model and for idempotent preload start.
- [ ] Run the focused tests and observe the expected failures.
- [ ] Make readiness phase-aware and make `start_model_preload()` return the existing live/completed thread.
- [ ] Gate `/analyze` on failed warmup regardless of `_model` presence.
- [ ] Run the focused tests and the readiness suite.

### Task 2: Opening selection and tactical hints

**Files:**
- Modify: `backend/chess_extras.py`
- Modify: `backend/allie_local_server.py`
- Modify: `tests/test_chess.py`

- [ ] Add failing tests for both-side opening selection and immediate/possible two-ply mate hints.
- [ ] Run the focused tests and observe the expected failures.
- [ ] Add bounded legal helper logic and include `opening_selection` and `tactical_hints` in the result/plan messages.
- [ ] Run chess regression tests and verify unknown-history behavior remains unchanged.

### Task 3: Viewer/userscript loading and result blobs

**Files:**
- Modify: `viewer/index.html`
- Modify: `browser/allie21_overlay.user.js`
- Modify: `tests/test_viewer_reliability.js`
- Modify: `tests/test_browser_reliability.js`

- [ ] Add failing static assertions for loading phase text, both opening cards, and tactical bubbles.
- [ ] Run Node tests and observe the expected failures.
- [ ] Render strict health validation/loading state and show opening/tactical messages as bounded accessible bubbles.
- [ ] Run all Node tests and syntax checks.

### Task 4: Duplicate EXE and stale overlay guard

**Files:**
- Modify: `tools/launcher.py`
- Modify: `backend/native_overlay.py`
- Modify: `backend/live_server.py`
- Modify: `tests/test_offline.py`
- Modify: `tests/test_native_overlay.py`

- [ ] Add failing tests for the single-instance guard contract and session reset.
- [ ] Run focused tests and observe failure.
- [ ] Add the retained Windows mutex guard and `PrivateOverlayController.reset()`; call reset plus lease release on start/stop.
- [ ] Run launcher/native regression tests and verify no process-kill behavior changed.

### Task 5: Version, docs, and cleanup

**Files:**
- Modify: `pyproject.toml`, `backend/config.py`, `browser/allie21_overlay.user.js`, `browser/manifest.json`
- Modify: `README_DE.md`, `VERSIONEN.md`, `CHANGELOG.md`, `AGENT_PROGRESS.md`
- Modify: stale version assertions in tests

- [ ] Bump the paired application/userscript/Edge versions to 11.2.22/11.2.22.0.
- [ ] Document the loading state, duplicate-launch behavior, unknown-history hints, and environment limits.
- [ ] Remove only obsolete duplicate documentation references; keep required task/progress records.
- [ ] Run the complete available verification matrix and record blockers.

### Task 6: GitHub integration

**Files:** repository tree on `main`

- [ ] Create a short-lived branch from the verified `main` SHA using the GitHub connector.
- [ ] Commit the tested tree, open a PR into `main`, inspect status/diff, and merge it.
- [ ] Read back the resulting `main` SHA and verify changed files on the standard branch.
