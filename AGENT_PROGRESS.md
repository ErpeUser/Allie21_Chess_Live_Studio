# Allie 2.1 - Arbeitsfortschritt

## Ziel

Die bestehende Allie-2.1-Chess.com-Live-Overlay-Erweiterung soll lokal verifiziert, minimal repariert, dokumentiert und nur bei eindeutigem privaten GitHub-Remote veröffentlicht werden. GOAL = 100 % erst bei stabilem Pfeil-Rendering, korrekter Eröffnungsbuch-Integration mit legalem Fallback, konsistentem Edge-Stand, aktivem Capture-Schutz, grünen Tests/Smoke-Checks und verifiziertem privatem Release.

## Phase / Stand

- Phase: Lokale Fixes, Regressionen, Build-Smoketest und GOAL-Abnahme dokumentiert; externe Windows-/Remote-Nachweise offen.
- Auftragsdatei: `AGENT_TASK.md` (vollständiger konsolidierter Fortsetzungsauftrag).
- Branch: `codex/allie-first-exe`
- Remote: keiner konfiguriert; daher aktuell kein Release möglich.
- Manifest-Version: `11.2.16.0` / `11.2.16`
- Python-Projektversion: `11.2.16` (mit uv.lock/Manifest angeglichen)
- Arbeitsbaum: mehrere bestehende Änderungen und neue Dateien vorhanden; nichts davon wurde verworfen.

## Agentenberichte

- Pfeile: board-lokales SVG, Resize/Scroll/visualViewport/ResizeObserver-Repaint und SPA-Session-Invalidierung sind integriert; `replaceChildren` und `pointer-events:none` bleiben erhalten.
- Eröffnungsbuch: 3.865 TSV-PGNs sind legal; Auswahl bleibt nach Abweichung strikt auf der aktiven Linie, EPD-Schlüssel berücksichtigen Zugrecht/Rochade/En-passant.
- Manifest/Capture: Manifest/Userscript/Python/uv.lock `11.2.16`; MV3-Alarm 30 s mit Recovery; Native-Capture-Affinität fail-closed und Session-/Revision-Gate integriert. Echte Windows/OBS-Verifikation fehlt.

## Baseline / aktueller Nachweis

- `.allie-venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -q` am 09.11.2026: 96 Tests, OK, 1 Skip.
- Alle neun `tests/test_*.js`-Fixtures am 09.11.2026: OK.
- `node --check browser/allie21_overlay.user.js` und `browser/background.js`: OK.
- Manifest JSON: OK.
- `uv run --frozen ...`: in dieser Umgebung weiterhin wegen fehlender gecachter `chess-tcn`-Distribution bzw. uv-Cache-Lock nicht ausführbar; `.allie-venv`-Tests und `doctor.py` sind der reproduzierbare Nachweis.

## Checkpoint 09.11.2026 05:34

- Repo/Branch/HEAD: `codex/allie-first-exe` / `59463bd`; Arbeitsbaum bleibt absichtlich dirty, keine Änderungen verworfen.
- Aktive Teilaufgaben: `/root/browser_lifecycle` (nur Browser/Viewer), `/root/openings_legal` (nur Opening/Chess), `/root/native_mv3_packaging` (nur Native/MV3/Version/Build).
- Eigene Prozesse/Jobs: keine gestarteten Dauerprozesse; Tests liefen im `.allie-venv`.
- Private-Modus: Userscript defaultet `privateMode=true`; lokale Native-Affinität ist fail-closed implementiert, echte Windows-/OBS-Aufnahme jedoch ungetestet.
- Release: kein Remote; kein Commit/Tag/Upload ausgeführt.

## Nächste Schritte

1. Bei neuer Sitzung diesen Checkpoint lesen und nur noch externe Nachweise bzw. ausdrücklich freigegebene Integrationsschritte fortsetzen.
2. Capture-/Fresh-Path-/Edge-E2E auf echter Zielumgebung ausführen, falls sie verfügbar gemacht wird.
3. Nur bei eindeutigem privatem Remote und verifizierter Authentifizierung committen/taggen/pushen/releasen; sonst als externer Blocker dokumentieren.

