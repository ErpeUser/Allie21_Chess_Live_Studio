# Allie 2.1 Chess Live Studio v11

Lokale Windows-Anwendung für menschliche Zugprognosen mit Allie 2.1 und objektive Varianten mit Stockfish 19. Das Studio verarbeitet freigegebene Fenster, Browserbretter sowie vollständige PGN-Dateien. Es spielt und klickt nie selbst.

## Schnellstart unter Windows

1. Projekt vollständig entpacken.
2. **`START_HIER.bat` doppelklicken** oder den portablen Onedir-Build aus `source/automation/build_exe.ps1` starten.
3. Warten, bis `http://127.0.0.1:8765/viewer` geöffnet wird. Mit `ALLIE_PORT=18765` wird der benutzerdefinierte Port auch in der Startmeldung verwendet.

Die EXE ist ein portables Onedir: Im selben Ordner liegen `app` (Server, Viewer und Assets) und `runtime` (Python 3.12 mit den eingefrorenen Paketen). Sie benötigt für den Start weder Checkout, `uv` noch eine globale Python-Installation. Beim ersten Modellstart können die Allie-Gewichte unter `generated/dependencies/models/` nachgeladen oder aus dem vorhandenen Modellcache benutzt werden; Stockfish liegt im App-Ordner. Solange Allie läuft, erscheint rechts unten im Windows-Infobereich ein Allie-Symbol: Doppelklick oder „Allie öffnen“ öffnet den Viewer, „Allie beenden“ schließt Server und Symbol vollständig.

Das echte Allie-Modell wird beim Serverstart automatisch im Hintergrund mit der Startstellung vorgewärmt. Die Gewichte benötigen ungefähr 18,4 GB Speicherplatz; der CPU-Betrieb benötigt viel Arbeitsspeicher. Sobald im Viewer „Allie geladen“ steht, ist der erste Live-Zug ohne Modell-Kaltstart bereit.

## Eingabewege

- **Video/Fenster:** Im Viewer „Quelle auswählen“ anklicken und in Chrome oder Edge ein sichtbares Discord-, Browser- oder Monitorfenster freigeben. `chessvision` und optional RapidOCR werden erst beim ersten Frame geladen.
- **Browser-Overlay:** In Edge/Chrome unter `edge://extensions` bzw. `chrome://extensions` den Entwicklermodus aktivieren und den Ordner `source/app/browser/` als „Entpackte Erweiterung laden“ wählen. Die Erweiterung unterstützt gezielt Chess.com und Lichess, beobachtet DOM-Änderungen gebündelt und sendet nur an den lokalen Dienst. Für Canvas-Bretter und andere Websites den Video- oder PGN-Weg verwenden.
- **PGN/FEN:** „PGN oder FEN ohne Stream analysieren“ öffnen. Nur eine vollständige, bestätigte Partiegeschichte ab der Startstellung wird an Allie übergeben. FEN allein wird ausschließlich mit Stockfish analysiert.

## Korrektheit und Anzeigen

### Adaptive Eröffnungen und Ragebait

Die Auswahl für Weiß und Schwarz ist deine bevorzugte Eröffnung. Weicht die Partie davon ab, sucht Allie in den vorhandenen Linien eine zur aktuellen Stellung passende Fortsetzung. Zugumstellungen werden erkannt; gemeinsame nächste Züge können mehrere Eröffnungen kombinieren. Die Anzeige trennt **Deine Wahl** von **Aktuell passend** und erklärt den Wechsel. Ohne passende Buchlinie geht die freie Analyse weiter.

**Ragebait** bevorzugt passende ungewöhnliche Gambits, konkrete Drohungen und Königsdruck. Der Stil darf spekulativer sein als **Aggressiv**; er ist keine Zusage für den objektiv besten Zug. Ein sofortiges Matt und das Vermeiden eines gegnerischen Matts im nächsten Zug haben Vorrang. Die angezeigten Prozentwerte bleiben Allies tatsächliche menschliche Zugwahrscheinlichkeiten. Frische Profile starten mit Ragebait; einen bereits gespeicherten anderen Stil kannst du im Feld **Spielstil** umstellen.

Remisstellungen behalten ihre aktuellen Zughinweise, solange legale Züge vorhanden sind. Bei Matt/Patt ohne legalen Zug bleibt die Anzeige ohne Zugpfeil. Der explizite Rückblick auf eine beendete Partie bleibt getrennt von der sichtbaren Live-Stellung.

### Pfeilfarben

