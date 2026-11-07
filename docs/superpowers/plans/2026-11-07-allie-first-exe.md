# Allie-first and Windows EXE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Allie the sole move recommender, let Stockfish score Allie's candidates, keep arrows current, and ship a working double-click Windows EXE.

**Architecture:** `analyse_position()` performs one serialized Allie analysis and then one reused Stockfish evaluation constrained to those moves. `LiveSession` owns one latest-only combined job, so no partial merge can publish. Both JavaScript clients use the same five semantic arrow colors. A tiny PyInstaller launcher starts the reproducible `START_HIER.bat` workflow beside the EXE.

**Tech Stack:** Python 3.12, python-chess, official Allie 2.1 API, Stockfish 19, FastAPI/Uvicorn, browser DOM APIs, PyInstaller 6.22.3.

**Spec:** User request in the active task; no separate design document because the user explicitly requested autonomous execution without questions.

## Global Constraints

- Preserve complete confirmed history; never invent moves, castling, or en-passant rights.
- Load one Allie model and one Stockfish process; retain their caches.
- Only the latest position/settings/session may publish arrows.
- Keep FEN-only Stockfish fallback and all existing input paths.
- Run only short targeted checks plus the already-fast local suite.

## Review Focus

- Allie order remains unchanged even when Stockfish ranks candidates differently.
- Missing history never invokes Allie and still permits Stockfish fallback.
- A stopped or superseded live job cannot publish.
- All five arrow roles have stable distinct colors in both clients.
- The built EXE finds the adjacent batch starter and reports a missing starter clearly.

---

### Task 1: Allie-first analysis and latest-only live session

**Files:** Modify `backend/chess_extras.py`, `backend/allie_local_server.py`, `backend/live_session.py`; test `tests/test_chess.py`.

**Interfaces:** `stockfish_lines(board, limit_seconds, root_moves=None)` optionally evaluates only supplied legal moves; `LiveSession` submits one `analysis_source='both'` job for complete history.

- [ ] Add failing tests proving Stockfish receives Allie's ordered candidates and only one live job publishes.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement the minimal constrained Stockfish evaluation and single-worker live pipeline.
- [ ] Run focused tests, then the fast suite.

### Task 2: Exact arrows and lean overlay invalidation

**Files:** Modify `browser/allie21_overlay.user.js`, `viewer/index.html`, `tests/test_offline.py`.

**Interfaces:** Five arrow roles: own top 1 `#16c784`, own top 2 `#7ee2b8`, opponent top 1 `#ef3340`, opponent top 2 `#ff9299`, safe pre-move `#2f80ed`.

- [ ] Add a failing contract check for the shared role/color map and request invalidation token.
- [ ] Run it and confirm failure.
- [ ] Centralize each client's palette and abort/suppress stale overlay requests immediately.
- [ ] Run the focused check and JavaScript syntax validation.

### Task 3: Double-click EXE and concise delivery docs

**Files:** Create `tools/launcher.py`, `tools/build_exe.ps1`, `Allie21 Chess Live Studio.exe`; modify `README_DE.md`, `VERSIONEN.md`, `CHANGELOG.md`, `.gitignore`, `tests/test_offline.py`.

**Interfaces:** The EXE launches adjacent `START_HIER.bat`; `--check` validates the installation without starting the server.

- [ ] Add a failing launcher check test.
- [ ] Implement the minimal launcher and reproducible PyInstaller build script.
- [ ] Build with pinned PyInstaller 6.22.3 and run the EXE `--check`.
- [ ] Run the short suite, server health/start check, and inspect the final Git diff.
