# Allie21 Chess Live Studio v11 – technische Analyse und Modernisierung

**Prüfdatum:** 09.11.2026, Europe/Vienna  
**Arbeitsbaum:** `codex/allie-first-exe`, Commit `59463bd`  
**Projektwurzel:** `C:\Users\User\Desktop\Allie21_Chess_Live_Studio_v10`

## 1. Gesamturteil

Die vorhandene Architektur ist für lokalen, privaten Trainings- und Analysebetrieb tragfähig: FastAPI/Uvicorn, getrennte Browser- und Video-Pfade, `PositionTracker`, Allie-first, Stockfish als Ergänzung und SVG-Overlays sind vorhanden. Die lokale Offline-Suite ist reproduzierbar grün (78 Python-Tests, 7 Node-Tests, `compileall`, Doctor und Lockfile-Prüfung).

Der Checkout ist trotzdem **nicht releasefähig**. Die entscheidenden Blocker liegen an der HTTP-Sicherheitsgrenze, am fehlenden atomaren Result-Vertrag und am Packaging: Origin und statischer Header sind keine Authentisierung; `/api/frame` liest den Body nach einer reinen `Content-Length`-Prüfung ungebunden; bei unvollständiger History können konkrete Stockfish-Pfeile gezeichnet werden; und die EXE erwartet neben sich einen vollständigen Quell-Checkout. Diese Punkte sind im Ist-Code belegt, nicht nur aus dem historischen Bericht übernommen.

Die folgenden Aussagen unterscheiden ausdrücklich zwischen **belegt**, **nicht reproduziert**, **widerlegt** und **offen**. Historische Messwerte aus `VERSIONEN.md` werden nicht als aktuelle Release-Evidenz behandelt.

## 2. Evidenzgrenzen und Baseline

| Check | Ergebnis am 09.11.2026 | Status |
|---|---|---|
| `.allie-venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` | 78 Tests, 1,962 s, `OK` | belegt |
| 7 vorhandene `tests/test_*.js` via Node | alle bestanden | belegt |
| `python -m compileall -q backend tools tests` | erfolgreich | belegt |
| `backend/doctor.py` | Python 3.12.10, Abhängigkeiten, Stockfish und 5/5 Opening-Dateien erkannt | belegt |
| `UV_CACHE_DIR=.uv-cache uv lock --check --offline` | 83 Pakete, erfolgreich | belegt |
| `uv lock --check` mit globalem Cache | wegen gesperrter globaler Cache-Datei (`os error 5`) nicht möglich | Umgebungsgrenze |
| `tools/launcher.py --check` | Exitcode 0 im vollständigen Repository | belegt |
| EXE `--check` | nur im Parent-Repository bestanden; isolierter Release-Ordner nicht geprüft | teilweise belegt |
| Pytest/Ruff/mypy/pyright/Coverage/CI | nicht installiert bzw. nicht konfiguriert | offen |
| Live-`healthz`/`readyz`, frische Windows-Maschine, Offline-First-Run | in dieser Sitzung nicht reproduziert | offen |
| Modell-/Engine-Laufzeit | Unit-/Mockpfad vorhanden; ein neuer Kalt-/Warmbenchmark wurde nicht gemessen | offen |

Die beiden unabhängigen Reviews wurden ohne Änderungen am Arbeitsbaum ausgeführt:

* **Agent A – Feature/Schach/Sicherheit:** bestätigte Legalitäts- und Generation-Stärken, fand aber P0-HTTP-Lücken sowie P1-Result-Key-, History-, Farb- und Adapterprobleme.
* **Agent B – Release/Dead Code:** bestätigte Lockfile, Build-/Hash-Bestand und fehlenden offensichtlichen Dead Code; fand Packaging-, Dokumentations- und Clean-Install-Gates.

## 3. Tatsächlicher Datenfluss

