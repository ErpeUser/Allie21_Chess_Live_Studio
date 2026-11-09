# Allie21 Chess Live Studio v11 – Ist-Aufnahme (TEIL K)

Stand der Prüfung: 09.11.2026, Arbeitsbaum `codex/allie-first-exe`, Commit `59463bd`.
Dieser Bericht beschreibt den tatsächlich vorliegenden Code. Die vom Nutzer angehängte
Datei liegt außerhalb des beschreibbaren Projektordners; dieser Bericht ist deshalb die
ausführbare Kopie des geforderten TEIL-K-Ergebnisses. Es wurden keine Projektdateien für
diese Bestandsaufnahme verändert.

## K1 – Projekt- und Laufzeitbestand

Projektwurzel: `C:\Users\User\Desktop\Allie21_Chess_Live_Studio_v10`.

| Bereich | Tatsächliche Dateien | Aufgabe |
|---|---|---|
| Backend | `backend/live_server.py` | FastAPI/Uvicorn, HTTP-Grenze, CORS/Host-/Größenprüfung, Viewer- und Userscript-Routen |
| Backend | `backend/live_session.py` | Video-Worker, neueste Analyse, Generationen gegen veraltete Ergebnisse |
| Backend | `backend/position_tracker.py`, `browser_session.py` | legale Brettübergänge, History-Rekonstruktion und Sitzungen |
| Backend | `allie_local_server.py` | Allie-Laden, PGN/FEN-Validierung, Top-k, Gegner-Vorschau, Pre-Move, Hinweise |
| Backend | `chess_extras.py` | Eröffnungsindex, Repertoire, python-chess- und Stockfish-Helfer, Kurztexte |
| Backend | `config.py` | einzige Zeitkontroll-/Konfigurationsvalidierung, Modell-ID und Revision |
| Backend | `vision.py` | optionales Chessvision/ONNX-Brett und OCR, bedarfsgerecht beim ersten Videoframe |
| Backend | `doctor.py`, `download_stockfish.py` | Diagnose bzw. Download des festgelegten Stockfish-Archivs |
| Daten | `backend/openings/a.tsv` … `e.tsv` | gebündelte Lichess-Opening-Daten; `beispiele/italienisch_1950.pgn` ist Test-/Beispieldatei |
| Browser | `browser/allie21_overlay.user.js` | Chess.com-/Lichess-Adapter, DOM-Brett, Figuren, Orientierung, History, SVG-Pfeile, Polling |
| Browser | `browser/manifest.json` | Manifest-V3-Entpackt-Erweiterung für Chess.com und Lichess |
| Oberfläche | `viewer/index.html` | lokale Kamera-/Fenster-/Tab-Aufnahme über Browser MediaDevices, Status, Einstellungen, SVG-Pfeile, Analyseblase |
| Start/EXE | `START_HIER.bat`, `EDGE_OVERLAY_INSTALLIEREN.bat`, `tools/launcher.py`, `tools/build_exe.ps1` | reproduzierbarer uv-Start, Erweiterungsinstallation, Windows-Tray-Starter und PyInstaller-Build |
| Tests/Doku | `tests/*.py`, `tests/*.js`, `README_DE.md`, `CHANGELOG.md`, `VERSIONEN.md`, `QUELLEN_LIZENZEN.md` | Offline-/HTTP-/Overlay-Tests, Bedien- und Reproduzierbarkeitsnachweise |

Ausgeschlossene Arbeitsartefakte: `.allie-venv`, `.uv-cache`, `.uv-tools`, `.build`,
`release` und `.git` sind erzeugte Umgebung bzw. Versionsverwaltung, keine Quellmodule.
Eine Datei `tests/test_overlay_dom.js`, die in einem früheren Aufruf erwartet wurde,
existiert nicht; die vorhandenen JavaScript-Tests sind die fünf `test_overlay_*.js`-Dateien.

## K2 – Architektur und Datenfluss

```mermaid
flowchart LR
  A[START_HIER.bat oder EXE-Tray] --> B[uv/venv + Uvicorn]
  B --> C[FastAPI live_server]
  C --> D[viewer/index.html]
  C --> E[userscript / Manifest-V3]
  E --> F[Chess.com/Lichess DOM]
  F --> G[placement + Site-History/TCN]
  G --> H[BrowserTrackerPool/PositionTracker]
  D --> I[MediaDevices JPEG]
  I --> J[BoardVision optional]
  J --> K[LiveSession]
  H --> L[/api/browser-position]
  L --> M[/analyze]
  K --> M
  M --> N[python-chess validiert PGN/FEN]
  N --> O[Allie 2.1 analyze/predict]
  N --> P[Stockfish UCI ergänzend]
  O --> Q[Top-k, Gegnerzweige, Pre-Move, Hinweise]
  P --> Q
  Q --> R[JSON-State]
  R --> D
  R --> E
```

