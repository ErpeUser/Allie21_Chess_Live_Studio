# Lokaler PGN-Lernrückblick

Der Viewer kann eine einzelne PGN-Partie als sichtbares Schachbrett Schritt für
Schritt wiedergeben. Der Rückblick zeigt ausschließlich die importierte
Hauptlinie. Er startet weder Allie noch Stockfish und benötigt keine neuen
Pakete, Modellgewichte oder Internetverbindung. Der lokale Allie-Dienst muss
laufen.

## Eine Partie ansehen

1. Eine laufende Bildschirmfreigabe mit **Analyse stoppen** beenden.
2. Falls der private Modus aktiv ist: unter **Einstellungen** bewusst
   **Browser-HUD nur im Schach-Tab** auswählen. Die Trainingspartie wird im
   Viewer angezeigt und kann deshalb in einer Aufnahme des Viewers sichtbar sein.
3. **Lokaler PGN-Lernrückblick** öffnen.
4. Eine PGN in das beschriftete Textfeld einfügen und **Rückblick laden** wählen.
   Alternativ über **Oder eine lokale PGN-Datei öffnen** eine UTF-8-Datei auswählen;
   sie wird direkt eingelesen und geprüft.
5. Mit **Start**, **Zurück**, **Weiter**, **Ende** oder **Stellung auswählen** durch
   die Partie gehen. Ein Schritt entspricht einem Halbzug, also dem Zug einer Seite.
6. **Partie entfernen** leert Eingabe, Dateiauswahl und Brett. Ein Wechsel in den
   privaten Modus oder der Start einer Bildschirmfreigabe entfernt den Rückblick
   ebenfalls. Eine verspätete Importantwort stellt ihn nicht wieder her.

Zum Ausprobieren genügt diese künstliche Trainingsfolge:

```pgn
1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
```

Das Brett zeigt Weiß unten. Die umrandeten Felder markieren Herkunft und Ziel
des zuletzt **gespielten** Zuges. Es gibt keine vorgeschlagenen oder automatisch
ausgeführten Züge. Das Zugrecht, Schach und ein auf dem Brett erreichtes
Partieende werden als Text angezeigt. Ein Ergebnis-Tag allein beweist kein Matt:
Eine durch Aufgabe beendete Partie kann auf dem letzten Brett noch legale Züge
haben.

## Tastatur und Textdarstellung

Alle Bedienelemente sind mit Tab erreichbar und haben sichtbare Fokusmarkierungen.
Wenn der Steuerbereich oder eine seiner Schaltflächen den Fokus hat, gehen die
Pfeiltasten links/rechts einen Halbzug zurück/weiter. **Pos1** und **Ende** springen
zur ersten beziehungsweise letzten Stellung. In der Zugauswahl bleibt die normale
Tastaturbedienung des Browsers erhalten; die Tastenkürzel greifen nicht global.

Importstatus und Stellungswechsel besitzen eine höfliche Live-Region für
assistive Technik. **Figuren und FEN als Text** enthält eine lesbare Liste wie
„e4: weißer Bauer“ sowie die vollständige FEN. Die Darstellung benötigt keine
Farbunterscheidung, um Zug, Seite und Stellung zu verstehen. Die vorhandene
Einstellung des Betriebssystems für reduzierte Bewegung bleibt wirksam.

## Unterstützte Eingaben und Grenzen

| Eingabe | Verhalten |
| --- | --- |
| Eine Standardschachpartie ab der normalen Startstellung | Hauptlinie wird eingelesen; jeder erkannte Zug wird auf Legalität geprüft. |
| Kommentare, Namen, Seiten-URLs und Nebenvarianten | Können in einer PGN enthalten sein; sie werden nicht in den Rückblick-Daten zurückgegeben. Nebenvarianten werden geparst, aber nicht dargestellt. |
| Rochade, en passant, Umwandlung, Schach und Matt | Folgen den Regeln der bereits vorhandenen Bibliothek `python-chess`. SAN und FEN werden aus dem tatsächlichen Brett erzeugt. |
| Leere Eingabe oder Partie ohne Zug | Verständliche Fehlermeldung; kein leeres oder erfundenes Brett. |
| Erkannter illegaler, mehrdeutiger oder Nullzug | Gesamter Import wird abgelehnt. Es bleibt kein Teilrückblick sichtbar. |
| Mehrere Partien in einer Datei | Import wird abgelehnt. Eine einzelne Partie exportieren. |
| Schachvarianten oder `SetUp`-/`FEN`-Tags | Import wird abgelehnt. Die vorhandene separate FEN-Analyse bleibt für manuelle Einzelstellungen verfügbar. |
| Sehr große Eingabe | Höchstens 40.000 Zeichen; Dateien höchstens 40.000 Byte; höchstens 1013 Halbzüge. Der JSON-HTTP-Größenschutz gilt zusätzlich. |

