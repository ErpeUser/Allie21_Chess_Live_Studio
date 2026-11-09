# ALLIE21 MASTER-FORTSETZUNGSAUFTRAG
## 1. Auftrag: vorhandene Arbeit retten, fertigstellen und belegen

Übernimm das bestehende Allie-2.1-Chess-Live-Studio im tatsächlich zugänglichen Repository. Der vorige Codex-Chat ist nach einem Accountwechsel verloren gegangen; die Umsetzung wurde durch ein Nutzungslimit unterbrochen. Setze am vorhandenen Arbeitsstand fort. Erstelle nicht bloß einen Plan, einen neuen Prompt oder einen weiteren Audit-Bericht.

Ziel ist implementierter, bereinigter und getesteter Code mit stabilen Pfeilen, korrektem Eröffnungsrepertoire, verlässlicher Allie-first-Pipeline, privatem Windows-HUD, einer echten Windows-Onedir-Distribution und einem verifizierten Release ausschließlich in einem privaten GitHub-Repository. Die Windows-EXE ist ein Pflichtliefergegenstand, nicht durch „releasebereit“ oder eine reine Launcher-EXE ersetzbar.

Priorität: zuerst unterbrochene Fehlerkorrekturen und korrekten Datenfluss abschließen; danach verbleibende Capture-/Pipeline-Anforderungen, Stabilität und Performance; anschließend gezieltes Cleanup, vollständige Tests, Windows-Build und privater Release. Bereits funktionierende Teile weiterverwenden. Ein früher abgeschlossener Teilfix ist kein Grund, den restlichen Master-Auftrag auszulassen.

Arbeite innerhalb der tatsächlich verfügbaren Werkzeuge und Berechtigungen selbstständig weiter, bis die GOAL-Abnahme erfüllt oder weitere Arbeit objektiv blockiert ist. Keine unbelegten Erfolgsbehauptungen, keine Umgehung von Nutzungslimits und kein Versprechen einer nicht eingerichteten Hintergrundfortsetzung.

## 2. Verlorenen Stand rekonstruieren, nicht von vorne beginnen

Dieser Auftrag konsolidiert den Master „ALLIE21_MASTER_PROMPT_TECHNIK_CAPTURE_EXE.md“, den bisherigen Fortsetzungsauftrag, den Eröffnungsnachtrag, die GOAL-/Resume-Regeln und den zuletzt eingefügten Abbruchverlauf. Er ist auch ohne den verlorenen Chat benutzbar. Vorhandene Originaldateien zusätzlich lesen; fehlende Anhänge nicht erfinden. Die genannte „ALLIE_ANALYSE_IST.md“ liegt möglicherweise nur im alten Workspace.

Suche einmal gezielt nach dem Projekt und vorhandenen Wiederaufnahmeartefakten: aktive Workspace-/IDE-Projekte, AGENT_PROGRESS.md, vorhandene Auftrags-/Planungsdateien, relevante lokale Git-Branches, Worktrees, Commits und Reflog sowie tatsächlich zugängliche Codex-Aufgaben-/Sitzungsexporte. Nutze einen vorhandenen autorisierten Verlaufssuchmechanismus, falls verfügbar. Behaupte keinen Zugriff auf das frühere Konto; suche nicht nach Tokens oder fremden Kontodaten. Eine erfolglose Chatsuche darf die Implementierung im vorhandenen Checkout nicht blockieren.

Der früher genannte Pfad C:\Users\User\Desktop\Allie21_Chess_Live_Studio_v10\browser ist nur ein Suchhinweis. Ermittle den echten Repository-Root. Falls kein Quellcode zugänglich ist, benenne genau diesen Blocker und benötigten Zugriff; baue kein erfundenes Ersatzprojekt aus Dateinamen.

