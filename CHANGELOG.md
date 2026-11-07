# v10 – GUI- und Bedienkorrektur

## v10.7.0

- Browser-Overlay von festen Chess.com-/Lichess-Seitenmustern entkoppelt: Es erkennt sichtbare DOM-Bretter, Figuren und Orientierung nun generisch auf beliebigen Websites.
- `python-chess` rekonstruiert die Zuggeschichte aus legalen Übergängen aufeinanderfolgender Brettstellungen; die Website-Zugliste ist nur noch ein optionaler, vollständig validierter Starthelfer.
- Das Overlay bleibt auf Seiten ohne erkanntes Schachbrett unsichtbar. Canvas-only-Bretter und geschlossenes Shadow-DOM werden weiterhin über die vorhandene Fenster-/Bildschirmfreigabe abgedeckt.
- Keine Bot-/Human-, Live-/Analyse- oder sonstige Partieart-Unterscheidung. Der lokale Dienst braucht weiterhin weder Zugriffs-Token noch Konto.
- Automatische Tests für Startstellung, `e4 ... Nc6`, einen übersprungenen Zwischenframe und beliebige Overlay-Webseiten ergänzt.
- Nachrichtentexte wiederholen nicht mehr Pfeile und Prozentwerte, sondern erklären Eröffnung, Stellungsmerkmale, wahrscheinliche gegnerische Absicht, Vorhersagbarkeit und konkrete Gefahren. Die Nimzowitsch-Verteidigung nach `1. e4 Nc6` ist offline enthalten.
- Frühe Partien funktionieren auch nach verspätetem Overlay-Start oder Seiten-Reload: `python-chess` rekonstruiert bis zu drei bereits gespielte Halbzüge eindeutig und legal von der Startstellung. Damit liefert z. B. `1. f3 e5` sofort Analyse statt „Position unchanged“.

## v10.6.0

- Neue feste Farblogik: zwei rote Allie-Gegnerprognosen, zwei grüne eigene Allie-Empfehlungen und ein blauer, über wahrscheinliche Varianten risikogewichteter Allie-Pre-Move.
- Technische Gegenantwort-Listen durch kurze Live-Nachrichten zu Eröffnung, Zugwahrscheinlichkeit, Schach- und Schlaggefahren ersetzt.
- Sämtliche Partieart-/Bot-/Human-Seitenlogik sowie der lokale Zugriffsschlüssel entfernt. Der Dienst bleibt ausschließlich an `127.0.0.1` gebunden und prüft Host/Origin.
- Zufällige Zugauswahl entfernt: Haupt- und Zweitpfeil folgen deterministisch der Allie-Reihenfolge. Stockfish bleibt objektiver Textvergleich und erzeugt keine Ersatzpfeile.

## v10.6.1

- Chess.com-Zuglistenerkennung um neue Web-Components, Datenattribute, CSS-Klassen und Schachfigurensymbole erweitert.
- Alte Nachrichten und Pfeile werden bei einem Stellungswechsel sofort entfernt; Ergebnisse einer früheren Stellung bleiben nie mehr neben dem aktuellen Brett stehen.