Die Halbzuggrenze übernimmt den bestehenden Analysevertrag (`len(moves) < 1014`)
und begrenzt zugleich Antwortgröße und Viewer-Zugliste. Es wird keine neue
Modellfähigkeit aus dieser Grenze abgeleitet.

Der PGN-Parser von `python-chess` ist absichtlich tolerant und kann unbekannte
Texttoken überspringen. Der Rückblick ist deshalb keine vollständige
PGN-Syntaxzertifizierung. Erkannte Parserfehler führen zur Ablehnung; die
ausgegebenen Stellungen werden ausschließlich aus legalen Bibliothekszügen
aufgebaut. Die angezeigte Zugzahl sollte zur exportierten Hauptlinie passen.

## Lokale Verarbeitung und faire Nutzung

Der Browser liest eine bewusst ausgewählte Datei über die lokale File-/Blob-API
und sendet ihren Text ausschließlich an `POST /api/pgn/replay` des lokalen Diensts.
Der Endpunkt verwendet dieselbe Capability-/Instanzauthentifizierung sowie
Host-, Origin- und Größenprüfung wie die übrigen geschützten API-Aufrufe.
Er greift nicht auf Captures, Browserpartien oder Live-Sitzungen zu.

Zurückgegeben werden nur Zugindex, SAN, UCI, FEN, Zugbezeichnung, Zugrecht,
Schachstatus und Brett-Partieende. Dateiname, Spieler, Ort, Datum, Kommentare,
URLs, Tokens und Aufnahmen gehören nicht zur Antwort. PGNs werden nicht in
`localStorage`, Dateien, Telemetrie oder zusätzlichen Caches gespeichert.
Parserfehler geben eine allgemeine deutsche Meldung aus und schreiben die private
PGN nicht ins Standard-Fehlerlog der Bibliothek.

Der Lernrückblick ist für abgeschlossene Partien und eigene Trainingsfolgen
gedacht. Chess.com und Lichess verbieten externe Spielhilfe während laufender
menschlicher Partien. Der neue Bereich verbindet sich deshalb nicht mit einem
Spiel-Tab, liefert keine Enginehinweise und führt keine Züge aus. Er bewertet
auch nicht, ob eine vom Nutzer eingefügte Partie tatsächlich abgeschlossen ist.

## Recherche und Auswahl vom 15.11.2026

Vor der Umsetzung wurden Produktvision, README, Viewer, Analyse-/PGN-Vertrag,
HTTP-Schutz, MV3-Status und vorhandene Tests gelesen. Es wurden nur allgemeine
technische Suchanfragen an öffentliche Quellen gesendet, keine privaten
Projektinhalte.