Beim Programmstart wird das Allie-Modell in einem Hintergrundthread vorgeladen und mit
der Standardstellung gewärmt. Eine globale RLock schützt Modellzugriffe. Stockfish wird
einmalig über python-chess gestartet und wiederverwendet. `LiveSession` besitzt genau
einen Analyse-Worker und ersetzt wartende Jobs durch den neuesten Job. `generation` und
`session_id` verhindern, dass Antworten nach Stoppen, Neustart oder Stellungswechsel
noch veröffentlicht werden.

## K3 – Analyse- und Schachlogik

`allie_local_server.parse_history` akzeptiert Standard-PGN sowie legale SAN/UCI-Züge ab
der Ausgangsstellung. Es verwirft keine fehlenden Züge und erfindet keine Rochade- oder
En-passant-Rechte. FEN ist für Stockfish zulässig; Allie wird bei FEN-only ausdrücklich
übersprungen, weil die vollständige Geschichte fehlt. Varianten außer Standard-Chess und
ungültige/zu lange PGN werden abgelehnt.

`analyse_position` ruft Allie mit `analyze(moves, white_elo, black_elo, time_control,
clocks)` auf. Die API-Reihenfolge bleibt unverändert; die ersten fünf legal geprüften
Kandidaten sind die Allie-Top-k. `predict()` wird nur für die nötigen Gegnerzweige
aufgerufen. Bei `analysis_source=both` ordnet Stockfish Allie nicht um, sondern liefert
objektive Vergleichslinien. `safe_aggressive_order` lässt aggressiven Druck nur innerhalb
eines Sicherheitsabstands zu. `risk_weighted_premove` gewichtet Allie-Wahrscheinlichkeit
und Zweigabdeckung; Stockfish ersetzt fehlende Allie-Zweige nicht.

Pfeilrollen sind in `browser/allie21_overlay.user.js` und `viewer/index.html` identisch:
Starkgrün `#16c784` eigener Top-1, Hellgrün `#7ee2b8` eigener Top-2, Starkrot
`#ef3340` Gegner Top-1, Hellrot `#ff9299` Gegner Top-2, Blau `#2f80ed` sicherer
Pre-Move. `drawArrows` zeichnet nur, wenn Ergebnis-FEN und aktuelle Detektions-FEN
identisch sind; Reset/Stop/Settings löschen SVG und Bubble.

## K4 – Browser-Erkennung und Grenzen

Der Userscript-Adapter wird nur auf `*.chess.com` und `lichess.org` injiziert. Er sucht
gezielt nach den site-eigenen Brettcontainern, liest CSS-/DOM-Figuren, `data-*`-/Klassen-
Felder, Zuglisten und Koordinaten und trennt Brettorientierung von Spielerfarbe. Ein
`MutationObserver`/gebündeltes Polling wartet auf stabile DOM-Frames. Chess.com-TCN und
der Callback `callback/live/game/<id>` werden als zusätzliche History-Kandidaten genutzt;
Lichess-Zuglisten werden direkt aus dem DOM übernommen. Die sichtbare Stellung wird nur
akzeptiert, wenn beide Könige vorhanden sind und ein legaler Übergang bzw. bestätigte
History passt. Bei einem unaufgelösten Sprung werden Pfeile ausgeblendet statt Züge zu
erfinden.

Implementiert: Chess.com Live- und Spectator-Seiten, Lichess-Bretter, Standardstellung,
automatische Orientierung/Farbableitung, manueller PGN-Import im Viewer. Teilweise:
virtuelle/animierte Zuglisten benötigen einen stabilen Frame; Start mitten in einer
Partie kennt Rochaderechte und En-passant oft nicht. Nicht implementiert: automatische
DOM-Erkennung beliebiger Drittseiten, Discord/Twitch/YouTube als DOM-Brett und OCR- bzw.
Bildschirmanalyse ohne die optionale Vision-Installation. Der Viewer kann solche Quellen
als Browser-Tab/Fenster aufnehmen, aber die Erkennung hängt dann von Chessvision/OCR und
stabilen Bildern ab.

## K5 – HTTP- und Sicherheitsgrenze

