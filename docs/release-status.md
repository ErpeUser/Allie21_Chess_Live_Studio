# Release status

## Current branch

The reviewed implementation is on the permanent `main` branch at version **11.2.22**. The browser extension and userscript support the configured local port. The release contains GUI opening-setting synchronization, persistent viewer settings, centered arrowheads, blue premove rendering, bounded request handling, focus-safe native-overlay lifecycle, the private HUD chip, and the offline-vendored Allie model loader.

## Automated evidence

- Python syntax/compile checks pass.
- The dependency-light offline unittest slice passes (35/35), and the native-overlay/session regressions pass in the available runtime. The full chess/model suite remains dependency-gated here because `python-chess` and `pytest` are not installed in the base runtime.
- All checked-in JavaScript tests pass (72/72), including opening propagation, settings persistence, dynamic port configuration, arrow geometry, share/private lifecycle, and premove coverage.
- CI now runs unittest, pytest, Ruff, Mypy, compileall, JavaScript tests, and version-alignment checks.
- The Windows workflow now publishes both the complete onedir bundle and a separate unpacked Edge ZIP with a signed-by-content `allie-build.json` revision stamp.

## Remaining release gate

Run the Windows workflow and a manual Windows smoke test before tagging a release. Verify the selected `ALLIE_PORT` in the extension options or userscript when using a non-default port. Portable release binaries are intentionally excluded from Git history; the build script creates them from the locked environment and verifies Stockfish before packaging.
