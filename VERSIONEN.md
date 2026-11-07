# Reproduzierbare Versionen und Prüfstand

Stand der Prüfung: 7. November 2026, Windows 11 x64. Abhängigkeiten sind in `pyproject.toml` direkt und in `uv.lock` vollständig festgelegt.

## Laufzeit

| Komponente | Festgelegt / geprüft |
|---|---:|
| uv | 0.13.7 |
| Python | 3.12.x; geprüft mit 3.12.10 |
| chess | 1.11.2 |
| FastAPI | 0.162.0 |
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

PyTorch 2.15.0 ist für die veröffentlichte Allie-2.1-CPU-Implementierung beibehalten; „neueste“ bedeutet hier die neueste gemeinsam praktisch geprüfte Kombination, nicht blind die höchste Einzelversion.

## Modell und Daten

- Modell: `yimingzhang/allie-2.1`
- Hugging-Face-Revision: `d2545701ff5af46a51ac947911844f779b355a08`
- Stockfish-Release: `sf_19`
- Stockfish-Archiv SHA-256: `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`
- Installierte `stockfish.exe` SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- `uv.lock` SHA-256 beim Abschluss: `fa989dd1714b2d7dcd26ec0f5acf4ac3728a5e6205491678410fd26a12dda4f5`

Gebündelte Lichess-Eröffnungsdaten:

| Datei | SHA-256 |
|---|---|
| a.tsv | `3282e4c9155289a29224f9a85fba0decb46efa35c2fa5e39662d2ac48fb0f793` |
| b.tsv | `2744a3890879bd9dce79093147fe5b6c3a9d9d42a3388af698e67b6829be1c48` |
| c.tsv | `447bbd4b15d68067b150faf12bf66aa14b18582cf80d736aaa7c0081131806ef` |
| d.tsv | `1cf4057a8aece94f27bb3f278ad410ee2844831a642364eeceaafa091dbcceda` |
| e.tsv | `48c6f6645b031a5937c8386839debab0e2e48837251687ba1afb6369677f8546` |

## Praktische Messungen auf diesem System

- 41 automatisierte Tests: 1,383 s, alle bestanden (2,086 s einschließlich Prozessstart).
- Stockfish über `python-chess`, drei Varianten, Rapid-Budget 1,1 s: erster Aufruf 2,159 s einschließlich Prozessstart; zweiter Aufruf mit derselben Engine 1,103 s.
- Allie CPU: Modellladen aus lokalem Cache 44,194 s; reale Inferenz nach `1. e4 e5 2. Nf3 Nc6` 6,960 s; fünf Züge und WDL geliefert.
- chessvision/ONNX: bedarfsgerechte Initialisierung 0,615 s.
- Viewer: lokaler Uvicorn-Start, sichtbarer v11-Status, Spielerfarbe, Empfehlungsschalter und echte PGN-Allie-Ausgabe im Browser geprüft.

Die Videoerkennung wurde bis zur echten Initialisierung und über den Frame-/Stabilitäts-Integrationstest geprüft. Ein externes Discord-Livevideo und eine reale Tampermonkey-Installation standen in der automatisierten Umgebung nicht zur Verfügung.
