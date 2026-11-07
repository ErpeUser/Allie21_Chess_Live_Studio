# Allie 2.1 Chess Live Studio v10 – Windows, kompletter editierbarer Quellcode

**Was es macht:** Das lokale Studio analysiert ein freigegebenes Schachvideo, z. B. einen Stream im **Discord-Desktopprogramm**, in Chrome/Edge, auf Twitch oder YouTube. Es zeigt permanent zwei rote Allie-Pfeile für die wahrscheinlichsten Gegnerzüge, zwei grüne für deine besten aktuellen Möglichkeiten und – wenn Allie ihn zuverlässig ableiten kann – einen blauen risikogewichteten Pre-Move. Kurze Nachrichten erklären Eröffnung und unmittelbare Gefahren. Stockfish 19 liefert daneben nur den objektiven Vergleich und ersetzt keine Allie-Pfeile.

Mit dem Schalter **„Live-Zugpfeile & Empfehlungen“** kannst du alle Live-Hinweise jederzeit sofort aus- und wieder einschalten – zum Beispiel, wenn du selbst mit einem Freund spielst. Bei „Aus“ werden Pfeile, Erklärungen und Engine-Berechnungen pausiert; die Brett-Erkennung darf weiterlaufen.

**Was es nicht ist:** Kein universell garantiert fehlerfreier Brettscanner, keine Manipulation des Original-Discord-Fensters und keine Automatik zum Spielen oder Klicken. Die Pfeile erscheinen im Studio-Fenster beziehungsweise per optionalem Tampermonkey-Overlay; dort entscheidest du selbst mit dem manuellen Schalter, wann Live-Hinweise laufen.

## Schnellstart (Windows 10/11 x64)

1. Das ZIP **vollständig entpacken**.
2. **`Allie21_Chess_Live_Studio.exe` doppelklicken**. Der Windows-Starter öffnet ein bereits laufendes Studio direkt oder zeigt sofort ein Start-/Fortschrittsfenster, während die lokale Einrichtung läuft. Alternativ funktioniert weiterhin **`START_HIER.bat`**. Die Einrichtung sucht Python 3.12 x64, installiert es bei Bedarf über `winget` (wenn vorhanden), richtet `.venv` ein, installiert die Bibliotheken und lädt Stockfish 19 und Lichess-Eröffnungsdaten. Sie ist wiederholt ausführbar; vorhandene Pakete werden normalerweise nicht erneut installiert. Internetzugang und Speicherplatz sind erforderlich.
3. Der Browser öffnet `http://127.0.0.1:8765/viewer`. Konsole offen lassen.
4. Auf **„Discord-App / Fenster / Bildschirm freigeben“** klicken. Im Browser-Freigabedialog **Fenster** auswählen und **Discord** anklicken (das kann die installierte Discord-Windows-App sein). Alternativ den **gesamten Bildschirm** freigeben und Discord im Vordergrund halten. Die Discord-App darf **nicht minimiert** werden. Ein Browser-Tab ist *nicht* erforderlich.
5. Das Programm zeigt das freigegebene Videobild, scannt automatisch nach Schachbrettern und blendet erkannte Stellung und Analysen darüber sowie rechts ein. Kein manueller Screenshot und kein FEN-Kopieren erforderlich.

Wenn du selbst im Discord-Desktopprogramm einen Stream **anschaust**, öffne seine Videowiedergabe groß genug, damit die Figuren erkennbar sind. Bei einem vollständigen Monitor muss der Stream sichtbar bleiben; der Viewer sollte auf einem anderen Monitor/als nicht überdeckendes Fenster stehen, sonst kann es zu Rückkopplungen kommen. Manche geschützten oder minimierten Fenster können beim Browser-Capture schwarz sein. Dann den Monitor freigeben oder auf Browserwiedergabe ausweichen.

**Modellgewichte:** Das echte `yimingzhang/allie-2.1` wird beim ersten echten historischen Vorhersageaufruf geladen (ca. 18 GB Download, rund 9,8 GB CPU-RAM für die quantisierte Inferenz). Mit **`ALLIE_VORLADEN.bat`** kannst du es bewusst vorher laden. Auf Windows verwendet Allie bei fehlender CUDA-Unterstützung die langsamere PyTorch-Referenz; ein Linux-spezifischer Rust-Beschleuniger wird **nicht** installiert. Mehr RAM als das Modell allein benötigt ist sinnvoll (z. B. 16 GB oder mehr). Der Modellanbieter verwendet `trust_remote_code=True`; dessen offiziellen Code vor Ausführung prüfen.