Historischer Stand laut Übergabe, vor Verwendung lokal abgleichen:
- Branch codex/allie-first-exe; Commit 59463bd wurde in der älteren Ist-Aufnahme genannt. Nicht annehmen, dass HEAD noch darauf steht.
- Beim letzten Audit kein Git-Remote; Manifest 11.2.16.0, Python-Projekt 11.2.15, mehrere lokale Änderungen. Edge hatte zuvor teilweise Erweiterungsrevision 11.2.15.0 geladen.
- AGENT_PROGRESS.md wurde laut Verlauf bereits erstellt. Vorhandene Inhalte lesen und fortschreiben, nicht durch eine neue leere Datei ersetzen.
- Bearbeitungen wurden an chess_extras.py, live_server.py, allie21_overlay.user.js und test_chess.py gemeldet. Die tatsächlichen Pfade und Diffs entscheiden, nicht diese Kurzliste.
- Eröffnungsdaten in backend/openings/*.tsv aus lichess-org/chess-openings und python-chess wurden als vorhanden beschrieben. Installation, Datenstand und Integration in der aktuellen Umgebung prüfen.
- Der Capture-Ausschluss durfte zur Pfeildiagnose vorübergehend deaktiviert werden. Den jetzigen Modus feststellen; der finale Standard muss wieder private sein.

Die folgenden Befunde stammen aus dem verlorenen Audit. Sie sind konkrete Prüfhinweise, keine in dieser Sitzung erneut nachgewiesenen Tatsachen. Zeilennummern beziehen sich auf den damaligen Stand:

A. Browser-Repaint: browser/allie21_overlay.user.js:311-328 nutzte position:fixed/getBoundingClientRect(). Der MutationObserver rief nur tick() auf; bei gleicher FEN/History wurde paint() nicht erneut ausgeführt (:416, :511-514). Dadurch konnten Resize, Layout-Animationen und Orientierungswechsel alte Pfeilkoordinaten hinterlassen. Ein früher angekündigter „board-lokaler SVG-Fix“ gilt deshalb nicht automatisch als eingebaut oder ausreichend.

B. Transformation: center()/drawArrow() (:281-292) nutzten nur ein achsenparalleles Rechteck; CSS-Rotation/Transform-Matrix fehlte. Ein ResizeObserver allein beweist keine korrekte Rotation.

C. SPA-Lifecycle: boardSessionId, currentResult und Tracker wurden bei Navigation/Neupartie offenbar nicht zurückgesetzt (:68-70, :511-515). Ergebnisse konnten in eine neue Partie gelangen.

D. Native-Staleness: backend/live_server.py:134-146,355-362 und backend/native_overlay.py:694-729 akzeptierten generation/render_revision, ohne deren Reihenfolge zu erzwingen. Ein clientseitig abgebrochener HTTP-Request konnte serverseitig verspätet alte Pfeile aktivieren.

E. Viewer-Geometrie: viewer/index.html:125,134-135 aktualisierte Bildschirmkoordinaten bei Scroll/Resize erst mit dem nächsten Frame statt unabhängig davon.

F. Kein damaliger Nachweis einer Duplikat-/Leak-/Input-Block-Ursache: replaceChildren() und pointer-events:none waren vorhanden. Diese Eigenschaften erhalten und testen; keine gegenteilige Root Cause erfinden.

G. Edge/MV3: periodInMinutes: 0.1 wurde als unzulässiges Alarmintervall gemeldet; außerdem Versionsabweichungen und Dokumentationslücken. Die tatsächlichen API-Grenzen für die Zielbrowser anhand offizieller Dokumentation prüfen. „Service Worker; (Inaktiv)“ allein nicht als Fehler behandeln.

H. Eröffnungen: Der Integrator sollte „keine unpassenden Buchalternativen mehr“ sicherstellen. Der vollständige Opening-Audit liegt im eingefügten Verlauf nicht vor; die genaue Ursache daher aus Code und Regressionstest ermitteln, nicht behaupten.

Node-Overlaytests und Syntaxprüfung wurden als erfolgreich gemeldet; Python-Tests waren wegen fehlender pydantic-/pytest-Umgebung nicht vollständig ausführbar. Alte Aussagen „getestet“ sind kein Nachweis für den aktuellen Gesamtstand.

Letzte sichtbare Implementierungsaktion: „Adding board resize observer with paint coordination“. Zuvor angekündigt waren Repaint-/Navigation-Fixes, monotones Native-Gate, MV3-Alarme, Versionsangleichung, Opening-Fix, Regressionstests und Installationshinweise. Es können unfertige, uncommittete Teilpatches existieren. Prüfe und vervollständige sie, statt sie doppelt zu implementieren. Ein erfolgreicher Gesamt-Test, Windows-Build oder Release ist im Verlauf nicht belegt. Die damalige Limit-Anzeige „08:03“ ist kein aktueller Wiederaufnahmezeitpunkt.

## 3. Verbindliche Anforderungen und Grenzen

### 3.1 Bestehende Arbeit und Produktverhalten schützen

Vor Änderungen Repository-Root, Betriebssystem, Branch/HEAD, git status, Remotes, Staged-/Unstaged-Diffs, relevante unversionierte Dateien, Versionen, Lockfiles und vorhandene Start-/Test-/Buildbefehle sichern. Bereits laufende Jobs und Worktrees zuordnen. Keine fremden Prozesse beenden und keine Benutzeränderungen durch reset --hard, clean, ungezieltes Stash/Checkout, Force-Push oder Überschreiben verlieren. Sensible Dateien nicht in Backups, Commits oder Logs aufnehmen.

Lies die realen Einstiegspunkte: backend/live_server.py, live_session.py, position_tracker.py, browser_session.py, native_overlay.py, allie_local_server.py bzw. dessen tatsächlichen Pfad, chess_extras.py, config.py, vision.py; browser/allie21_overlay.user.js und manifest.json; viewer/index.html; tools/launcher.py, tools/build_exe.ps1, START_HIER.bat, PyInstaller-Specs und vorhandene Python-/JS-Tests. Fehlende Dateien nicht als vorhanden ausgeben.

Allie 2.1 bleibt Allie-first. Bestehenden Stockfish nur für vorgesehene objektive Vergleichs-/Sicherheitsprüfungen und den vorhandenen kontrollierten FEN-only-Pfad verwenden; Allie-Kandidaten nicht heimlich durch Engine-Züge ersetzen. „Keine neue Engine“ bedeutet nicht, den vorhandenen Stockfish zu entfernen. Kein Retraining, keine Modellgewichtsänderungen, keine zusätzliche Engine, keine zusätzliche Maus-/Zugautomation.

Echte Partiehistorie, Uhren, Elo-/Zeitparameter, Spielmodi einschließlich vorhandener calibrated-Optionen, Viewer, Browserintegration, Tray und braun-goldene Optik erhalten. Spielerfarbe player_side, Brettorientierung orientation und Zugrecht turn bleiben getrennt. Fehlende History niemals durch erfundene PGN, Rochade-/En-passant-Rechte oder Zugrechte ersetzen. python-chess bleibt kanonische Backend-Legalität. opening_white und opening_black bleiben gültige /analyze-Felder; keine erneute „Extra inputs are not permitted“-Regression.

Pfeilrollen, Anzahl, Legende und Farben exakt erhalten: eigenes Top-1 #16c784, eigenes Top-2 #7ee2b8, Gegner Top-1 #ef3340, Gegner Top-2 #ff9299, Pre-Move #2f80ed. Geometrie korrigieren, nicht die Semantik oder das visuelle Produkt neu entwerfen.

### 3.2 Eröffnungsbuch abschließen, nicht neu erfinden

Vorhandene ECO-/TSV-Daten und Auswahlmechanismen erweitern. Bestehende Eröffnungen und Benutzereinstellungen nicht löschen. Grob/Englund als im Master genannte provokante Defaults sowie Wiener, Dänisch, Budapest und Aljechin erhalten; existierende ausdrückliche Nutzereinstellungen nicht überschreiben.

Das gewünschte Troll-Repertoire umfasst mit Weiß Bongcloud, Grob-Gambit, Halloween-Gambit und mit Schwarz Stafford-Gambit, Traxler-Gegenangriff, Englund-Gambit. Steinitz-Gambit und Frankenstein–Dracula ergänzen, sofern klein und passend in der vorhandenen Struktur umsetzbar; andernfalls die konkrete Grenze nennen. Grob-Bongcloud nicht eigenmächtig zum bevorzugten Mix machen.

Bekannte Varianten einschließlich Zwischenstellungen nach einem geeigneten Stellungsschlüssel indexieren, etwa mit python-chess-EPD. Figurenstellung, Zugrecht, Rochaderechte und relevante En-passant-Möglichkeiten beachten. Transpositionen nur bei tatsächlich gleicher Stellung nutzen; Allie bekommt trotzdem die echte Zuggeschichte. Ähnliche Eröffnungsnamen beweisen keine kombinierbaren Varianten.

Gewünschte stellungsabhängige Zweige als legale Fixtures prüfen: Wiener Aufbau 1.e4 e5 2.Nc3 mit 2...Nf6 3.Nf3 Nc6 4.Nxe5 zum Halloween-Gambit; mit 2...Nf6 3.Bc4 Nxe4 4.Qh5 zu Frankenstein–Dracula; mit 2...Nc6 3.f4 exf4 4.d4 Qh4+ 5.Ke2 zum Steinitz-Gambit. Aus 1.e4 e5 2.Nf3 Nf6 führen 3.Nxe5 Nc6 zum Stafford und 3.Bc4 Nc6 4.Ng5 Bc5 zur Traxler-Stellung. Stafford/Traxler sind alternative Zweige, keine gleichzeitige Doppel-Eröffnung; Englund gegen 1.d4 bleibt separat. Diese Beispiele nicht gegen abweichende Gegnerzüge erzwingen.

Sind zur aktuellen Stellung und aktiven Auswahl passende bevorzugte Buchzüge vorhanden, innerhalb dieser legalen Kandidaten zuverlässig und abwechslungsreich auswählen. Allie-predict darf gewichten, ist aber kein Humor- oder objektiver Stärkennachweis. Keinen eingebauten Troll-Modus oder automatische Erfindung neuer Gambits unterstellen; eine höhere temperature allein ersetzt keine gezielte Repertoireauswahl. Keine fremden Buchalternativen als angeblich passende Fortsetzung einschleusen. Bei Gegnerabweichung, fehlendem Kandidaten oder Ende der kurzen Buchphase zum bisherigen Auswahlpfad zurückkehren. Der genannte Rahmen von höchstens zehn Zügen pro Seite ist ein konfigurierbarer Vorschlag, keine behauptete Allie-Vorgabe. Deaktivierte Präferenz muss das bisherige Verhalten erhalten; bei unvollständiger History gelten weiterhin die vorhandenen FEN-only-Regeln.

### 3.3 Pfeile, Geometrie und Session-Lifecycle

Den unterbrochenen ResizeObserver-/Paint-Patch zuerst abgleichen. Positionsanalyse und Geometrie-Repaint entkoppeln: gleiche FEN darf eine notwendige Neuzeichnung nicht verhindern. Board-Resize, Layoutänderungen, Scroll, visualViewport-/Browser-Zoom, Orientierungswechsel und Viewer-Fensterbewegungen müssen ohne neuen Analyse-/Videoframe korrekt reagieren. Observer und Listener beim Boardwechsel sauber entfernen; keine Duplikate oder neuen Leaks.

Kanonisches UCI-Feldmapping → normierte Brettkoordinaten → Zielkoordinaten für DOM und Native gemeinsam testen. CSS-Transformationen tatsächlich berücksichtigen, nicht aus einem achsenparallelen getBoundingClientRect() eine korrekte Rotation ableiten. Schwarz nicht doppelt spiegeln. Unbekannte/ungültige Geometrie verbergen statt falsch zeichnen und als funktionierend melden.

Browser-CSS-Pixel nicht blind als physikalische Windows-Pixel verwenden. Board-Rect, Viewport, devicePixelRatio, Zoom, Scroll, Orientierung, Monitor/DPI und verifizierte Browserfenster-/Inhaltsbereich-Zuordnung zusammenführen. ClientToScreen/MapWindowPoints, DWM-/DPI-APIs oder eine nachweislich korrekte vorhandene Lösung verwenden; screenX/screenY oder outerHeight-innerHeight nicht als universelle Toolbar-Korrektur behandeln. Untrusted HWND-Werte aus Browserdaten nicht ungeprüft übernehmen.

Zoom 67/80/100/125/150 %, Windows-Skalierung 100/125/150/200 %, gemischte Monitor-DPI, negative Monitor-Koordinaten, Move/Resize/Maximize, Taskbar, Fullscreen und Board-Flip abdecken. Nur dem aktiven, eindeutig zugeordneten Brett folgen. Bei Fokusverlust, Minimize, Navigation, Tabwechsel, unpassendem Board oder Verbindungsverlust sofort verbergen. Events debouncen/rate-limitieren; kein permanentes 60-Hz-Polling. Temporäre Kalibrier-Ecken/Feldmitten ausschließlich im geschützten nativen Fenster, danach abschalten.

Bei SPA-Navigation, Neupartie, Import, Stop/Reset, Mode-Switch und Positionswechsel Session-/Tracker-/Result-Zustand korrekt invalidieren und alte Pfeile/Blasen sofort löschen. Monotone generation/render_revision serverseitig und vor nativer Darstellung erzwingen, innerhalb der aktiven Session; alte Sessions dürfen auch mit hohen Revisionsnummern nicht wieder aktiv werden. Geometrie hat eine eigene Revision. Verspätete HTTP-Antworten, alte Show-/Clear-Nachrichten und abgebrochene Requests gezielt testen. AbortController allein ist kein serverseitiger Stale-Schutz.

### 3.4 Privater Windows-HUD und Capture-Ausschluss

Vorhandenen Native-Renderer/Controller vervollständigen, nicht parallel ersetzen. Im Modus private liegen alle sichtbaren Allie-HUD-Elemente in einem eigenen transparenten nativen Top-Level-Fenster: Pfeile, Bubble, Facts, Bewertung, Tooltips, Markierungen und gegebenenfalls Control-Popups. Browser-DOM, SVG, Canvas, Shadow-DOM und Viewer-Capture-Fläche bleiben frei davon. Click-Through und No-Activate erhalten; das Brett bleibt sichtbar und bedienbar.

Eine zentrale Renderinstanz entscheidet: private = nur geschützter Native-HUD; normal = vorhandener normaler Renderer, Native aus; unsupported/exclusion_error = kein HUD und kein stiller DOM-Fallback; stopped/stale/end_position = alles leer/verborgen. normal → private zuerst DOM/Viewer leeren, Schutz prüfen, dann Native zeigen; private → normal zuerst Native verbergen. Session/Generation/Render-Revision sichern den Wechsel gegen Rennen ab.

Windows-API SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE = 0x11) nur für das eigene Top-Level-HWND nutzen; mit GetWindowDisplayAffinity kontrollieren. ctypes-argtypes/restype, Pointer-/Handle-Größen und GetLastError korrekt definieren. Voraussetzungen der Ziel-Windows-Version/DWM anhand offizieller Quellen und realer Tests prüfen. WDA_MONITOR oder eine schwarze Capture-Fläche nicht als gleichwertigen Erfolg ausgeben.

Fenster zunächst unsichtbar erzeugen, DPI/Position/Click-Through/No-Activate konfigurieren, Ausschluss setzen und zurücklesen, Schutz-/DWM-Bereitschaft sicherstellen, erst dann anzeigen: kein ungeschützter Erstframe. Bei HWND-/WinIdChange, Reparenting, Neustart, Displaywechsel, RDP/Resume erneut validieren. Bei fehlender Unterstützung, API-Fehler, ungültigem Zustand oder ungeklärter Capture-Kompatibilität fail closed: HUD verbergen, lokalen technischen Status melden, normal nur auf ausdrückliche Auswahl.

UI/Tray-Schalter „Privates Overlay: Ein/Aus“ und tatsächlicher Status aktiv/nicht unterstützt/fehlerhaft/verborgen; Einstellung persistent, erfolgreicher Installationsstandard Ein. Debug-normal ist bereits ausschließlich für die Pfeildiagnose erlaubt: Status offen kennzeichnen, im Checkpoint festhalten und nach der Diagnose wieder private setzen. Vor finaler Abnahme, Paketierung und Release erneut prüfen. Eine Unterbrechung darf nicht unbemerkt einen vermeintlich privaten, tatsächlich normalen Modus hinterlassen. Beim Wiederanlauf einen unklaren Modus zunächst private/hidden behandeln; Debug-normal nur gezielt erneut aktivieren.

Capturepfade unterscheiden: Tab-, Browserfenster- und Monitoraufnahme, OBS-Methoden, Browser-getDisplayMedia sowie verfügbare Discord-/Zoom-/Teams-Probeaufnahmen separat. Erfolgreiche Win32-Rückgabe beweist keine Unsichtbarkeit in jeder Anwendung. Keine Garantie für Kameras, Capture-Karten, Spiegelung oder inkompatible Hooks/Remote-Pfade. Taskleisten-/Tray-Inhalte sind nicht automatisch durch die HUD-Affinity geschützt; im Privatmodus keine neuen verräterischen Tray-Toasts, Steuerung bei Bedarf über vorhandene/konfigurierbare Hotkeys. Keine Treiber, fremden Prozessmanipulationen, Capture-Hooks oder ungeprüften DLL-Downloads.

### 3.5 Gemeinsamer Vertrag, Pipeline und Performance

Vorhandene typisierte PositionSnapshot-/AnalysisResult-/Visual-Verträge konsolidieren, nicht eine zweite Tracker-/Engineinstanz schaffen. Relevante Felder: schema_version, source/source_id, session_id, generation, render_revision, geometry_revision, analysis_key, fen/fen_confidence, history_complete, turn_verified, turn, board_orientation/orientation, player_side, model_revision, engine_revision, updated_at, mode, target_window, geometry, arrows, messages, visible. Geometrie umfasst Board-Rect, Viewport, DPR und Orientierung. Pfeilrollen/Farben zentral festlegen; Beispielwerte sind keine Laufzeitdaten. Pydantic-/JSON-Schema und daraus abgeleitete Typen dort einsetzen, wo dies bestehende Contract-Divergenzen reduziert.

Verbindlicher Datenfluss: DOM/MediaDevices/Manual-PGN → Observe/Validate → Board/Player/Orientation normalisieren → Stabilisierung/History → Legalität/FEN-Vertrauen → latest-only Scheduler → Allie analyze/predict → begrenzte Stockfish-Prüfungen → Risiko-/Opening-Hinweise → versioniertes Ergebnis → private_native/normal_dom/hidden. Sichtbarkeit nur bei passender aktiver Session, validierter Stellung/analysis_key, aktuellen Revisionen, gültiger Geometrie und bestätigter Schutzbereitschaft.

Zustände idle, capturing, confirming, tracking, analyzing, ready, stale, ended, error mit eindeutigen Übergängen. Je Live-Session genau ein aktueller Analysejob und höchstens ein wartender neuer Job; alte Queue-Einträge zusammenfassen. Analyse-Key an Session, Generation, vollständigen validierten Boardzustand, Settings und Modell-/Engine-Revision binden. Rein geometrische Änderungen lösen keine neue Modellinferenz aus.

Stockfish-Suche soweit möglich wirklich stoppen; nicht abbrechbare Allie-Inferenz darf auslaufen, ihr altes Ergebnis wird aber verworfen. Keine vorgetäuschten Abbrüche. Netzwerk/OCR/Inferenz außerhalb zentraler Locks; Backpressure, CPU-/Speichergrenzen und klare Prozessverantwortung. Modell einmal initialisieren, Warm-up vom GUI-Start trennen, bei Mode-Switch nicht neu laden. Stop idempotent und ohne verwaiste eigene Worker, HWNDs oder Verbindungen.

Bestehenden Loopback-Kanal nutzen. WebSocket/SSE nur, falls dadurch tatsächlich einfacher; rate-limitiertes HTTP ist zulässig. Allie-Signaturen einschließlich moves, white_elo, black_elo, time_control, clocks sowie predict/Top-k gegen die reale Revision prüfen. Aggressiven Stil und objektive Sicherheit getrennt darstellen; Eigenmatt, unmittelbare Widerlegung und klar schlechte Material-/Eval-Lage nicht als „sicher“ kennzeichnen.

Messwerte mit Szenario, Hardware und Revision erfassen: capture_ms, recognition_ms, history_ms, queue_wait_ms, allie_ms, stockfish_ms, render_ms, end_to_end_ms, dropped_frames, stale_results, capture_exclusion_state, fps, RSS/RAM und CPU. Reproduzierbare Cold-/Warm-Läufe mit mindestens 30 Frames/Positionen für Browser/Viewer, p50/p95 und Idle-/Recovery-Verhalten. Budgets aus realer Baseline ableiten, keine erfundenen Millisekundenwerte. Historische Benchmarks erst reproduzieren; Messungen sollen die UI nicht unnötig bremsen.

### 3.6 Bibliotheken, Edge und Cleanup

Fertige, passende Bausteine und vorhandene Abhängigkeiten vor großem Eigenbau bevorzugen. Keine pauschale Framework-Migration oder große neue Abhängigkeit. Falls der vorhandene Renderer nicht genügt, PySide6/QPainter in einem kleinen Windows-Prototyp hinsichtlich Alpha, Click-Through, Latenz, Bundlegröße und PyInstaller-Plugins messen; nur bei belegtem Bedarf/Vorteil übernehmen. Bei Qt QWidget/QPainter, FramelessWindowHint, WA_TranslucentBackground, WindowTransparentForInput und winId()/WinIdChange korrekt konfigurieren und testen. Ein vorhandener einfacherer Win32-Renderer kann die bessere Wahl sein. Electron/setContentProtection/setIgnoreMouseEvents ist nur eine begründete Alternative, kein Standardumbau.

Context7/Firecrawl nur nutzen, wenn tatsächlich verfügbar; sonst zugängliche offizielle Primärquellen verwenden. Versionen, API-Grenzen, Release Notes und Lizenzen zum Implementationszeitpunkt gegen Lockfiles prüfen. Referenzen EliseyRotar/Eli6Overlay, Ibook000/dwm-draw-overlay und safzanpirani/acecoder-open sind Rechercheanker, keine freigegebenen Binärpakete: Source, Lizenz, Aktivität, Issues und Build-Integrität vor Übernahme prüfen.

Playwright für DOM-/Viewer-E2E; vorhandene Python-/JS-Tests erweitern. pytest/Hypothesis, Ruff, mypy/pyright, Vulture, deptry, TypeScript/tsc/knip nur passend einsetzen. chessops nur bei begründetem Nutzen und geprüfter Lizenzverträglichkeit; keine konkurrierende eigene Schachregel-Engine. WXT höchstens nach funktionierendem HUD bei echtem Bedarf. IDE-Erweiterungen, Debugger, Process Explorer/Spy++ sind Entwicklungswerkzeuge, keine Runtime-Abhängigkeiten. Notwendige Pakete gezielt in Projektumgebung und Lockfiles pinnen, nicht wahllos global installieren.

MV3-Alarme, Worker-Lifecycle und Recovery nach aktueller Zielbrowser-API korrigieren und testen; den Service Worker nicht künstlich permanent wachhalten. Manifest, Python-Paket, Launcher und Build-Artefakte einem konsistenten Release zuordnen; formatspezifische Versionsdarstellungen sind erlaubt. Tatsächlich geladenen Content-Script-/Erweiterungsstand mit Laufzeitnachweis prüfen. Installationspfad, Edge-Reload, Tab-Neuladen, erforderlichenfalls vollständigen Neustart bzw. gesicherte Neuinstallation dokumentieren. Ein Versionsbump oder Neustart allein ist kein Nachweis, dass alter Code ersetzt wurde.

Cleanup selbst nach Feature-Fixes und vor finalen Tests/Build ausführen: tatsächlich tote Funktionen, Imports, doppelte Helfer, redundantes CSS, temporäre Diagnosen, Debug-Logs, unbenutzte Assets/Abhängigkeiten entfernen. Normal-Renderer, produktive dynamische Imports, FastAPI-Routen, PyInstaller-Hooks und Runtime-Assets erhalten. Statische Analyse durch Runtime-/Import-/Packaging-Tests absichern; nicht blind per Textsuche löschen. Danach Formatierung, Lint/Types, Schemas und Lockfile konsistent prüfen und gesamten Testlauf wiederholen.

### 3.7 Echte Windows-Distribution und privater Release

tools/build_exe.ps1 und reale PyInstaller-Specs für eine Windows-Onedir-Distribution vervollständigen. Native-/Qt-Komponenten, dynamische Imports, Torch/Transformers-Laufzeit, Modellrevision, Stockfish samt NNUE, Browser-/Viewer-Assets, Lizenz-/Versionsinformationen und erforderliche Runtime-Dateien sauber bündeln. Eine EXE, die nur START_HIER.bat/uv im Checkout aufruft, erfüllt das Standalone-Ziel nicht.

Modellgewichte entweder zulässig offline bündeln oder einen explizit dokumentierten First-run-Download anbieten; kein heimlicher Download im Offline-Test. Build in frischem isoliertem Pfad ohne Checkout, uv oder globale Python-Installation starten; frisches Windows-Benutzerprofil/Fresh-Machine-Szenario und den zugesagten Offline-Betrieb prüfen. Erster/zweiter Start, belegter Port, Tray, Viewer, Browser-Rückkanal, healthz/readyz, Modell/Stockfish, Private-HUD, Stop und Neustart müssen funktionieren. Nach Fixes Build neu erzeugen.

Konsistente Version, Distribution und optional ZIP, Artefaktgrößen, SHA-256 für EXE/ZIP/Lockfile, Dependency-/SBOM- und Lizenzinformationen liefern. Keine Secrets, Tokens, privaten Nutzerdaten oder unnötigen lokalen Logs bündeln. Ohne echte Windows-Umgebung alle erreichbaren Code-/Unit-Arbeiten abschließen, aber Windows-Build/Capture-E2E als blockiert ausweisen; Linux-/Mock-Tests ersetzen keinen bestandenen Windows-Nachweis.

GitHub: vorhandenes, eindeutig zugeordnetes privates Remote und berechtigte Authentifizierung prüfen. Nur dann sind normaler Branch-Push, passender semantischer Tag, Release-Notes und Upload der verifizierten Artefakte autorisiert. Repository-Sichtbarkeit tatsächlich kontrollieren; ein als „private“ benannter Release genügt nicht. Kein öffentlicher Release, kein geratenes Ziel, keine eigenmächtige Repository-Neuanlage/Sichtbarkeitsänderung, kein Force-Push und keine Ausgabe von Zugangsdaten.

Fehlendes/mehrdeutiges Remote oder fehlende Authentifizierung darf lokale Implementierung und Tests nicht verhindern. Danach eine einzige gezielte Rückfrage zu den noch benötigten externen Angaben stellen. Ein nur vorbereiteter Release ist nicht veröffentlicht. Pflichtabnahmen nicht zugunsten eines schnellen Uploads überspringen.

## 4. GOAL-Funktion und belegbare Abnahme

GOAL = 100 % genau dann, wenn alle zehn Pflichtziele PASS sind. Pro Ziel PASS / FAIL / BLOCKED / UNTESTED plus Beleg führen. BLOCKED, UNTESTED und ausgelassene Tests sind nicht PASS. Die Liste darf nicht nachträglich verkleinert werden, um Erfolg zu behaupten; optionale Werkzeuge sind dagegen keine zusätzlichen Pflichtziele.

G1 Arbeitsstand gerettet: realer Checkout und Teilpatches gesichert, persistenter Auftrag/Fortschritt vorhanden, nachvollziehbare Wiederaufnahme möglich.
G2 Pfeile/Lifecycle: Browser, Viewer und Native feldgenau; Resize/Scroll/Zoom/Transformation/Flip ohne Drift; Navigation, Stop und verspätete Frames ohne alte Anzeige; keine Leaks, Duplikate oder Input-Blockierung.
G3 Eröffnungen/Schach: gewünschte Auswahl, legale Transpositionen, echte History, korrekte Gegnerabweichung und unveränderter Fallback; keine unpassenden Buchalternativen und keine Request-Regression.
G4 Erweiterung: Versionsstand konsistent, aktueller Code nachweislich geladen, MV3-Alarm-/Worker-Lifecycle und Reload dokumentiert/getestet.
G5 Privater Modus: final Ein, normaler Debug-Modus beendet; lokal sichtbarer HUD, kein privater DOM-Leak, Fail-Closed/Erstframe-/HWND-Recovery korrekt und reale Capture-Nachweise pro unterstütztem Pfad.
G6 Pipeline/Funktionserhalt: Allie-first, Stockfish-Zusatz, Session-/Job-/Contract-Semantik und bestehende Produktfunktionen durch Regressionstests bestätigt.
G7 Qualität: Cleanup abgeschlossen, relevante Gesamt-/Lint-/Type-/E2E-Tests bestanden, Performance nachvollziehbar gemessen, Start/Stop ohne eigene Prozessreste.
G8 Windows-Paket: tatsächlich erzeugte autonome Onedir-Distribution mit Hashes/Lizenzen, sauberem Fresh-Path-/Profil-Test und wahrheitsgemäßem Offline-/Modellstatus.
G9 Dokumentation: Installation, Modellbereitstellung, Edge-Reload, Capture-Kompatibilität, Tests, Build, Betrieb, Rollback und Resume entsprechen dem getesteten Stand.
G10 Privater Release: privates Ziel verifiziert, getesteter Commit/Tag gepusht, Release und Asset-Inhalte tatsächlich vorhanden und geprüft.

Belege pro relevantem Lauf: Befehl, Arbeitsverzeichnis/Umgebung, Revision bzw. Dirty-Stand, Zeitpunkt, Exitcode, Testanzahl und Log-/Artefaktpfad. Unvollständige Python-Umgebung reproduzierbar über Projekt-Lockfile und notwendige Extras herstellen. Nicht einfach Tests deaktivieren oder fehlende Pakete als grünes Ergebnis behandeln. Baselinefehler getrennt von neuen Regressionen erfassen; nach finalem Cleanup erneut testen.

Befehle aus dem echten Repo ableiten. Mögliche Ausgangspunkte, keine Behauptung bereits ausgeführter Tests: uv sync --frozen mit bewusst gewählten Extras; uv run python -m unittest discover -s tests -p 'test_*.py'; vorhandene test_chess.py-/test_overlay_*.js-Skripte; konfigurierte pytest-, Syntax-, Ruff-, Typecheck- und Playwright-Läufe; powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_exe.ps1. Nicht blind --all-extras mit großen Vision-Paketen installieren; Lockfile vor Build korrekt aktualisieren, danach eingefroren verwenden.

Mindestens folgende Regressionen abdecken:
- Chess.com und Lichess mit Weiß/Schwarz, getrennten Spieler-/Orientierungs-/Zugrecht-Werten, Board-Flip, Promotion, Rochade/En-passant, ungültigen SAN/PGN/UCI/FEN, fehlenden Königen, Matt/Patt, unvollständiger History sowie Drei-/Fünffachwiederholung sowie 50-/75-Züge-Regeln nur bei ausreichender History.
- Unveränderte FEN bei Layoutänderung, Scroll, Zoom, CSS-Transformation, DPR-/Monitorwechsel, Fensterbewegung und Viewer-Geometrie ohne neuen Frame. DOM und Native müssen dieselben UCI-Quell-/Zielfelder zeigen.
- Neue Partie/SPA/Import/Reset/Stop/Enginefehler; alte Session; vertauschte Generationen/Revisionen; späte HTTP-Requests nach Abbruch; gleichzeitige Clear-/Show-/Mode-Wechsel; Listener-Cleanup und keine blockierte Brettbedienung.
- Opening-Auswahl beider Farben, Transpositionen, unpassende Gegnerantworten, keine passenden Buchzüge, Buchphasenende, ausgeschaltete Präferenz und opening_white/opening_black im Request.
- Private off/on, API-Fehler, HWND-Neuerstellung, Verbindungsverlust, Minimize/Fokusverlust, RDP/Resume und ungeschützter Erstframe. Bei Fehlern kein DOM-Fallback und kein stehen gebliebenes HUD.
- Tab-/Window-/Monitor-getDisplayMedia und OBS Display-/Window-Capture getrennt nach Methode, gegebenenfalls Game Capture; weitere tatsächlich verfügbare Aufnahme-Apps separat dokumentieren. Browser-Freigaben respektieren.
- Windows-Distribution in isolierter Umgebung, Start/Ready, belegter Port, Modell-/Engine-Finden, Tray/Viewer/Rückkanal, Stop ohne Reste und Neustart.

Für Capture-Abnahme immer zwei unabhängige Nachweise: gesetzte/zurückgelesene HWND-Affinity UND reale Probeaufnahme/Preview mit lokal weiterhin sichtbarem HUD und im Capture vollständig sichtbarem Brett ohne Allie-Zeichnungen/schwarze Ersatzfläche. Ein Screenshot, der den geschützten HUD absichtlich auslässt, beweist allein nicht seine lokale Sichtbarkeit. Mocks und Headless-Tests nur entsprechend kennzeichnen. Nicht verfügbare Capture-Methode als ungetestet/nicht freigegeben dokumentieren, niemals pauschal Schutz behaupten.

## 5. Dauerhafter Arbeitsstand und Ergebnislieferung

Speichere diesen vollständigen konsolidierten Auftrag im Repository als AGENT_TASK.md oder in der bereits bestehenden gleichwertigen Auftragsdatei. AGENT_PROGRESS.md ist der knappe, verbindliche Wiederaufnahmepunkt; bestehende Inhalte und Erkenntnisse erhalten. Keine unnötige Sammlung konkurrierender Plan-/Report-Dateien erzeugen.

Der Hauptagent aktualisiert AGENT_PROGRESS.md nach jedem abgeschlossenen Teilfix, relevanten Test-/Buildlauf und Integrationsschritt sowie vor absehbarem Kontextwechsel. Nicht bis zur letzten Nachricht warten: Ein hartes Limit kann jederzeit eintreten. Checkpoints atomar schreiben; nur ein koordinierter Schreiber, Subagents liefern ihre Ergebnisse an ihn.

Jeder Checkpoint enthält: Auftragsdateipfad und GOAL-Liste mit Belegen; realen Repo-/Branch-/HEAD-/Dirty-Stand samt gesicherten Änderungen; aktuelle Phase; erledigte/nicht erledigte Teilpatches; konkrete Entscheidungen und noch unbewiesene Hypothesen; geänderte Dateien; letzte Befehle/Exitcodes/Logpfade; Agentenaufgaben und tatsächlich integrierte Ergebnisse; bekannte Fehler/Blocker; aktuellen private/normal-/Capture-Affinity-Status; laufende eigene Prozesse/Jobs; Build-/Release-Status; als Nächstes auszuführenden Befehl oder klar abgegrenzten Patch mit erwarteter Prüfung. Keine Secrets speichern.

Git-Commits logisch und nachvollziehbar halten. Unfertige Zwischenstände eindeutig kennzeichnen; Git nicht mit einem sicheren Backup unversionierter Dateien verwechseln. Keine erzwungenen Checkpoint-Commits fremder Änderungen. Auftrags-/Fortschrittsdatei bei einem Workspacewechsel zusammen mit den benötigten Quelländerungen erhalten; ein Dateiname allein stellt keinen anderen Workspace wieder her.

Pflege README/Release-Notizen mit tatsächlichen Installations-, Modell-, Start/Stop-, Edge-Reload-, Debug-/Privatmodus-, Test-, Build- und Rollback-Schritten. Capture-Matrix, Benchmarks, Artefakthashes und bekannte Einschränkungen müssen auffindbar sein. Dokumentation muss zum getesteten Paket passen.

Zwischenmeldungen auf Deutsch: kurz, konkrete erreichte Änderung oder Blocker, ohne immer neue Pläne und ohne Arbeitszeitversprechen. Abschluss: belegte Ursachen/Fixes; geänderte und entfernte Dateien mit Zweck; übernommene/verworfene Bausteine mit Grund; echte Befehle/Exitcodes/Testzahlen; Capture-Modus und Matrix; p50/p95 samt Hardware; EXE-/ZIP-Pfad, Größen, SHA-256, Standalone-/Modell-/Offline-/Fresh-Path-Status; Installation/Reload/Rollback; verbleibende konkrete Grenzen; GOAL-Liste. Commit, Tag und private Release-URL nur nennen, wenn vorhanden und verifiziert. Bei Blockierung sachlich „teilweise umgesetzt / noch nicht vollständig abgenommen“ melden, nicht „fertig“.

## 6. Ausführung, mehrere Agents und Wiederaufnahme

Löse die alten Ablaufwidersprüche so: Das umfangreiche Audit ist bereits als Verlauf vorhanden; jetzt nur einen kurzen read-only Wiederaufnahme-Abgleich und gezielte Reproduktion der noch offenen Befunde durchführen. Danach implementieren. Keine neue Runde reiner Review-Agenten oder abstrakter Reports. Unabhängige Qualitätsprüfung bedeutet tatsächlich ausgeführte Tests, nicht bloß eine weitere Meinung.

Nutze mehrere Agents nur, wenn die Umgebung echte Subagenten unterstützt und Aufgaben sinnvoll parallel sind. Geeignete Implementierungs-/Testpakete: A Browser-/Viewer-Geometrie und SPA-Lifecycle; B Opening-Legalität/Fallback mit Regressionen; C Native-/MV3-/Versions-/Windows-Paketierungsaufgaben. Der Hauptagent bleibt Integrator und hält gemeinsame Kontrakte, live_server.py und andere gemeinsam betroffene Dateien unter klarer Schreibzuständigkeit. Separate Worktrees nur, wenn sie den vorhandenen Dirty-Stand korrekt übernehmen/schützen; sonst nicht überlappende Dateizuständigkeiten oder serielle Integration.

Jeder Agent liefert tatsächliche Diffs, ausgeführte Tests und offene Grenzen. Keine parallelen Überschreibungen, doppelten Frameworks oder endlosen Auditketten. Kein Erfolg allein aufgrund eines Agentenberichts: Integrator prüft Diffs und relevante Tests. Ohne Subagenten dieselben Pakete selbst abarbeiten; keine imaginären Agenten melden. Verfügbare Superpowers-/Debugging-/TDD-Werkzeuge gezielt nutzen, ohne die ausdrücklich gewünschte Fortsetzung durch neue Freigaberunden für bereits beschlossene Anforderungen zu blockieren.

Arbeitsreihenfolge:
1. Auftrag/Fortschritt/Git/Teilpatches abgleichen und sichern; nur fehlende Informationen gezielt prüfen. Den begonnenen ResizeObserver-/Paint-Patch lokalisieren.
2. Für noch offene Fehler gezielte rote Regressionen bzw. nachvollziehbare Reproduktionen erstellen; kleinste passende Fixes für Repaint/Transform, Navigation, Viewer-Geometrie, monotones Native-Gate, Opening-Auswahl, MV3 und Versionen umsetzen.
3. Bestehenden Native-HUD und Datenfluss gegen alle Master-Anforderungen vervollständigen. Temporären normal-Debugmodus beenden; private einschalten und Schutz testen.
4. Integrieren, gesamte Regression/Browser-/Windows-Capture-Prüfung und Performance-Messung ausführen; Fehler beheben. Cleanup, dann finale Prüfungen erneut.
5. Reproduzierbaren Windows-Build erstellen, isoliert starten/testen, Hashes/Lizenzen/Dokumentation sichern. Erst aus dem abgenommenen Stand Commit/Tag und berechtigten privaten Release erzeugen; Remote/Assets nochmals verifizieren.

Die GOAL-Funktion ist eine verbindliche Steuerungsregel, keine behauptete spezielle Plattformfunktion. Falls eine echte integrierte Goal-/Task-Funktion verfügbar ist, darfst du dieses Ziel dort abbilden; andernfalls genügen Auftragsdatei, Fortschrittsdatei und Tests. Keine erfundene /goal-Funktion, kein zusätzlicher Scheduler und keine Konto-/Limitumgehung.

Wiederaufnahme bei neuem Chat, Accountwechsel oder Kontextreset:
- Zuerst AGENT_TASK.md, AGENT_PROGRESS.md und die referenzierten Belege lesen; tatsächlichen Git-/Dateistand damit vergleichen.
- Historische Angaben, unintegrierte Agentenpatches und aktuell verifizierte Tatsachen auseinanderhalten. Fehlende Checkpoints aus diesem Auftrag und vorhandenen Diffs rekonstruieren.
- Den dokumentierten nächsten Schritt ausführen, mit gezieltem Smoke-/Regressionstest absichern und fortsetzen. Nicht alles neu analysieren; nicht annehmen, alte Agents/Prozesse lebten noch.
- Die Nutzernachricht „Weiter bis GOAL = 100 %“ bedeutet: diesen Wiederaufnahmeablauf starten und offene Pflichtziele weiterbearbeiten, nicht Anforderungen neu erfragen.

Ein Usage-/Kontextlimit kann nicht umgangen werden. Bei absehbarer Unterbrechung sofort sichern und den exakten nächsten Schritt hinterlassen. Nach einem harten Abbruch den letzten gespeicherten Checkpoint verwenden; nicht behaupten, nachträglich noch gespeichert zu haben. Automatische Fortsetzung nur bei einer tatsächlich vorhandenen, erlaubten Plattformfunktion; sonst beim nächsten vom Nutzer gestarteten Lauf. Kein versprochenes selbstständiges Aufwachen zu einer Uhrzeit und keine angebliche Erinnerung über Konten hinweg.

STOP nur bei vollständiger Abnahme, ausdrücklichem Nutzerstopp, erreichtem Plattformlimit oder einem echten externen Blocker, der die noch mögliche Arbeit verhindert. Ein blockierter Release rechtfertigt nicht, erreichbare lokale Aufgaben liegen zu lassen. Keine Nachfrage für normale reversible Implementierungsentscheidungen. Bei fehlendem Quellzugriff sofort den konkreten Zugriff benennen; bei späteren Windows-/Remote-/Auth-Blockern zuerst alles unabhängig Erreichbare erledigen und dann die notwendigen Angaben gebündelt anfordern. Fehlgeschlagene Ansätze ursachenbezogen ändern statt identische Fehler oder Analysen endlos zu wiederholen.

## 7. Letzte Kontrolle und sofortiger Einstieg

Vor einer Erfolgsmeldung alle G1-G10 mit aktuellen Belegen prüfen. Sind alle verpflichtenden Master-Anforderungen im getesteten Stand enthalten? Sind die begonnenen Teilpatches wirklich integriert? Bleiben Farben, Allie-first, History, Opening-Optionen und Fallback erhalten? Sind alte Frames/Partien ausgeschlossen und Edge-Versionen nachgewiesen? Ist private wieder aktiv, ohne DOM-Leak, mit echter Capture-Probe? Wurden nach Cleanup Tests und Windows-Paketierung tatsächlich ausgeführt? Startet das Paket ohne Checkout/uv/globales Python? Stimmen Hashes, Commit/Tag und hochgeladene Release-Assets überein? Ist das Repository nachweislich privat? Kann eine neue Sitzung aus den gespeicherten Dateien fortsetzen?

Ungeprüfte Antworten bleiben UNTESTED/BLOCKED, keine erfundenen Erfolge. Ein fehlender Windows-Test oder Release wird nicht durch einen guten Prompt, einen Plan, einen Mock oder einen Agentenbericht ersetzt.

Beginne jetzt mit dem vorhandenen AGENT_PROGRESS.md, dem tatsächlichen Git-/Dateistand und dem zuletzt begonnenen ResizeObserver-/Paint-Fix. Sichere die vorhandene Arbeit, bestätige kurz den realen Wiederaufnahmepunkt und arbeite von dort bis zur vollständigen GOAL-Abnahme oder einem sauber dokumentierten unvermeidbaren Blocker weiter.