# Allie21 v11.2 Final Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the final, smaller and reproducible Windows release without changing the working Allie-first behavior.

**Architecture:** Keep the existing FastAPI/python-chess/Allie/Stockfish pipeline and direct Manifest V3 extension. Remove only proven dead code and ineffective configuration, apply compatible patch releases, and rebuild the small launcher EXE.

**Tech Stack:** Python 3.12, uv, FastAPI/Pydantic/Uvicorn, python-chess, Allie 2.1/Transformers/PyTorch, Stockfish 19, Manifest V3 JavaScript, PyInstaller.

**Spec:** `README_DE.md` plus the user's final-cleanup request from 2026-11-08.

## Global Constraints

- Preserve current fast Allie move output, staged opponent prediction, arrows, complete-history rules, and model warmup.
- Add no runtime dependency unless it removes more project code and remains compatible with Windows and Allie.
- Keep video/OCR lazy-loaded and the direct Edge extension install path.
- Use pinned reproducible versions and rebuild the checked launcher EXE.

## Review Focus

- Existing browser settings must migrate without losing automatic player-side detection.
- Start-position warmup must still call the real Allie API exactly once.
- Removing model fields from `config.json` must not change the fixed model ID or revision.
- The launcher must extract temporary PyInstaller files outside the project directory.
- Every displayed version and recorded hash must match the final artifacts.

---

### Task 1: Remove ineffective configuration and dead code

**Files:**
- Modify: `tests/test_offline.py`
- Modify: `backend/config.py`
- Modify: `backend/live_server.py`
- Modify: `backend/live_session.py`
- Modify: `backend/allie_local_server.py`
- Modify: `browser/allie21_overlay.user.js`
- Delete: `backend/preload_allie.py`

**Interfaces:**
- Consumes: `MODEL_ID`, `MODEL_REVISION`, and the existing `CONFIG` runtime dictionary.
- Produces: fixed model metadata from constants, with only effective user settings in `CONFIG`.

- [ ] Write a failing test that requires model ID/revision to stay fixed while being absent from loaded user configuration.
- [ ] Run the focused test and confirm the old configuration fails it.
- [ ] Remove the ineffective fields, dead imports/function, and redundant preload script.
- [ ] Run focused and full tests.

### Task 2: Refresh compatible pins and release metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `browser/manifest.json`
- Modify: `browser/allie21_overlay.user.js`
- Modify: `tests/test_offline.py`
- Modify: `tests/test_http_offline.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: official PyPI release metadata and the existing lockfile.
- Produces: v11.2.0 with FastAPI 0.162.2 and unchanged verified Allie/Vision pins.

- [ ] Update version assertions first and confirm they fail.
- [ ] Update project/extension versions and FastAPI patch pin.
- [ ] Regenerate `uv.lock` with only the requested package upgrade.
- [ ] Run the full suite and JavaScript syntax checks.

### Task 3: Polish the existing interface and copy

**Files:**
- Modify: `viewer/index.html`
- Modify: `browser/allie21_overlay.user.js`

**Interfaces:**
- Consumes: the existing Allie dark theme and current analysis/status data.
- Produces: a calmer, clearer interface without a UI framework or bitmap asset.

- [ ] Preserve the existing layout and behavior while simplifying visible German copy.
- [ ] Use the existing palette with clearer surface levels, hierarchy, focus, and status treatments.
- [ ] Keep the chess motif as lightweight CSS/SVG rather than adding image/runtime weight.
- [ ] Run comprehension and UI-code reviews plus focused browser parser tests.

### Task 4: Correct installer, help, and build cleanup

**Files:**
- Modify: `viewer/index.html`
- Modify: `README_DE.md`
- Modify: `VERSIONEN.md`
- Modify: `tools/build_exe.ps1`

**Interfaces:**
- Consumes: direct Edge extension folder and PyInstaller's default Windows temp extraction.
- Produces: accurate help text and a launcher that no longer leaves `_MEI*` beside the project.

- [ ] Replace obsolete Tampermonkey/preload instructions.
- [ ] Remove the project-local `--runtime-tmpdir` build option.
- [ ] Delete ignored crash/test/build artifacts after resolving their exact paths.
- [ ] Rebuild and run `Allie21 Chess Live Studio.exe --check`.

### Task 5: Final verification and reproducibility record

**Files:**
- Modify: `VERSIONEN.md`

**Interfaces:**
- Consumes: final `uv.lock`, EXE, test suite, and launcher.
- Produces: exact final hashes and verification evidence.

- [ ] Run all Python and JavaScript tests plus compile and diff checks.
- [ ] Compute and record final lockfile/EXE hashes.
- [ ] Re-run tests affected by the hash update.
- [ ] Commit the clean final release.