```mermaid
flowchart LR
  A[START_HIER.bat oder EXE] --> B[Uvicorn 127.0.0.1:8765]
  B --> C[FastAPI HTTP-Grenze]
  C --> D[Viewer]
  C --> E[Userscript/MV3]
  E --> F[Chess.com/Lichess DOM]
  F --> G[Placement + History/TCN]
  G --> H[BrowserTrackerPool/PositionTracker]
  D --> I[JPEG Frame]
  I --> J[BoardVision/OCR optional]
  J --> K[LiveSession]
  H --> L[/api/browser-position]
  K --> M[Analyseauftrag]
  L --> M
  M --> N[python-chess Legalität]
  N --> O[Allie 2.1]
  N --> P[Stockfish]
  O --> Q[Allie-Kandidaten und Vorschau]
  P --> Q
  Q --> R[JSON-State]
  R --> S[FEN-/Clientprüfung]
  S --> T[SVG-Pfeile/Bubble]
```

Die Kette ist funktional vorhanden, aber der Vertrag zwischen `R` und `S` enthält derzeit nur einen Teil der für Release-Sicherheit nötigen Identität. `generation` und `session_id` werden intern erhöht (`backend/live_session.py:60-117,264-283`), erscheinen aber nicht im Ergebnis. Viewer und Overlay prüfen im Wesentlichen FEN bzw. clientseitige Seriennummern.

## 4. Befunde nach Priorität

### P0 – vor jedem Release beheben

1. **Keine echte Request-Authentisierung.** `backend/live_server.py:176-205` akzeptiert Host/Origin und `X-Allie-Overlay: 1`, aber kein zufälliges Start-Token, keine kurze Token-Lebensdauer, keinen Replay-Schutz und kein Rate-Limit. Die vorhandenen Header sind von jedem lokalen Prozess nachahmbar.
2. **Body-Limit nur über `Content-Length`.** Die Middleware prüft `Content-Length`, danach liest `/api/frame` mit `await request.body()` (`live_server.py:277-280`) den gesamten Stream. Chunked Transfer oder ein fehlender Header umgehen die Grenze. Das Limit muss beim Lesen des Streams gelten.
3. **Chess.com-Callback standardmäßig aktiv.** `_fetch_chesscom_tcn()` (`live_server.py:127-157`) ruft den undokumentierten Callback mit Timeout/Cache auf. Er braucht ein explizites Feature-Flag, begrenzten Backoff, Telemetrie und einen sicheren Default `off`.
4. **Release-Wahrheit der EXE.** `tools/build_exe.ps1` baut nur EXE + `_internal`. Der aktuelle Release-Ordner enthält keine `START_HIER.bat`, `pyproject.toml`, `uv.lock` oder `backend/live_server.py`; `tools/launcher.py:14-39` verlangt diese Dateien. Die EXE ist daher ein Launcher für einen daneben liegenden Checkout, keine portable Anwendung.

### P1 – Korrektheit und Plattformrobustheit

