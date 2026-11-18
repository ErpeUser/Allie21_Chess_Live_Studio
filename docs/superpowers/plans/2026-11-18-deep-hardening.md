# Superpowers Deep Hardening - 2026-11-18

## Goal and scope
Harden the existing local Windows Allie21 project without redesigning chess analysis, weakening local authentication, changing model weights, or publishing. Preserve the already tested portable release and the user's local preferences. Make only evidence-driven changes.

## Approaches
- Keep downloadable second Stockfish copy: simple but uses another ~98 MB and fails offline if not installed.
- Reuse a pinned, SHA-256-verified engine already in the portable release: preferred; no download, no duplicate payload, same Windows-only trust boundary.
- Trust every external binary: rejected as unsafe.

## Constraints / decisions
The checkout carried 110 preexisting uncommitted changes on main. Their state was preserved by creating local branch audit/superpowers-deep-20261118. No push, main merge, deletion of user data, or model download. Windows release stays in place until a new candidate passes checks. The installed runtime is usable for source tests without regenerating a new environment.

### Task 1: Offline source Stockfish reuse
Modify backend/download_stockfish.py and backend/chess_extras.py. Add regression tests in tests/test_stockfish_installer.py and tests/test_offline.py for reuse of a pinned release binary without network or duplicate copy, and rejection of tampering. Confirm RED with the current code, implement minimal verified fallback, confirm GREEN.

### Task 2: Fail-closed release manifest
Modify tools/release_smoke.py. Add tests in tests/test_release_smoke_shutdown.py to reject unlisted files and duplicate manifest entries and verify streaming hashing. Watch RED, implement, watch GREEN. Verify the actual installed release manifest and smoke startup without touching the release.

### Task 3: Reliable quality checks after cache cleanup
Add a small PowerShell resolver for tested source-venv or installed portable site-packages. Test the real resolver against isolated temporary project trees (source preferred, fallback, fail closed). Integrate into tools/quality_check.ps1 so users do not need to download multi-gigabyte Torch again merely to run tests.

### Task 4: Full verification and handoff
Check real Windows start / doctor, vendor integrity, tests (unittest, pytest, JavaScript/Playwright), Ruff, Mypy, version/lock, and SHA manifest. Assess Bandit findings at original call sites. Review the complete changeset. Preserve a local branch; do not publish or merge main without explicit approval. Disclose what is unverified, especially model-weight inference and native capture exclusion.
