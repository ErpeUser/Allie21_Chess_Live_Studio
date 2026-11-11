# Reproduzierbare Versionen und Prüfstand

## Update 11.2.19 / Edge-Erweiterung 11.2.19

Der aktuelle `main`-Stand verwendet für Anwendung, Userscript und WebExtension
den geprüften Stand 11.2.19; `browser/manifest.json` ist 11.2.19.0 mit
`version_name` 11.2.19.
Die feste Erweiterungs-ID bleibt unverändert.

Der nachfolgende Wartungsstand basiert auf Commit `13131c8` vom 10. November
2026. Historische Angaben zu `v11.2.16` beziehen sich auf den früheren Branch
`codex/allie-first-exe` und sind kein Nachweis für diesen `main`-Stand.

- Opening-Einstellungen werden in Viewer und Browser-GUI normalisiert, persistent gespeichert, an den Server gesendet und als angewandte Repertoire-Auswahl zurückgemeldet.
- Viewer-Einstellungen überleben Neustarts; der Browser-Port kann in der Erweiterungs-Optionsseite oder im Userscript gesetzt werden und muss mit `ALLIE_PORT` übereinstimmen.
- Pfeilspitzen enden geometrisch exakt in der Mitte des Zielfeldes. Der blaue Best-Premove verwendet denselben gemeinsamen Zeichenpfad.
- Native Overlay, Session-/Render-Gates, Request-Limits, CORS-Allowlist, Cache-Kanonisierung, Multi-PGN-Ablehnung und Stockfish-Hashprüfung sind gehärtet.

Stand der Prüfung: 9. November 2026. Abhängigkeiten sind in `pyproject.toml` direkt und im Remote-Branch zusätzlich in `uv.lock` festgelegt.

## Aktueller Prüfstand

- Overlay-Modi: Privatmodus mit verifizierter Windows-Capture-Exclusion und Share-Modus mit bewusst deaktivierter Exclusion; ein Browser-HUD wird im Privatmodus nie als Rückfall verwendet.
- Website, Userscript und Edge-Optionsseite verwenden den versionierten lokalen Overlay-Status; Viewer und Extension lösen veraltete Schreibvorgänge über Version/Zeitstempel auf.
- Die EXE startet Backend, Runtime, Modell und Stockfish über das Tray ohne sichtbares CMD-Fenster, verwendet eine gesunde eigene Instanz auf Port 8765 wieder und beendet keine fremden Listener.

- JavaScript: 10/10 Node-Fixtures bestanden; Userscript und Service-Worker bestehen `node --check`.
- Native-/Regression-Regressionen: 14 Tests ausgeführt, 12 bestanden, 2 wegen fehlendem globalem `python-chess` übersprungen. Die vollständige locked-Umgebung führt die chess-abhängigen Tests aus.
- Python-Syntax, `compileall`, YAML-Parsing und `git diff --check` bestanden.
- Locked-Quality-Lauf: `114 passed, 1 skipped` in Pytest, `115` Unittests OK / 1 Skip, Ruff 0 und Mypy 0.
- Portable Release-Binaries werden absichtlich nicht in Git versioniert; `tools/build_exe.ps1` erzeugt sie lokal und verifiziert Stockfish vor dem Packaging.
- Windows-HWND-Affinität, OBS/getDisplayMedia, echte Extension-Origin und ein vollständiger Stockfish-/EXE-Smoke bleiben manuelle Windows-Gates.

## Laufzeit

| Komponente | Festgelegt / geprüft |
|---|---:|
| uv | 0.13.7 |
| Python | 3.12.x; geprüft mit 3.12.10 |
| chess | 1.11.2 |
| chess-tcn | 1.0.1 |
| FastAPI | 0.162.2 |
| Pydantic | 2.14.3 |
| Uvicorn | 0.54.0 |
| Pillow | 13.0.0 |
| chessvision | 0.13.1 |
| NumPy | 2.5.4 |
| RapidOCR | 3.10.0 |
| ONNX Runtime | 1.31.1 |
| Transformers | 5.22.2 |
| PyTorch CPU | 2.15.0 |
| Stockfish | 19 |
| PyInstaller (nur EXE-Build) | 6.22.3 |
| pystray (nur EXE-Build) | 0.19.5 |

PyTorch 2.15.0 ist für die veröffentlichte Allie-2.1-CPU-Implementierung beibehalten; „neueste“ bedeutet hier die neueste gemeinsam praktisch geprüfte Kombination, nicht blind die höchste Einzelversion.

## Modell und Daten

- Modell: `yimingzhang/allie-2.1`
- Hugging-Face-Revision: `d2545701ff5af46a51ac947911844f779b355a08`
- Vendorter Allie-Code: `backend/vendor/allie_model`, SHA-256-Manifest geprüft; Modellstart offline sowie echte `analyze()`-/`predict()`-Aufrufe geprüft.
- Stockfish-Release: `sf_19`
- Stockfish-Archiv SHA-256: `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`
- Installierte `stockfish.exe` SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`


Gebündelte Lichess-Eröffnungsdaten:

| Datei | SHA-256 |
|---|---|
| a.tsv | `3282e4c9155289a29224f9a85fba0decb46efa35c2fa5e39662d2ac48fb0f793` |
| b.tsv | `2744a3890879bd9dce79093147fe5b6c3a9d9d42a3388af698e67b6829be1c48` |
| c.tsv | `447bbd4b15d68067b150faf12bf66aa14b18582cf80d736aaa7c0081131806ef` |
| d.tsv | `1cf4057a8aece94f27bb3f278ad410ee2844831a642364eeceaafa091dbcceda` |
| e.tsv | `48c6f6645b031a5937c8386839debab0e2e48837251687ba1afb6369677f8546` |

## Historische Messwerte aus dem vorherigen Prüfstand

Die folgenden Werte sind historische Messungen und keine aktuelle Release-Freigabe.

- Chess.com-Spectator-Prüfung mit Spiel `186750736526`: 83 Halbzüge aus `moveList` dekodiert, 0 PGN-/Legalitätsfehler.
- Animations-Regressionsfall `1. g4 d5 2. f3 d4`: 4/4 Halbzüge bestätigt; warme Allie-Top-2-Antwort 1,756 s, vollständige Allie-/Stockfish-Vorschau mit Gegner-Top-2 und Pre-Move 1,984 s.
- Stockfish über `python-chess`, drei Varianten, Rapid-Budget 1,1 s: erster Aufruf 2,159 s einschließlich Prozessstart; zweiter Aufruf mit derselben Engine 1,103 s.
- Allie CPU nach Neustart: einmaliger Modell-Kaltstart 84,541 s; danach aktuelle Top-2-Auswahl 0,551 s und vollständige Allie-/Stockfish-Vorschau 1,576 s. Das Modell wird deshalb ab v11.1.1 direkt beim Programmstart im Hintergrund vorgeladen.
- chessvision/ONNX: bedarfsgerechte Initialisierung 0,615 s.
- Viewer: lokaler Uvicorn-Start, sichtbarer v11-Status, Spielerfarbe, Empfehlungsschalter und echte PGN-Allie-Ausgabe im Browser geprüft.

Die Videoerkennung wurde bis zur echten Initialisierung und über den Frame-/Stabilitäts-Integrationstest geprüft. Die direkte entpackte Edge-Erweiterung wurde auf Chess.com sichtbar geladen; ihre lokale CORS-Verbindung und der Stockfish-Fallback wurden zusätzlich per echtem HTTP-Aufruf geprüft.

