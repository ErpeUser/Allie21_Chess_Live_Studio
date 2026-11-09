# Reproduzierbare Versionen und Prüfstand

Stand der Prüfung: 8. November 2026, Windows 11 x64. Abhängigkeiten sind in `pyproject.toml` direkt und in `uv.lock` vollständig festgelegt.

## Aktueller Wiederaufnahme-Checkpoint (09.11.2026)

- Python-Regression: 97 Tests, OK, 1 Skip (`.allie-venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -q`).
- Browser-/Viewer-Regression: 9 Node-Fixtures, `node --check` für Userscript und Service Worker sowie Manifest-JSON-Prüfung, alles OK.
- PyInstaller-Onedir-Build: `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_exe.ps1`, Exitcode 0; EXE 2.625.829 Byte, portable Distribution 1.179.028.625 Byte (Runtime + App).
- Aktuelle SHA-256: EXE `C586212F51F5DDE26E6F3E6C94F7C8380116F47D37855D26E9EB44A7C3872DB5`, `base_library.zip` `7F191DB99D38A04974B52B0301E2B8B65BEEBE7597F02DC36FB7524271C9672E`, `uv.lock` `14E0820B55010B622C6416554E8FED84C45617B794D84769AB70C3BB94B7C990`.
- `tools\launcher.py --check` ist im Checkout OK und direkt aus dem portablen Release-Ordner ebenfalls OK. Die Distribution enthält `app` und `runtime`; der Runtime-Python importiert FastAPI/Chess/PIL, und der Server-Health-Smoke antwortet mit HTTP 200. Das Modell-Preload wurde für diesen Smoke deaktiviert; die Modellgewichte bleiben ein First-Run-Download in den lokalen Cache.
- Echte HWND-Affinitäts-/OBS-/getDisplayMedia-Proben sind in dieser Umgebung nicht verifiziert. Das private GitHub-Repository und Release `v11.2.16` sind unter `https://github.com/ErpeUser/Allie21_Chess_Live_Studio/releases/tag/v11.2.16` verifiziert.
- Optionaler Qualitätslauf: `tools\quality_check.ps1` installiert Ruff/Mypy/Pytest/Playwright in `.quality-venv`; Pytest 96 bestanden/1 übersprungen, Ruff 55 Befunde, Mypy 24 Befunde. Diese Lint-/Type-Befunde sind offen dokumentiert.

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
- Stockfish-Release: `sf_19`
- Stockfish-Archiv SHA-256: `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`
- Installierte `stockfish.exe` SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- `uv.lock` SHA-256 beim aktuellen Checkpoint: `14e0820b55010b622c6416554e8fed84c45617b794d84769ab70c3bb94b7c990`
- `release\Allie21 Chess Live Studio\Allie21 Chess Live Studio.exe` SHA-256: `4503a19743c76242ce3519066a9cd4e19d72abbcb40df4e103dd4789786df99b`

Gebündelte Lichess-Eröffnungsdaten:

| Datei | SHA-256 |
|---|---|
| a.tsv | `3282e4c9155289a29224f9a85fba0decb46efa35c2fa5e39662d2ac48fb0f793` |
| b.tsv | `2744a3890879bd9dce79093147fe5b6c3a9d9d42a3388af698e67b6829be1c48` |
| c.tsv | `447bbd4b15d68067b150faf12bf66aa14b18582cf80d736aaa7c0081131806ef` |
| d.tsv | `1cf4057a8aece94f27bb3f278ad410ee2844831a642364eeceaafa091dbcceda` |
| e.tsv | `48c6f6645b031a5937c8386839debab0e2e48837251687ba1afb6369677f8546` |

## Praktische Messungen auf diesem System

- 73 kurze automatisierte Tests, alle am 8. November 2026 bestanden.
- Chess.com-Spectator-Prüfung mit Spiel `186750736526`: 83 Halbzüge aus `moveList` dekodiert, 0 PGN-/Legalitätsfehler.
- Animations-Regressionsfall `1. g4 d5 2. f3 d4`: 4/4 Halbzüge bestätigt; warme Allie-Top-2-Antwort 1,756 s, vollständige Allie-/Stockfish-Vorschau mit Gegner-Top-2 und Pre-Move 1,984 s.
- Stockfish über `python-chess`, drei Varianten, Rapid-Budget 1,1 s: erster Aufruf 2,159 s einschließlich Prozessstart; zweiter Aufruf mit derselben Engine 1,103 s.
- Allie CPU nach Neustart: einmaliger Modell-Kaltstart 84,541 s; danach aktuelle Top-2-Auswahl 0,551 s und vollständige Allie-/Stockfish-Vorschau 1,576 s. Das Modell wird deshalb ab v11.1.1 direkt beim Programmstart im Hintergrund vorgeladen.
- chessvision/ONNX: bedarfsgerechte Initialisierung 0,615 s.
- Viewer: lokaler Uvicorn-Start, sichtbarer v11-Status, Spielerfarbe, Empfehlungsschalter und echte PGN-Allie-Ausgabe im Browser geprüft.
- Windows-EXE: 2.625.829 Byte; portabler App-Ordner-Starter mit mitgeliefertem Python 3.12. `--check`, Runtime-Imports und `/health` (HTTP 200) direkt aus dem Release-Ordner geprüft. Modell-Preload war für den Smoke deaktiviert.

Die Videoerkennung wurde bis zur echten Initialisierung und über den Frame-/Stabilitäts-Integrationstest geprüft. Die direkte entpackte Edge-Erweiterung wurde auf Chess.com sichtbar geladen; ihre lokale CORS-Verbindung und der Stockfish-Fallback wurden zusätzlich per echtem HTTP-Aufruf geprüft.
