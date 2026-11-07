# Änderungen

## v11.1.4

- Direkte Edge-Erweiterung ersetzt den fehleranfälligen Tampermonkey-Installationsweg.
- Eng begrenzte CORS-Freigabe für Chess.com und Lichess ergänzt.
- Bei fehlender vollständiger Historie startet nach eindeutig erkanntem Zug automatisch ein Stockfish-Fallback; Allie bleibt strikt an bestätigte Historie gebunden.
- Alte Browser-Kompatibilitätsschicht, wirkungslose Einstellungen, internes Plan-Dokument und unbenutzte `.venv` entfernt.

## v11.1.3

- Chess.com-Läufercodes wie `bb` werden nicht mehr als Springer gelesen (`Bb7` statt illegalem `Nb7`).
- Windows nutzt den unterstützten PyTorch-Pfad ohne erfolglosen Rust-Backend-Versuch und mit acht aktiven Experten für schnellere Blitz-Analysen.

## v11.1.2

- Veraltete Pfeile werden bei nicht eindeutig erkannten Brettwechseln sofort ausgeblendet.
- Chess.com-Zuglisten werden zusätzlich aus Buttons, Rollen und sortierten `data-ply`-Elementen gelesen.
- Standardprofil ist 5-Minuten-Blitz (`300+0`); DOM-Änderungen werden nach 120 ms verarbeitet.
- Das Overlay ist kleiner und zeigt nur die zwei wichtigsten Hinweise.

## v11.1.1

- Browser-Overlay zeigt die aktuelle Allie-Top-2-Auswahl sofort und ergänzt Gegner- sowie Pre-Move-Pfeile anschließend.
- Unbenutzte Allie-Vorschauzweige entfernt: maximal drei statt fünf Modellaufrufe pro vollständiger Live-Analyse.
- Allie-Modell wird beim Programmstart im Hintergrund vorgeladen.
- Automatisch eingeblendeten Textblock entfernt und Pfeile deutlich schlanker dargestellt.

## v11.1.0

- Allie-first-Pipeline: Allie ordnet menschlich wahrscheinliche Züge; Stockfish bewertet anschließend nur diese Kandidaten.
- Zwei parallele Live-Worker und die Ergebnis-Zusammenführung durch einen generation-gesicherten latest-only Auftrag ersetzt.
- Fünf Pfeilrollen in Viewer und Overlay exakt vereinheitlicht; sichere Pre-Move-Abdeckung bleibt Allie-basiert.
- Teure universelle DOM-Scans entfernt und alte Overlay-Anfragen bei Stellung oder Einstellung sofort abgebrochen.
- Funktionierende `Allie21 Chess Live Studio.exe` samt reproduzierbarem PyInstaller-Build ergänzt.
- Beschädigte alte `.venv` entfernt; Laufzeitumgebung eindeutig auf `.allie-venv` festgelegt.

## v11.0.0

- Eigenen HTTP-Handler durch FastAPI, Pydantic und Uvicorn ersetzt; lokale Bindung, Herkunftsprüfung und Größenlimits erhalten.
- Installation auf `pyproject.toml`, `uv.lock` und einen einzigen Doppelklickstarter reduziert.
- C#-Starter, PowerShell-Installationskette, zusätzliche BAT-Dateien, altes Requirements-Format und redundanten Öffnungs-Downloader entfernt.
- Allie auf die offizielle `analyze()`-/`predict()`-API mit deren Sortierung und Cache umgestellt; Modellrevision fest gepinnt.
- Eine Stockfish-Instanz und eine Allie-Instanz wiederverwendet; kombinierte Analyse parallelisiert; Videojobs auf die neueste Stellung begrenzt.
- `_merge_human`-Ausfall beseitigt und die Zusammenführung für beide Fertigstellungsreihenfolgen vereinheitlicht.
- Browser und Video auf gemeinsame Stellungs-/Analysekernlogik gebracht; Spielerfarbe von Brettorientierung getrennt.
- Rekonstruktion nicht beobachteter Eröffnungszüge entfernt. Allie erhält nur bestätigte vollständige Historien.
- Overlay auf Chess.com/Lichess begrenzt, ereignisgesteuert gebündelt und gegen veraltete Antworten abgesichert.
- Tests für Reihenfolge, Stoppen/Neustart, veraltete Antworten, fehlende Historie, HTTP-Grenzen und den neuen Startweg ergänzt.
