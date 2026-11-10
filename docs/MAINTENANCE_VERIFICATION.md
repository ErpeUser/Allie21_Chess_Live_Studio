# Maintenance verification - 2026-11-10

Base inspected through GitHub: 23dc7d635f3a68c71c38ce13ede05d5cafdba580.

Fresh targeted checks executed against the modules being published:
- 17 Python unittest cases passed: merge policy including missing required jobs,
  pagination, continuing after a blocked PR, fingerprints, backups, rollback,
  symlink rejection, real child-process shutdown and bounded kill fallback.
- 13 Node tests passed: development update marker, suspension/session state,
  opt-out/store handling, concurrent/sequential reload suppression, cold worker
  messages, foreign-sender rejection and single-flight pairing.
- Python compilation and Node syntax checks for the available changed modules.
- POSIX syntax checks for the Codex scripts.
- Tested background.js and release_smoke.py hashes matched their staged Git blobs.

These tests use actual new production modules and controlled browser/network
boundaries. They do NOT run a complete repository checkout or the full original
project suite. They do NOT establish Windows/Edge end-to-end acceptance.

Not run here: full original pytest/unittest/JavaScript suites, Ruff/Mypy,
PowerShell/CMD execution, PyInstaller, native Windows startup and overlay, COM
Desktop shortcut, actual Edge reload, real OCR or Allie computation. Git/gh remote
operations through the new local CLI were not integration-tested. GitHub publication
is performed separately through the connector and verified by reading back main.
No local Windows installation is changed by this chat or by Codex cloud.

The CI workflow retains full-project checks and adds dedicated maintenance and
Windows-script parsing checks. Workflow creation is not a claim of a green run.
The extension shell release is separate from application 11.2.17 and does not
claim to fix every remaining arrow/history problem.