| Kandidat | Befund und Nutzen | Entscheidung |
| --- | --- | --- |
| Lokaler PGN-Rückblick | Es gab eine Endstellungsanalyse, aber kein schrittweise bedienbares Trainingsbrett. Vorhandenes `python-chess` kann Hauptlinie, SAN und FEN liefern. | **Implementiert**: Datei/Text → lokaler Parser → sichtbares Brett → Navigation. |
| Barrierearme Trainingsdarstellung | Sichtbarer Fokus, Statusregionen und reduzierte Bewegung existierten teilweise. Ein neuer Rückblick benötigt zusätzlich vollständige Tastaturbedienung und eine Textalternative zum Brett. | **Implementiert im Rückblick**; keine pauschale WCAG-Zertifizierung. |
| Anonymisierter Trainingssnapshot | Ein Export nur aus FEN/Zügen könnte reproduzierbare Fehlerberichte erleichtern. PGN-Namen, URLs, Kommentare und Dateinamen müssten ausgeschlossen werden. | **Recherchiert, nicht implementiert**; eigener Export-/Importvertrag und Redaktionsprüfung erforderlich. |
| Lokales Zug-Quiz aus eigener PGN | Die Hauptlinie könnte als nachvollziehbare Auflösung dienen. Eine Bewertung alternativer Antworten benötigt klar getrennte Allie-/Stockfish-Ergebnisse und zusätzliche Modellzustände. | **Recherchiert, nicht implementiert**; der kleine Rückblick kommt ohne Modell aus. |
| MV3-Offline-Wiederherstellung | Worker-Wake-up, Verbindungsbadge und Portfehler werden bereits in `browser/background.js` und zugehörigen Tests behandelt. Ein schlafender Worker ist normal. | **Bereits teilweise vorhanden**; keine zweite Wiederherstellungslogik eingeführt. |

Die Auswahl priorisiert unmittelbar nutzbares Training, lokale Datenhaltung,
Offlinefähigkeit, bestehende Abhängigkeiten und überschaubare prüfbare Änderungen.
Es wurden keine Browserberechtigungen, Modelle, Telemetrie- oder Runtime-Pakete
ergänzt.

### Offizielle Primärquellen

Alle folgenden Quellen wurden am **15.11.2026** abgerufen:

- [python-chess: PGN parsing and writing](https://python-chess.readthedocs.io/en/latest/pgn.html):
  `read_game`, `GameBuilder`, `mainline_moves`, Parserfehler und die dokumentierte
  Toleranz des Parsers. Die Anwendung verwendet diese API und keine zweite
  Schachregel- oder PGN-Implementierung.
- [W3C: Keyboard](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html),
  [Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible) und
  [Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html):
  Grundlage für Tastaturäquivalente, sichtbaren Fokus und Statusinformationen ohne
  erzwungenen Fokuswechsel.
- [Mozilla: Blob.text()](https://developer.mozilla.org/en-US/docs/Web/API/Blob/text):
  Promise-basierter UTF-8-Textimport bewusst ausgewählter lokaler Dateien.
- [Chrome: Extension service worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle):
  reguläres Beenden inaktiver Worker, Wiederaufwecken durch Ereignisse und
  Persistenzgrenzen globaler Variablen.
- [Lichess: Fair Play](https://lichess.org/page/fair-play) und
  [Chess.com: Fair Play](https://www.chess.com/legal/fair-play), dort Stand
  **25. März 2026**: Grundlage für die Beschränkung auf Rückblick und Training
  außerhalb laufender menschlicher Partien.

## Nachweis und offene Abnahme

`tests/test_pgn_training.py` prüft reale Bibliotheksverarbeitung mit künstlichen
PGNs, einschließlich Sonderzügen, Matt, Grenzen, privaten Metadaten und Fehlerlogs.
`tests/test_viewer_reliability.js` prüft die ausgeführte Viewer-Logik für lokalen
Import, Navigation, Authentifizierungsheader, Fehler, Privacy-Gates sowie verspätete
Antworten. Die Tests enthalten keine echten Nutzerpartien.

Die zusätzlichen Tests in `tests/test_viewer_browser.py` verbinden die tatsächliche
Viewer-HTML über einen kontrollierten In-Memory-Transport mit dem echten
`build_replay`-Parser und prüfen Dateiauswahl, DOM, Tastatur und mobile Breite.
Ihre Ausführung benötigt ein startbares Chromium. Die initiale Cloud-Prüfung
scheiterte vor dem DOM-Aufbau an einer Socket-Sperre der Laufzeitumgebung; daraus
folgt kein bestandener Browsertest. Native Windows-/Edge- und Screenreader-Abnahme
sind gesondert durchzuführen. HTTP-Positiv-/Negativtests gehören zur integrierten
Route und werden mit den Schutzprüfungen des Hauptbranches gemeinsam ausgeführt.
