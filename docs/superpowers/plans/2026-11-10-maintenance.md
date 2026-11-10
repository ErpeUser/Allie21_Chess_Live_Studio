# Allie maintenance implementation record

Goal: one explicit local update command for clean-main synchronization, PR
eligibility checks, conservative cleanup, staged Windows deployment and MV3
diagnostics. The user explicitly authorized publication directly to main.

Architecture: Python stdlib with git/gh for repository operations, PowerShell for
the existing Windows build/shortcut, event-driven MV3 update checks. No permanent
worker keepalive, unchecked merges, unmerged-branch deletion or cloud-to-PC claims.

- [x] Implement and test merge policy, required jobs, backups and fingerprints.
- [x] Implement staged Windows deployment and local pull hooks.
- [x] Implement extension version/update diagnostics and cold-worker tests.
- [x] Add Codex instructions, setup/maintenance scripts and CI checks.
- [x] Record targeted verification and unavailable platform/full-suite checks.
- [ ] Verify final main ref after publishing the atomic commit.

Rulings: PRs blocked by CI/review are reported rather than force-merged. Only
proven merged branches are deleted. A desktop shortcut points to the complete
portable directory, not an incomplete standalone EXE. Extension-shell versioning
is separate from the unchanged application/userscript version. A local pull
without changes does not fire post-merge: use UPDATE_ALLIE.cmd for every sync.
