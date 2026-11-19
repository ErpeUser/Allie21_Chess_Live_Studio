# Allie instructions for Codex

## Application boundaries
The project is a local Windows Python server, a portable onedir launcher, a web
viewer, and an unpacked Manifest V3 extension. Preserve localhost authentication,
pairing, capture-exclusion checks and stale-position suppression. No automatic
chess moves. A sleeping MV3 worker is not an error or proof of missing arrows.

## Project layout
All owned code, tests, automation and documentation live under `source/`.
Only mandatory GitHub metadata and Windows bootstrap entry points stay at root.
All build products, virtual environments, caches and downloads belong under
`generated/`. `generated/protected/git/` contains the LOCAL Git database:
never delete or run an unscoped `git clean -fdx` on `generated/`.
The reviewed vendored Allie module and its SHA-256 manifest under
`generated/dependencies/vendor/` are tracked source inputs, not disposable cache.
Source tests use `source/tests/`; the Windows executable is deployed under
`generated/dist/win/Allie21 Chess Live Studio/`.

## Environment and checks
Use `source/automation/agents/setup.sh` for setup and `source/automation/agents/maintenance.sh` after cache restore.
These files must be selected in the Codex environment; committing them does not
configure a remote environment automatically.
Use locked dependencies: `uv sync --frozen --extra quality`.
Before declaring completion, run the full project checks:

```sh
uv run --frozen python -m unittest discover -s source/tests -v
uv run --frozen pytest -q
node --test source/tests/*.js
uv run --frozen ruff check source/app/backend source/automation source/tests
uv run --frozen mypy source/app/backend --ignore-missing-imports
python source/automation/check_versions.py
git diff --check
```

Report all failures, skips and unexecuted platform tests. Targeted tests are not
a substitute for the full suite or real Windows/Edge acceptance. Do not generate
model weights or change uv.lock unless the task actually requires it.

## Repository synchronization
The local entry point is UPDATE_ALLIE.cmd. For an authenticated, clean main
checkout without Windows deployment:

```sh
python source/automation/maintain.py --git-only --process-prs --cleanup
```

It reports every remote branch and every main PR, classifies already-integrated,
newer and combination candidates, then fast-forwards a clean local main only.
No branch is checked out, created, merged, rebased, deleted or pushed by this
reporting pass. Review candidates remain available for an explicit decision.
Never reset --hard, force-merge unchecked changes, replace existing user hooks
silently, or claim a push without reading back the main SHA. When a task calls
for a GitHub write, commit directly on `main`, run the required checks, push
`main`, and read back the remote SHA.

## Local Windows deployment
Cloud tools do not update the user's Desktop or browser. UPDATE_ALLIE.cmd performs
the local work: source fingerprints, staged portable build when necessary, hashes
and HTTP startup smoke test, previous-bundle backup, then Desktop shortcut and
stable unpacked Edge folder. Never copy just the launcher EXE without app/runtime.
Do not kill arbitrary Python/Edge processes or edit browser profile files/registry.
Read source/docs/UPDATE_PIPELINE_DE.md for first-run setup and recovery.

## Versioning
Application version and standalone userscript version stay paired. The extension
shell is independently versioned in source/app/browser/manifest.json. Preserve its key and
ID omboihgfgofgmidefcpkihgglhkiielo; bump version and version_name when changing
extension code. Deployment writes generated/build/allie-build.json and includes a stamp in the staged extension; it is not tracked.

## Permanent Git, GitHub and Codex policy
This checkout is the single canonical project. Work in its existing checkout
and the standard `main` branch. Never clone/copy the project, create a nested
Git repository, worktree, branch, PR, workflow, symlink or junction for
convenience. Respect
existing Step 1 rules and architecture. Do not delete real user data or
irreplaceable files. The protected Git directory and model weights are not
cleanup targets. Do not use symlinks/junctions to repair import resolution.

Before edits: read this file, README_DE.md, source/docs/UPDATE_PIPELINE_DE.md,
source/tests/test_project_structure.py, source/automation/check_repository_policy.py,
and relevant application interfaces. Check git root, branch, remotes,
status --porcelain=v1 -uall, staged/unstaged changes, and git diff. Preserve
all unrelated changes. State the impact on browser, server, security, models,
build and Windows launcher. Avoid documentation and automation churn.

GitHub `main` is the only integration branch. Agents must never create or use
other branches, worktrees or PRs. For a GitHub write, commit directly to local
`main` and push only `origin/main` after the full checks. For sync: verify clean
working tree AND index, verify expected origin/main, fetch origin/main, inspect
all remote branches and main PRs, compare ancestry, and merge --ff-only ONLY on
clean main. The updater never auto-merges, rebases, closes or deletes candidates.
On divergence, conflicts, dirty tree, unknown checks or failures: STOP and
report. Never auto-stash, reset --hard, clean -fdx, force-push, or overwrite.
Do not move the current audit branch just to sync main.

Only files under source/, approved root entrypoints/configs, approved .github/
files and the pinned manifest-checked vendor in generated/dependencies/vendor/
may be tracked. All other generated/ contents, test reports, logs, caches,
model weights and local credentials remain untracked and ignored. The local
Git metadata under generated/protected/git/ must remain intact. No user data
or irreplaceable files may be removed by agents.

Before and after code changes run:
```sh
python source/automation/check_repository_policy.py
python -m unittest discover -s source/tests -p 'test_repository_policy.py' -v
python -m unittest discover -s source/tests -p 'test_project_structure.py' -v
python -m unittest discover -s source/tests -p 'test_maintenance.py' -v
```
Then run applicable full Python unittest/pytest, Node tests, Ruff, Mypy,
version check, git diff --check, Windows build and HTTP smoke/real browser tests
as applicable. Use paths under source/app/backend and source/automation (never
old backend/tools locations). Report every failed, skipped or unrun check.
GitHub `main` is the default public branch and is updated directly by the
maintainer workflow. CI and security workflows still run on every push. Force
pushes and deletion remain forbidden by the local pre-push guard. Instructions
alone do not enforce safe reasoning, user-data preservation or local behavior.
A new Codex session must start at repository root and independently report the
root, main branch, generated vendor exception and pre/post-change gates.