## Aussagekraft der Anzeigen

- **Stark/leicht Rot:** wahrscheinlichster und zweitwahrscheinlichster Gegnerzug. **Stark/leicht Grün:** deine erste und zweite Allie-Empfehlung. **Blau:** ein Pre-Move, den Allie über die wahrscheinlichsten Varianten hinweg nach Wahrscheinlichkeit und Abdeckungsrisiko auswählt. Prozentwerte sind *geschätzte Zugwahrscheinlichkeiten*, **keine** objektive Gewinnchance.
- Auf dem Brett wird bewusst **kein Stockfish-Pfeil** eingeblendet. Fehlt die vollständige Zuggeschichte, wartet die Pfeilanzeige auf Allie.
- **Text im Videobild:** kurze Nachrichten wie „Das ist die Italienische Eröffnung“ oder „Der wahrscheinlichste Zug setzt dich in Schach“ statt technischer Gegenantwort-Listen.
- **Eröffnung aus Einzelbild:** Nur ein **Stellungsabgleich**. Ohne vollständige Geschichte kann das Programm den tatsächlichen Eröffnungsverlauf nicht beweisen. Bei unklarem Zugrecht gibt es **keine** Zugpfeile.
- **Geschichte:** Das Programm beobachtet aufeinanderfolgende Figurenstellungen, testet legale Schachzüge und liest optional eine sichtbare PGN-Zugliste über RapidOCR. Ein Stream, der mitten in einer Partie startet, liefert **nicht** automatisch die gesamte Vorgeschichte. Ein passendes vollständiges PGN kann im Viewer manuell ergänzt werden. Unbekannte Rochaderechte/En-passant können Stockfish-Varianten einschränken.
- **Blitz, Rapid, Classical:** Rechenbudgets werden automatisch an `time_control` angepasst. Stockfish vertieft bei unveränderter Stellung bis zu zwei weitere Stufen. Bei einer neuen Stellung werden veraltete Ergebnisse ausgeblendet.

## Eigene Analysen und Browser-Overlay

- Im Viewer **„PGN / FEN ohne Stream analysieren“** ausklappen. Mit PGN ab Zug 1 läuft das echte Allie-Modell. Bei FEN allein bleibt die menschliche Vorhersage bewusst aus; Stockfish und Stellungstipps sind weiterhin möglich.
- Das optionale Tampermonkey-Overlay ist nicht mehr auf Chess.com oder Lichess begrenzt. Es sucht auf jeder Website nach einem sichtbaren 8×8-DOM-Brett, erkennt Figuren und Orientierung aus üblichen Klassen, Bildern und Barrierefreiheitsangaben und lässt `python-chess` die legale Zugfolge aus aufeinanderfolgenden Stellungen rekonstruieren. Website-Zuglisten dienen nur noch optional als validierter Starthelfer. Es gibt keine Partieart-, Bot-/Human- oder Live-/Analyse-Unterscheidung und keinen Zugriffsschlüssel. Auf Seiten mit reinem Canvas-Brett oder unzugänglichem geschlossenem Shadow-DOM muss weiterhin der universelle Fenster-/Bildschirmmodus im Viewer verwendet werden.

## Einstellungen

Alle Standardwerte stehen in **`config.json`** (editierbar mit Notepad):

| Feld | Standard | Bedeutung |
|---|---|---|
| `white_elo`, `black_elo` | 1950 | Elo-Kontext für Allie 2.1 |
| `time_control` | `600+0` | Ausgangszeit + Inkrement in Sekunden; für 10-Minuten-Partien voreingestellt |
| `recognition_interval_ms` | 750 | Frame-Abstand; 10-Minuten-Modus analysiert ungefähr alle 0,8 Sekunden |
| `stability_frames` | 2 | Übereinstimmende Frames vor einer Stellung |
| `ocr_history` | true | Sichtbare Zughistorie lesen (nur wenn nötig) |
| `progressive_engine` | true | Stockfish vertiefen, solange die Stellung gleich bleibt |
| `preview_opponent_replies` | true | Allie-Antwortprognosen für zwei Kandidaten |
| `stockfish_threads`, `stockfish_hash_mb` | 2, 128 | Engine-Ressourcen |

