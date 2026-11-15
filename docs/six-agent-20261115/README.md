# Allie 2.1 – sechs Rollen, implementierte Änderungen und Prüfbelege

**Stand: 15. November 2026. Status: TEILWEISE – Code implementiert und lokal geprüft; Browser-, CI- und native Abnahmen bleiben offen.**

Die Änderungen liegen im [Draft-PR #11](https://github.com/ErpeUser/Allie21_Chess_Live_Studio/pull/11). Der PR enthält reproduzierte Fehlerkorrekturen, eine gemessene Optimierung, eine belegte Bereinigung und einen vollständigen lokalen PGN-Lernrückblick. Dieser Bericht ist keine Freigabe einer Windows-Installation. `main`, Desktop, Edge-Profile und Modellgewichte wurden nicht verändert.

## 1. Verifizierter Ausgangspunkt und Ergebnis

| Gegenstand | Nachweis |
| --- | --- |
| Repository | Privates `ErpeUser/Allie21_Chess_Live_Studio` |
| Ausgangsbranch/-commit | `main`, `c5ea9a324a28f1b16fb544cfbe2ef140178213a0` |
| Ausgangs-Tree | `365af574ec35ab3f4d3fea9f7367d901ee8c386d`, nicht abgeschnitten |
| Ausgangsinventar | 153 getrackte Dateien, 3.037.457 Bytes |
| Arbeitsbranch | `fix/allie21-six-agent-20261115` |
| Lokal vollständig geprüfter Code-Commit | `16bc123d8a310ff46475c9b6c85b77167c4732e2` |
| Inhaltlich identischer GitHub-Code-Commit | `25aecacb6fb6ee8d9ca8c428d7dee706e8ae5d46` |
| Identischer Code-Tree beider Commits | `4f7b961f75ae70f366bf906bdb6e78850d706d6d` |
| App und Userscript | 11.2.25 |
| MV3-Version / version_name | 11.2.25.0 / 11.2.25 |
| Extension-ID | `omboihgfgofgmidefcpkihgglhkiielo`, unverändert |

Die nachfolgenden Berichtscommits ergänzen ausschließlich dieses Dokumentationsverzeichnis. Der aktuelle PR-Head wird im PR selbst ausgewiesen. [publication-map.json](publication-map.json) ordnet jeden lokalen Code-Commit seinem GitHub-Commit und dem identischen Tree zu. Die unterschiedlichen Commit-IDs entstehen durch die Veröffentlichung mit dem authentifizierten GitHub-Connector; die Tree-Gleichheit wurde für jeden Schritt geprüft.

Ein normaler HTTPS-Clone konnte hier keine Git-Anmeldedaten beziehen. Deshalb wurden Repository-Metadaten und Dateien über den verbundenen GitHub-Connector übernommen. 152 Blobs wurden mit ihren Original-Git-Hashes materialisiert. Der 1.239.566 Byte große PNG-Blob konnte nicht als Binärinhalt abgerufen werden. Sein unveränderter Tree-Eintrag `4e962591e1698fd92ae406ec4c24f99ad3f29aac` wurde erhalten; kein Ersatzbild und keine Löschung wurden veröffentlicht. Diese Einschränkung ist im Inventar ausdrücklich sichtbar.

## 2. Reproduzierte Fehler und Korrekturen

Die vollständigen Auslöser, RED/GREEN-Nachweise, Dateien, Commit-IDs, Reviewer und Grenzen stehen in [findings.json](findings.json). Die Prioritäten beziehen sich auf diesen Prüfauftrag.

| Befund | Reproduktion und Ursache | Implementiertes Ergebnis |
| --- | --- | --- |
| **ARCH-01, P2: bestätigtes Zugrecht** | Nach zunächst unvollständigem Verlauf blieb der Versuch mit der Gegenseite aktiv, obwohl das Zugrecht inzwischen verifiziert war. Zwei neue Unterfälle akzeptierten deshalb einen falschen Seitenwechsel. | Der Fallback in `position_tracker.py` ist nur bei unbestätigtem Zugrecht erlaubt. Drei neue Methoden und 59 angrenzende Fälle bestanden. |
| **SEC-001, P2: Pairing-Budget** | Die Capability-Route begrenzte Fehlversuche, während GET/POST/PUT der Overlay-Einstellungen denselben Code ohne gemeinsames Budget prüften. Sechs Testmethoden erzeugten elf erwartete Fehlschläge. | Prüfung und Zählung liegen unter demselben Lock. Die Endpunkte teilen pro Origin das Budget von fünf Fehlversuchen pro 60 Sekunden. Gültige Statusabfragen verbrauchen das Fehlerbudget nicht. Konkurrenz, Ablauf und Endpunktwechsel sind geprüft. |
| **NATIVE-001, P1: alter Nachrichtentimer** | Nach `visible=False`, fehlender Geometrie, abweichendem Payload-Modus oder Wechsel auf normal konnte ein alter Timer die zwischengespeicherten Pfeile erneut zeigen. Vier Unterfälle waren rot. | Akzeptierte neue Frames und echte Moduswechsel entwerten Timer-Token und Rendercache. Auch ein bereits auf den Render-Lock wartender Callback bleibt wirkungslos. 36 Overlaytests und fünf unabhängige Zusatzfälle bestanden. |
| **Build-Pfade und fremde Ausgaben, P1** | Ausgabe gleich Quelle beziehungsweise überlappende Archivpfade konnten Quelldaten löschen oder überschreiben. Fremde Ausgabeordner wurden ebenfalls ungeprüft entfernt. | Aufgelöste Pfade dürfen sich nicht überschneiden. Finale Ausgabesymlinks/Junctions werden abgelehnt. Vorhandene Ordner werden nur mit passendem eigenem Stamp, Manifestversion und erneutem Inhaltshash ersetzt. |
| **Build-Vorbereitung, P2** | Kopier- oder ZIP-Fehler konnten erst nach dem Verlust der bisherigen Ausgabe auftreten. | Kopie, Hash, Stamp und ZIP entstehen zunächst in temporären Nachbarverzeichnissen. Die tatsächlichen Fehlerfälle erhalten den bisherigen Build und das Archiv. Insgesamt: 25 erwartete RED-Fälle, danach 43 Build-/Maintenance-Fälle grün. |
| **SEC-002, P1: Viewer übernimmt Privatmodus verspätet** | Der Settings-Aufruf setzte den Modus schon vor dem Vergleich im Aufrufer. Ein vorhandener Rückblick blieb sichtbar. Die unabhängige Reproduktion zeigte 64 Brettfelder und weiterhin PGN-Text. | Ein gemeinsamer Annahmepfad aktualisiert die Privacy-Anzeige unmittelbar für POST und GET-Fallback. Eingaben, Brett und ausstehende Imports werden gelöscht beziehungsweise entwertet. Drei neue Fälle waren rot; alle 25 Viewer-Node-Tests sind grün. |
| **Browser-Restore, P1** | Nach verborgenem Tab und verändertem Brett wurden alte Pfeile wieder gezeichnet. Zusätzlich konnte ein noch auf seine native Lease wartender Frame später mit neuer Generation gesendet werden. | Restore invalidiert Ergebnis und laufende Antworten vor asynchronem IO. Die gemeinsame Clear-Funktion verwirft auch die native Warteschlange ohne vorhandenen Owner-Token. Danach wird die aktuelle Stellung neu geprüft. |
| **Browser-Privatmodus, P1** | Bereits gezeichnetes SVG blieb während einer hängenden nativen Claim-Anfrage sichtbar, obwohl die Remote-Einstellung privat lautete. | Beide Settings-Antwortpfade entfernen die Darstellung synchron. Ein späterer Repaint stellt Browserpfeile im Privatmodus nicht wieder her. Restore und Privacy bestehen 25 gezielte Node-Fälle einschließlich vier neuer Regressionen. |

Die Build-Änderung garantiert den Erhalt bei Validierungs- und Vorbereitungsfehlern. Das abschließende Ersetzen von Verzeichnis und ZIP ist weiterhin **keine gemeinsame atomare Transaktion**. Fehler bei diesen letzten Veröffentlichungsschritten und Prozessabstürze haben keine neue Rollback-Garantie.

Die native und die Browser-Lifecycle-Reproduktion verwendeten kontrollierte Win32-, DOM- und Netzwerkgrenzen. Dabei wurden echte Produktionsfunktionen ausgeführt, aber keine fremden Partien, realen Nutzerprofile oder Capture-Sitzungen bedient.

## 3. Eingebaut: lokaler PGN-Lernrückblick

Die [deutsche Nutzerdokumentation](../PGN_TRAINING_DE.md) beschreibt den vollständigen Ablauf. Der Viewer akzeptiert eine bewusst eingefügte PGN oder eine ausgewählte lokale UTF-8-Datei. Er zeigt die Hauptlinie auf einem Brett mit 64 Feldern. Start, Zurück, Weiter, Ende und Zugauswahl erlauben die schrittweise Navigation. Im Steuerbereich funktionieren Pfeiltasten, Pos1 und Ende. Zugrecht, Schachstatus und ein auf dem Brett erreichtes Partieende werden als Text ausgegeben; Figurenliste und vollständige FEN ergänzen die visuelle Darstellung.

Der neue Endpunkt `POST /api/pgn/replay` verwendet die vorhandene Capability-/Instanzauthentifizierung sowie Host-, Origin- und Body-Grenzen. `python-chess` erzeugt SAN und FEN aus legalen Zügen. Der Rückblick startet keine Engine, lädt kein Modell und verändert keine Live-Sitzung. Diese Unabhängigkeit wurde über echte lokale HTTP-Anfragen auch bei den Modellzuständen `loading` und `failed` geprüft.

Es gelten höchstens 40.000 Zeichen, bei Dateien 40.000 Byte, und 1.013 Halbzüge. Unterstützt wird genau eine Standardschachpartie ab der Startstellung. Erkannte illegale oder Nullzüge, mehrere Partien, andere Varianten und SetUp/FEN werden abgelehnt. Kommentare, Namen und URLs erscheinen nicht in der Antwort. PGNs werden nicht in Local Storage, Dateien oder zusätzlichen Caches gespeichert. Bibliotheksfehler werden ohne private PGN-Diagnose weitergegeben.

Der zugrunde liegende PGN-Parser ist absichtlich tolerant und kann unbekannte Texttoken überspringen. Die Funktion prüft die erkannte legale Hauptlinie; sie zertifiziert nicht die vollständige PGN-Syntax. Ein Ergebnis-Tag allein beweist ebenfalls kein auf dem Brett erreichtes Matt.

Vor dem Rückblick muss die Bildschirmfreigabe beendet sein. Der standardmäßige Privatmodus erfordert eine bewusste Umstellung auf den Browser-HUD. Ein späterer Wechsel zurück auf privat, eine neue Bildschirmfreigabe oder „Partie entfernen“ löscht den Rückblick. Revisionen und Abort-Signale verhindern, dass verspätete Antworten ihn wiederherstellen. Der Bereich ist für abgeschlossene Partien und eigene Trainingsfolgen vorgesehen und verbindet sich nicht mit einer laufenden Partie.

Vor der Umsetzung wurden fünf Kandidaten anhand des vorhandenen Produkts geprüft: PGN-Rückblick, zugängliche Trainingsdarstellung, anonymisierter Trainingssnapshot, Zug-Quiz und MV3-Wiederherstellung. Rückblick und dessen Tastatur-/Textdarstellung wurden umgesetzt. Export und Quiz blieben bewusst außerhalb dieses kleinen Slices; Teile der Worker-Wiederherstellung existierten bereits. Abhängigkeiten und Browserberechtigungen wurden nicht erweitert.

## 4. Performance und belegte Bereinigung

`tactical_hints` erzeugte SAN-Text für jeden untersuchten Zug, obwohl fast alle Texte verworfen wurden. Nun wird SAN erst erzeugt, wenn eine tatsächlich zurückgegebene Mattfolge feststeht. Suchgrenzen 24/24/64, Reihenfolge, erste gefundene Fortsetzung und bestehende Ergebnistexte bleiben unverändert.

| Synthetischer Fall | Median vorher → nachher | P95 vorher → nachher | Medianreduktion |
| --- | ---: | ---: | ---: |
| Startstellung | 152,728 → 96,427 ms | 177,335 → 133,465 ms | 36,86 % |
| Ruy Lopez | 326,716 → 193,907 ms | 425,536 → 222,993 ms | 40,65 % |
| Mittelfeld mit Rochaderechten | 519,974 → 314,446 ms | 643,791 → 391,244 ms | 39,53 % |
| Mattfolge in zwei Zügen | 15,942 → 9,103 ms | 23,559 → 14,041 ms | 42,90 % |
| Summe der zehn Teststellungen | 1.041,117 → 616,831 ms | 1.256,897 → 730,250 ms | 40,75 % |

Gemessen wurden 25 gepaarte Wiederholungen je Stellung und Version, drei Warmups und zehn feste gültige FENs mit alternierender Reihenfolge. Brettaufbau und Instrumentierung liegen außerhalb der Zeitmessung. P95 verwendet den nächsten Rang. Ausgaben und Brettzustände waren in jedem Lauf identisch. Die unabhängige Gegenprüfung hat alle 44 Median-/P95-Serien und die Summen nachgerechnet. Die endgültige Funktion ist bytegleich mit dem vermessenen Funktionssegment; der spätere Cleanup verändert einen anderen Abschnitt.

Die mediane CPU-Zeit der Suite sank von 1.039,467 auf 613,435 ms. SAN-Aufrufe der drei großen Fälle sanken von 9.342/17.621/27.646 auf null, bei der Mattfolge von 764 auf drei. Beim sehr kurzen sofortigen Mattfall stieg P95 leicht von etwa 0,291 auf 0,313 ms. Das ist ein lokaler Taktikscan-Benchmark und kein gemessener Gewinn für Modellstart, GPU oder die gesamte Windows-Anwendung. [Rohmessungen](performance.json) und [Benchmarkwerkzeug](../../tools/benchmark_tactical.py) sind enthalten.

Der Cleanup entfernt die ungenutzte Placement-Map und ihre Wrapper. Repositoryweite Aufrufer- und Packaging-Prüfungen fanden keinen benötigten Nutzer dieses Helfers. Die 3.865 vollständigen EPD-Einträge sind vor und nach der Änderung identisch; kanonischer SHA-256: `417386a36f890efd59411b9b97d9b38b90ac3252b0ca107f708169bd77ff2091`. Die entfernte Map mit 3.863 Einträgen samt Schlüsseln belegte in CPython 3.12 mindestens 461.389 Bytes, ohne geteilte Werte mitzuzählen. Der Produktionscode schrumpft um zwölf Zeilen. Vier Charakterisierungstests bestanden schon vorher; es wird kein künstlicher RED-Fehler behauptet.

## 5. Tatsächlich ausgeführte Gesamtprüfungen

Alle Prüfungen wurden gegen den oben genannten Code-Tree ausgeführt. [quality-gates.json](quality-gates.json) enthält Befehle, Exitcodes, Laufzeiten und die jeweiligen [lesbaren Logs](logs/). Die bytegenauen Originalausgaben liegen zusätzlich in [raw-logs.json](raw-logs.json); bei den lesbaren Kopien wurden ausschließlich Leerzeichen am Zeilenende und abschließende Leerzeilen entfernt. Der zusätzliche Testlauf ohne Browserfixtures ersetzt den vollständigen Lauf nicht.

| Gate | Ergebnis |
| --- | --- |
| `uv sync --frozen --extra quality` | **PASS**, eingefrorene Umgebung; 75 ausgewählte Pakete geprüft |
| `uv run --frozen python -m unittest discover -s tests -v` | **ERROR_ENVIRONMENT**: 245 Tests ausgeführt, ein Browser-Klassen-Setupfehler; keine Assertion-Fehlschläge |
| `uv run --frozen pytest -q` | **ERROR_ENVIRONMENT**: 290 bestanden, 14 Browser-Setupfehler, zwei vorhandene FastAPI-Warnings |
| Pytest ohne `test_viewer_browser.py` und `test_extension_options_browser.py` | **PASS**: 290 bestanden, zwei vorhandene Warnings |
| `node --test tests/*.js` | **PASS**: 91 Tests, keine Fehler oder Skips |
| `uv run --frozen ruff check backend tools tests` | **PASS** |
| `uv run --frozen mypy backend --ignore-missing-imports` | **FAIL_BASELINE_PLATFORM**: 35 vorhandene Windows-`ctypes`-Befunde in einer Datei |
| Zusätzliches Mypy mit `--platform win32` | **PASS**: 18 Quelldateien; drei vorhandene Hinweise zu untypisierten Funktionskörpern |
| `python tools/check_versions.py` | **PASS**: 11.2.25 / 11.2.25.0, feste ID unverändert |
| `uv lock --check` | **PASS**: 94 Lock-Einträge; sämtliche 93 externen Pakete und Hashes unverändert |
| `python -m compileall -q backend tools tests` | **PASS** |
| `git diff` gegen die Ausgangsrevision mit `--check` | **PASS** |

Chromium scheitert vor dem Seitenaufbau an der Erzeugung seines ProcessSingleton-Sockets: `Operation not permitted`. Damit sind zehn Viewer- und vier Extension-Optionsfälle im Pytest-Setup blockiert. Ein Versuch, außerhalb dieser Beschränkung zu prüfen, wurde von der automatischen Umgebungsfreigabe abgelehnt. Es wurde keine Umgehung versucht. Fünf der offenen Viewer-DOM-Fälle wurden für den Rückblick und seine Remote-Privacy-Grenze neu ergänzt.

Die drei ursprünglichen Ruff-EXE001-Befunde sind behoben: Das reine Importmodul verliert seine überholte Shebang; die beiden echten CLI-Einstiege erhalten den passenden ausführbaren Git-Modus. Mypy-Konfiguration und Fehlerunterdrückungen wurden nicht angepasst, um die Linux-Befunde zu verbergen. Der Windows-Zieltypcheck ist weiterhin kein nativer Windows-Test.

Der Versionswechsel erforderte genau eine Änderung am virtuellen Projekt-Eintrag von `uv.lock`. Ein Offline-Neuresolve fand nicht alle Registry-Metadaten im Cache. Anschließend wurde ausschließlich dieses Versionsfeld aktualisiert; der vollständige TOML-Vergleich aller übrigen Felder und `uv lock --check` bestanden. Vendor-Dateien, ihre Integritätsliste, Eröffnungsdaten, Modellrevisionen und Assets sind gegenüber der Baseline unverändert.

## 6. Sechs getrennte Rollen und unabhängige Gegenprüfung

Es wurden genau sechs getrennte Rollen-Kontexte eingesetzt. Wegen vier gleichzeitiger Laufzeitplätze einschließlich Koordination liefen sie in Wellen und mit getrennten Worktrees. Überschneidende Schreibbereiche wurden nacheinander übergeben.

| Rolle | Tatsächlich gelieferte Implementierung |
| --- | --- |
| Architektur | Guard für bereits bestätigtes Zugrecht; Regressionen |
| Bugs/Security | Atomarer gemeinsamer Pairing-Fehlerzähler; echte HTTP-Regressionen |
| Modernisierung | Sichere Pfadprüfung und Vorbereitung des Extension-Builds mit vorhandenen Standardbibliotheken |
| Performance | Verzögerte SAN-Erzeugung, reproduzierbares Benchmarkwerkzeug und Verhaltenstests |
| Cleanup | Tote Placement-Eröffnungsmap entfernt; vollständiger Indexvergleich und Charakterisierungstests |
| Kreativ/Feature | PGN-Rückblick mit UI, Parser, Tests und deutscher Doku; anschließend die zusätzlich reproduzierten Browser-Lifecycle-Fixes |

Die Koordination verband die Replay-API, ergänzte echte HTTP-Tests und behob den reproduzierten nativen Timerfehler sowie die im Gegenreview gefundene Viewer-Lücke. Architektur und Security prüften gegenseitig die ersten Fixes. Architektur überprüfte zusätzlich Build, Timer, CLI-Modi und Vendor-/Loader-Grenzen. Security überprüfte PGN, Viewer, Performance, Cleanup und die Browserfixes und entdeckte dabei den zusätzlichen wartenden nativen Frame.

Die [Architektur-Gegenprüfung](evidence/cross_review_architecture_final.json) und [Security-Gegenprüfung](evidence/cross_review_security_final.json) enthalten konkrete Quellenintervalle, eigene Gegenversuche und ausgeführte Tests. Im geprüften Änderungsumfang blieben nach deren Nachprüfung keine bestätigten blockierenden Befunde offen. Diese Aussage gilt nicht als vollständige Fehlerfreiheit des gesamten Produkts.

## 7. Audit-Abdeckung und Grenzen

[manifest.json](manifest.json) enthält alle 153 Ausgangsdateien mit Größe, Modus und Original-Blob. [coverage.json](coverage.json) kombiniert nur Intervalle desselben Pfads und desselben Blob-SHA. Suchtreffer, Struktur-/Hashprüfungen und bloße Diff-Lektüre werden nicht zu vollständiger Quellenlektüre umgedeutet.

| Nachweis an mindestens einem dokumentierten Blob | Ausgangsdateien |
| --- | ---: |
| Vollständige Quellenintervalle | 116 |
| Teilweise Quellenintervalle | 3 |
| Nur Struktur-/Hashprüfung | 10 |
| Keine Quellenintervalle dokumentiert | 23 |
| Nicht verfügbar und ungelesen | 1 |

Für den exakten Ausgangs-Blob sind 115 vollständige und vier teilweise Lektüren belegt. Für den exakten getesteten Blob sind es 105 vollständige und sechs teilweise; insbesondere spätere Versions-/Dokumentationsdeltas wurden nicht pauschal als Volllektüre übernommen. Alle elf neuen Dateien am getesteten Code-Commit besitzen vollständige dokumentierte Quellenintervalle. Die 34 geänderten Pfade umfassen 23 vorhandene und elf neue Dateien; der getestete Code-Tree enthält damit 164 Dateien. Dieses spätere Belegpaket wird getrennt gezählt.

Historische Auditberichte gelten ausschließlich als Kontext. Die überlieferten Rollenbelege bilden zum Teil frühere Übergabezeitpunkte mit damals offenen Gates ab. Für den konsolidierten Endstand gelten dieses Dokument, die beiden Gegenprüfungen und `quality-gates.json`. [evidence-index.json](evidence-index.json) ordnet ursprüngliche Log-/Dateinamen den dauerhaft beigefügten Kopien und deren SHA-256 zu; ursprüngliche absolute Pfade in Rollenbelegen sind Herkunftsangaben aus der Prüfumgebung.

## 8. GitHub-Checks und offene Abnahme

Die automatisch nach PR-Erstellung gestarteten Workflows sind nicht grün:

- [CI, Run 43755351881](https://github.com/ErpeUser/Allie21_Chess_Live_Studio/actions/runs/43755351881): `maintenance-tests` und `windows-tests` fehlgeschlagen, jeweils ohne verfügbare Steps.
- [Security, Run 43755351855](https://github.com/ErpeUser/Allie21_Chess_Live_Studio/actions/runs/43755351855): Secret Scan und beide CodeQL-Jobs fehlgeschlagen, ebenfalls ohne verfügbare Steps.
- Die abgefragten Windows-/Secret-Scan-Logs liefern `404 BlobNotFound`. Der Annotation-Endpunkt ist über den verfügbaren Connector nicht lesbar. Daraus wird keine aktuelle Abrechnungsursache, kein Quellcodefehler und kein erfolgreicher Security-Scan abgeleitet.

[remote-ci.json](remote-ci.json) enthält die Antworten für den veröffentlichten Code-Commit. Spätere automatische Läufe des reinen Dokumentationscommits müssen anhand ihres tatsächlichen Status beurteilt werden. Es wurden keine manuellen Release-Workflows gestartet oder fehlerhafte Checks umgangen.

Die ausstehenden Schritte sind im [Fortsetzungs-Checkpoint](08_INTEGRATION_FORTSETZUNG.md) konkret beschrieben: echte Chromium-DOM-Tests in einer geeigneten Umgebung, native Windows-/Edge-Capture-Prüfung, DPI/HWND/OBS/getDisplayMedia, verifizierter Stockfish- und portable-Installer-Lauf sowie gegebenenfalls gesondert autorisierte Modell-/GPU-Abnahme. Die vollständige Quellenlektüre der noch offenen Inventarbereiche bleibt ebenfalls separat ausgewiesen.

`UPDATE_ALLIE.cmd`, Deployment, Main-Merge, Release-Tags, Modell-Downloads, Browserprofile und Desktop-Verknüpfungen wurden nicht ausgeführt oder verändert. Der PR bleibt bis zur erforderlichen Abnahme Draft.

## 9. Offizielle Recherchequellen

Abrufdatum: **15. November 2026**. Recherchiert wurden allgemeine technische Fragen; privater Quelltext und Nutzerdaten wurden nicht an öffentliche Suchdienste übermittelt.

- [python-chess: PGN parsing and writing](https://python-chess.readthedocs.io/en/latest/pgn.html) – vorhandener Parser, Hauptlinie, Besucherschnittstellen und dokumentierte Toleranz.
- [W3C: Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), [Keyboard](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html), [Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible) – Tastatur, sichtbarer Fokus und Statusregionen; keine pauschale WCAG-Zertifizierung.
- [Mozilla: Blob.text()](https://developer.mozilla.org/en-US/docs/Web/API/Blob/text) – bewusst ausgewählte lokale UTF-8-Dateien.
- [Chrome: Service worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle) – reguläre MV3-Ruhephasen; kein unnötiger Dauer-Keepalive.
- [Python 3.12: pathlib](https://docs.python.org/3.12/library/pathlib.html) und [tempfile](https://docs.python.org/3.12/library/tempfile.html) – aufgelöste Pfade, Junction-Prüfung und temporäre Verzeichnisse.
- [uv: Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) – eingefrorene Ausführung und explizite Lock-Prüfung.
- [Lichess Fair Play](https://lichess.org/page/fair-play) und [Chess.com Fair Play](https://www.chess.com/legal/fair-play) – Abgrenzung des neuen Rückblicks von Hilfen in laufenden menschlichen Partien.

## 10. Geänderte Dateien am geprüften Code-Stand

Die folgende Liste wird aus dem Git-Diff gegen die verifizierte Ausgangsrevision erzeugt. Das Belegpaket unter diesem Verzeichnis kommt anschließend hinzu.

| Änderung | Datei |
| --- | --- |
| Geändert | [CHANGELOG.md](../../CHANGELOG.md) |
| Geändert | [README_DE.md](../../README_DE.md) |
| Geändert | [VERSIONEN.md](../../VERSIONEN.md) |
| Geändert | [backend/allie_local_server.py](../../backend/allie_local_server.py) |
| Geändert | [backend/chess_extras.py](../../backend/chess_extras.py) |
| Geändert | [backend/config.py](../../backend/config.py) |
| Geändert | [backend/download_stockfish.py](../../backend/download_stockfish.py) |
| Geändert | [backend/http_boundary.py](../../backend/http_boundary.py) |
| Geändert | [backend/live_server.py](../../backend/live_server.py) |
| Geändert | [backend/native_overlay.py](../../backend/native_overlay.py) |
| Neu | [backend/pgn_training.py](../../backend/pgn_training.py) |
| Geändert | [backend/position_tracker.py](../../backend/position_tracker.py) |
| Geändert | [backend/security.py](../../backend/security.py) |
| Geändert | [browser/allie21_overlay.user.js](../../browser/allie21_overlay.user.js) |
| Geändert | [browser/manifest.json](../../browser/manifest.json) |
| Neu | [docs/PGN_TRAINING_DE.md](../../docs/PGN_TRAINING_DE.md) |
| Geändert | [docs/UPDATE_PIPELINE_DE.md](../../docs/UPDATE_PIPELINE_DE.md) |
| Geändert | [docs/release-status.md](../../docs/release-status.md) |
| Geändert | [pyproject.toml](../../pyproject.toml) |
| Geändert | [tests/test_browser_reliability.js](../../tests/test_browser_reliability.js) |
| Neu | [tests/test_build_edge_safety.py](../../tests/test_build_edge_safety.py) |
| Neu | [tests/test_http_pairing_limits.py](../../tests/test_http_pairing_limits.py) |
| Neu | [tests/test_native_overlay_timer.py](../../tests/test_native_overlay_timer.py) |
| Neu | [tests/test_opening_lookup.py](../../tests/test_opening_lookup.py) |
| Neu | [tests/test_pgn_replay_http.py](../../tests/test_pgn_replay_http.py) |
| Neu | [tests/test_pgn_training.py](../../tests/test_pgn_training.py) |
| Neu | [tests/test_position_tracker_architecture.py](../../tests/test_position_tracker_architecture.py) |
| Neu | [tests/test_tactical_performance.py](../../tests/test_tactical_performance.py) |
| Geändert | [tests/test_viewer_browser.py](../../tests/test_viewer_browser.py) |
| Geändert | [tests/test_viewer_reliability.js](../../tests/test_viewer_reliability.js) |
| Neu | [tools/benchmark_tactical.py](../../tools/benchmark_tactical.py) |
| Geändert | [tools/build_edge.py](../../tools/build_edge.py) |
| Geändert | [uv.lock](../../uv.lock) |
| Geändert | [viewer/index.html](../../viewer/index.html) |
