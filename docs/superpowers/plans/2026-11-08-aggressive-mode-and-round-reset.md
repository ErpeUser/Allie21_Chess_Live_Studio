# Aggressive Mode and Round Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe aggressive Allie-first style and prevent finished-game arrows from leaking into the next round.

**Architecture:** Keep the existing FastAPI/browser pipeline. Add one pure candidate-ranking helper in the backend and one persisted selector in the overlay; live requests never request finished-game review.

**Tech Stack:** Python 3.12, python-chess, FastAPI/Pydantic, JavaScript content script, unittest/Node regression scripts

**Spec:** `docs/superpowers/specs/2026-11-08-aggressive-mode-and-round-reset-design.md`

## Global Constraints

- No new dependency and no automatic website clicks.
- Normal mode preserves Allie ordering exactly.
- Aggressive mode only reranks legal candidates already returned by Allie.
- Stale arrows are cleared on every position/round change.

## Review Focus

- Normal mode ordering must remain byte-for-byte stable.
- Aggressive mode must prefer immediate mate/check without promoting ordinary captures by material value.
- Opponent predictions must retain Allie's probability order.
- A finished game must never render arrows for the pre-final position.
- The setting must survive reload and invalidate in-flight analysis when changed.
- Reload and manual analysis must reset the backend browser tracker exactly once before rebuilding history.

---

### Task 1: Backend play style

**Files:**
- Modify: `backend/allie_local_server.py`
- Modify: `backend/live_server.py`
- Test: `tests/test_chess.py`
- Test: `tests/test_http_offline.py`

**Interfaces:**
- Consumes: `play_style: Literal['normal', 'aggressive']`
- Produces: `rank_allie_candidates(board, candidates, play_style)` and `play_style` in analysis output

- [ ] Write failing tests for normal stability, aggressive mate/check preference, opponent-order preservation, and API validation.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Implement the minimal pure ranking helper and schema field.
- [ ] Apply ranking only to the player's move choices.
- [ ] Run focused tests and confirm they pass.

### Task 2: Overlay setting and round boundary

**Files:**
- Modify: `browser/allie21_overlay.user.js`
- Modify: `browser/manifest.json`
- Test: `tests/test_offline.py`
- Test: `tests/test_overlay_round_style.js`

**Interfaces:**
- Consumes: `cfg.playStyle`
- Produces: API `play_style`, live requests with `review_finished: false`, and a one-shot browser-session reset on reload/manual analysis

- [ ] Write failing source/behavior tests for the selector, request payload, invalidation and finished-game policy.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Implement the selector and request fields without adding a dependency.
- [ ] Bump the patch version and reproducibility hashes.
- [ ] Run the complete short test suite and verify the local health endpoint.