FastAPI/Pydantic validieren Typen, Zeitkontrolle, Elo, Größen und erlaubte Felder
(`extra="forbid"`). Uvicorn bindet ausschließlich `127.0.0.1:8765`. Middleware prüft
Host, erlaubte Origins (localhost, Chess.com, Lichess bzw. explizite Extension mit
`X-Allie-Overlay: 1`), POST-Größen (JSON 64 KiB, JPEG 3,5 MB) und setzt CSP,
`nosniff`, `DENY`, No-Store und Referrer-Policy. Öffentliche Chess.com-/Lichess-APIs
werden nicht als Authentifizierungs- oder Schreibschnittstelle verwendet.

## K6 – Versionen und Modelle

Festgelegt in `pyproject.toml`/`uv.lock`: Python 3.12.x, uv 0.13.7, chess 1.11.2,
chess-tcn 1.0.1, FastAPI 0.162.2, Pydantic 2.14.3, Uvicorn 0.54.0, Pillow 13.0.0,
PyTorch 2.15.0, Transformers 5.22.2. Optional: chessvision 0.13.1, NumPy 2.5.4,
ONNX Runtime 1.31.1, RapidOCR 3.10.0. EXE-Build: PyInstaller 6.22.3, pystray 0.19.5.
Allie: `yimingzhang/allie-2.1`, Hugging-Face-Revision
`d2545701ff5af46a51ac947911844f779b355a08`, Windows nutzt den Torch-Backend statt des
Linux-only Rust-Fast-Backends. Stockfish ist Release 19 (`sf_19`) und wird via UCI/
python-chess angesprochen. Alle Versionen und SHA-256 stehen in `VERSIONEN.md`.

## K7 – Verifiziertes Fehlerbild und Korrekturen

Der konkrete Fehler `opening_black: Extra inputs are not permitted` war real: der
Userscript-Request enthielt Eröffnungsfelder, während `AnalysisRequest` sie nicht
modellierte. Commit `59463bd` ergänzt die erlaubten Literale für Weiß/Schwarz; der
Regressionstest `test_analysis_accepts_opening_selection` besteht. Zusätzlich werden
Start/Stop, kürzere neue Partien, unmatched boards, fehlende History, aggressive
Sicherheitsmarge und Stale-Analyse in `tests/test_chess.py`/`test_offline.py` geprüft.

Offene technische Grenzen sind keine verschwiegenen Fehler: optionale OCR/ONNX-Echt-
Erkennung wurde nur initialisiert und über Integrationstests geprüft, nicht für jede
Drittseite; das Modell ist CPU-speicherintensiv; eine vollständige p50/p95-Messreihe für
jedes Zielsystem liegt nicht vor. Die fünf vorhandenen Overlay-JavaScript-Testdateien
bestätigen Adapter, Orientierung, Insights, Startstellung und Reset/Stil.

## K8 – Tests und Messwerte

Am 09.11.2026 lokal ausgeführt: `python -m unittest discover -s tests -p test_*.py` →
**78 Tests in 1,981 s, OK**. Die Ausgabe enthält zwei absichtlich erzeugte Warnfälle
für ungültige Test-Konfigurationen; sie sind erwartetes Verhalten. Alle fünf Node-
Overlaytests bestanden. Der laufende Server antwortete:

```json
{"alive":true,"model":"yimingzhang/allie-2.1","model_revision":"d2545701ff5af46a51ac947911844f779b355a08","model_loaded":true,"stockfish_available":true}
```

Dokumentierte Praxiswerte in `VERSIONEN.md`: Allie-Kaltstart ca. 84,541 s, warme Top-2-
Auswahl ca. 0,551 s, vollständige Allie/Stockfish-Vorschau ca. 1,576 s; Stockfish
zweiter Aufruf ca. 1,103 s; Chess.com-Spectator-Test 83 Halbzüge ohne PGN-/Legalitäts-
fehler; EXE-`--check` Exitcode 0 in ca. 396 ms. Diese Werte sind Einzelmessungen, keine
Garantie für andere Hardware.

## K9 – Windows-Start und Artefakte

`START_HIER.bat` setzt Projektpfad und Cache, führt `uv sync --frozen --all-extras
--no-dev` aus, lädt bei Bedarf Stockfish und startet Uvicorn. `tools/launcher.py` wird
als PyInstaller-Onedir/Windowed-EXE gebaut, erstellt ein Tray-Symbol mit „Allie öffnen"
und „Allie beenden" und beendet nur den eigenen Prozessbaum. Die geprüfte EXE liegt in
`release\Allie21 Chess Live Studio\Allie21 Chess Live Studio.exe`.

## K10 – Gesamturteil

