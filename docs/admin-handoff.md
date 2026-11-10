# Admin- und Abnahme-Handoff

`main` ist Standardbranch und privat; die Remote-Branchliste enthält ausschließlich `main`. Der vorherige Remote-Stand vor diesem Handoff-Commit war `925b043d1286df3bd092af018e832114f05de67d`.

## GitHub Advanced Security und CodeQL

Die Aktivierung wurde als Repository-Administrator versucht und von GitHub mit folgendem Fehler abgelehnt:

```text
422 Advanced security has not been purchased.
```

CodeQL und Gitleaks bleiben im Workflow aktiv. Nach einem passenden GitHub-Tarif kann der Workflow erneut gestartet werden:

```powershell
gh api --method PATCH `
  repos/ErpeUser/Allie21_Chess_Live_Studio `
  -f 'security_and_analysis[advanced_security][status]=enabled'
gh workflow run .github/workflows/security.yml --repo ErpeUser/Allie21_Chess_Live_Studio --ref main
```

Die zuletzt gestarteten CI-/Security-Läufe wurden wegen eines GitHub-Abrechnungs-/Spending-Limits nicht ausgeführt. GitHub annotierte: `recent account payments have failed or your spending limit needs to be increased`.

## Branch-Schutz

Der Branch-Protection-Endpunkt wurde versucht und mit folgendem Tariffehler abgelehnt:

```text
403 Upgrade to GitHub Pro or make this repository public to enable this feature.
```

Nach einem Tarifwechsel kann der Schutz mit den realen Check-Namen aus dem Actions-Tab gesetzt werden. Force-Push und Löschen von `main` müssen verboten bleiben; ein PR-Review und erfolgreiche CI-/Security-Checks sollen erforderlich sein.

## Windows-Abnahme

Auf Windows 11 müssen `START_HIER.bat`, ein benutzerdefinierter `ALLIE_PORT`, `browser/` als entpackte Erweiterung, `getDisplayMedia`, der native `WDA_EXCLUDEFROMCAPTURE`-HUD und ein verifizierter Stockfish-Prozess real getestet werden. Die automatisierte CI simuliert keine Windows-Fenster-, DPI-, OBS- oder Browser-Berechtigungsdialoge.

## Modell-Vendoring

Die fest gepinnte Revision `d2545701ff5af46a51ac947911844f779b355a08` von `yimingzhang/allie-2.1` wurde unter `backend/vendor/allie_model` übernommen. Die Python-Dateien sind im [SHA-256-Manifest](../backend/vendor/allie_model.sha256.csv) erfasst. Der Loader registriert die lokalen Klassen und verwendet `trust_remote_code=False` sowie `local_files_only=True`.

Geprüft wurden:

- fehlende oder manipulierte Vendor-Dateien werden vor dem Start abgelehnt;
- der lokale `AllieConfig`-Load funktioniert offline;
- echte `analyze()`- und `predict()`-Aufrufe liefern legale UCI-Züge;
- die Hugging-Face-Modellkarte weist MIT als Lizenz aus.

## Nachweis der lokalen Qualität

- `uv lock --check`: erfolgreich;
- Unittest: `115` Tests, `1` Skip;
- Pytest: `114 passed, 1 skipped`;
- Ruff: `All checks passed!`;
- Mypy: `Success: no issues found`;
- Compileall und JavaScript-Tests: erfolgreich;
- `git diff --check`: erfolgreich.

## Release

Der portable EXE-Build wurde lokal erfolgreich erzeugt und sein Launcher-/Vendor-Smoke-Test bestanden. Die portable EXE wird erst nach einem echten Windows-Fresh-Path-/OBS-Test als Release-Artefakt freigegeben. Ohne diese Abnahme bleibt der Release-Gate ausdrücklich offen.
