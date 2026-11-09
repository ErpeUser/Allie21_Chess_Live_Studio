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
| G3 Eröffnungen/Schach | PASS | 43 Chess-Regressionen im Vollauf 96 Tests PASS; EPD-/Transpositions-/Abweichungs-/Fallback-Fälle enthalten. |
| G4 Erweiterung | UNTESTED | Version 11.2.16 konsistent, MV3-Alarmlogik statisch/Node geprüft; tatsächliches Edge-Reload und geladener Content-Script-Stand nicht verifiziert. |
| G5 Privater Modus | BLOCKED | Native Affinität/Fail-Closed und Mocktests PASS; echte HWND-Rücklesung plus OBS/getDisplayMedia/Discord/Zoom/Teams-Proben fehlen. |
| G6 Pipeline/Funktionserhalt | PASS | Python-Volltest 96 Tests PASS, 1 Skip; Allie-first-/Stockfish-/Session-/HTTP-Regressionsfälle enthalten. |
| G7 Qualität | UNTESTED | `git diff --check`, Unit-/JS-Läufe PASS; keine vollständige Lint-/Type-/Playwright-/p50/p95-Abnahme. |
| G8 Windows-Paket | PASS | Portables Onedir mit `app` + `runtime` gebaut; EXE `--check`, Runtime-Imports und Server-`/health` (HTTP 200) direkt aus dem Release-Ordner geprüft. Modell-Download bleibt First-Run. |
| G9 Dokumentation | PASS | README_DE, VERSIONEN, CHANGELOG, AGENT_TASK/PROGRESS entsprechen dem getesteten und explizit begrenzten Stand. |
| G10 Privater Release | BLOCKED | Kein Git-Remote/Auth verifiziert; kein Commit/Tag/Push/Release autorisiert oder behauptet. |

## Checkpoint 09.11.2026 06:10

- `.allie-venv\Scripts\python.exe -m compileall -q backend tools`: Exitcode 0.
- `.allie-venv\Scripts\python.exe backend/doctor.py`: Exitcode 0; Python-/FastAPI-/Pydantic-/Uvicorn-/Vision-/Torch-/Stockfish-/Opening-/Browseraufnahme-Prüfungen OK.
- GOAL-Status bleibt unverändert: erreichbare lokale Regressionen PASS; reale Capture-, autonome Fresh-Path- und private Remote-Abnahmen BLOCKED/UNTESTED.

## Checkpoint 09.11.2026 06:20

- G2/G3/G7-Kernchecks erneut ausgeführt: 96 Python-Tests OK (1 Skip), alle 9 JS-Fixtures OK, `node --check` für Userscript/Service Worker OK, `compileall` OK. G3 bleibt PASS; G2 und G7 bleiben wegen fehlendem echten Edge/Playwright bzw. fehlenden Lint-/Type-/Performance-Tools UNTESTED, nicht wegen eines bekannten lokalen Fehlers.
- G8 umgesetzt: `tools/build_exe.ps1` kopiert jetzt App-Dateien und die `.allie-venv`-Pakete in `release\Allie21 Chess Live Studio\app` und `runtime`. Portable EXE-Check, Import-Smoke und `/health` HTTP 200 bestanden; laufender Testprozess wurde beendet.
- Aktuelle Distribution: EXE 2.625.829 Byte, Gesamt 1.179.028.625 Byte; Hashes und First-Run-Modellhinweis in `VERSIONEN.md`, Bedienhinweis in `README_DE.md`.
- G10 bleibt BLOCKED: kein Remote konfiguriert; `gh auth status` meldet ungültigen Token für `ErpeUser`. Für Commit/privates Repo/Push fehlt nur die echte GitHub-Reauth bzw. der gewünschte Remote-Name.

## Release-Status / Blocker

Kein Remote vorhanden. Ein privater GitHub-Release ist derzeit nicht verifizierbar und darf nicht behauptet werden.

## Wiederaufnahmeplan

Beim Fortsetzen zuerst diese Datei, `AGENT_TASK.md` und die referenzierten Agentenberichte lesen. Dann beim zuletzt offenen Schritt fortfahren; keine bereits verifizierten Arbeiten wiederholen.