## Checkpoint 09.11.2026 05:52

- Browser-/Viewer-Teilfix integriert: board-lokales SVG, Resize/Scroll/visualViewport/ResizeObserver-Repaint, CSS-Transform-Folge, SPA-Navigation mit neuer Session-ID und Listener-Cleanup. Neuer JS-Test `tests/test_overlay_geometry_lifecycle.js`.
- Opening-Teilfix integriert: Auswahl bleibt strikt auf der aktiven Linie; EPD inklusive Zugrecht/Rochade/En-passant statt placement-only FEN-Fallback. Transpositions- und Gegnerabweichungs-Regressionen ergänzt.
- Native-/MV3-Teilfix integriert: monotones `(generation, render_revision)`-Gate, retired sessions, Affinität fail-closed, MV3-Alarm 30 s mit Recovery, Version `11.2.16` in Python/Lockfile/Manifest.
- Zusätzlicher Lifecycle-Fix: `/api/overlay/clear` akzeptiert Session-/Revisionsgrenze und retiert alte Session-Frames; Browser und Viewer senden diese Grenze bei Navigation/Focus/Stop. Regressionen in `tests/test_native_overlay.py` und `tests/test_http_offline.py`.
- Verifizierte Läufe: Python `unittest discover` 96 Tests OK, 1 Skip; alle 9 JS-Fixtures plus `node --check` für Userscript/Service Worker OK; Manifest JSON parse OK; `git diff --check` ohne inhaltliche Fehler.
- Offene Nachweise: echte Windows-DPI/HWND-/OBS-/getDisplayMedia-Capture-Proben, autonomer Onedir-Build im frischen Windows-Profil und privater GitHub-Release sind weiterhin BLOCKED (kein Remote bzw. keine separate Windows-Capture-Abnahme in dieser Umgebung).
- Nächster Integrationsbefehl: Build-/Launcher-Smoke prüfen, Dokumentation/Hashes mit dem tatsächlich getesteten Stand abgleichen, danach GOAL G1-G10 einzeln bewerten.

## Checkpoint 09.11.2026 06:04

- Buildlauf: `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_exe.ps1` Exitcode 0; Onedir-Distribution neu erzeugt (EXE 2.625.153 Byte, Gesamt 33.122.286 Byte).
- Launcher: `tools\launcher.py --check` im Checkout Exitcode 0. Isolierte Fresh-Path-Kopie ohne Projektdateien Exitcode 2; deshalb G8 weiterhin BLOCKED statt als Standalone ausgegeben.
- Hashes und Status in `VERSIONEN.md`, Bedien-/Resume-/Blocker-Hinweise in `README_DE.md`, Release-Hinweis in `CHANGELOG.md` aktualisiert.
- Zusätzlicher stale-Clear-Fix geprüft: Session-boundary-Clear in Native/HTTP/Browser/Viewer; gezielte Native- und HTTP-Regressionen OK.
- Nächster Befehl: finaler Volltest nach Dokumentations-/Clear-Änderungen, anschließend G1-G10-Abnahmebericht und ggf. verbleibende externe Angaben bündeln.

## GOAL-Abnahme am 09.11.2026

