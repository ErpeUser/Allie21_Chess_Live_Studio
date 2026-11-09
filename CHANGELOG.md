# Änderungen

## v11.2.16

- Browser-/Viewer-Pfeile zeichnen bei Resize, Scroll, Zoom, CSS-Transform und visualViewport-Änderungen ohne neuen Analyseframe neu; SPA-Navigation retiert alte Sessions.
- Opening-Auswahl bleibt strikt bei der gewählten legalen Linie; EPD-Schlüssel berücksichtigen Zugrecht, Rochade und En-passant.
- Privater Native-HUD erhält monotone Session-/Render-Gates, Session-boundary-Clear und fail-closed Capture-Affinität; MV3-Gesundheitsalarm nutzt 30 Sekunden und Worker-Recovery.
- Python-, Lockfile- und Erweiterungsversion auf 11.2.16 angeglichen. Der Onedir-Build ist lokal reproduzierbar, aber die autonome Fresh-Path-Abnahme bleibt offen.

## v11.2.15
- Hotfix: Opening-Auswahl wird von der FastAPI-Anfrage akzeptiert; kein „Extra inputs are not permitted“ mehr.

## v11.2.14
- Warmes Schach-Design für Viewer und Browser-Overlay; Pfeilfarben unverändert.
- Opening-Auswahl bleibt konfigurierbar, Standard ist Grob Gambit (Weiß) und Englund Gambit (Schwarz).

## v11.2.13

- Standardrepertoire hinterlegt: Weiß Wiener Gambit mit Dänischem Gambit als Alternative; Schwarz Budapester Gambit mit Aljechin-Verteidigung als Alternative. Die Präferenz bleibt legal, weich und Allie-first.

- Ragebait-Standard ergänzt: Grob Gambit für Weiß und Englund Gambit für Schwarz; Wiener/Budapest sowie Dänisch/Aljechin bleiben als Alternativen erhalten.

## v11.2.11

- Pfeile verwenden jetzt dieselbe figurenbasierte Brettorientierung wie die Stellungserkennung; dadurch werden schwarze Bretter nicht mehr gespiegelt gezeichnet.

## v11.2.10

- Aggressiver Königsdruck bleibt Allie-first, wird aber bei klarer Materialverschlechterung durch Stockfish zurückgestellt; Züge, die sofortiges Matt zulassen, werden ebenfalls nicht bevorzugt.

## v11.2.9

- Automatische Spielerfarbe nutzt sichtbare Plattformmarker und fällt bei fehlenden Markern auf die Brettseite zurück; Brettorientierung und manuelle Farbauswahl bleiben getrennt.

## v11.2.8

- Automatische Spielerfarbe ist jetzt unabhängig von der Brettorientierung und liest die sichtbare Spielerfarbe der Plattform; manuelle Weiss/Schwarz-Auswahl bleibt erhalten.

## v11.2.7

- Die Windows-EXE bleibt als Infobereich-Steuerung aktiv und zeigt ein eigenes Allie-Symbol.
- „Allie öffnen“ öffnet den lokalen Viewer; „Allie beenden“ schließt den ausschließlich von dieser EXE gestarteten BAT-/uv-/Server-Prozessbaum.
- Endet der Server anderweitig, verschwindet das Symbol automatisch.
- Der Windows-Build verwendet Python 3.12 und eine schnell startende App-Ordner-EXE statt der auf diesem System hängenden Onefile-Selbstentpackung.

## v11.2.6

- Neuer optionaler Spielstil „Aggressiv“: Innerhalb von Allies legalen Top-Kandidaten werden Matt, Schach und direkter Königsdruck bevorzugt; Normalmodus und gegnerische Allie-Reihenfolge bleiben unverändert.
- Seiten-Neuladen und „Jetzt analysieren“ bauen den lokalen Browser-Tracker vor der nächsten Analyse einmal vollständig neu auf.
- Beendete Partien zeigen keine Pfeile der Stellung vor dem letzten Zug mehr; eine neue, kürzere und vollständig validierte Runde hebt alte Wiederholungswartezeiten sofort auf.

## v11.2.5

- Chess.com-Stellungen werden aus den autoritativen `square-XY`-Klassen gelesen; Doppelschritt-Animationen können dadurch keine falschen Zwischenzüge mehr speichern.
- Lichess/Chessground verwendet die Zielkoordinaten aus dem Inline-`transform`; ausgeblendete Ghost-/Fading-Figuren werden ignoriert.
- Unbekannte DOM-Bretter behalten die allgemeine Geometrie-Erkennung, werden aber erst nach einem stabilen Brettbild verarbeitet.

