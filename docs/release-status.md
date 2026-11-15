# Release status

## Current branch

The separate review branch `fix/allie21-six-agent-20261115` declares application/userscript **11.2.25** and extension **11.2.25.0**. Its verified `main` baseline is `c5ea9a324a28f1b16fb544cfbe2ef140178213a0`. Source changes include authenticated local PGN replay, pairing limits, stale/privacy lifecycle corrections, safe extension-build preparation, measured tactical-scan optimization and unused-index removal. The extension key/identity and third-party lock entries are preserved.

See the [current six-role implementation report](six-agent-20261115/README.md) for exact checks and blockers. This branch is not merged, released or installed on Windows by this work. Real browser DOM and native Windows acceptance remain required.

## Historical automated evidence for PR #10

- PR #10 was compared with baseline `15464e2` and validated locally on Windows on 15 November 2026. Its overlay-settings authorization and private-status corrections fix reproducible defects in that baseline.
- Locked unittest: 216 tests, 3 platform skips, no failures. Locked pytest: 236 passed, 3 platform skips; includes all nine Playwright viewer/extension-options tests. Node: 77 passed. Ruff, Mypy, version/identity, and diff checks pass.
- Only free local checks are used for this integration. Historical GitHub CI/Security infrastructure failures are not a merge gate under the user's explicit instruction. No remote CI or CodeQL pass is claimed.
- Detailed scope, regression evidence, skips, and local secret-scan results are recorded in `docs/full-audit/pr-10-local-review.md`.

## Remaining release gate

The six-role source changes do not create or certify a new portable/Windows/GitHub release. Real Edge capture, DPI/HWND, OBS/getDisplayMedia, and model-weight acceptance are not executed in this review and are not claimed. Verify the selected `ALLIE_PORT` in the extension options or userscript when using a non-default port. Portable binaries remain excluded from Git history; the existing build script creates them from the locked environment and verifies Stockfish before packaging.