Vollständig verifiziert: lokaler FastAPI-Server, Allie-Preload und Cache, Stockfish-
Fallback/Ergänzung, legale PGN-/FEN-Prüfung, Chess.com-/Lichess-Overlaypfad, farbige
Pfeile, Analyseblase, Reset-/Stale-Schutz, Start/Stop, Opening-Auswahl, Tray-EXE und
Offline-Regressionssuite. Teilweise verifiziert: echte Video-/OCR-Erkennung und
animierte/virtuelle Bretter. Nicht vorhanden: universelle automatische Brett- und
History-Erkennung auf beliebigen Websites oder Livestream-Plattformen.

Aktuelle Hashes: EXE
`649dbf4810677c2bfb8a69fbb7e34599d5f739dac89adf6f49c0913049311b7a`, `uv.lock`
`c88069bfa715eb51d28989177a93122002c82e20391b88b9a008a671050a97f3`. Der Arbeitsbaum
ist sauber; die letzten Commits sind `40f7cc4` (Theme/Opening-Auswahl) und `59463bd`
(Opening-Request-Fix).

## K11 – Vollständige Ablaufbeschreibung vom Start bis zum Pfeil

### 1. Prozessstart

1. Beim Doppelklick auf `release\Allie21 Chess Live Studio\Allie21 Chess Live
   Studio.exe` startet PyInstaller `tools/launcher.py` im Windows-Tray.
2. `project_root()` sucht den Projektordner anhand von `START_HIER.bat`,
   `pyproject.toml`, `uv.lock` und `backend/live_server.py`. Fehlt eine Datei,
   erscheint eine Windows-Fehlermeldung und der Launcher beendet sich.
3. `TrayApp.start()` startet genau `cmd.exe /d /c START_HIER.bat` mit neuem
   Konsolenfenster. `START_HIER.bat` setzt Arbeitsordner und `UV_CACHE_DIR`, prüft
   uv, synchronisiert die eingefrorene Umgebung, lädt optional Stockfish und ruft
   `uv run --frozen python backend/live_server.py` auf.
4. `live_server.main()` startet den Allie-Preload-Thread, öffnet nach etwa einer
   Sekunde `/viewer` und bindet Uvicorn an `127.0.0.1:8765`. Im `finally` wird
   `SESSION.stop()` aufgerufen.
5. `get_model()` lädt exakt `yimingzhang/allie-2.1` an der festgelegten Revision.
   Das Modell bleibt global in `_model`; `_model_lock` serialisiert Zugriffe.
   Die Startstellung wird durch `_preload_model()` einmal analysiert. Der optionale
   Vision-Stack wird dagegen erst beim ersten Videoframe instanziiert.

### 2. Viewer-/Overlay-Auswahl

Der Viewer lädt HTML über `GET /viewer`; der Server ersetzt `__ALLIE_CONFIG__` durch
validierte JSON-Konfiguration. Der Viewer startet keine eigene Engine. Er sendet nur
JPEG-Snapshots an `/api/frame`, liest JSON-Zustand aus der Antwort und zeichnet SVG.
Die Bildschirmfreigabe erfolgt ausschließlich über `navigator.mediaDevices.getDisplayMedia`
(Fenster/Tab/Monitor); es gibt keine Mausautomation und keinen Upload zu einem fremden
Server.

Das Browser-Userscript läuft direkt auf Chess.com/Lichess. Es besitzt eine eigene
Browser-Session-ID, liest DOM-Snapshots und sendet an `/api/browser-position`. Es
zeichnet direkt im Seiten-DOM bzw. in einer über dem Brett positionierten SVG-Schicht.
Beide Clients teilen die HTTP-Analysepipeline, aber nicht denselben visuellen
Erkennungscode: der Viewer nutzt BoardVision/OCR, der Overlay-Adapter Plattform-DOM.

### 3. Erkennung und Normalisierung

**Overlay:** `readBoardSnapshot()` findet das sichtbare Brett, ordnet Felder anhand von
Koordinaten und CSS-/`data-piece`-Informationen zu und liefert mindestens
`placement`, `orientation`, `board`/`box` und Plattformmarker. Ghost-/Fading-Figuren
werden bei den Plattformadaptern herausgefiltert. `detectedPlayerSide()` trennt die
eigene Farbe vom Brettflip; ein manueller Wert hat Vorrang, `auto` nutzt Plattformmarker
oder die sichtbare Seite als kontrollierten Fallback.

**Video:** `BoardVision.recognize()` gibt eine erkannte Figurenbelegung, Box,
Konfidenz und Bildgröße zurück. `LiveSession.submit_frame()` akzeptiert nur JPEGs bis
3,5 MB und 200–2200 Pixeln. Eine neue placement wird zunächst als „wird bestätigt“
markiert; `config.stability_frames` (aktuell 2) muss erfüllt sein. Nach vier nicht
zuordenbaren Sprüngen wird die Historie verworfen und die Stellung als unbekannt neu
initialisiert. OCR läuft außerhalb des Locks und wird nur genutzt, wenn noch keine
komplette History vorliegt.