| Ziel | Status | Beleg / Grenze |
|---|---|---|
| G1 Arbeitsstand gerettet | PASS | `AGENT_TASK.md`, `AGENT_PROGRESS.md`, Branch/HEAD/Dirty-Stand und nächste Schritte gesichert. |
| G2 Pfeile/Lifecycle | UNTESTED | 9 JS-Fixtures und Syntaxchecks PASS; reale Playwright-/Browser-Zoom-/DPI-/Fensterbewegungs-E2E nicht ausgeführt. |
| G3 Eröffnungen/Schach | PASS | 43 Chess-Regressionen im Vollauf 97 Tests PASS; EPD-/Transpositions-/Abweichungs-/Fallback-Fälle enthalten. |
| G4 Erweiterung | UNTESTED | Version 11.2.16 konsistent, MV3-Alarmlogik statisch/Node geprüft; tatsächliches Edge-Reload und geladener Content-Script-Stand nicht verifiziert. |
| G5 Privater Modus | BLOCKED | Native Affinität/Fail-Closed und Mocktests PASS; echte HWND-Rücklesung plus OBS/getDisplayMedia/Discord/Zoom/Teams-Proben fehlen. |
| G6 Pipeline/Funktionserhalt | PASS | Python-Volltest 97 Tests PASS, 1 Skip; Allie-first-/Stockfish-/Session-/HTTP-Regressionsfälle enthalten. |
| G7 Qualität | UNTESTED | Qualitätsumgebung installierbar; Pytest 96 PASS/1 Skip, Ruff 55 Befunde und Mypy 24 Befunde; keine vollständige Lint-/Type-/Playwright-/p50/p95-Abnahme. |
| G8 Windows-Paket | PASS | Portables Onedir mit `app` + `runtime` gebaut; EXE `--check`, Runtime-Imports und Server-`/health` (HTTP 200) direkt aus dem Release-Ordner geprüft. Modell-Download bleibt First-Run. |
| G9 Dokumentation | PASS | README_DE, VERSIONEN, CHANGELOG, AGENT_TASK/PROGRESS entsprechen dem getesteten und explizit begrenzten Stand. |
| G10 Privater Release | PASS | Privates Repository, Commit, Tag `v11.2.16`, Branch-Push und Release-Asset verifiziert. |

## Checkpoint 09.11.2026 06:10

- `.allie-venv\Scripts\python.exe -m compileall -q backend tools`: Exitcode 0.
- `.allie-venv\Scripts\python.exe backend/doctor.py`: Exitcode 0; Python-/FastAPI-/Pydantic-/Uvicorn-/Vision-/Torch-/Stockfish-/Opening-/Browseraufnahme-Prüfungen OK.
- GOAL-Status bleibt unverändert: erreichbare lokale Regressionen PASS; reale Capture-, autonome Fresh-Path- und private Remote-Abnahmen BLOCKED/UNTESTED.

## Checkpoint 09.11.2026 06:20

- G2/G3/G7-Kernchecks erneut ausgeführt: 97 Python-Tests OK (1 Skip), alle 9 JS-Fixtures OK, `node --check` für Userscript/Service Worker OK, `compileall` OK. G3 bleibt PASS; G2 und G7 bleiben wegen fehlendem echten Edge/Playwright bzw. offenen Ruff/Mypy-Befunden UNTESTED, nicht wegen eines bekannten Runtime-Fehlers.
- G8 umgesetzt: `tools/build_exe.ps1` kopiert jetzt App-Dateien und die `.allie-venv`-Pakete in `release\Allie21 Chess Live Studio\app` und `runtime`. Portable EXE-Check, Import-Smoke und `/health` HTTP 200 bestanden; laufender Testprozess wurde beendet.
- Aktuelle Distribution: EXE 2.625.829 Byte, Gesamt 1.179.028.625 Byte; Hashes und First-Run-Modellhinweis in `VERSIONEN.md`, Bedienhinweis in `README_DE.md`.
- G10 war bis zur Reauth BLOCKED; nach erfolgreicher Reauth sind Repository, Branch, Tag und Release verifiziert.

## Checkpoint 09.11.2026 06:45

- GitHub-Reauth erfolgreich; privates Repository `https://github.com/ErpeUser/Allie21_Chess_Live_Studio` verifiziert. Branch `codex/allie-first-exe`, Tag `v11.2.16` und privater Release mit portablem ZIP-Asset sind vorhanden.
- Qualitätswerkzeuge als optionale `quality`-Abhängigkeiten dokumentiert. `tools\quality_check.ps1` installiert bei Bedarf in `.quality-venv` (eigener uv-Cache), setzt die geprüften `.allie-venv`-Pakete für Pytest wieder ein und kann Chromium mit `-InstallBrowsers` nachladen.
- Qualitätslauf: Pytest `97 passed, 1 skipped`; Ruff `55` Befunde; Mypy `24` Befunde. Diese Befunde sind sichtbar und werden nicht als bestanden behauptet. Runtime-Tests bleiben grün.

