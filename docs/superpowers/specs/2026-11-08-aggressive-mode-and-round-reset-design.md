# Aggressiv-Modus und Rundenwechsel

## Ziel

Das Live-Overlay soll nach Remis oder anderem Partieende keine veralteten Pfeile zeigen und auf derselben Website eine neue Partie sauber erkennen. Zusätzlich erzwingen sowohl ein Seiten-Neuladen als auch „Jetzt analysieren“ vor der nächsten Analyse einen Neuaufbau der Browser-Sitzung. Ein optionaler Spielstil „Aggressiv“ soll unter Allies legalen Top-Kandidaten Matt, Schach und direkten Königsdruck bevorzugen, ohne die vollständige Historie oder Allie-first aufzugeben.

## Grenzen

- Das Overlay klickt weder Züge noch „Neue Partie“ automatisch.
- „Normal“ behält die unveränderte Allie-Reihenfolge.
- „Aggressiv“ wählt nur aus Allies vorhandenen Kandidaten; Stockfish bleibt Kontrolle und ersetzt Allie nicht.
- Gegnerzüge werden nicht aggressiv umsortiert.
- Keine neue Abhängigkeit.

## Ansatz

Eine kleine, zentral getestete Rangierfunktion gewichtet im aggressiven Modus sofortiges Matt, Schach und Angriffe im gegnerischen Königsring vor der Allie-Wahrscheinlichkeit. Das Overlay sendet den Stil an die bestehende Analyse-API. Live-Anfragen aktivieren keine Endspiel-Rückschau; dadurch kann eine beendete Partie keine Pfeile für die Stellung vor dem letzten Zug auf das Endbrett malen. Beim ersten stabilen Brettbild nach Scriptstart oder nach „Jetzt analysieren“ wird der lokale Browser-Tracker genau einmal zurückgesetzt und anschließend aus der bestätigten sichtbaren Historie neu aufgebaut. Die bestehende Browser-Sitzung akzeptiert weiterhin eine kürzere, vollständig validierte Historie als neue Runde.

## Verworfene Ansätze

- Reiner Stockfish-Angriffsstil: verletzt Allie-first.
- Automatisches Klicken auf „Neue Partie“: unnötiger Eingriff in die Website.
- Neue Schachbibliothek: python-chess und die vorhandene Stockfish-Anbindung reichen aus.
