# Allie: kompakte Oberfläche und kurze Hinweise am Brett

Status: Vorschlag zur Freigabe. Noch keine Änderung am Produktcode.

## Grundlage und Ziel

Die zehn Aufnahmen aus `.build/gui-screenshots.html` zeigen einen sehr hohen
leeren Vorschaubereich, ständig offene Einstellungen, gleichgewichtete Kästen,
zu große Radiofelder im Browser-Overlay und doppelte Erklärungstexte. Die schmale
Ansicht ist über 3.000 Pixel lang. Der Nutzer möchte eine einfachere Anordnung,
natürliche deutsche Texte und kurze Sprechblasen neben dem Schachfeld, die bald
wieder verschwinden.

## Betrachtete Ansätze

1. **Empfohlen: vorhandenes Studio gezielt vereinfachen.** Bedienleiste und
   Einstellungen neu ordnen; Hinweise als eigene kurzlebige Komponente in Viewer,
   Browser-Overlay und nativem Overlay. Die vorhandenen Analyse- und Sicherheits-
   pfade bleiben die Grundlage. Das ist der kleinste zusammenhängende Umbau.
2. **Nur das Browser-Overlay reduzieren.** Schneller, lässt aber die überladene
   Viewer-Oberfläche und widersprüchliche Hinweisdarstellung bestehen.

Ein Frameworkwechsel oder eine neue Analyse-Engine lösen die sichtbaren Probleme
nicht und gehören nicht zu diesem Auftrag.

## Empfohlene Anordnung

- Oben: Quelle wählen, Start/Stop, ein klarer Moduswähler, kurzer Systemstatus.
- Eine Hauptfläche für das Brett bzw. die Vorschau, mit begrenzter Leerhöhe und
  ohne Streckung durch die Höhe der Einstellungsseitenleiste.
- Elo, Zeit, Farbe, Stil und Eröffnungen unter zunächst geschlossenen
  Analyse-Einstellungen. Port, Worker und Updates unter Verbindung/Diagnose.
- Privat, Teilen und Im Tab sind eine exklusive Auswahl, keine drei unabhängig
  wirkenden Ein/Aus-Schalter. Die bestehenden internen Modi bleiben erhalten.
- Zugdaten und Details nur bei Bedarf. Mobil keine ständig offene Formularwand.
- Im Browser öffnet eine neue Analyse nicht mehr automatisch das Einstellungs-
  fenster. Die Sprechblase ist eine separate Komponente außerhalb des Bretts.

## Kurz-Hinweise

- Ein aktueller Hinweis, höchstens zwei kurze Sätze; Richtwert 100 Zeichen.
- Vorrang für echte taktische Warnungen, danach konkrete Stellungsinformationen.
  Eröffnungsnamen, Debug-Status und Wiederholungen werden nicht als laufende
  Sprechblasen ausgegeben.
- Standarddauer: fünf Sekunden. Eine identische Meldung zur selben Stellung
  setzt die Frist bei Polling, Lease-Erneuerung oder Neuzeichnen nicht zurück.
- Stellungswechsel, Sessionwechsel, Stop, deaktivierte Empfehlungen und veraltete
  Ergebnisse entfernen alte Hinweise sofort. Alte Timer dürfen neuere Hinweise
  nicht entfernen.
- Platzierung rechts neben dem Brett, sonst links, darunter oder darüber in
  freiem Platz. Keine Figur und kein Brettfeld überdecken. Bei fehlendem Raum
  unter dem Brett im Dokumentfluss anzeigen.
- Im Viewer neben der angezeigten Brettfläche; keine ungesicherten absoluten
  Bildschirmkoordinaten für fremde Capture-Quellfenster erfinden.
- Im nativen Overlay läuft die Textfrist eigenständig ab. Das Ausblenden des
  Texts entfernt keine weiterhin gültigen Pfeile und schwächt den bestätigten
  Aufnahmeausschluss nicht ab.
- Fehlt nativ außerhalb des Bretts freier Monitorplatz, den Text auslassen und
  gültige Pfeile erhalten. Die Ausweichposition im Dokumentfluss gilt für die
  Browseroberflächen.
- Im Privatmodus keinerlei DOM-/SVG-Fallback für Empfehlungen. Ein nicht
  bestätigtes natives Overlay bleibt geschlossen und meldet die Ursache.
- Verbindungs- und Modellfehler bleiben als kleiner, lesbarer Status erhalten.
  Sie werden nicht durch eine kurzlebige Sprechblase ersetzt.

## Sprache und Darstellung

- Beispiele: „Wähle ein Fenster mit dem Schachbrett.“, „Allie lädt noch.
  Stockfish ist bereit.“, „Zugfolge fehlt. Importiere die Partie als PGN.“
- „Dein König steht im Schach.“ nur bei tatsächlich erkanntem Schach.
- Keine garantierte Sicherheit, erfundene Wahrscheinlichkeiten oder sichere
  Mattbehauptungen aus unvollständigen Varianten. Zugempfehlungen behalten ihren
  tatsächlichen Engine- und Verlaufskontext.
- Bestehende Schach-Farbwelt ruhiger einsetzen: dunkles Braun, helle Schrift,
  ein goldener Aktionsakzent; deutlich weniger Kästen und keine Zierverläufe.
- Abstände und Hierarchie durch die gelesene Linear-Designstudie informiert;
  keine fremden Markenfarben, Texte oder Logos übernehmen.
- Produktschrift bleibt die vorhandene Systemschrift. Figma nutzt Roboto als
  verfügbare Entwurfsschrift. Sichtbare Fokusmarkierungen und reduzierte Bewegung
  bleiben berücksichtigt.

## Bearbeitbarer Entwurf

Figma: https://www.figma.com/design/sYQ0atSaf6YjzUnZAdHhbw

Drei bearbeitbare Ansichten: kompaktes Studio, unabhängige Sprechblase neben
dem Brett und schmale Ansicht mit geschlossenen Einstellungen. Die Brettinhalte
und Hinweisbeispiele sind als Designbeispiele zu verstehen, nicht als neue
Modellvorhersagen.

Ein separater Humanizer ist in dieser Sitzung weder als lokale Anleitung noch
als verbundenes Werkzeug verfügbar. Die Texte werden direkt sprachlich gekürzt.

## Umsetzung und Prüfung nach Freigabe

- Vorhandenes HTML, JavaScript und Python weiterverwenden; nur auf main arbeiten.
- UI-Kontext und Designentscheidungen in DESIGN.md festhalten.
- Zuerst Regressionen für Hinweisfrist, Duplikate, Positions-/Sessionwechsel,
  privaten Fehlerpfad und Platzierung außerhalb des Bretts.
- Browser- und Viewer-Tests mit echten DOMs und kontrollierten Daten ausführen;
  native Textablauf-Tests mit dem vorhandenen Win32-Testadapter.
- Vollständige AGENTS.md-Prüfsequenz ausführen und alle Skips sowie Warnungen
  nennen. Neue Screenshots im bestehenden `.build`-Bereich aufnehmen.
- Anwendung und Userscript gemeinsam versionieren; Extension-Code erhält eine
  neue version/version_name. Extension-Key und ID unverändert erhalten.
- Keine neuen Gewichte, kein Training, kein automatischer Schachzug, keine
  kostenpflichtigen Dienste, keine Änderung an GitHub-Abrechnung oder Runnern.
- Eine lokale Bundle-Aktualisierung und ein Push erfolgen nur im freigegebenen
  Umfang; keine Veröffentlichung eines GitHub-Releases.
