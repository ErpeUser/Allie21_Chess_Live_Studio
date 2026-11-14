# Audit decisions

1. Use the actual `main` tree at commit `15464e24278f540e081d07c067e20d4cc0d076e8`; the supplied component list is only a starting map.
2. Keep audit state on `audit/full-repository-2026-11-14` until each published change has fresh tests and a readback of the target ref.
3. Treat historical `AGENT_PROGRESS.md` and release notes as evidence to recheck, not current line coverage.
4. Record CI failures with missing logs as blockers, never guessed code defects.
5. Preserve product, security, version, and packaging contracts unless a confirmed root-cause finding requires a minimal change.
6. Resume from blob SHAs, intervals, and content fingerprints; a bare line number is invalid.
7. Current version drift in `VERSIONEN.md` and `docs/release-status.md` is a confirmed documentation finding candidate because `pyproject.toml`/MV3/lockfile report 11.2.24 while those docs still lead with 11.2.22; confirm by reading the current files before editing.