1. **Unvollständige History kann konkrete Pfeile erzeugen.** `LiveSession._queue_locked()` erlaubt bei `turn_verified` eine FEN-Stockfish-Analyse (`live_session.py:94-115`). Viewer `drawArrows()` zeichnet danach `my_moves`, `opponent_moves` und `premove` allein bei FEN-Gleichheit (`viewer/index.html:145-147`). Der neue Vertrag verlangt bei `history_complete=false` oder unsicherem Zugrecht keine konkreten Pfeile/Premoves, auch wenn Stockfish intern laufen darf.
2. **Kein atomarer Result-Key.** Es fehlen `session_id`, `generation`, `analysis_key`, normalisiertes FEN, `board_box_hash` und `transform_revision` in einem Ergebnis. Ein gleiches FEN nach Resize/Flip kann mit einer neuen Box gezeichnet werden. Browser und Viewer haben damit unterschiedliche, unvollständige Stale-Gates.
3. **Provenienz und Reihenfolge sind nicht maschinenlesbar.** `describe_move()` liefert keine `source`, `confidence`, `uncertainty` oder `result_id`. Repertoire-, aggressive- und Sicherheitslogik darf die Kandidatenreihenfolge verändern (`allie_local_server.py:360-383,462-464`), obwohl Allie im `both`-Modus sichtbar primär bleiben soll.
4. **Farbe und Orientierung sind nicht vollständig getrennt fail-closed.** Der Overlay-Fallback leitet bei fehlendem Plattformmarker die Spielerfarbe aus der Orientierung ab. Das widerspricht der Regel „Auto-Farbe nur aus verifiziertem Marker; sonst Warnstatus/manueller Override“. Auch generische Selektoren wie `.board`, `[role="grid"]` und `[class*="chess-board"]` können unbekannte DOMs zu früh akzeptieren.
5. **Adaptervertrag fehlt.** Es gibt einen monolithischen Userscript-Pfad statt `readPosition`, `readHistory`, `orientation`, `playerColor`, `mode`, `renderShapes`, `teardown`. Nur ein `MutationObserver` und ein Intervall sind sichtbar; `ResizeObserver`, explizites Teardown und ein Unknown-Layout-Fail-closed-Modus fehlen.
6. **Playwright-E2E fehlt.** Die Node-Tests sind wertvolle VM-/String-Fixtures, ersetzen aber keine Browser-Fixtures für Animation, Flip, Zuschauer, Promotion, Game-over, Resize und Layoutwechsel.
7. **Clean-Install und Windows-Smoke sind offen.** Ein frischer `uv run --frozen` konnte wegen blockiertem PyPI-Netzwerk nicht abgeschlossen werden; der EXE-Test deckt nur den vollständigen Parent-Checkout ab.

### P2 – Performance, Packaging, Lizenz und Wartung

1. **Pixelbomb-Schutz ist nicht explizit.** `live_session.py:186-191` prüft Bytezahl sowie minimale/maximale Seitenlänge, aber keine harte Pixelgrenze vor Dekodierung (`Image.MAX_IMAGE_PIXELS`/eigene Grenze).
2. **Cancellation ist nur logisch.** Der Worker verwirft alte Ergebnisse nach Abschluss, beendet aber laufende Allie-/Stockfish-Arbeit nicht (`live_session.py:264-283`). Latest-only-Queue, kooperative Cancellation und Engine-`stop` fehlen.
3. **Dokumentationsdrift.** `VERSIONEN.md:51` nennt 73 Tests statt 78 Python + 7 Node. `live_server.py:137` sendet noch `Allie21-Live-Studio/11.2.4`, während Projekt und Manifest 11.2.15 tragen.
4. **Lizenzinventar deckt direkte Komponenten ab, nicht alle transitive Bundles.** GPL-3.0-Komponenten (`chess`, Stockfish, chessvision) und der eigene GPL-Hinweis sind dokumentiert; eine SBOM- und EXE-Beipackprüfung fehlt.

### P3 – optional/später

WXT, chessops, Chessground, ONNX/OCR-Erweiterungen, Nuitka und Tauri sind keine P0-Lösungen. Sie dürfen erst nach dem gemeinsamen Zustandsvertrag anhand messbarer Wartungs-, Lizenz-, Bundle- und Performance-Vorteile eingeführt werden. Chessground bleibt bis zur Lizenzentscheidung ausgeschlossen.

## 5. Tragfähige Teile

* `PositionTracker` verbindet sichtbare Stellungen nur über legale python-chess-Übergänge; Rochade/En-passant werden bei unbekannter Vorgeschichte nicht erfunden.
* Allie wird bei FEN-only übersprungen; Stockfish ist als objektive Ergänzung getrennt.
* Generation und Session verhindern, dass alte Worker-Ergebnisse nach Stop/Reset veröffentlicht werden.
* Allie liefert die Kandidatenreihenfolge; Stockfish wird im normalen `both`-Pfad nicht als stiller Ersatz verwendet.
* Pfeilfarben sind festgelegt: `#16c784`, `#7ee2b8`, `#ef3340`, `#ff9299`, `#2f80ed`.
* SVG-Layer werden bei Reset/Stop/fehlender Sichtbarkeit geleert; die vorhandenen Overlay-Tests sichern mehrere Stale- und Orientierungspfade.
* Direkte Module und Dependencies sind nach `rg`/`uv tree` plausibel referenziert; es wurde nichts unreferenziert gelöscht.