### 4. History-Rekonstruktion und rechtlicher Schachzustand

`PositionTracker` führt `board`, `moves`, `complete_history`, `turn_verified` und
`history_origin`. Aufeinanderfolgende sichtbare Platzierungen werden nur über legale
python-chess-Übergänge verbunden. `set_notation()` akzeptiert nur eine vollständige
legale PGN ab der Standardstellung, die zur beobachteten Platzierung passt. Wird die
Ausgangsstellung erkannt, beginnt der Tracker mit `*`; ein späterer legaler Zug macht
das Zugrecht überprüfbar.

Eine reine Platzierung enthält weder zuverlässiges Zugrecht noch Rochaderechte,
En-passant-Feld, Halbzugzähler oder Zugnummer. Deshalb wird bei unvollständiger History
kein Allie-PGN erfunden. Das Backend verwendet dann kontrolliert FEN nur für Stockfish,
setzt `history_complete=false` und schreibt den Unsicherheitshinweis in das Ergebnis.
Bei kompletter PGN werden alle Halbzüge samt Uhrinformationen an Allie weitergegeben.

### 5. Backend-Anfragen

| Endpoint | Eingabe | Ergebnis |
|---|---|---|
| `POST /api/start` | Elo, `player_side`, Zeitkontrolle, OCR-/Empfehlungsschalter | neue `LiveSession`, Generation/Tracker/Detector zurückgesetzt |
| `POST /api/frame` | `Content-Type: image/jpeg`, max. 3,5 MB | Erkennung, Trackerstatus, ggf. Analysezustand |
| `POST /api/history` | vollständiger PGN | PGN-Import gegen sichtbares Brett |
| `POST /api/browser-position` | `session_id`, `placement`, PGN-Kandidaten, optional TCN/`game_id` | `ready`, `fallback_ready`, FEN/PGN, Historyquelle |
| `POST /api/browser-position/reset` | `session_id` | Browser-Tracker entfernt |
| `POST /analyze` | PGN oder FEN, nie beides, Spielstil, Opening-Felder | Allie-/Stockfish-Ergebnis |
| `GET /api/state` | keine | aktueller Viewer-State |
| `POST /api/stop` | keine | idempotenter Stop und Löschung sichtbarer Ergebnisse |

`live_server` prüft vor jeder Route Host, Origin, Content-Length und Pydantic-Felder.
Ein unbekanntes Feld wie der frühere `opening_black`-Fehler wird seit Commit
`59463bd` nicht mehr abgelehnt, weil beide Opening-Felder Bestandteil von
`AnalysisRequest` sind.

### 6. Analyse-Orchestrierung

`LiveSession._queue_locked()` entscheidet anhand der History: vollständige PGN führt zu
`analysis_source='both'`, unvollständige FEN ausschließlich zu `stockfish`. Pro Stellung
existiert maximal ein wartender Job. Vor dem Einreihen werden Ergebnis und
`analysing`-Status geleert; `generation` steigt monoton.

Im Worker wird `analyse_position(payload)` außerhalb des Session-Locks ausgeführt. Beim
Zurückschreiben muss `running` noch wahr und die lokale Job-Revision identisch mit der
aktuellen Generation sein. Sonst wird das Ergebnis ohne UI-Nebenwirkung verworfen.
Damit blockiert eine alte Allie-/Stockfish-Antwort nicht die neue Stellung und zeichnet
keine alten Pfeile.

`analyse_position()` validiert zunächst Eingabetypen, PGN/FEN-Ausschluss, Standardvariante,
Legalität, Elo, Zeitklasse und Endstellung. Danach:

1. Opening-Index und Position-Facts werden bestimmt.
2. Allie `analyze()` liefert die menschlich wahrscheinlichsten Züge. Die API-Reihenfolge
   bleibt maßgeblich; es werden keine Wahrscheinlichkeiten neu sortiert.
3. Die ersten fünf Kandidaten werden mit python-chess legal geprüft, in SAN umgewandelt
   und mit Schlagzug/Schach/Matt/Patt-Flags versehen.
4. Für die tatsächlich eigene Seite wird optional der gewählte Spielstil angewandt.
   Im aggressiven Stil priorisiert `rank_allie_candidates()` legalen Mattdruck, Schach,
   Königseinschränkung und Wahrscheinlichkeit; `safe_aggressive_order()` verhindert,
   dass ein klar verlorenes Allie-Manöver als sichere Empfehlung erscheint.
