# Private- und Share-Overlay – Design

## Zweck

Allie21 unterscheidet zwischen einem geschützten privaten Windows-HUD und einem
ausdrücklich aktivierten Share-Modus. Private ist der Standard und zeigt nur
ein verifiziert capture-excluded HWND. Share deaktiviert diese Exclusion und
zeigt denselben Renderzustand in einer Gesamtbildschirm-Aufnahme; ein einzelnes
Browserfenster wird nur als unterstützt gemeldet, wenn der Browser-HUD tatsächlich
in dieser Quelle enthalten ist.

## Ziele

- Eine versionierte lokale Modusquelle synchronisiert Viewer, Edge-Erweiterung,
  Native-HUD und Statusdiagnose.
- Private bleibt bei fehlender/unklarer `SetWindowDisplayAffinity`-Bestätigung
  unsichtbar und meldet „Privatmodus nicht verifiziert“.
- Share ist ein expliziter Umschalter „HUD in Bildschirmübertragung anzeigen“.
- Board-Geometrie, Orientierung, Farben, Pfeilbreite, Zugfolge und Hinweise
  kommen aus einem gemeinsamen Visual-Payload.
- Launcher startet oder verwendet genau einen eigenen Dienst, erneuert Pairing
  und beendet nur eigene Prozesse.
- Onedir-Build, entpackte Edge-Erweiterung, Desktop-Verknüpfung, Hashes und
  Smoke-Diagnose sind reproduzierbar.

## Nicht-Ziele

- Keine automatischen Schachzüge oder Maus-/Tastatursteuerung.
- Keine Behauptung, dass ein einzelnes Overlay zugleich aus Capture ausgeschlossen
  und in derselben Quelle sichtbar sein kann.
- Keine Beendigung fremder Prozesse und keine Änderungen an Browserprofilen.

## Architekturentscheidung

Das Backend ist die lokale Quelle der Wahrheit. Ein Modusdatensatz enthält
`mode`, monotone `version`, `updated_at`, Quelle und Verbindungs-/Capture-Status.
Viewer und Erweiterung senden Änderungen mit erwarteter Version; der Server
entscheidet bei Konflikten nach Version und Zeitstempel und liefert den
bestätigten Datensatz zurück. Beide Clients pollen bzw. abonnieren denselben
Status und stellen ihn nach Neustart wieder her.

Der native Controller kennt `private` und `share`. Private setzt und liest
`WDA_EXCLUDEFROMCAPTURE` vor dem ersten sichtbaren Frame. Share setzt
`WDA_NONE`, bleibt topmost, transparent, click-through und no-activate. Wenn
die API nicht sicher bestätigt werden kann, bleibt Private verborgen; Share
bleibt sichtbar, aber der Status nennt die tatsächliche Capture-Eigenschaft.

Der Browser-HUD ist nur bei `share` aktiv. Die Viewer-Geometrie markiert die
Aufnahmequelle (`monitor`, `window`, `tab`) und darf für eine einzelne
Browserfenster-Quelle nur dann „unterstützt“ anzeigen, wenn der eigene HUD in
dieser Quelle gerendert wird. Der private Pfad leert Browser-DOM/SVG immer.

## Betriebs- und Rückfallregeln

- Port 8765: eigener, kompatibler Allie-Dienst wird wiederverwendet; ein
  fremder Dienst wird nicht beendet und führt zu einer eindeutigen Diagnose.
- Lease-TTL wird bei unveränderter Stellung erneuert; abgelaufene Claims werden
  erneut angefordert. Fehlgeschlagene Claims werden nicht als bestätigt gespeichert.
- `/health` trennt `alive`, `ready`, `model_loaded` und `stockfish_available`.
- Beim Stoppen werden Session, Overlay, Runtime und Tray sauber geschlossen.

## Verifikation

Automatisiert werden Modus-/Versionskonflikte, Lease-Erneuerung, Pairing nach
Kaltstart und Dienstneustart, stale-position suppression, beide Websites,
alle fünf Pfeilfarben sowie Build-/Shutdown-Diagnose geprüft. Echte Windows-
DWM-, Discord- und Multi-Monitor-Abnahmen bleiben als Plattformtests
gekennzeichnet und werden nicht aus Linux-Smokes abgeleitet.