Die Modellkennung ist im Quellcode **fest auf `yimingzhang/allie-2.1` begrenzt**, sie wird nicht durch ein fiktives Modell ersetzt. Einstellungen nach Änderung des JSON durch Neustart übernehmen; Änderungen im Viewer vor dem Start der Freigabe festlegen.

## Fehlerbehebung

- **Python fehlt:** Falls `winget` nicht vorhanden ist, Python 3.12 x64 von https://www.python.org/downloads/windows/ installieren; dann `START_HIER.bat` erneut doppelklicken.
- **Fensterfreigabe fehlt:** Aktuelles Chrome oder Edge auf `http://127.0.0.1:8765/viewer` verwenden. Eine einmalige explizite Freigabe ist aus Browsersicherheitsgründen zwingend; sie ist nicht per Code umgehbar.
- **Discord-Desktop-Fenster fehlt im Dialog:** Discord groß anzeigen, Fenster nicht minimieren; im Freigabedialog **Ganzer Bildschirm** wählen.
- **Keine Stellung erkannt:** Schachbrett groß anzeigen, Figuren und komplette 8×8-Fläche sichtbar lassen. Die `chessvision`-Bilderkennung kann bei bestimmten Brettern, Browserzooms, Videokompression oder Überlagerungen scheitern.
- **Kein Allie-Prozentwert:** Entweder fehlt eine vollständige verifizierte Zugliste oder das große Allie-Modell ist noch nicht geladen. **Kein Stockfish-Ersatz für Allie**.
- **Kein Stockfish:** Setup erneut starten; alternativ die originale Stockfish-19-Windows-EXE in `backend/engines/stockfish.exe` legen.
- **Start-/Versionsdiagnose:** `TEST_HIER.bat` zeigt die lokalen Tests und `backend/doctor.py` listet die installierten Komponenten. Die große Modellinferenz wird dabei nicht automatisch ausgeführt.

## Architektur – bewusst möglichst wenig Eigenentwicklung

| Fertiges Projekt / API | Aufgabe |
|---|---|
| Browser `getDisplayMedia` | Discord-Desktopfenster, Browserfenster oder Bildschirm erfassen |
| `chessvision` | Schachbrett und Figuren aus Videoframes erkennen |
| `python-chess` | Züge, PGN/FEN, Legalität, Eröffnungsschlüssel, UCI |
| `rapidocr` + ONNX Runtime | Optional sichtbare Schachnotation erkennen |
| Original Allie 2.1 via `transformers`/`torch` | Menschliche Züge, Gegnerantworten, Bedenkzeit, WDL |
| Stockfish 19 | Objektive Analyse und Varianten |
| Lichess Chess Openings (CC0) | ECO-Codes und Eröffnungsnamen |

Nur die lokale Verbindung, Abgleich mehrerer Frames und die Oberfläche sind eigener Code. Der HTTP-Server steckt ausschließlich in **`backend/live_server.py`**, die Allie-Schachlogik in **`backend/allie_local_server.py`**. Eine separate EXE, ein eingebetteter Electron-Stack oder zusätzliche OS-Hooks sind nicht erforderlich.

## Tests, Sicherheit, Rechte

`TEST_HIER.bat` führt die Test-Suite aus. Der Server bindet ausschließlich an **127.0.0.1** und prüft Host/Origin sowie die Overlay-Anfrageart; ein Konto, API-Schlüssel oder lokaler Zugriffs-Token existiert nicht. Videoframes werden nur lokal verarbeitet und **nicht gespeichert oder an eine Cloud geschickt**. Einrichtung und Modell-Downloads benutzen die offiziellen Onlinequellen; bei Stockfish wird der offizielle ZIP-SHA-256 geprüft.

Lizenz und Drittlizenzen: `LICENSE.txt`, `QUELLEN_LIZENZEN.md`.

**Prüfstand:** Python- und JavaScript-Syntax, lokale HTTP-Grenzen (Host/Origin), Konfigurationsprüfung und die Pfeil-/Pre-Move-Datenform werden automatisch geprüft. Die vollständige Allie-Inferenz benötigt die großen Modellgewichte und entsprechend viel RAM; deshalb kann der erste echte Lauf deutlich länger dauern.