5. Für die nötigen Kandidaten wird Allie `predict()` auf der Folgeposition aufgerufen.
   Bei eigenem Zug wird nur der wahrscheinlichste eigene Kandidat weiterverfolgt, um
   doppelte Inferenz zu vermeiden; bei gegnerischem Zug werden die zwei sichtbaren
   eigenen Kandidaten betrachtet.
6. Stockfish wird über python-chess/UCI mit Threads, Hash und einem Zeitbudget der
   zentralen `time_profile()` angesprochen. Er bewertet Varianten objektiv, ersetzt
   aber im `both`-Modus nicht Allies Reihenfolge.
7. `risk_weighted_premove()` verbindet Allie-Wahrscheinlichkeit und Abdeckung über
   wahrscheinliche Gegnerzweige. `make_plan_messages()` erzeugt Opening-, Stellungs-,
   Gegnerabsichts-, Gefahren- und Pre-Move-Hinweise.

### 7. Ergebnis bis zum sichtbaren Pfeil

Das JSON enthält unter anderem `fen`, `my_moves`, `opponent_moves`, `premove`, `brief`,
`plan_messages`, `opening`, `position_facts`, `stockfish`, `history_complete` und bei
Problemen `allie_skip_reason`. Der Viewer akzeptiert ein Resultat nur, wenn
`result.fen === detection.fen`. Das Userscript besitzt zusätzlich `analysisSerial`,
`analysisKey`, `lastPGN` und prüft, ob die Seite noch am Ende derselben History steht.

`drawArrows()` leert vor jeder Darstellung das SVG und verwirft unpassende/ungültige
UCI-Züge. Es projiziert UCI von der kanonischen weißen Perspektive auf die erkannte
Brettorientierung, verkürzt die Enden innerhalb des Feldes und zeichnet Linie plus
Pfeilspitze. Ein Reload, `/api/stop`, Session-Reset, Settings-Wechsel, fehlende
Stabilität, Endstellung oder FEN-Mismatch ruft `clearOverlay()`/`replaceChildren()` auf.
Die Analyseblase wird aus maximal vier `plan_messages` neben dem Brett positioniert;
bei fehlender aktueller Erkennung oder ohne Hinweise ist sie verborgen.

## K12 – Konkrete Ablaufbeispiele

### Chess.com-Livepartie

Der Adapter erkennt die Chess.com-Brettinstanz, liest Figuren-/Orientierungsdaten und
die sichtbare Zugliste. Bei Spiel-ID wird zusätzlich serverseitig der Chess.com-
Callback geladen und TCN mit `chess_tcn.tcn_to_pgn()` dekodiert. Stimmen Kandidat und
Platzierung überein, meldet `/api/browser-position` `ready=true`; danach folgt `/analyze`
mit vollständiger PGN. Bei Animation, fehlender History oder nicht eindeutigem
Brettwechsel bleiben Pfeile verborgen.

### Lichess-Livepartie

Der Adapter liest Chessground-nahe DOM-/Koordinateninformationen und den sichtbaren
Move-List-Text. Die vollständige serverseitige Spiel-API ist nicht erforderlich. Sind
History und Stellung konsistent, läuft derselbe Allie-first-Pfad wie bei Chess.com.
Bei einem bloßen Figuren-Snapshot bleiben vollständige FEN-Rechte unbekannt und es gibt
nur den kontrollierten Stockfish-Fallback.

### Chess.com-Spectator/Archiv

Die virtuelle Zugliste wird über `game_id`/Callback ergänzt. Navigation oder ein kürzeres
neues Spiel erzeugt über `browser-position/reset` bzw. die Session-Logik eine neue
Zustandszuordnung. Ein historisch nachgewiesener Test mit Spiel-ID `186750736526`
dekodierte 83 Halbzüge ohne Legalitätsfehler. Das ist ein verifizierter Einzelfall, kein
Beweis für jede spätere Website-Struktur.

### Unbekannte Website, Discord, Twitch oder YouTube

Es gibt keinen DOM-Adapter für diese Seiten. Der Benutzer kann den Tab/Fensterinhalt im
Viewer freigeben; BoardVision versucht dann ein Bildbrett zu erkennen. Ohne stabile
Figuren, vollständige Zugliste und bestätigtes Zugrecht meldet die Anwendung Unsicherheit
und unterdrückt Pfeile. Eine universelle automatische History-Erkennung ist nicht
implementiert.

### Manuell geladene PGN

Der PGN wird über `/analyze` oder `/api/history` eingelesen. python-chess prüft Start-
stellung, Variantenart, Legalität und Endstatus. Bei laufender Partie berechnet Allie
die menschlich wahrscheinlichsten Top-k-Züge; Stockfish liefert Vergleichslinien. Bei
beendeter Partie wird nur mit `review_finished=true` die Entscheidung vor dem letzten
Zug analysiert; ansonsten wird kein veralteter Pfeil erzeugt.

