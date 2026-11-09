# Admin- und Abnahme-Handoff

Der Quellcode und die automatisierten Tests sind auf `main` fertig. Der Merge-Commit ist `89ab33d9ad0a2c9210d7e6bcf3dea2678759be93`. Die folgenden Schritte benötigen GitHub-Administratorrechte oder einen echten Windows-Rechner und können deshalb nicht aus dem Repository-Commit heraus sicher automatisiert werden.

## GitHub Advanced Security und CodeQL

CodeQL analysiert den Code, kann die SARIF-Ergebnisse aber erst in GitHub veröffentlichen, wenn Code Scanning/Advanced Security für das private Repository aktiviert ist:

```powershell
gh api --method PATCH `
  repos/ErpeUser/Allie21_Chess_Live_Studio `
  -f 'security_and_analysis[advanced_security][status]=enabled'
```

Danach den Security-Workflow erneut starten:

```powershell
gh workflow run Security --repo ErpeUser/Allie21_Chess_Live_Studio --ref main
gh run list --repo ErpeUser/Allie21_Chess_Live_Studio --workflow Security.yml --limit 5
```

## Branch-Schutz

Die Schutzregeln erfordern Repository-Adminrechte. Die Statusnamen müssen exakt den in GitHub angezeigten Check-Namen entsprechen:

```powershell
@'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "CI / windows-tests",
      "Security / CodeQL (python)",
      "Security / CodeQL (javascript-typescript)",
      "Security / Secret scan"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true
}
'@ | Set-Content protection.json
gh api --method PUT `
  repos/ErpeUser/Allie21_Chess_Live_Studio/branches/main/protection `
  --input protection.json
Remove-Item protection.json
```

## Windows-Abnahme

Auf Windows 11 müssen `START_HIER.bat`, ein benutzerdefinierter `ALLIE_PORT`, `browser/` als entpackte Erweiterung, `getDisplayMedia`, der native WDA_EXCLUDEFROMCAPTURE-HUD und ein verifizierter Stockfish-Prozess einmal real getestet werden. Die automatisierte CI deckt die Python-, JavaScript-, Lockfile- und statischen Prüfungen ab, simuliert aber keine Windows-Fenster- oder Browser-Berechtigungsdialoge.

## Entfernen von `trust_remote_code`

Die aktuelle Implementierung pinnt Modell- und Code-Revision. Eine vollständige Entfernung von `trust_remote_code=True` benötigt einen bewusst großen, externen Vendor-Schritt:

```powershell
$env:MODEL_REVISION='d2545701ff5af46a51ac947911844f779b355a08'
huggingface-cli download yimingzhang/allie-2.1 `
  --revision $env:MODEL_REVISION `
  --include '*.py' `
  --local-dir backend/vendor/allie_model
Get-ChildItem backend/vendor/allie_model -Filter '*.py' -Recurse |
  Get-FileHash -Algorithm SHA256 |
  Export-Csv backend/vendor/allie_model.sha256.csv -NoTypeInformation
```

Danach müssen die vendorten Klassen mit `trust_remote_code=False`, `local_files_only=True` geladen, das Manifest im Review geprüft und die zusätzlichen Dateien in Git versioniert werden. Ohne diese Prüfung wäre das Abschalten der Option nur eine Scheinmaßnahme.

## Nach dem Merge: Default-Branch und Bereinigung

Nach dem Merge muss ein GitHub-Administrator `main` als Standardbranch setzen und die alten Arbeitsbranches löschen. Diese REST-Aufrufe sind absichtlich separat aufgeführt, weil die verfügbare Connector-Schnittstelle keine Repository-Einstellungen und keine DELETE-Ref-Operation bereitstellt:

```powershell
gh auth login

gh api --method PATCH `
  repos/ErpeUser/Allie21_Chess_Live_Studio `
  -f default_branch=main

gh api --method DELETE `
  repos/ErpeUser/Allie21_Chess_Live_Studio/git/refs/heads/codex/allie-full-fix

gh api --method DELETE `
  repos/ErpeUser/Allie21_Chess_Live_Studio/git/refs/heads/codex/allie-first-exe

gh api --method DELETE `
  repos/ErpeUser/Allie21_Chess_Live_Studio/git/refs/heads/fix/allie-first-browser-visible

gh api --method DELETE `
  repos/ErpeUser/Allie21_Chess_Live_Studio/git/refs/heads/fix/ci-version-assertions
```
