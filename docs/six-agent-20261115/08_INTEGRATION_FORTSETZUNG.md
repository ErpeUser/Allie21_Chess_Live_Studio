# Fortsetzungs-Checkpoint – Allie 2.1, 15. November 2026

**Status: TEILWEISE. Implementierung und lokale Gegenprüfung abgeschlossen; Plattform-/CI-Abnahme offen.**

## Verbindlicher Stand

| Feld | Wert |
| --- | --- |
| Projekt | `ErpeUser/Allie21_Chess_Live_Studio` |
| Start-Commit | `c5ea9a324a28f1b16fb544cfbe2ef140178213a0` auf `main` |
| Arbeitsbranch | `fix/allie21-six-agent-20261115` |
| Lokal geprüfter Commit | `16bc123d8a310ff46475c9b6c85b77167c4732e2` |
| Veröffentlichter gleichwertiger Code-Commit | `25aecacb6fb6ee8d9ca8c428d7dee706e8ae5d46` |
| Geprüfter Code-Tree | `4f7b961f75ae70f366bf906bdb6e78850d706d6d` |
| PR | [Draft #11](https://github.com/ErpeUser/Allie21_Chess_Live_Studio/pull/11) |
| Version | App/Userscript 11.2.25; MV3 11.2.25.0 |
| Weitere Commits | Nur das Audit-Dokumentationsverzeichnis; aktuellen Head im PR lesen |

Alle sechs getrennten Rollen haben Implementierungen geliefert und ihre Arbeitsbereiche übergeben. Die unabhängigen Architektur- und Security-Gegenprüfungen sind abgeschlossen. Bestätigte zusätzliche Privacy-/Queue-Probleme wurden vor der Abgabe behoben. Keine weiteren Agenten arbeiten nach Ende dieser Sitzung im Hintergrund.

## Vorhandene Implementierungen

- Bestätigtes Zugrecht bleibt verbindlich; gemeinsames atomisches Pairing-Fehlerbudget.
- Native Timer und Browser-/Queue-Frames werden an Lifecycle-Grenzen entwertet.
- Remote-Privatmodus blendet Viewer und Browser unverzüglich aus.
- Sichere Extension-Build-Pfade, Prüfung bestehender eigener Ausgabe und temporäre Vorbereitung.
- PGN-Lernrückblick mit geschützter API, lokalem Parser, Brett, Datei/Text, Tastatur, Textalternative und deutscher Doku.
- Verzögerte SAN-Erzeugung: synthetischer Suite-Median −40,75 % bei unverändertem Verhalten.
- Tote Placement-Eröffnungsmap entfernt; exakter Index unverändert.

Details, RED/GREEN und Commit-Zuordnung: [findings.json](findings.json), [publication-map.json](publication-map.json), [README.md](README.md).

## Tatsächlicher Prüfstand

| Prüfung | Status |
| --- | --- |
| Frozen Quality Sync | PASS |
| Core-Pytest | 290 PASS; zwei vorhandene DeprecationWarnings |
| Vollständiges Pytest | 290 PASS, 14 Browser-Setup-ERROR |
| Vollständiges Unittest | 245 ausgeführt, ein Browser-Klassen-Setup-ERROR |
| Node | 91 PASS, keine Skips |
| Ruff, Version/ID, Lock, compileall, Diff | PASS |
| Mypy/Linux | 35 unveränderte Windows-ctypes-Befunde |
| Mypy mit Windows-Ziel | PASS, 18 Quelldateien |
| Remote CI/Security | Fehlgeschlagen ohne verfügbare Steps; Logabfragen `404 BlobNotFound` |
| Native Windows/Edge, Capture, Modell/GPU, portable Auslieferung | NICHT AUSGEFÜHRT |

Es gibt keine bestätigten offenen P0/P1 im gegengeprüften Änderungsumfang. Das ist kein umfassender Fehlerfreiheitsnachweis. Die Liste noch ungelesener oder nur strukturell geprüfter Dateien steht im vollständigen [Manifest](manifest.json) und der [Abdeckung](coverage.json).

## Nächste konkrete Arbeiten

1. **Browser-Gate in geeigneter Testumgebung:** Den tatsächlichen PR-Head in einem eigenen, sauberen Checkout prüfen. Die im Repository geforderte Python-3.12-Umgebung mit `uv sync --frozen --extra quality` herstellen. Chromium für Playwright bereitstellen und `ALLIE_REQUIRE_BROWSER_TESTS=1` setzen. `tests/test_viewer_browser.py` und `tests/test_extension_options_browser.py` vollständig ausführen. Erwartet sind 14 echte DOM-/Optionsfälle ohne Setupfehler. Danach alle AGENTS-Gates wiederholen. In der bisherigen Cloud-Umgebung verhindert die Socket-Sperre bereits den Browserstart; wiederholte identische Versuche liefern keinen zusätzlichen Nachweis.
2. **Windows-Abnahme durch zuständigen lokalen Prüfer:** In synthetischen oder ausdrücklich berechtigten Trainingssituationen Privat/Share/Normal, Fokus-/Tabwechsel, verändertes Brett, verzögerte Kopplung, Bildschirmfreigabe und unterschiedliche DPI/Monitore prüfen. Windows-HWND-Affinität und OBS/getDisplayMedia separat beobachten. Keine fremde laufende menschliche Partie als Test verwenden.
3. **Build-/Dateisystem-Abnahme:** Auf Windows die neuen Build-Safety-Tests einschließlich verfügbarer Symlinks/Junctions und Dateisperren ausführen. Regulären Build und Wiederholungsbuild prüfen. Die letzte Verzeichnis-/ZIP-Veröffentlichung ist nicht als Transaktion implementiert. Ein vollständiger authentifizierter Checkout muss den unveränderten Original-PNG enthalten; in diesem Cloud-Checkout war dessen Binärinhalt nicht verfügbar.
4. **CI-Zugang klären:** Die tatsächlichen Run-/Job-Anmerkungen und die Actions-Verfügbarkeit durch einen berechtigten Repository-Administrator prüfen. Vor einem erneuten Lauf die Ursache der leeren Steps und fehlenden Logs klären. Kein fehlgeschlagener Check wird zu PASS erklärt. Der bestehende manuelle Windows-Release-Workflow wird dadurch nicht automatisch freigegeben.
5. **Optionale Modell-/Installer-Abnahme gesondert autorisieren:** Vorhandene Modellgewichte beziehungsweise einen separat genehmigten Download und eine echte Stockfish-/Portable-Umgebung verwenden. Die bisherigen Tests enthalten keine echte Modell-/GPU- oder Windows-Installation.
6. **Verbleibende Quellenabdeckung fortsetzen:** Im Manifest mit Status „keine Quellenintervalle“ beziehungsweise „teilweise“ beginnen und anhand des angegebenen Blob-SHA lesen. Frühere Intervalle nicht ungeprüft auf neue Versionen übertragen. Vendor- und Datenintegrität sind bereits separat erfasst; Änderungen daran benötigen einen konkreten Befund.

Ein Main-Merge, Release oder lokaler Aufruf von `UPDATE_ALLIE.cmd` gehört nicht zu diesem bereits ausgeführten Auftragsschritt. Bis zur erforderlichen Abnahme bleibt der PR Draft. Alle Quelländerungen und Nachweise sind bereits vorhanden; es wird keine spätere automatische Fortsetzung behauptet.