## K13 – Zustands-/Fehlermatrix

| Ereignis | interne Reaktion | Anzeige |
|---|---|---|
| neue Session/„Jetzt analysieren“ | Generation/Session erhöhen, Tracker/Resultat leeren | Analyse wartet auf aktuelles Brett |
| neuer stabiler legaler Zug | Tracker aktualisieren, neuester Job ersetzt alten | alte Pfeile weg, Analyse läuft |
| unbekannter Sprung | Generation erhöhen, Job verwerfen | „Stellungswechsel nicht eindeutig“ |
| vier unzuordenbare Frames | Tracker neu synchronisieren, History unbekannt | nur sicherer FEN-Stockfish-Fallback |
| Stop/Reload | Job, Resultat, SVG und Bubble löschen | gestoppt bzw. neue Session |
| Matt/Patt/Remis | keine weitere Live-Empfehlung für Endstellung | keine alten Pfeile |
| Server/Modell nicht erreichbar | HTTP-/Analysefehler im Status | verständliche Fehlermeldung, kein Fake-Ergebnis |
| fehlende Allie-History | Allie übersprungen | Stockfish-Hinweis mit Unsicherheit |

## K14 – Ehrliche Restunsicherheiten

Nicht aus dem Repository belegbar sind eine vollständige p50/p95-Latenzverteilung auf
mehreren Rechnern, ein Test jeder aktuellen Chess.com-/Lichess-DOM-Variante, ein
vollständiger Windows-Ab-/Anmeldezyklus und eine robuste Erkennung beliebiger
Livestream-Overlays. Die vorhandenen Einzelmessungen, Offline-Fixtures und der laufende
Health-Check belegen die oben genannten Pfade, ersetzen diese fehlenden End-to-End-
Szenarien aber nicht.

## K15 – Zentraler Funktionskatalog mit Aufrufkette

Die folgenden Einträge sind die für die Pipeline relevanten, tatsächlich vorhandenen
Methoden (Zeilennummern beziehen sich auf den geprüften Stand; kleine UI-Helfer sind
zusammengefasst).