## v11.2.4

- Der lokale Server lädt die vollständige Chess.com-Historie jetzt selbst; Browser-CORS kann lange oder beobachtete Partien nicht mehr nach einigen Zügen stoppen.
- Der Abruf ist auf numerische Chess.com-Spiel-IDs begrenzt, kurz gecacht und wird weiterhin exakt gegen das sichtbare Brett validiert.

## v11.2.3

- Beim Zuschauen liest das Overlay die vollständige Chess.com-Live-Historie anhand der Spiel-ID, auch wenn die sichtbare Zugliste nur späte Züge enthält.
- `chess-tcn` 1.0.1 dekodiert Chess.coms kompakte `moveList`; das Ergebnis wird vor jeder Analyse exakt gegen das sichtbare Brett validiert.

## v11.2.2

- Chess.com-Figurensymbole werden direkt aus verschachtelten Zugknoten in korrektes SAN umgewandelt.
- Autoritative `data-node`-Züge bleiben vor breiten DOM-Ersatztreffern priorisiert; ungültige Duplikate verdrängen die echte Partiehistorie nicht mehr.
- Beim Eintritt in eine neue Startstellung wird die alte Browser-Sitzung automatisch verworfen.

## v11.2.1

- Chess.com sendet jetzt mehrere erkannte Zuglistenvarianten; Python wählt ausschließlich die legale Variante, die exakt zur sichtbaren Stellung passt.
- Dadurch blockiert eine längere, aber fehlerhafte DOM-Variante nicht mehr die vollständige Allie-Historie.

## v11.2.0

- Viewer und Browser-Overlay ruhiger, klarer und kompakter gestaltet; Texte und Statusmeldungen vereinfacht.
- Wirkungslose Modellfelder, unbenutzte Wrapper und das durch automatisches Warmup überflüssige Preload-Skript entfernt.
- FastAPI auf den kompatiblen Patchstand 0.162.2 aktualisiert.
- EXE-Build verwendet wieder das sichere Windows-Temp-Verzeichnis und hinterlässt keine `_MEI*`-Ordner im Projekt.
- Direkte Edge-Erweiterung und automatische Allie-Vorwärmung in Hilfe und Startanleitung richtig dokumentiert.

## v11.1.7

- Beim Serverstart läuft jetzt immer eine echte Allie-Startstellungsanalyse im Hintergrund; Modell und Allie-Cache sind dadurch vor dem ersten Zug warm.
- Die Analyseblase zeigt sofort nach der Bretterkennung Eröffnungs- und Statushinweise, während Allie rechnet.
- Die Orientierung wird nur noch am sichtbaren Brett und seinen Eltern bestimmt; versteckte Chess.com-Bot-Bretter können sie nicht mehr verfälschen.
- Aktuelle Chess.com-Zugknoten mit `data-node="0-N"` werden in der richtigen Halbzugreihenfolge gelesen und gegen das sichtbare Brett validiert.

## v11.1.6

- Die eindeutig erkannte Standardstartstellung wird sofort als vollständige Partie ab Zug 1 analysiert und kann nicht mehr an einer alten Chess.com-Bot-Sitzung hängen bleiben.

## v11.1.5

- Die vollständige Allie-Spielanalyse öffnet sich wieder automatisch neben dem erkannten Brett.
- Bis zu sechs Hinweise zeigen Eröffnung, Stellungsmerkmale, Gegnerabsicht, konkrete Gefahr, Spielverhalten und Pre-Move-Risiko; Stockfish bleibt der objektive Vergleich.
- Chess.com und Lichess nutzen weiterhin dieselbe automatische DOM-Erkennung für Brett, Orientierung, Spielerfarbe und validierte Zuggeschichte – ohne zusätzliche API oder Bibliothek.

## v11.1.4

