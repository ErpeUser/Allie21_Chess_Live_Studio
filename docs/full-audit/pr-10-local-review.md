# PR #10: local review and integration

Review date: 15 November 2026. Baseline: `15464e24278f540e081d07c067e20d4cc0d076e8`.
Reviewed audit head: `80217f31634af967ea5a6b55b5e88ab42a30f265`.

## Decision

Accept the PR. Its two production changes are absent from the current main and improve security and privacy status reporting. It changes neither model weights nor dependency pins, the extension identity, automatic chess moves, or capture-exclusion policy. Documentation corrects the version to 11.2.24/11.2.24.0 and marks old evidence historical. Audit inventory files are retained as the original dated review snapshot, not a fresh certification of every source line after integration.

The user explicitly authorized local-only, free validation, integration into main, and deletion of the audit branch after a verified merge. Historical Actions/CodeQL/log issues are excluded from this merge gate. No hosted workflows are manually started. The merge commit uses `[skip ci]` to avoid push-triggered hosted CI.

## Verified production fixes

- POST and PUT `/api/overlay/settings` now apply the same `_require_overlay_settings_access` guard as GET before any mode or lease changes. An unpaired chess-site request returns 403. Reconstructing the pre-PR handler in memory reproduced the new test failure for both methods (200 instead of 403); the fixed handler passes the complete local HTTP suite.
- An idle private viewer preserves verified backend availability/capture-exclusion flags instead of manufacturing success from the requested mode. Running the new regression against baseline main reproduced `Bereit` instead of `Nicht verfuegbar`; the PR passes both VM and real DOM tests. Private browser fallback remains suppressed.

## Corrections made during integration

- The Windows mutex test previously used the production launcher mutex, so a running Allie instance caused a false failure. The test now uses a unique local name, exercises contention and release/reacquisition, and always releases its own handles. Production launcher protection is unchanged.
- The private-viewer browser test now opens the deliberately collapsed settings before checking the retry button. It also asserts that settings start closed.
- Removed a trailing empty line from the audit plan, reported by `git diff --cached --check`.
- Gitleaks 8.30.1 flagged two public SHA256 manifest rows as generic API keys. The eight vendored source hashes were verified. `.gitleaksignore` contains only the two exact historical finding fingerprints; no file, path, or scanner rule is disabled.

## Local validation

The frozen quality environment was synchronized with `uv sync --frozen --extra quality`. Test-server/browser checks ran outside the restricted tool process so localhost access was available; tests use injected models and do not generate or download model weights.

| Check | Result |
| --- | --- |
| `uv run --frozen python -m unittest discover -s tests -v` | 216 run, 3 skips, zero failures/errors |
| `uv run --frozen pytest -q -rs` | 236 passed, 3 skipped; `ALLIE_REQUIRE_BROWSER_TESTS=1` |
| `node --test tests/*.js` | 77 passed |
| `uv run --frozen ruff check backend tools tests` | Pass |
| `uv run --frozen mypy backend --ignore-missing-imports` | Pass, 17 source files |
| `python tools/check_versions.py` | 11.2.24 / 11.2.24.0; extension ID unchanged |
| `git diff --check` and staged diff check | Pass |
| Gitleaks, all local Git refs and staged changes, with redacted output | Pass after classifying the two public-hash false positives |

The three skips are Windows symlink privilege availability, the non-Windows native fallback, and the unsupported non-Windows Stockfish platform case. The two pytest warnings are the existing FastAPI `on_event` startup deprecation. Mypy also reports existing untyped-body notes; these are not errors.

Real Edge capture, OBS/getDisplayMedia, DPI/HWND acceptance, portable release startup, and actual model-weight inference are not executed for this source integration. The nine Playwright tests exercise production viewer/extension-options DOM with deterministic API/media fixtures; they do not certify real capture exclusion. No binary release or desktop/extension deployment is part of this PR merge.