| Datei / Zeile | Funktion/Klasse | Eingabe → Ausgabe | Nebenwirkung / Aufrufer |
|---|---|---|---|
| `live_server.py:48–70` | `_preload_model`, `start_model_preload` | keine → Thread | lädt Allie und wärmt Startposition; `main()` |
| `live_server.py:74–113` | `InputModel`, `StartRequest`, `AnalysisRequest` | JSON → validiertes Pydantic-Modell | unbekannte Felder/ungültige Werte werden 400 |
| `live_server.py:127–155` | `_fetch_chesscom_tcn` | Spiel-ID → TCN/leer | 1,2-s-LRU-ähnlicher Cache, max. 32 IDs |
| `live_server.py:160–216` | `local_boundary` | HTTP Request → Response | Host/Origin/Größe/CSP; vor jeder Route |
| `live_server.py:262–309` | `analyze`, `start`, `stop`, `frame`, `history`, `recommendations`, `browser_position`, `reset_browser_position` | JSON/JPEG → JSON | verbindet HTTP mit Analyse-, Video- und Browser-Sessions |
| `allie_local_server.py:31–47` | `get_model` | keine → globales Allie-Modell | einmaliger HF-Ladevorgang, Lock |
| `allie_local_server.py:50–94` | `parse_history`, `describe_move` | PGN/SAN/UCI + UCI → Board/Kandidaten | python-chess-Legalitätsprüfung |
| `allie_local_server.py:125–188` | `rank_allie_candidates`, `safe_aggressive_order` | Allie-Kandidaten/Stockfish → geordnete Kandidaten | Stilfilter, Sicherheitsabstand |
| `allie_local_server.py:190–224` | `risk_weighted_premove` | gewichtete Antwortzweige → ein Pre-Move | Allie-Wahrscheinlichkeit, Abdeckungs-/Risikowert |
| `allie_local_server.py:227–285` | `make_plan_messages` | Ergebnis → maximal sechs Hinweise | Opening-, Gefahr-, Verhaltenstexte |
| `allie_local_server.py:287–472` | `analyse_position` | AnalyseRequest → vollständiges JSON | Allie `analyze/predict`, Stockfish, Ergebniszusammenführung |
| `chess_extras.py:41–68` | `standard_repertoire`, `repertoire_move_for` | Seite/Auswahl/History → Repertoire-Move | Opening-Wunsch wird nur bei legalem Match bevorzugt |
| `chess_extras.py:70–177` | `opening_for_position`, `opening_note`, `position_facts` | Board/History → Opening/Fakten | nutzt gebündelte Opening-Daten |
| `chess_extras.py:218–318` | `find_stockfish`, `_get_stockfish`, `stockfish_lines` | Konfiguration/Board → UCI-Linien | Engine-Prozess und MultiPV-Limits |
| `position_tracker.py:21–177` | `PositionTracker.reset`, `set_notation`, `observe`, `current_fen` | PGN/FEN-Snapshots → `Change`/FEN | rekonstruiert nur legale Übergänge; markiert History-Unsicherheit |
| `browser_session.py:20–86` | `BrowserTrackerPool.observe/reset` | Session + placement + Kandidaten → Browser-State | LRU-artige Begrenzung auf 16 Sitzungen |
| `live_session.py:19–92` | `LiveSession.start/stop/get_state` | Settings → State | neue Session/Generation und Detector-Reset |
| `live_session.py:94–165` | `_queue_locked`, `set_recommendations`, `import_pgn`, `_clear_detection_locked` | Board/Schalter/PGN → Job/State | latest-only Job, Ergebnislöschung bei Reset |
| `live_session.py:167–253` | `submit_frame` | JPEG → Erkennung/State | Vision, Stabilitätsframes, Tracker, OCR |
| `live_session.py:264–290` | `_analysis_worker` | Job → Ergebnis oder Fehler | verwirft alte Generationen |
| `vision.py:8–89` | `sanitize_ocr_history`, `BoardVision.recognize/read_notation` | Bild → Board/OCR | optionale Vision-Abhängigkeiten |
| `browser/allie21_overlay.user.js:69–146` | History-Leser | DOM → SAN/PGN-Kandidaten | Chess.com/Lichess-Zuglisten und TCN-Kandidat |
| `browser/allie21_overlay.user.js:151–240` | Board-/Figurenfunktionen | DOM → Placement/Orientation/Box | ignoriert Ghosts, prüft Könige/Materialgrenzen |
| `browser/allie21_overlay.user.js:241–315` | `clearOverlay`, `drawArrow`, `paint`, `show`, `postJson` | Resultat → SVG/Panel | HTTP-Timeout, Pfeilrollen, Bubble/Status |
| `browser/allie21_overlay.user.js:319–383` | Session-/Farb-/Startfunktionen | DOM/Settings → Reset/Seite | Reset bei neuer Partie, automatische Spielerfarbe |
| `browser/allie21_overlay.user.js:384–449` | `analyze`, `tick`, `scheduleTick` | History/Placement → Requests/UI | `analysisSerial`, MutationObserver, 120-ms-Debounce, 5-s-Sicherheits-Poll |
| `viewer/index.html:121–158` | `fitStage`, `report`, `drawArrows`, `start`, `tick`, `end`, `manualGo` | Media/JSON/PGN → Viewer | Bildschirmfreigabe, JPEG-Loop, SVG, manueller PGN/FEN-Pfad |
| `tools/launcher.py:22–114` | `find_project_root`, `TrayApp`, `main` | EXE → Tray/Serverprozess | Start, Viewer öffnen, eigener Prozessbaum stoppen |

### Exakte Aufrufkette der Browseranalyse

`MutationObserver/setInterval` → `scheduleTick` → `tick` → `readBoardSnapshot` →
`historyFromVisibleBoard` → `localPost('/api/browser-position')` →
`BrowserTrackerPool.observe` → `PositionTracker.set_notation/observe` → Antwort
`ready/fallback_ready` → `analyze` → `postJson('/analyze')` → `analyse_position` →
`paint/show` → `drawArrow`/`insightLines`. Jede Stufe kann bei fehlender Stabilität,
ungültiger History, Timeout oder neuer Position abbrechen; in diesen Fällen wird keine
Empfehlung als gültig dargestellt.

### Exakte Aufrufkette der Videoanalyse

`getDisplayMedia` → `<video>` → `viewer.tick` → Canvas-Downscale/JPEG →
`POST /api/frame` → `LiveSession.submit_frame` → `BoardVision.recognize` →
Stabilitätsprüfung → `PositionTracker.observe` → `_queue_locked` →
`_analysis_worker` → `analyse_position` → `GET /api/state`-Darstellung durch
`viewer.report` → FEN-/History-Panel, Analyseblase und SVG-Pfeile. Ein neuer Frame kann
den laufenden Job nicht direkt abbrechen, aber eine höhere Generation macht dessen
Antwort beim Zurückschreiben ungültig; es bleibt höchstens Rechenzeit bis zum Ende des
laufenden Allie-/Stockfish-Aufrufs.