- Starkgrün: mein Allie Top 1; Hellgrün: mein Allie Top 2.
- Starkrot: Gegner Allie Top 1; Hellrot: Gegner Allie Top 2.
- Blau: geplante eigene Fortsetzung über die untersuchten Gegnerzweige. Risiko und Zweigabdeckung berücksichtigen, bei welchen Antworten der Zug als Allie-Kandidat verfügbar bleibt.
- Allie liefert bei vollständiger Historie die menschlichen Zugwahrscheinlichkeiten. Eigene Stil-/Repertoirepräferenzen und verfügbare Stockfish-Bewertungen werden vor der zugehörigen Vorschau angewandt; Gegnerprognosen bleiben in Modellreihenfolge. Bei einem Einstieg mitten in der Partie startet nach dem ersten eindeutig beobachteten Zug automatisch ein konservativer Stockfish-Fallback ohne erfundene Rochade- oder en-passant-Rechte.

Brettorientierung und Spielerfarbe werden getrennt verwaltet und bei Livepartien standardmäßig automatisch aus dem sichtbaren Brett bestimmt; Weiss/Schwarz bleiben als manuelle Overrides verfügbar. Bei einem Einstieg mitten in der Partie werden fehlende Züge, Rochaderechte und en-passant-Rechte nicht erfunden. Allie wartet auf eine vollständige PGN; Stockfish kann eine ausdrücklich gelieferte FEN dennoch analysieren.

Die einheitliche Zeitklasse verwendet `Grundzeit + 40 × Inkrement`:

- unter 180 s: Bullet, Stockfish 0,25 s
- unter 600 s: Blitz, Stockfish 0,65 s
- unter 1.800 s: Rapid, Stockfish 1,1 s
- ab 1.800 s: Classical, Stockfish 2,0 s

## Einstellungen

Die validierten Standardwerte stehen in `source/app/backend/config.py`. Eine optionale, nicht versionierte `generated/protected/config.json` kann diese Werte bei Bedarf überschreiben. Wichtige Felder sind `white_elo`, `black_elo`, `player_side`, `time_control`, `recognition_interval_ms`, `stability_frames`, `ocr_history`, `stockfish_threads` und `stockfish_hash_mb`. Modellkennung und Modellrevision sind absichtlich festgelegt.

Der Schalter „Live-Zugpfeile & Empfehlungen“ verwirft sofort laufende Ergebnisse. Nach Stellungs-, Einstellungs- oder Sitzungswechseln akzeptiert die Pipeline nur Antworten der aktuellen Generation.

Die EXE kann reproduzierbar neu gebaut werden: `powershell -ExecutionPolicy Bypass -File source/automation/build_exe.ps1`. PyInstaller wird dabei nur für den Build geladen und ist keine Backend-Laufzeitabhängigkeit. Die schnelle App-Ordner-Ausgabe vermeidet das langsame und auf diesem Windows unzuverlässige Selbstentpacken einer Onefile-EXE; der komplette `generated/dist/win/Allie21 Chess Live Studio/`-Ordner muss zusammenbleiben.

## Tests und Diagnose

```powershell
powershell -ExecutionPolicy Bypass -File source/automation/quality_check.ps1
node --test source/tests/*.js
& "$PWD\generated\dist\win\Allie21 Chess Live Studio\runtime\python.exe" source/app/backend/doctor.py
```

Der optionale Qualitätslauf verändert die Produktionsumgebung nicht. Er installiert Ruff, Mypy, Pytest und Playwright bei Bedarf in `generated/environments/quality`; mit `-InstallBrowsers` werden zusätzlich Chromium-Browserdaten geladen. Pytest verwendet die bereits geprüften Runtime-Abhängigkeiten aus `generated/environments/source` oder, falls die Quell-Umgebung entfernt wurde, aus der installierten portablen Runtime unter `generated/dist/win/`. Torch/Vision müssen dafür nicht ein zweites Mal installiert werden. Ruff/Mypy melden bestehende Befunde mit Exitcode 1, statt sie still zu überspringen.

Der Server bindet ausschließlich an `127.0.0.1`, prüft Host und Herkunft, begrenzt JSON und JPEG-Größen und speichert keine Videoframes. Exakte geprüfte Versionen, Modellrevisionen, Hashes und Messwerte stehen in `source/docs/VERSIONEN.md`; Lizenzen in `source/docs/QUELLEN_LIZENZEN.md`.

Die Browser-Erweiterung öffnet über ihre Optionen die Einstellung „Lokaler Port“ und speichert sie in `chrome.storage.local`; das Userscript bietet denselben Port im Allie-Menü. Beide müssen mit `ALLIE_PORT` des Servers übereinstimmen. Die Erweiterung verwendet für localhost bewusst eine Port-Wildcard und fragt den konfigurierten Port über den MV3-Service-Worker ab.

