# Adaptive Openings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement the tasks with independent review.

**Goal:** Vorhandene Eröffnungen passend kombinieren, einen stärkeren Ragebait-Stil anbieten und den Remis-Pfeilfix erhalten.

**Architecture:** Ein begrenzter Stellungsabgleich liefert legale Repertoirekandidaten. Eine gemeinsame Auswahlpolitik ordnet eigene reale Modellzüge vor ihren Vorschauen; die Oberflächen zeigen Präferenz und aktive Linie getrennt.

**Tech Stack:** Bestehendes Python 3.12, python-chess, FastAPI, JavaScript, Node-Testharness und Playwright.

**Spec:** ../specs/2026-11-15-adaptive-openings-design.md

## Global Constraints

- Authentifizierung, Pairing, Capture-Schutz, exakte Stellung und veraltete Ergebnisse bleiben unverändert geschützt.
- Keine automatischen Schachzüge, erfundenen Modellwahrscheinlichkeiten, neuen Abhängigkeiten oder Modellgewichte.
- API-Standard `normal`; frische UI-Profile `ragebait`; gespeicherte ausdrückliche Stile erhalten.
- App/Userscript 11.2.26; Extension 11.2.26.0; unveränderte Extension-ID.

## Review Focus

- Abweichende Zugrechte/Rochade/En-passant und späte Wiederholungen liefern keinen falschen Buchzug.
- Ausgewählte seltene Buchzüge außerhalb der ersten fünf verwenden ihre echte Modellwahrscheinlichkeit.
- Taktische/Engine-Umordnung darf Vorschau und Hauptpfeil nicht voneinander trennen.
- Gegnerprognosen und Mehrzweig-Risiken werden nicht als eigene Stilbewertungen umgedeutet.
- Angepasste Anzeigen verändern keine Präferenzen und bleiben im Privatmodus verborgen.

## Task 1: Repertoire-Resolver

**Files:** backend/chess_extras.py; tests/test_adaptive_repertoire.py.

**Interface:** `adaptive_repertoire_candidates(moves, side, selection=None)` liefert `selection`, `primary`, `uci`, `san`, `match`, `matched_plies`, `preferred`. Bestehende strikte Hilfsfunktionen bleiben kompatibel.

- [x] Fehlende Fallback-/Zugumstellungsfälle und Rechte-/Halbzuggrenzen als rote Tests belegen.
- [x] Nur legale, zur aktuellen Stellung passende eigene Fortsetzungen liefern.
- [x] Vorhandenen Stockfish-Mattwert als `score_mate` weiterreichen.
- [x] Gezielt testen und unabhängig prüfen.

## Task 2: Eigene Zugauswahl und Vorschau

**Files:** backend/allie_local_server.py; tests/test_ragebait_analysis.py.

- [x] Seltene Buchzüge, taktischen Vorrang, wechselnde Engine-Spitze und Gegnerreihenfolge reproduzieren.
- [x] Echte Verteilung bis zur begrenzten Kandidatenauswahl erhalten und Ragebait ergänzen.
- [x] Eigene Reihenfolge vor Vorschauen abschließen; Stil und Repertoire auf eigene Fortsetzungen anwenden.
- [x] Metadaten und frühe native Erklärung ergänzen; Remis-Regressionen erneut prüfen.

## Task 3: Anzeigen und Wire-Vertrag

**Files:** viewer/index.html; browser/allie21_overlay.user.js; backend/live_server.py; backend/live_session.py; zugehörige JS-/HTTP-Tests.

- [x] Rote Tests für Ragebait-Roundtrip, Präferenz/aktive Linie, Legacy-Daten und Privatsphäre ergänzen.
- [x] Stil akzeptieren, speichern und anzeigen; keine Auswahl durch Serverantwort überschreiben.
- [x] HTTP- und Live-Annahme mit echten Validierungswegen prüfen.

## Task 4: Integration und Veröffentlichung

**Files:** Versionsmetadaten, CHANGELOG.md, README_DE.md, VERSIONEN.md und PR #12.

- [x] Versionsmetadaten ohne Paketänderungen auf 11.2.26 synchronisieren.
- [x] Vollständige lokale AGENTS.md-Prüfungen ausführen; Grenzen/Skips dokumentieren.
- [x] Unabhängiges Gesamt-Review und konkrete Befunde durch Regressionstests schließen.
- [ ] Geprüften Commit hochladen, Windows-/Browser-CI ausführen und den PR aktualisieren.

### Prüfstand vor dem Upload

- Unittest: 289 Tests, erfolgreich, ein Skip der lokal nicht startbaren Chromium-Optionsklasse.
- Pytest mit erforderlichen Browsertests: 335 bestanden; 14 Browser-Setup-Fehler durch den von der Sandbox verweigerten Chromium-Socket; zwei vorhandene FastAPI-Deprecation-Warnungen.
- Node: 105 bestanden, keine Skips. Ruff, Compileall, Versions-/Identitätsprüfung, Lockfile-Konsistenz und `git diff --check` erfolgreich.
- Mypy unter Linux: 35 Meldungen in `native_overlay.py`, identisch mit der eingecheckten Plattform-Baseline. Mypy für `win32`: erfolgreich, 18 Quelldateien.
- Unabhängiger Resolver-/UI-Review sowie abschließender Server-Review ohne verbleibende Findings. Die während des Reviews reproduzierten Fehler bei seltenen Mattabwehrzügen und blauen Fortsetzungen sind mit Regressionstests geschlossen.

Der Abschluss der Veröffentlichung und die Ergebnisse am tatsächlich hochgeladenen Commit werden in [PR #12](https://github.com/ErpeUser/Allie21_Chess_Live_Studio/pull/12) dokumentiert. Dieser Plan hält den lokalen Stand unmittelbar vor dem Upload fest. Echte Modellgewichte und eine native Windows-/Edge-Abnahme auf dem Benutzer-PC gehören nicht zu diesem lokalen Prüflauf.