## 6. Versions-, Lizenz- und Framework-Matrix

| Komponente | Lock/Manifest | Bewertung für v11 |
|---|---:|---|
| Python | 3.12.x, lokal 3.12.10 | belegt; Clean-Machine-Gate offen |
| chess / chess-tcn | 1.11.2 / 1.0.1 | belegt; GPL-3.0+ für python-chess prüfen |
| FastAPI / Pydantic / Uvicorn | 0.162.2 / 2.14.3 / 0.54.0 | Lockfile konsistent |
| Pillow / Torch / Transformers | 13.0.0 / 2.15.0 / 5.22.2 | Modell-/Windows-Wheel-Preflight offen |
| Stockfish | 19 (`sf_19`) | Binary-Hash dokumentiert; UCI-Stop/Restart-Test offen |
| PyInstaller / pystray | 6.22.3 / 0.19.5 | Onedir gebaut; portable Produktfrage offen |
| Vision extras | chessvision 0.13.1, NumPy 2.5.4, ONNX Runtime 1.31.1, RapidOCR 3.10.0 | graceful degradation und Pixel-/RAM-Gates fehlen |
| Browser | MV3, Chess.com/Lichess-Matches | lokal gebündelt; kein Remote-Code |
| Lizenzen | GPL-Projekt, MIT/Apache/BSD/HPND/LGPL-Anteile dokumentiert | transitive SBOM und EXE-Beipack noch offen |

Aktuelle lokale Hash-Evidenz: `uv.lock` SHA-256 `c88069bfa715eb51d28989177a93122002c82e20391b88b9a008a671050a97f3`; EXE SHA-256 `649dbf4810677c2bfb8a69fbb7e34599d5f739dac89adf6f49c0913049311b7a`.

## 7. Zielarchitektur und gemeinsamer Zustandsvertrag

Die Pipeline wird als messbare Kette betrieben:

`capture → detect → normalize → stabilize → reconstruct history → validate legal state → allie inference → candidate features → safety/risk ordering → stockfish complement → merge with provenance → result-key check → render → telemetry`

Jede Stufe schreibt Start-/Endzeit, Drop-Grund, Queue-Tiefe und Cancellation-Status. Private Frames werden nicht persistiert.

```json
{
  "session_id": "uuid",
  "generation": 42,
  "analysis_key": "sha256(canonical-input)",
  "fen": "normalized-fen",
  "history_status": "complete|partial|unknown",
  "turn_verified": true,
  "rights_confidence": 0.0,
  "player_color": "white|black|unknown",
  "orientation": "white|black|unknown",
  "board_box_hash": "sha256(rect)",
  "transform_revision": 7,
  "source": "chess.com|lichess|video|manual",
  "mode": "live|spectator|review",
  "uncertainty": {"level": "none|warning|blocked", "reasons": []}
}
```

`AnalysisResult` übernimmt diesen Schlüssel unverändert. Ein Client zeichnet nur bei exakt gleichem Schlüssel. Bei `history_status != complete` oder `turn_verified != true` sind `my_moves`, `opponent_moves` und `premove` leer; ein klar markierter Stockfish-Orientierungswert darf separat angezeigt werden.

## 8. Priorisierter Umsetzungsplan

### Phase 0 – Baseline festnageln

1. Prüfbefehle und Hashes in einer maschinenlesbaren Release-Manifestdatei speichern.
2. Alle historischen K1–K15-Claims als `belegt`, `nicht reproduziert`, `widerlegt` oder `offen` markieren.
3. Python-/Node-Suite, `uv lock --check`, `doctor`, Launcher- und EXE-`--check` in CI ausführen.

