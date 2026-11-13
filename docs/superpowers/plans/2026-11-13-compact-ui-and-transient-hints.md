# Compact UI and Transient Hints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify Allie’s viewer and browser overlay so settings stay closed, the main board remains primary, and current hints appear briefly beside the board.

**Architecture:** Keep the current HTML, userscript, API payloads, native overlay, and security boundaries. Add a small transient-hint controller at each presentation layer, with independent five-second text expiry and generation/session guards; keep arrows and native capture exclusion alive after text expires.

**Tech Stack:** Existing HTML/CSS/JavaScript, Python native overlay controller, Node tests, Playwright browser tests, Ruff/Mypy.

**Spec:** `docs/superpowers/specs/2026-11-13-compact-ui-and-transient-hints-design.md`

## Global Constraints

- No automatic chess moves.
- Preserve localhost authentication, pairing, capture-exclusion checks, and stale-position suppression.
- Preserve private mode as native-only and fail-closed.
- Keep extension key/ID unchanged; application and userscript versions remain paired.
- Hints last five seconds, do not reset on polling, and disappear on position/session changes.
- Native text expiry must not remove valid arrows or weaken capture exclusion.

## Review Focus

- Repeated polling of the same position must not extend a hint timer: test in viewer and userscript.
- A newer position must prevent an older timer from hiding its hint: test with two generations.
- Stopping or disabling recommendations must clear the hint immediately: test in viewer.
- Private mode must never show a DOM/SVG fallback: preserve existing private-mode tests and add the transient path assertion.
- A native overlay with no free monitor space must omit text while retaining arrows: test native controller behavior.

### Task 1: Viewer transient hint and compact hierarchy

**Files:**
- Modify: `viewer/index.html`
- Test: `tests/test_viewer_reliability.js`, `tests/test_viewer_browser.py`

**Interfaces:**
- Produces: a browser-global helper `showTransientHint(text, key, generation)` used by `report`, reset, stop, and recommendation-toggle paths.

- [x] **Step 1–5:** Implemented and covered by the viewer VM tests; the hint is keyed, deduplicated, independently dismissed, and positioned beside the board.

### Task 2: Browser userscript transient hint and settings separation

**Files:**
- Modify: `browser/allie21_overlay.user.js`
- Test: `tests/test_browser_reliability.js`, `tests/test_overlay_insights.js`, `tests/test_overlay_start_position.js`

**Interfaces:**
- Produces: `showTransientHint(message, key, sessionId, renderRevision)` and guarded cleanup integrated with `show`, `clearOverlay`, `resetBoardSession`, and visibility handlers.

- [x] **Step 1–5:** Implemented; the detailed panel is click-open only and the five-second hint timer leaves arrows and private-mode rules intact.

### Task 3: Native overlay text lifetime

**Files:**
- Modify: `backend/native_overlay.py`
- Test: `tests/test_native_overlay_reliability.py`

**Interfaces:**
- Consumes: existing `PrivateOverlayController.update()` snapshots and render revisions.
- Produces: native text that expires independently of the arrow snapshot and retains valid arrows/capture state.

- [x] **Step 1–4:** Implemented and verified with a deterministic timer test; message expiry updates only text and retains arrows.

### Task 4: Copy and visual regression evidence

**Files:**
- Modify: `docs/superpowers/specs/2026-11-13-compact-ui-and-transient-hints-design.md`
- Create/refresh: `.build/gui-screenshots.html`, `.build/gui-screenshots.json`, `.build/gui-*.png`

- [ ] **Step 1–2:** The capture helper was attempted but its local server did not become healthy in this environment.
- [x] **Step 3:** Targeted checks pass; full HTTP/model suites remain environment-blocked and are recorded in the delivery report.
- [ ] **Step 4:** Commit, push, and deployment follow after the final repository check.
