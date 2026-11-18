# Portable Windows Build und Tray-Start

Die portable Distribution besteht aus drei Teilen: der Tray-EXE, `app/` mit
Backend, Viewer und Extension sowie `runtime/` mit der geprüften Python-Laufzeit.
Die EXE startet den lokalen Dienst ohne sichtbares CMD-Fenster und zeigt ein
Allie-Symbol im Infobereich. `Allie öffnen` öffnet den lokalen Viewer; `Allie
beenden` beendet nur den von dieser Tray-Instanz gestarteten Prozessbaum.

## Wiederverwendung von Port 8765

Beim Start prüft der Launcher zuerst `http://127.0.0.1:8765/health`. Eine
Antwort mit der Allie-Health-Struktur (`alive=true`, API-/Schema-Version,
Instanz-ID und Overlay-Status) wird als eigene laufende Allie-Instanz
wiederverwendet. In diesem Fall besitzt die Tray-Instanz keinen Prozess und
beendet beim Schließen keinen fremden Prozess. Ein anderer Listener führt zu
einem sichtbaren Fehler und wird nie beendet.

## Build und Nachweis

`tools/build_exe.ps1` erzeugt einen Onedir-Build, kopiert die komplette
Anwendung und Laufzeit und schreibt `app/release-version.json`. Dieser Nachweis
enthält getrennte App-/Userscript- und Extension-Versionen, die Quellrevision
und die UTC-Bauzeit. `SHA256SUMS.txt` wird nach dem Kopieren aller Dateien
berechnet. Die Release-Prüfung kontrolliert auch die vollständige Dateimenge:
zusätzliche, doppelt gelistete und veränderte Dateien führen zum Abbruch; große
Bibliotheksdateien werden speicherschonend gestreamt. Der Build schließt regenerierbare `__pycache__`-/Bytecode-Dateien,
Python-Standardbibliotheks-Tests, IDLE-/Installationshilfen und ausschließlich
für Paket-Tests bestimmte Ordner aus. Der Smoke-Test verweigert einen Release,
falls solche Dateien versehentlich erneut im Bundle landen.

`tools/release_smoke.py --bundle <bundle> --with-model` prüft Manifest,
Stockfish-Hash, Runtime-Inventar und HTTP-Start. Der Health-Check verlangt
`alive=true`; mit `--with-model` müssen zusätzlich `/readyz?source=both`,
`ready=true`, `model_loaded=true` und `stockfish_available=true` erfüllt sein.
Der Prozess wird anschließend innerhalb eines begrenzten Zeitfensters beendet.

Ein fehlgeschlagener Smoke-Test darf nicht veröffentlicht werden. Der
Wartungspfad erstellt den Kandidaten in einem Staging-Ordner und ersetzt den
aktiven Bundle-Ordner erst nach erfolgreicher Prüfung; ein vorhandener Build
bleibt als Backup erhalten.