### Phase 1 – HTTP- und Sicherheitsgrenze

1. Beim Prozessstart ein kryptografisch zufälliges Token erzeugen; Viewer und Userscript erhalten es über einen kontrollierten Bootstrap.
2. Token-TTL, Nonce/Replay-Schutz und per-Route/per-Session Rate-Limit ergänzen.
3. JSON- und JPEG-Bodies mit einem begrenzten Async-Stream lesen; `Content-Length` bleibt nur ein schneller Vorcheck.
4. Pillow-Pixelgrenze, JPEG-Format, Seitenlimits und Dekompressionsfehler vor Vision setzen.
5. Chess.com-Callback standardmäßig deaktivieren; bei expliziter Aktivierung Timeout, exponentiellen Backoff, Cache und Drop-Grund protokollieren.

### Phase 2 – Zustands- und Schachkorrektheit

1. `PositionSnapshot`, `AnalysisResult`, `Arrow`, `Mode`, `Uncertainty` und `OpeningPreference` als gemeinsames Schema definieren.
2. `session_id`, `generation`, `analysis_key`, FEN, Box-Hash und Transformationsrevision in jede Antwort schreiben.
3. Unvollständige History/unsicheres Zugrecht fail-closed rendern: keine Pfeile, Premoves oder konkreten Suggestions.
4. Allie-Reihenfolge als unveränderliche `allie_rank` erhalten; Repertoire und aggressive Präferenzen als separate weiche Metadaten modellieren.
5. Jede Empfehlung mit `source`, `result_id`, Konfidenz und Unsicherheitsgründen versehen.

### Phase 3 – Adapter und Rendering

1. Site-Adapter mit `readPosition`, `readHistory`, `orientation`, `playerColor`, `mode`, `renderShapes`, `teardown` einführen.
2. Plattformmarker sind für Auto-Farbe zwingend; bei fehlendem Marker `unknown` plus manuellem Override statt Orientierung-Fallback.
3. Mutation-/Resize-Observer debouncen, Animation-Mindestalter/Hysterese und Backpressure ergänzen; Teardown bei Navigation/Reset abmelden.
4. Eine kanonische Arrow-/Koordinaten-/Farbkernschicht für Viewer und Userscript generieren.

### Phase 4 – Performance und Vision

1. Latest-only-Queue mit maximaler Inferenzrate und kooperativen Cancellation-Punkten einführen.
2. Stockfish-`stop`, Timeout, `quit` und Wiederanlauf testen; Threads/Hash/MultiPV an Hardwareprofil koppeln.
3. Allie-Kaltstart, Warmstart, p50/p95, CPU/RAM und Verhalten ohne Modell/Engine messen.
4. Vision nur mit Konfidenz-/Stabilitätshysterese annehmen; Framerate, JPEG-Bytes, Pixel und OCR-Zeit begrenzen.

### Phase 5 – Tests und zwei Reviews

1. Contract-, Property- und Fuzz-Tests für FEN/PGN/UCI, HTTP-Streaming und Result-Key schreiben.
2. Playwright-Fixtures für hell/dunkel, Weiß/Schwarz, Flip, Animation, Zuschauer, virtuelle History, Promotion, Game-over, Resize und unbekanntes Layout ergänzen.
3. Agent A wiederholt Feature/Schach/Sicherheit; Agent B wiederholt Release/Dead-Code/Dependency/Lizenz. Beide prüfen die jeweils andere Reviewliste nicht.

### Phase 6 – Cleanup und Packaging

