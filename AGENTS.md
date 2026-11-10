# Allie instructions for Codex

## Application boundaries
The project is a local Windows Python server, a portable onedir launcher, a web
viewer, and an unpacked Manifest V3 extension. Preserve localhost authentication,
pairing, capture-exclusion checks and stale-position suppression. No automatic
chess moves. A sleeping MV3 worker is not an error or proof of missing arrows.

## Environment and checks
Use `.codex/setup.sh` for setup and `.codex/maintenance.sh` after cache restore.
These files must be selected in the Codex environment; committing them does not
configure a remote environment automatically.
Use locked dependencies: `uv sync --frozen --extra quality`.
Before declaring completion, run the full project checks:

```sh
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen pytest -q
node --test tests/*.js
uv run --frozen ruff check backend tools tests
uv run --frozen mypy backend --ignore-missing-imports
python tools/check_versions.py
git diff --check
```

Report all failures, skips and unexecuted platform tests. Targeted tests are not
a substitute for the full suite or real Windows/Edge acceptance. Do not generate
model weights or change uv.lock unless the task actually requires it.

## Repository synchronization
The local entry point is UPDATE_ALLIE.cmd. For an authenticated, clean main
checkout without Windows deployment:

```sh
python tools/maintain.py --git-only --process-prs --cleanup
```

It processes open main PRs, updates outdated trusted branches, merges only tested
eligible heads, then pulls main and removes only fully merged/unprotected branches
without open PRs. Pending, failing, draft, fork and conflicting PRs remain open;
record their reasons and fix coding failures separately with tests and review.
Never reset --hard, force-merge unchecked changes, delete unmerged work, replace
existing user hooks silently, or claim a push without reading back the main SHA.
Direct publication to main requires explicit user authorization for that task.

## Local Windows deployment
Cloud tools do not update the user's Desktop or browser. UPDATE_ALLIE.cmd performs
the local work: source fingerprints, staged portable build when necessary, hashes
and HTTP startup smoke test, previous-bundle backup, then Desktop shortcut and
stable unpacked Edge folder. Never copy just the launcher EXE without app/runtime.
Do not kill arbitrary Python/Edge processes or edit browser profile files/registry.
Read docs/UPDATE_PIPELINE_DE.md for first-run setup and recovery.

## Versioning
Application version and standalone userscript version stay paired. The extension
shell is independently versioned in browser/manifest.json. Preserve its key and
ID omboihgfgofgmidefcpkihgglhkiielo; bump version and version_name when changing
extension code. Deployment generates browser/allie-build.json; it is not tracked.
