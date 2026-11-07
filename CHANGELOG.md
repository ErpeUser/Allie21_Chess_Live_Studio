# Änderungen

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