1. `rg`, `uv tree`, Ruff/Typecheck/Coverage, dynamische Route-/Import-Allowlist sowie Asset-/Lizenzinventar ausführen.
2. Nur nach Referenzprüfung löschen; dynamische FastAPI-Routen, Userscript-Endpunkte, PyInstaller-Daten und optionale Plugins explizit erlauben.
3. Entweder ein echtes Onedir-/Installer-Produkt mit allen benötigten Runtime-Daten bauen oder die Datei eindeutig als `Launcher` benennen und ein vollständiges Release-Archiv liefern.
4. Reproduzierbaren Windows-Build mit `PYTHONHASHSEED`, `SOURCE_DATE_EPOCH`, SHA-256, SBOM, Lizenzbeipack und Rollback erzeugen.

## 9. Tests und Abnahmekriterien

Release ist nur zulässig, wenn alle folgenden Gates grün sind:

* Kein konkreter Pfeil/Premove bei unbestätigtem Zugrecht, unvollständiger History, FEN-/Generation-/Transform-Mismatch oder unbekanntem Sprung.
* Jede Empfehlung enthält `source`, Konfidenz/Unsicherheit, Modus und exakte Ergebnis-ID; Allie-Reihenfolge bleibt sichtbar unverändert.
* Auto-Farbe/Flip-Matrix besteht für Weiß/Schwarz, beide Orientierungen und manuelle Overrides; fehlende Marker bleiben `unknown`.
* Alte SVGs verschwinden bei Reset, Stop, Settings, Navigation, Game-over und jedem Key-Mismatch.
* Body-Limits gelten während des Lesens; Token, TTL, Replay-Schutz, Rate-Limit und JPEG-Pixelgrenze sind getestet.
* Unbekannte DOMs zeigen Unsicherheit statt erfundener Züge; Playwright-Fixtures bestehen auf allen unterstützten Layouts.
* EXE startet auf sauberem Windows, meldet `readyz`, öffnet den Viewer, beendet Kindprozesse und behandelt einen zweiten Start.
* `uv lock --check`, Lint/Typecheck, Python-/Node-/Property-/Fuzz-/E2E-Suite, SBOM/Lizenzen, SHA-256 und Rollback sind dokumentiert.

## 10. Cleanup- und Release-Bericht

In dieser Prüfphase wurden **keine Dateien oder Dependencies gelöscht**. `rg`/`uv tree` zeigen keine offensichtlich unreferenzierten Backend-Module oder direkten Dependencies. Offene Cleanup-Punkte sind transitive EXE-Lizenzen, die historische User-Agent-Version, die Testzahldrift und die fehlende CI-/Coverage-Konfiguration. Der Release-Ordner darf erst nach einer Entscheidung „portable Produkt oder Launcher“ als auslieferbar bezeichnet werden.

## 11. Kopierfertiger deutscher Master-Prompt

