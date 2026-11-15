# Release status

## Current branch

The current `main` source and browser release are version **11.2.24** (extension **11.2.24.0**). The current baseline commit is `15464e2`. The browser extension and userscript support the configured local port. The release contains GUI opening-setting synchronization, persistent viewer settings, centered arrowheads, blue premove rendering, bounded request handling, focus-safe native-overlay lifecycle, the private HUD chip, and the offline-vendored Allie model loader.

## Automated evidence

- PR #10 was compared with baseline `15464e2` and validated locally on Windows on 15 November 2026. Its overlay-settings authorization and private-status corrections fix reproducible defects in that baseline.
- Locked unittest: 216 tests, 3 platform skips, no failures. Locked pytest: 236 passed, 3 platform skips; includes all nine Playwright viewer/extension-options tests. Node: 77 passed. Ruff, Mypy, version/identity, and diff checks pass.
- Only free local checks are used for this integration. Historical GitHub CI/Security infrastructure failures are not a merge gate under the user's explicit instruction. No remote CI or CodeQL pass is claimed.
- Detailed scope, regression evidence, skips, and local secret-scan results are recorded in `docs/full-audit/pr-10-local-review.md`.

## Remaining release gate

This PR integration does not create or certify a new portable/Windows/GitHub release. Real Edge capture, DPI/HWND, OBS/getDisplayMedia, and model-weight acceptance are not executed in this review and are not claimed. Verify the selected `ALLIE_PORT` in the extension options or userscript when using a non-default port. Portable binaries remain excluded from Git history; the existing build script creates them from the locked environment and verifies Stockfish before packaging.
