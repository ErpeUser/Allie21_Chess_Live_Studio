# Release status

## Current branch

The reviewed implementation is on the permanent `main` branch at version **11.2.17**. The browser extension and userscript support the configured local port. The release contains GUI opening-setting synchronization, persistent viewer settings, centered arrowheads, blue premove rendering, bounded request handling, native-overlay lifecycle fixes, and the offline-vendored Allie model loader.

## Automated evidence

- Python syntax/compile checks pass.
- Native-overlay and regression unittest checks: 14 executed, 12 passed, 2 skipped because the global runtime lacks `python-chess`; the locked project environment runs the chess-dependent cases.
- All checked-in JavaScript tests pass (10/10), including opening propagation, settings persistence, dynamic port configuration, arrow geometry, and premove coverage.
- CI now runs unittest, pytest, Ruff, Mypy, compileall, JavaScript tests, and version-alignment checks.

## Remaining release gate

Run the Windows workflow and a manual Windows smoke test before tagging a release. Verify the selected `ALLIE_PORT` in the extension options or userscript when using a non-default port. Portable release binaries are intentionally excluded from Git history; the build script creates them from the locked environment and verifies Stockfish before packaging.