```text
Ziel: Modernisiere Allie21 Chess Live Studio v11 für lokalen, privaten Trainings- und Analysebetrieb. Behandle den vorhandenen Checkout als einzige Wahrheit und verifiziere jede historische Behauptung in Code, Lockfile, Tests, Logs oder Build-Artefakten. Liefere die technische Umsetzung und genau einen abschließenden Markdown-Bericht; behaupte keine funktionierende EXE, solange der Clean-Windows-Smoke nicht bestanden ist.

Priorität P0: sichere die lokale HTTP-Grenze mit zufälligem Start-Token, TTL, Replay-Schutz, Rate-Limit, begrenztem Async-Body-Stream und expliziter Pillow-Pixelgrenze. Der undokumentierte Chess.com-Callback ist standardmäßig aus und nur mit Feature-Flag, Timeout, Backoff und Telemetrie erlaubt. Entscheide ausdrücklich zwischen echtem portablem Onedir/Installer und einem als Launcher bezeichneten vollständigen Projektarchiv.

Definiere einen gemeinsamen, typisierten Vertrag für PositionSnapshot, AnalysisResult, Arrow, Mode, Uncertainty und OpeningPreference. Jedes Ergebnis enthält session_id, generation, analysis_key, normalisiertes FEN, history_status, turn_verified, player_color, orientation, board_box_hash und transform_revision. Nur ein exakter Result-Key darf zeichnen. Bei unvollständiger History oder unsicherem Zugrecht dürfen keine konkreten Pfeile, Premoves oder Move-Suggestions erscheinen; Stockfish darf nur als klar markierter Orientierungswert laufen.

Allie bleibt primäre Kandidatenreihenfolge. Jeder Kandidat wird mit python-chess legalisiert und erhält source, allie_rank, Konfidenz, Unsicherheit und result_id. Stockfish ergänzt objektive Linien und darf Allie im both-Modus nicht still umsortieren. Brettorientierung und Spielerfarbe sind getrennt; Auto-Farbe kommt nur aus einem verifizierten Plattformmarker, sonst unknown plus manueller Override. Opening-Präferenzen bleiben weiche Labels und überstimmen niemals Legalität oder Sicherheitsgates.

Implementiere Site-Adapter mit readPosition, readHistory, orientation, playerColor, mode, renderShapes und teardown. Debounce Mutation-/Resize-Observer, erkenne Animationen und unbekannte Layouts fail-closed. Teile Arrow-Projektion, Farben und Result-Key-Prüfung zwischen Viewer und Userscript. Ergänze Contract-, Property-, Fuzz- und Playwright-Fixtures für Flip, Animation, Zuschauer, Promotion, Game-over, Resize, Layoutwechsel, HTTP-Streaming, FEN/PGN/UCI und Cancellation/Backpressure.

Führe vor Freigabe zwei unabhängige Reviews durch: Agent A prüft Feature/Schach/Sicherheit, Agent B Release/Dead Code/Dependencies/Lizenzen. Danach Cleanup nur nach rg-/Allowlist-Referenzprüfung, reproduzierbarer Windows-Onedir-/Installer-Smoke, readyz, Start/Stop/zweitem Start, SHA-256, SBOM, Lizenzbeipack und Rollback. Fehlende Gates werden als nicht releasefähig mit Ursache dokumentiert.
```

## 12. Validierter JSON-Packet-Block

```json
{
  "validator_status": "PASS",
  "source_custody": "Die angehängte technische Analyse bleibt historische Eingabe; alle Statusangaben oben wurden gegen den Checkout vom 09.11.2026 geprüft.",
  "objective": "Allie21 Chess Live Studio v11 technisch modernisieren und für lokalen privaten Trainings- und Analysebetrieb releasefähig machen.",
  "operating_mode": "local_private_training_analysis",
  "must_keep": [
    "Allie bleibt primäre Kandidatenreihenfolge",
    "Stockfish ergänzt objektive Linien",
    "Brettorientierung und Spielerfarbe bleiben getrennt",
    "keine erfundene History, Rochade oder En-passant-Rechte",
    "Pfeilfarben #16c784 #7ee2b8 #ef3340 #ff9299 #2f80ed",
    "alte Overlays bei Reset oder Result-Key-Mismatch löschen"
  ],
  "pipeline": [
    "capture",
    "detect",
    "normalize",
    "stabilize",
    "reconstruct_history",
    "validate_legal_state",
    "allie_inference",
    "candidate_features",
    "safety_risk_ordering",
    "stockfish_complement",
    "merge_with_provenance",
    "result_key_check",
    "render",
    "telemetry"
  ],
  "release_blockers": [
    "token_ttl_replay_rate_limit",
    "streaming_body_limit",
    "jpeg_pixel_limit",
    "callback_feature_flag",
    "atomic_result_key",
    "no_arrows_on_incomplete_history",
    "portable_or_explicit_launcher_packaging",
    "clean_windows_smoke",
    "sbom_and_license_beipack"
  ],
  "required_reviews": [
    "feature_chess_security",
    "release_dead_code_dependencies"
  ],
  "acceptance": {
    "python_tests_current": 78,
    "node_tests_current": 7,
    "lock_check_current": true,
    "release_ready_now": false
  }
}
```