- Direkte Edge-Erweiterung ersetzt den fehleranfälligen Tampermonkey-Installationsweg.
- Eng begrenzte CORS-Freigabe für Chess.com und Lichess ergänzt.
- Bei fehlender vollständiger Historie startet nach eindeutig erkanntem Zug automatisch ein Stockfish-Fallback; Allie bleibt strikt an bestätigte Historie gebunden.
- Chess.com-Zuglisten werden auch gelesen, wenn Zugnummern nur optisch statt als DOM-Text dargestellt werden; Python validiert die gesamte Folge gegen das sichtbare Brett.
- Eine neue, kürzere Partie auf derselben Chess.com-Seite ersetzt jetzt zuverlässig die Historie der vorherigen Partie.
- Während Brettanimationen wird die Stellung höchstens viermal kurz nachgemessen, statt bis zum Fünf-Sekunden-Intervall zu warten.
- Getrennte Chess.com-Figurensymbole und SAN-Texte werden gemeinsam gelesen (`♘` + `f3` wird `Nf3`), sodass die vollständige sichtbare Historie validiert werden kann.
- Spielerfarbe wird standardmäßig automatisch aus der erkannten Live-Brettseite bestimmt; Weiss/Schwarz bleiben als manuelle Overrides verfügbar.
- Vorhandene `data-san`-Werte und Lichess-Figurensymbole werden direkt übernommen und vollständig gegen das sichtbare Brett validiert.
- Alte Browser-Kompatibilitätsschicht, wirkungslose Einstellungen, internes Plan-Dokument und unbenutzte `.venv` entfernt.

## v11.1.3

- Chess.com-Läufercodes wie `bb` werden nicht mehr als Springer gelesen (`Bb7` statt illegalem `Nb7`).
- Windows nutzt den unterstützten PyTorch-Pfad ohne erfolglosen Rust-Backend-Versuch und mit acht aktiven Experten für schnellere Blitz-Analysen.

## v11.1.2

- Veraltete Pfeile werden bei nicht eindeutig erkannten Brettwechseln sofort ausgeblendet.
- Chess.com-Zuglisten werden zusätzlich aus Buttons, Rollen und sortierten `data-ply`-Elementen gelesen.
- Standardprofil ist 5-Minuten-Blitz (`300+0`); DOM-Änderungen werden nach 120 ms verarbeitet.
- Das Overlay ist kleiner und zeigt nur die zwei wichtigsten Hinweise.

## v11.1.1

- Browser-Overlay zeigt die aktuelle Allie-Top-2-Auswahl sofort und ergänzt Gegner- sowie Pre-Move-Pfeile anschließend.
- Unbenutzte Allie-Vorschauzweige entfernt: maximal drei statt fünf Modellaufrufe pro vollständiger Live-Analyse.
- Allie-Modell wird beim Programmstart im Hintergrund vorgeladen.
- Automatisch eingeblendeten Textblock entfernt und Pfeile deutlich schlanker dargestellt.

## v11.1.0

- Allie-first-Pipeline: Allie ordnet menschlich wahrscheinliche Züge; Stockfish bewertet anschließend nur diese Kandidaten.
- Zwei parallele Live-Worker und die Ergebnis-Zusammenführung durch einen generation-gesicherten latest-only Auftrag ersetzt.
- Fünf Pfeilrollen in Viewer und Overlay exakt vereinheitlicht; sichere Pre-Move-Abdeckung bleibt Allie-basiert.
- Teure universelle DOM-Scans entfernt und alte Overlay-Anfragen bei Stellung oder Einstellung sofort abgebrochen.
- Funktionierende `Allie21 Chess Live Studio.exe` samt reproduzierbarem PyInstaller-Build ergänzt.
- Beschädigte alte `.venv` entfernt; Laufzeitumgebung eindeutig auf `.allie-venv` festgelegt.

## v11.0.0

- Eigenen HTTP-Handler durch FastAPI, Pydantic und Uvicorn ersetzt; lokale Bindung, Herkunftsprüfung und Größenlimits erhalten.
- Installation auf `pyproject.toml`, `uv.lock` und einen einzigen Doppelklickstarter reduziert.
- C#-Starter, PowerShell-Installationskette, zusätzliche BAT-Dateien, altes Requirements-Format und redundanten Öffnungs-Downloader entfernt.
- Allie auf die offizielle `analyze()`-/`predict()`-API mit deren Sortierung und Cache umgestellt; Modellrevision fest gepinnt.
- Eine Stockfish-Instanz und eine Allie-Instanz wiederverwendet; kombinierte Analyse parallelisiert; Videojobs auf die neueste Stellung begrenzt.
- `_merge_human`-Ausfall beseitigt und die Zusammenführung für beide Fertigstellungsreihenfolgen vereinheitlicht.
- Browser und Video auf gemeinsame Stellungs-/Analysekernlogik gebracht; Spielerfarbe von Brettorientierung getrennt.
- Rekonstruktion nicht beobachteter Eröffnungszüge entfernt. Allie erhält nur bestätigte vollständige Historien.
- Overlay auf Chess.com/Lichess begrenzt, ereignisgesteuert gebündelt und gegen veraltete Antworten abgesichert.
- Tests für Reihenfolge, Stoppen/Neustart, veraltete Antworten, fehlende Historie, HTTP-Grenzen und den neuen Startweg ergänzt.