## Aktueller Quellstand und lokale Installation

Der technische Checkpoint steht in `source/docs/VERSIONEN.md`; ein laufender Hintergrundprozess wird nicht vorausgesetzt.

Die Anwendung/Userscript-Version ist 11.2.26. Die separat versionierte Edge-Erweiterung ist 11.2.26.0/11.2.26; `source/automation/check_versions.py` prüft diese beiden Versionierungsverträge und die unveränderte Erweiterungs-ID getrennt. [PR #12](https://github.com/ErpeUser/Allie21_Chess_Live_Studio/pull/12) enthält die Remis-, Eröffnungs- und Ragebait-Änderungen mit ihren aktuellen automatisierten Prüfergebnissen. Für die lokale Aktualisierung im Windows-Git-Checkout `UPDATE_ALLIE.cmd` ausführen; die [Update-Anleitung](source/docs/UPDATE_PIPELINE_DE.md) erklärt Voraussetzungen und PR-Prüfung.

Neu ist der [lokale PGN-Lernrückblick](source/docs/PGN_TRAINING_DE.md): eine bewusst importierte Partie auf einem Schachbrett schrittweise ansehen, per Tastatur navigieren und Figuren/FEN als Text lesen. Der Rückblick benötigt keine Modellgewichte und startet keine Engine.

Der Onedir-Build ist reproduzierbar, erzeugt die Ausgabe aber absichtlich nur lokal unter `generated/dist/win/`; dieser Ordner ist per `.gitignore` ausgeschlossen und wird nicht als unveränderliches GitHub-Artefakt versioniert. Echte Windows-Capture-Proben (HWND, OBS, getDisplayMedia) bleiben für den aktuellen Stand eine externe Abnahme. Hashes und der genaue Prüfstand stehen in `source/docs/VERSIONEN.md`.

## Grenzen

Videoerkennung hängt von Größe, Design, Kompression und Sichtbarkeit des Brettes ab. Das Originalfenster wird nicht verändert; Pfeile erscheinen im Viewer oder im optionalen Overlay. Der geprüfte Allie-Python-Code liegt unter `generated/dependencies/vendor/allie_model`; der Loader verwendet `trust_remote_code=False`, `local_files_only=True` und prüft das SHA-256-Manifest vor dem Start.


## Kanonische Git-/Codex-Arbeitsweise
Die kanonische Quellbasis liegt in diesem Checkout unter `source/`; die
gepruefte Vendorquelle ist ausschliesslich unter
`generated/dependencies/vendor/` versioniert. Alle anderen Inhalte unter
`generated/` (einschliesslich Modelle, Builds und Git-Metadaten) sind nicht
zur Versionierung vorgesehen. Vor jeder Arbeit `AGENTS.md` lesen.

Fuer Codeaenderungen gilt: ausschliesslich im bestehenden Checkout auf `main`
arbeiten, fremde lokale Aenderungen erhalten, `python source/automation/check_repository_policy.py`
ausfuehren und die entsprechenden Struktur-, Qualitaets- und Funktionstests
laufen lassen. Ein Agent erzeugt keine Kopien, Nebenbranches, PRs, Workflows oder
Links. GitHub-Aenderungen werden direkt als Commit auf `main` veroeffentlicht,
wenn die Aufgabe einen GitHub-Schreibvorgang verlangt.

Die Synchronisierung ist ausschliesslich fuer sauberes `main` zulaessig:
```powershell
git status --porcelain=v1 -uall
git branch --show-current
git remote -v
git fetch --no-tags origin main
git merge-base --is-ancestor HEAD origin/main
# Nur wenn diese Pruefungen erfolgreich sind und der Checkout sauber auf main ist:
git merge --ff-only origin/main
```
`UPDATE_ALLIE.cmd` prueft diesen Zustand, liest bei jedem Abgleich alle
Remote-Branches und main-PRs und schreibt fuer jeden Kandidaten eine Empfehlung
in `generated/protected/maintenance/maintenance-report.json`. `candidate-newer`
steht fuer eine neuere eigenstaendige Fassung, `combine-fix-with-main` fuer
einen divergierten Fix-Branch und `combine-review` fuer andere divergierte
Aenderungen. Der Bericht nimmt keine fremden Aenderungen automatisch auf.
Force-Pushes, Branch-Loeschungen und Nebenbranches sind durch die lokale
Arbeitsweise ausgeschlossen. Der neue Strukturcheck wirkt auf GitHub nach dem
ersten Commit im oeffentlichen `main`.
