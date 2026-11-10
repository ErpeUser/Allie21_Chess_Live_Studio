# Final reliability implementation plan

> Execution: superpowers:executing-plans, inline; no subagent tool available.

**Goal:** Repair confirmed extension, API and engine-installation failures.
**Architecture:** Retain existing interfaces; extract only boundary helpers that
can be tested independently of expensive model/vision dependencies.
**Tech Stack:** Python, FastAPI/Starlette, MV3 JavaScript, Node, Playwright Chromium.
**Spec:** docs/superpowers/specs/2026-11-10-final-reliability-design.md

## Global constraints
- Target remote default branch main; no force push or unrelated branch deletion.
- Preserve Allie probabilities, weights, engine pins and capture fail-closed behavior.
- Reproduce every reported defect before changing production code.
- Never conceal skipped or unavailable tests.

## Review focus
- Non-ASCII/oversized/duplicate authorization must fail safely, not HTTP 500.
- Different rate-window sizes and random-key floods must not reset live budgets.
- CSP must permit options scripts; storage failures must not appear as success.
- Late health responses must not overwrite the newer port's status.
- Archive, extraction or filesystem errors must preserve the installed executable.

### Task 1: API capability and rate windows
Files: backend/security.py; tests/test_security_reliability.py.
Interface: require_capability(Request), RequestRateLimiter.allow(key, limit, window_seconds).
- [x] Write/run regressions for non-ASCII token, mixed windows and capacity flooding.
- [x] Fix validation, retain per-policy windows and do not evict active buckets.
- [x] Run tests plus existing available regression coverage; record evidence.

### Task 2: MV3 options and health status
Files: browser/options.html, browser/options.js, browser/background.js;
tests/test_extension_options_browser.py, tests/test_extension_health.js.
- [ ] Real Chromium navigation blocked by administrator; packaged-script behavior verified under Node.
- [x] Externalize JS; add safe async storage handling, connection test and viewer link.
- [x] Test badge parsing, timeout, stale-response suppression and storage changes.
- [x] Run Node tests and record the Chromium navigation blocker.

### Task 3: Verified engine installer
Files: backend/download_stockfish.py; tests/test_stockfish_installer.py.
- [x] Reproduce replacing an installed EXE with wrong extracted digest.
- [x] Stream bounded download to temporary storage; verify archive and EXE before atomic replace.
- [x] Test corrupt/oversize/truncated/multiple-EXE inputs, cleanup, reuse and CLI exit codes.

### Task 4: HTTP boundary simplification
Files: backend/http_boundary.py, backend/live_server.py; tests/test_http_boundary_reliability.py.
- [x] Reproduce forged Content-Length and invalid origins against extracted current boundary.
- [x] Use public ASGI receive/send instead of private Request._body mutation.
- [x] Preserve authentication, CORS and security headers for normal/error responses.
- [x] Verify buffered replay, disconnects, deadlines, JSON/Frame bounds and route integration.

### Task 5: Diagnostics, review and delivery
- [x] Inspect startup, health/readiness and build prerequisites; implement tested narrow corrections.
- [x] Review final diff independently from implementation; report unresolved risks.
- [ ] Verify remote lease, apply only intended blobs, read remote commit and branch list.
- [ ] Inspect actual new CI result and document exact execution limits.
