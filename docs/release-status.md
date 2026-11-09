# Release status

## Current branch

The reviewed implementation is on branch `codex/allie-full-fix` at version **11.2.17**. The branch contains the GUI opening-setting synchronization, persistent viewer settings, centered arrowheads, blue premove rendering, bounded request handling, and the native-overlay lifecycle fixes.

## Automated evidence

- Python syntax/compile checks pass.
- Native-overlay and regression unittest checks pass in the available runtime; chess-dependent tests require the locked project environment.
- All checked-in JavaScript tests pass (10/10), including opening propagation, settings persistence, arrow geometry, and premove coverage.
- CI now runs unittest, pytest, Ruff, Mypy, compileall, JavaScript tests, and version-alignment checks.

## Remaining release gate

Run the Windows workflow and a manual Windows smoke test before tagging a release. Portable release binaries are intentionally excluded from Git history; the build script creates them from the locked environment and verifies Stockfish before packaging.