## Release-Status / Blocker

- Der lokale Onedir-Stand wurde neu gebaut; das vorhandene portable ZIP ist noch das vorherige Artefakt und wurde wegen fehlender AusfÃ¼hrungscredits nicht neu gepackt. Es ist daher fÃ¼r den aktuellen Dirty-Stand nicht als Release-Artefakt freigegeben.

Remote `origin` zeigt auf `https://github.com/ErpeUser/Allie21_Chess_Live_Studio.git`; Repository-Sichtbarkeit ist `private`. Release-URL: `https://github.com/ErpeUser/Allie21_Chess_Live_Studio/releases/tag/v11.2.16`.

## Wiederaufnahmeplan

Beim Fortsetzen zuerst diese Datei, `AGENT_TASK.md` und die referenzierten Agentenberichte lesen. Dann beim zuletzt offenen Schritt fortfahren; keine bereits verifizierten Arbeiten wiederholen.

## Checkpoint 09.11.2026 09:40

- Den wiedergefundenen Alt-Chat gegen `AGENT_TASK.md` abgeglichen; der aktuelle Checkout ist bereits der dort beschriebene Integrationsstand. Keine konkurrierenden Alt-Patches oder verlorenen Dateien gefunden.
- Qualitätsbereinigung integriert: Ruff-Importsortierung und sichere lokale Lint-Fixes, präzise Mypy-Typisierung an ctypes-/Payload-Grenzen, robuste Sequenz-/Bounds-Validierung und explizite `subprocess.run(check=False)`-Aufrufe. Breite Fehlerbehandlungen bleiben nur an bewusst fail-soften Modell/OCR/Win32-Grenzen mit begründeten lokalen `# noqa`-Hinweisen.
- Nachweis: `tools\quality_check.ps1` Exitcode 0; Ruff 0, Mypy 0, Pytest 96 passed / 1 skipped. Separater Unittest-Lauf: 97 Tests OK / 1 Skip.
- Browser-/Paket-Smokes erneut PASS: neun Node-Fixtures, `node --check` für Userscript/Service Worker, Manifest-JSON, `compileall`, Launcher-Check im Checkout und im portablen Ordner.
- Onedir-Build nach Freigabe eines ausschließlich projektbezogenen Stockfish-/Release-Prozesslocks erneut erfolgreich: EXE 2.625.831 Byte, Distribution 1.180.055.514 Byte. Aktuelle Hashes stehen in `VERSIONEN.md`.
- Verbleibende Grenzen unverändert: echte Edge-/Playwright-Zoom-/DPI-E2E, HWND-Affinitäts-Rücklesung sowie reale OBS/getDisplayMedia-/Discord-/Zoom-/Teams-Capture-Proben sind in dieser Umgebung nicht ausgeführt; diese Ziele bleiben UNTESTED/BLOCKED und werden nicht als PASS behauptet.

## Checkpoint 10.11.2026 — main 13131c8, gezielte Abschlusskorrekturen

- Die historische v11.2.16-/G10-Aussage oben bleibt als Übergabe erhalten; sie
  bezieht sich nicht auf den aktuellen `main`-Stand `13131c8`, der bislang noch
  keinen neuen Tag/Release besitzt.
- Behoben: `analysis_source=both` mit FEN oder leerer Allie-Kandidatenliste
  übernimmt verfügbare Stockfish-Linien in `my_moves`/`opponent_moves`, ohne
  eine vorhandene Allie-Reihenfolge zu ersetzen. Regression in
  `tests/test_chess.py` rot und anschließend grün ausgeführt.