- Overlay 10.5 nutzt Allie als menschlichen Spieler statt als starre Top-1-Prognose: Aus den fünf plausibelsten Modellzügen wird gewichtet gewählt, eine starke andere Wahl bleibt als Alternative sichtbar. Elo 1950 und 600+0 fließen weiterhin direkt ins Modell ein.
- Overlay 10.4.1 erkennt eine unveränderte Standardstartstellung anhand aller 32 Figuren und Felder. Allie kann damit auf Analyse-, Computer- und Zuschauerbrettern bereits vor dem ersten Zug rechnen; beliebige Stellungen ohne Zuggeschichte bleiben ausgeschlossen.
- Neuer Sofort-Schalter **„Live-Zugpfeile & Empfehlungen“**: blendet Pfeile, Erklärblase, Hinweise und Analyse aus und stoppt im Hintergrund laufende Engine-Empfehlungen. Die Brett-Erkennung kann dabei weiterlaufen; die Auswahl wird lokal gespeichert.
- Das Tampermonkey-Overlay unterscheidet nicht mehr automatisch zwischen Online-, Freund-, Bot-, Analyse- oder Zuschauerpartien. Ausschließlich der manuelle Schalter **„Live-Hinweise: Ein/Aus“** bestimmt, ob Empfehlungen laufen.
- 10-Minuten-Schnellprofil als Standard: Brettprüfung ungefähr alle 0,8 Sekunden und kurze Stockfish-Bedenkzeit.
- Stockfish und Allie laufen jetzt parallel. Stockfish zeigt sofort eine Empfehlung; Allie ergänzt oder ersetzt sie, sobald die menschliche Zugprognose fertig ist.
- Allies Hauptzug und Nebenzug werden als grün/gelbe Pfeile ohne Nummern angezeigt. Eine Blase rechts am Brett erklärt die allgemeine Idee, beide Zugwahrscheinlichkeiten und prognostizierte Gegnerantworten.
- Schneller lokaler Bot-gegen-Bot-Test ergänzt: Er erzeugt ohne weitere EXE oder Downloads eine legale Partie und prüft zwei Allie-Kandidaten sowie Gegnerprognosen für beide Züge.
- Lichess-Overlay 10.2 repariert: Die aktuelle, absichtlich wechselnde Lichess-Zuglistenstruktur wird ohne feste Tag-Namen erkannt; das größte sichtbare Brett wird gewählt und die rechte Blase zeigt Gegnerprognosen für Haupt- und Nebenzug.
- Lichess-Analyse läuft zweistufig: Stockfish liefert sofort einen blauen Zwischenpfeil, während Allie parallel lädt; anschließend ersetzen grün/gelbe Allie-Pfeile die Zwischenanzeige.
- Overlay 10.3: Chess.com-Analyse erkennt das aktuelle `wc-chess-board` und die Hauptzugliste direkt, ohne Stream. Die Bubble trennt Hauptzug und Alternative farblich und erklärt jetzt jeweils Grund, menschliche Wahrscheinlichkeit und erwartete Gegnerantwort.
- Native 64-Bit-Windows-Starter-EXE ergänzt. Sie erkennt ein bereits laufendes Studio, zeigt sofort ein eigenes Start-/Fortschrittsfenster, öffnet den Viewer automatisch und verhindert parallele Einrichtungsstarts.
- Windows-Setup repariert: Vorhandenes Python 3.12 x64 wird nun korrekt aufgerufen; die `winget`-Meldung „bereits installiert/keine Aktualisierung“ führt nicht mehr zu einem falschen Abbruch.
- Viewer als responsives Studio-Dashboard neu geordnet: Live-Vorschau, Fortschritt, Einstellungen, Stellung, Zugverlauf und Analyse sind klar getrennt.
- Verzerrte Streamdarstellung korrigiert. Das Video behält jetzt sein Seitenverhältnis, damit Brettkoordinaten und Analysepfeile übereinstimmen.
- Eingaben werden bereits im Browser geprüft; laufende Aktionen zeigen Ladezustände und verhindern versehentliche Doppelaufrufe.
- Systemstatus für Stockfish und Allie, verständlichere Leer-/Fehlerzustände, größere mobile Bedienelemente und sichtbare Tastaturfokusse ergänzt.
- Desktop- und Mobilansicht ohne horizontalen Überlauf geprüft.

# v10 – Abschlussprüfung nach v9

- Die echte Quellenwahl auf **Discord als Windows-App**, weitere Desktopfenster, Browser-Tabs und Monitore ausgerichtet. Der Chrome/Edge-Freigabedialog bevorzugt Fenster (`getDisplayMedia(displaySurface='window')`) mit sicherem Fallback; der Anwender wählt die Quelle selbst. Kein Discord-Token, kein eigenes Bildschirmaufnahmeprogramm.
- Einen lokalen HTTP-Server aus früher zwei verschachtelten Handlern gemacht, mit einer einzigen Token-/Host-/Origin-Prüfung, einheitlichen JSON-Antworten und ohne URL-Token in Serverlogs.
- Alte Hintergrundresultate bei Streamwechsel und nicht übereinstimmender Stellung weiterhin verworfen; bei unbekanntem Zugrecht/ungültiger Stellung keine Engine-Empfehlung.
- Wertevalidierung ergänzt (nicht-endliche Stockfish-Zeit, ungültige Allie-Wahrscheinlichkeiten und unplausible Figurenmengen); zusätzliche Hinweise bei unvollständiger Partiegeschichte.
- Teure OCR nach bestätigter vollständiger History abgeschaltet; eine Modellinstanz, ein Stockfish-Prozess und eine Eröffnungstabelle bleiben wiederverwendbar.
- Den vorher nur **einmal** verwendeten `progressive_budgets()` tatsächlich für **zwei** Vertiefungsstufen aktiviert; bei veränderter Stellung werden Ergebnisse verworfen. Stufen verkürzt, damit neue Stellungen nicht unnötig lange blockiert werden.
- Im Viewer doppelte Freigabeaufrufe blockiert, asynchrone Frames an ihre jeweilige Streamgeneration gebunden, Quellinformation sichtbar gemacht und die Einstellungshinweise verdeutlicht.
- Optionales Tampermonkey-Overlay ignoriert veraltete Antworten bei geändertem PGN, hat ein Retry-Backoff statt still hängen zu bleiben.
- Fünf echte Offline-HTTP-Routentests hinzugefügt. Headless-Chromium-UI-Test mit **simuliertem** Videostream bestand (Pfeil, Text-HUD, Gegnerprognose, Stoppen).
- Python-, JavaScript-, JSON- und ZIP-Prüfungen wiederholt; externe Modell-/Discord-/Windows-Tests weiter offen.

## Grenzen, nicht versteckt

Das von Chrome/Edge freigegebene Discord-Desktopprogramm **wird im eigenen Viewer mit Analyse-Overlay angezeigt**. Das Original-Discord-Fenster wird nicht grafisch verändert. Manche minimierten/geschützten Fenster lassen sich nicht erfassen. Das Allie-Modell braucht die wirkliche Zuggeschichte ab Anfang; aus einem einzelnen Brettbild darf sie nicht erfunden werden.
