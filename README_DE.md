# Allie 2.1 Chess Live Studio v11

Lokale Windows-Anwendung für menschliche Zugprognosen mit Allie 2.1 und objektive Varianten mit Stockfish 19. Das Studio verarbeitet freigegebene Fenster, Browserbretter sowie vollständige PGN-Dateien. Es spielt und klickt nie selbst.

## Schnellstart unter Windows

1. Projekt vollständig entpacken.
2. `START_HIER.bat` doppelklicken.
3. Warten, bis `http://127.0.0.1:8765/viewer` geöffnet wird.

Der Starter installiert bei Bedarf den festgelegten Paketmanager `uv 0.13.7`, richtet Python 3.12 und alle Pakete aus `uv.lock` ein und lädt Stockfish 19 nur dann, wenn die Engine fehlt. Die Konsole zeigt verständliche Fehler und muss während der Nutzung geöffnet bleiben.

Das echte Allie-Modell wird erst bei der ersten PGN-Analyse geladen. Die Gewichte benötigen ungefähr 18,4 GB Speicherplatz; der CPU-Betrieb benötigt viel Arbeitsspeicher. Optional kann das Modell vorab mit folgendem Befehl geladen werden:

```powershell
uv run --frozen python backend/preload_allie.py
```

## Eingabewege

- **Video/Fenster:** Im Viewer „Quelle auswählen“ anklicken und in Chrome oder Edge ein sichtbares Discord-, Browser- oder Monitorfenster freigeben. `chessvision` und optional RapidOCR werden erst beim ersten Frame geladen.
- **Browser-Overlay:** Das Userscript aus dem Viewer installieren. Es unterstützt gezielt Chess.com und Lichess, beobachtet DOM-Änderungen gebündelt und sendet nur an den lokalen Dienst. Für Canvas-Bretter und andere Websites den Video- oder PGN-Weg verwenden.
- **PGN/FEN:** „PGN oder FEN ohne Stream analysieren“ öffnen. Nur eine vollständige, bestätigte Partiegeschichte ab der Startstellung wird an Allie übergeben. FEN allein wird ausschließlich mit Stockfish analysiert.

## Korrektheit und Anzeigen

- Rot: wahrscheinliche gegnerische Allie-Züge.
- Grün: eigene Allie-Empfehlungen.
- Blau: risikogewichteter Pre-Move, wenn aus den prognostizierten Varianten ableitbar.
- Stockfish bleibt eine getrennte objektive Textanalyse und erzeugt keine Allie-Ersatzpfeile.

Brettorientierung und Spielerfarbe sind getrennte Einstellungen. Bei einem Einstieg mitten in der Partie werden fehlende Züge, Rochaderechte und en-passant-Rechte nicht erfunden. Allie wartet auf eine vollständige PGN; Stockfish kann eine ausdrücklich gelieferte FEN dennoch analysieren.

Die einheitliche Zeitklasse verwendet `Grundzeit + 40 × Inkrement`:

- unter 180 s: Bullet, Stockfish 0,25 s
- unter 600 s: Blitz, Stockfish 0,65 s
- unter 1.800 s: Rapid, Stockfish 1,1 s
- ab 1.800 s: Classical, Stockfish 2,0 s

## Einstellungen

Die Standardwerte stehen in `config.json`. Wichtige Felder sind `white_elo`, `black_elo`, `player_side`, `time_control`, `recognition_interval_ms`, `stability_frames`, `ocr_history`, `stockfish_threads` und `stockfish_hash_mb`. Modellkennung und Modellrevision sind absichtlich festgelegt.

Der Schalter „Live-Zugpfeile & Empfehlungen“ verwirft sofort laufende Ergebnisse. Nach Stellungs-, Einstellungs- oder Sitzungswechseln akzeptiert die Pipeline nur Antworten der aktuellen Generation.

## Tests und Diagnose

```powershell
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python backend/doctor.py
```

Der Server bindet ausschließlich an `127.0.0.1`, prüft Host und Herkunft, begrenzt JSON und JPEG-Größen und speichert keine Videoframes. Exakte geprüfte Versionen, Modellrevisionen, Hashes und Messwerte stehen in `VERSIONEN.md`; Lizenzen in `QUELLEN_LIZENZEN.md`.

## Grenzen

Videoerkennung hängt von Größe, Design, Kompression und Sichtbarkeit des Brettes ab. Das Originalfenster wird nicht verändert; Pfeile erscheinen im Viewer oder im optionalen Overlay. Das Allie-Modell vertraut dem offiziellen Repository-Code über `trust_remote_code=True`; die verwendete Revision ist deshalb fest gepinnt.
