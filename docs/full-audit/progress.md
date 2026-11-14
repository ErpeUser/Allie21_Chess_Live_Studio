# Full audit progress

## Phase 0 — baseline

- Audit ID: `allie21-full-audit-2026-11-14`
- Repository: `ErpeUser/Allie21_Chess_Live_Studio`
- Baseline/current main commit: `15464e24278f540e081d07c067e20d4cc0d076e8`
- Root tree: `c4ecfe3a93f71dfc96d96f117300d0bc74d3f026`
- Deterministic inventory: 144 blobs, 19 trees, `truncated=false`.
- Required instruction files were read; historical `AGENT_PROGRESS.md` remains preserved context, not proof of current coverage.
- Audit branch: `audit/full-repository-2026-11-14`.
- Audit scaffolding commit: `f90a646eb8316dbe00173eac0abf5828e30a8f8b`.

## Finding AUDIT-0002 — documentation/version drift

The first confirmed finding interrupted the normal scan. Authoritative current version is 11.2.24/11.2.24.0 in `pyproject.toml`, `uv.lock`, `browser/manifest.json`, and `browser/allie21_overlay.user.js`; five current-state documents still led with 11.2.22 or lacked a 11.2.24 changelog entry. A minimal documentation-only correction is prepared on the audit branch and must be read back and statically checked before the scan resumes.

## Current blockers

- CI/Security runs 43571741050/43571740981 and 43625326792/43625326785 failed before any job step; connector logs return `BlobNotFound`. This is an infrastructure blocker, not an inferred source defect.
- Branch-protection read returned 403; branch object reports `protected=false` and no required status checks. Recheck before each main write.
- Windows onedir/EXE, Edge/Playwright, DPI/HWND, OBS/getDisplayMedia, and real capture acceptance are NOT_EXECUTED in this environment.

## Resume point

After validating the documentation fix, load the new `VERSIONEN.md` blob, reconcile the changed intervals/fingerprints, then resume with sorted file `.codex/maintenance.sh`. No code finding is confirmed yet; do not claim full coverage.
