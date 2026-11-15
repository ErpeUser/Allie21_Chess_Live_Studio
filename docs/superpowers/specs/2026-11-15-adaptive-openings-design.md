# Adaptive Openings und Ragebait

## Auftrag und Entscheidungen

Der Nutzer verlangt zusätzlich zum Remis-Pfeilfix eine passende Auswahl aus den vorhandenen Eröffnungen, Wechsel bei abweichendem Verlauf, kombinierte Pläne und mehr Ragebait. Umsetzung, vollständige Tests und Upload sind beauftragt. Die folgenden Implementierungsentscheidungen konkretisieren diesen Auftrag; es sind keine zusätzlich vom Nutzer vorgegebenen Einzelheiten.

Die gespeicherte Eröffnung bleibt die bevorzugte Linie. Die aktuell nutzbare Linie wird separat angezeigt. Kandidaten müssen zur vollständigen aktuellen Stellung einschließlich Zugrecht, Rochade und legalem En-passant passen. Zugumstellungen sind bei gleicher Halbzugzahl erlaubt; spätere Wiederholungen dürfen die Eröffnung nicht neu starten. Wenn keine gespeicherte Linie passt, läuft die freie Analyse weiter.

## Ansätze

Ein reiner Vergleich von Zugpräfixen verpasst Zugumstellungen und Alternativen. Das Übernehmen einer nur ähnlich aussehenden Linie könnte falsche Pläne und illegale Züge erzeugen. Gewählt wird deshalb ein begrenzter Index verifizierter Eröffnungsstellungen mit exaktem Stellungsabgleich. Gemeinsame nächste Züge können mehreren vorhandenen Eröffnungen zugeordnet sein. Der bevorzugte passende Plan erhält Vorrang; bei Alternativen helfen die tatsächlichen Allie-Zugwahrscheinlichkeiten bei der Auswahl. Sie werden nie als Gewinnchance bezeichnet.

## Auswahl und Vorschau

Der zusätzliche Stil `ragebait` berücksichtigt mehr reale Allie-Kandidaten und passende ungewöhnliche Eröffnungszüge. Er bevorzugt innerhalb taktischer Grenzen Gambits, Schachgebote, Drohungen und Königsdruck. Ein unmittelbares eigenes Matt und das Vermeiden eines gegnerischen Matts in einem Zug gehen vor. Vorhandene Stockfish-Bewertungen können unvertretbare Kandidaten zurückstufen; Ragebait erlaubt dabei mehr Spielraum als Aggressiv. Die Auswahl ist eine Heuristik und keine Garantie für objektiv beste Züge.

Eigene Hauptzüge werden vor der Berechnung ihrer Vorschau endgültig geordnet. Gegnerprognosen behalten die Modellreihenfolge. Eigene Antworten und blaue Fortsetzungen verwenden dieselbe Stil-/Repertoirepolitik, ohne Wahrscheinlichkeiten oder Zweigrisiken umzudefinieren. Eine riskante Stellung darf die gesamte legale Zugliste nicht verschwinden lassen.

## Oberfläche und Kompatibilität

`repertoire.selection` und `primary` bleiben die gespeicherte Präferenz. Neu sind `active_selection`, `active_primary`, `compatible_openings`, `adaptation_reason` und `applied`. `expected_move`/`expected_san` benennen einen möglichen Repertoirezug; ohne Modellunterstützung wird daraus kein angeblicher Allie-Kandidat. Die Oberfläche zeigt Präferenz, passende aktive Linie oder freies Spiel und den Grund getrennt. Native Kurzmeldungen erklären Wechsel früh genug für den zweizeiligen HUD.

Frische UI-Profile verwenden Ragebait; ausdrücklich gespeicherte Stile bleiben erhalten. API-Anfragen ohne Stil verwenden weiterhin `normal`. Privatmodus, Authentifizierung, Verlauf/Zugrecht, aktuelle FEN, Session- und Stale-Gates bleiben verbindlich. Keine automatischen Züge. Keine neuen Abhängigkeiten oder Modellgewichte. App/Userscript 11.2.26 und Extension 11.2.26.0 behalten Schlüssel und ID.
