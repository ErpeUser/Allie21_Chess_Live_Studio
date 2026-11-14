# Release status

## Current branch

The current `main` source and browser release are version **11.2.24** (extension **11.2.24.0**). The current baseline commit is `15464e2`. The browser extension and userscript support the configured local port. The release contains GUI opening-setting synchronization, persistent viewer settings, centered arrowheads, blue premove rendering, bounded request handling, focus-safe native-overlay lifecycle, the private HUD chip, and the offline-vendored Allie model loader.

## Automated evidence

- Python syntax/compile checks and the checked-in JavaScript regression suite are maintained by CI; the baseline CI/Security runs for `15464e2` failed before any job step and exposed no logs, so no current remote pass is claimed here.
- Historical offline and native-overlay counts from earlier releases are retained in `VERSIONEN.md` as historical measurements, not as a 11.2.24 release gate.
- The Windows workflow publishes the complete onedir bundle and a separate unpacked Edge ZIP when manually dispatched.

## Remaining release gate

Run the locked test suite, the Windows workflow, and a manual Windows smoke test before tagging a release. Verify the selected `ALLIE_PORT` in the extension options or userscript when using a non-default port. Portable release binaries are intentionally excluded from Git history; the build script creates them from the locked environment and verifies Stockfish before packaging.