- Behoben: MV3-Worker-/Options-Sandboxen ohne `chrome.action`,
  `runtime.getManifest()` oder optionale `management`-Berechtigung brechen nicht
  mehr; der Update-Check verwendet bei fehlender Management-API den lokalen
  Deployment-Stempel. Die 58 Node-Fixtures einschließlich der neuen Fälle sind
  grün.
- Behoben: Userscript und Viewer starten standardmäßig im privaten Modus;
  `off` bleibt eine explizite lokale Einstellung. Browser-/Viewer-Erststart-
  Regressionen sind abgedeckt.
- Behoben: Build-Skript verwendet den erwarteten benannten
  `$expectedStockfishSha256`-Vertrag. Installer-/Versions-Fixtures wurden auf
  die aktuelle unabhängige Edge-Version 11.2.18 aktualisiert; App/Userscript
  bleiben 11.2.17.
- Dokumentation: `VERSIONEN.md`, `README_DE.md` und `CHANGELOG.md` trennen den
  aktuellen `main`-Prüfstand vom historischen v11.2.16-Release.
- Letzte gezielte Befehle: `.venv2/bin/python -m unittest ...test_chess...` für
  den FEN-Fallback PASS; `node --test tests/*.js` 58/58 PASS; `python
  tools/check_versions.py` PASS. Der vollständige Python-Lauf ist noch nicht
  als PASS zu melden, solange die Projektumgebung nicht vollständig mit dem
  gelockten Torch-/Playwright-Stack installiert ist.
- Offene externe Nachweise: echter Windows-Onedir-Build/Fresh-Path, Edge-Reload,
  HWND-/OBS-/getDisplayMedia-Capture und GitHub-Actions-Nachlauf am neuen
  Commit. Keine EXE oder Release-URL wird für diesen Arbeitsstand behauptet.


## Checkpoint 12.11.2026 — final-integrity 11.2.22 worktree

- Ausgangsstand geprüft: remote `main` war `758776e4cd6ae19afd80e2628bed751207c295b1`; der aktuelle Abschluss wird über einen Review-Branch und anschließend per Pull Request in `main` integriert.
- Behoben: beide Opening-Auswahlen werden als `opening_selection.white/black` normalisiert und in Viewer, Userscript und Native-HUD sichtbar gemacht; die aktive Repertoirelinie bleibt seitenbezogen.
- Behoben: objektive Taktik-Blobs für unmittelbares Matt und vorsichtige mögliche Mattfolgen in zwei Zügen; bei FEN/unvollständigem Verlauf sind sie ausdrücklich als Stellungs-Hinweise markiert, während konkrete Pfeile und Repertoirezüge unterdrückt werden.
- Behoben: FEN-/unbekannte-history-Anfragen senden `show_moves=false`; Browser-SVG, Bildschirm-HUD und native Overlay respektieren die Sichtbarkeits-/History-Gates. Viewer-Share weist ausdrücklich auf die unterstützte Viewer-Fenster-/Monitor-Aufnahme und die Grenzen des Quellfenster-Koordinatenpfads hin.
- Behoben: Modellphase `loading`/`failed` bleibt auch bei vorhandenem Modellobjekt nicht bereit; ASGI-Startup startet den idempotenten Preload. Viewer und Userscript zeigen den Ladevorgang mit Spinner und begrenztem Retry.
- Behoben: `/api/start` und `/api/stop` invalidieren Overlay-Sessions und geben Leases frei; native `reset()` und `visible=false` verhindern verspätete Reaktivierung. Windows-Launcher nutzt einen benannten Mutex mit expliziten HANDLE-Signaturen.
- Synchronisiert: Anwendung, Userscript, Extension, Lockfile und Dokumentation auf 11.2.22 / 11.2.22.0; `tools/check_versions.py` prüft jetzt auch `uv.lock`.
- Verifikation in dieser Umgebung: `python -m compileall -q backend tools tests` PASS; `python -m unittest discover -s tests -v` 138 gesammelt, dependency-gated Fehler wegen fehlendem `python-chess`/`pytest`, ein Tombstone-Test nach Korrektur PASS; `python -m unittest tests.test_offline -v` 35/35 PASS; `node --test tests/*.js` 72/72 PASS; `python tools/check_versions.py` PASS.
- Externe Gates bleiben bewusst offen: Windows-Onedir-/EXE-Build, echte Edge-/Playwright-/DPI-/OBS-/Discord-Capture-Abnahme und Full-Python-Lauf mit gesperrter `uv`-Umgebung müssen in der Zielumgebung nach dem Merge laufen.


## Merge-Nachweis 12.11.2026

PR #9 `feat: finalize opening, loading, overlay, and launcher reliability` wurde nach Rücklese des Review-Branches in `main` gemergt. Main-Commit: `e1cc10be4dd79d30619aad7047253b7b5f53d93b`. Die im Final-Integrity-Checkpoint genannten externen Gates bleiben weiterhin ausdrücklich offen, bis Windows-Onedir, echte Capture-/DPI-Abnahme und die vollständige gelockte Python-Suite in der Zielumgebung gelaufen sind.

## Checkpoint 12.11.2026 — aktueller main `683e5847`

- Remote-Stand: `main` steht auf `683e5847eb53b5ef4bc18d0781a17be3d8448c35`
  (`fix: exclude global packages from portable runtime`). Es gibt keine offenen
  Pull Requests; das Repository ist privat und der authentifizierte Zugriff
  besitzt Admin/Maintain/Push-Rechte.
- CI #209 (`43245984541`) und Security #188 (`43245984443`) für diesen Commit
  schlagen jeweils bereits im ersten Lauf und nach Wiederholung
  (`run_attempt=2`) innerhalb weniger Sekunden fehl. Alle Jobs haben `steps=[]`,
  `duration_ms=0` und keine Logs; der Log-Endpunkt liefert `BlobNotFound`.
  Damit ist aktuell kein Test-, Lint-, CodeQL- oder Gitleaks-Fehler als
  Codeursache belegbar. Windows-Release wurde nicht ausgeführt, weil der
  Workflow ausschließlich `workflow_dispatch` verwendet. Der Blocker ist als
  GitHub-Actions-/Runner-Infrastrukturproblem zu behandeln.
- Lokale Prüfungen gegen den aus diesem Remote-Stand gelesenen Quellbaum:
  `node --test tests/*.js` 73/73 PASS, `python -m compileall -q backend tools
  tests` PASS, `tests.test_chess` 49/49 PASS mit den verfügbaren kleinen
  Laufzeitabhängigkeiten. `uv sync --frozen --extra quality` wurde begonnen,
  konnte aber wegen eines `fsspec`-Download-/Extraktions-Timeouts nicht
  vollständig abgeschlossen werden; ein vollständiger locked Pytest-, Ruff- und
  Mypy-Lauf ist daher weiterhin nicht nachgewiesen.
- Korrektur: `PositionTracker` übernimmt bei unveränderter Platzierung eine
  später gelieferte vollständige FEN (Zugrecht, Rochade- und En-passant-Feld)
  und setzt `turn_verified`; Regressionstest
  `tests/test_position_tracker_turn.py` ergänzt.
- Korrektur: Ein frisch beanspruchtes Overlay-Lease darf nach einem globalen
  `/api/start`-/`/api/stop`-Reset dieselbe logische Client-Sitzungs-ID erneut
  verwenden. `PrivateOverlayController.resume_session()` entfernt nur das
  Tombstone nach erfolgreichem Claim; alte Frames bleiben durch das neue
  Lease-Token abgewiesen. Der Viewer rotiert seine Session-ID vor jedem neuen
  Capture-Start. Regressionen in `tests/test_native_overlay.py` und
  `tests/test_viewer_reliability.js`.
- Weiterhin UNTESTED/BLOCKED: echte Windows-Onedir-/EXE-Abnahme, Edge-Reload,
  Playwright-/DPI-/HWND-/OBS-/getDisplayMedia-Capture, vollständige
  `uv`-Qualitätsumgebung sowie neue CI-Ausführung nach dem Korrektur-Commit.
