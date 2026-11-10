# Overlay-, Capture- und GUI-Audit

Gepruefte Ausgangsbasis: `c4987fd20e822ff7834ea4e043241da84317bb8c` auf `main`.
Datum: 2026-11-10. Dies ist kein Nachweis einer vollstaendigen Windows-Release-Abnahme.

## Ursachen und umgesetzte Korrekturen

1. **Viewer initialisierte nicht vollstaendig.** Das HTML hatte `class="stage"`,
   der JavaScript-Code suchte aber `id="stage"`. `ResizeObserver.observe(null)`
   konnte die Initialisierung vor dem Registrieren der Schalter und Capture-Handler
   abbrechen. Die echte ID und ein Test des kompletten HTML-DOMs verhindern dies.
2. **Privat angefordert ist nicht gleich verfuegbar.** Viewer und Erweiterung
   behalten den ausdruecklichen Privatwunsch auch bei API-/Windows-Fehlern.
   Es gibt keinen automatischen Wechsel zu sichtbaren Browserempfehlungen.
   Status und Wiederholen-Schaltflaeche zeigen den tatsaechlichen Zustand.
3. **Win64-Handles.** Alle verwendeten Win32-Funktionen haben explizite
   Argument- und Rueckgabetypen, einschliesslich Cursor, HDC und GDI-Objekten.
   Die MSG-Struktur enthaelt `lPrivate`; GetMessage-Fehler werden erkannt.
4. **Native Pfeile.** Bildschirmposition und lokale Fensterkoordinaten sind
   getrennt. Der Brettversatz wird nicht zweimal auf die Pfeile angewendet.
   Farbige Pfeilspitzen verwenden den passenden Brush; zuvor ausgewaehlte
   GDI-Objekte werden vor DeleteObject wiederhergestellt.
5. **Fenster-Lifecycle.** HWND und Fensterklasse werden vom GUI-Thread
   freigegeben. Ein noch lebender Thread nach Stop-Timeout kann nicht durch
   einen zweiten Thread ersetzt werden. Ein totes Fenster meldet nicht aktiv.
6. **Erklaerungen ausserhalb des Bretts.** Im Viewer liegen Bubble und Text-HUD
   strukturell in der Seitenleiste, auf schmalen Ansichten unter dem Video.
   Die Erweiterung verwendet rechte/linke/obere/untere freie Bereiche; bei
   bildschirmfuellendem Brett liegt das Panel darunter im Dokument und ist
   durch Scrollen erreichbar. Native Texte bekommen einen eigenen Bereich
   ausserhalb des Bretts; ohne passenden Monitorplatz wird Text ausgelassen.
7. **Bildschirmfreigabe.** Der Browser-Picker wird direkt aus dem Klick aufgerufen.
   Fenster/Tab/Bildschirm sind Praeferenzen, keine erzwungene Quelle. Abbruch,
   verweigerte Berechtigung, spaeter zurueckgelieferte Streams und Track-Ende
   werden behandelt. Stop beendet Tracks und laufende Frame-Requests.
   Bildskalierung erhaelt auch bei Hochformat/Ultrawide das Seitenverhaeltnis.
8. **Opening-Persistenz.** Die Erweiterung speicherte `opening_white`, las beim
   Wiederherstellen aber `whiteOpening`. Migration und gemeinsame Normalisierung
   halten gespeicherte Werte, Formular, Analyse-Key und Request konsistent.
9. **Blauer Premove.** Die Erweiterung forderte `preview:false` an und erhielt
   deshalb die erforderliche Fortsetzung nicht. Bei kompletter Zuggeschichte
   wird nun die echte Allie-Vorschau angefordert. FEN bleibt Stockfish-Fallback.
   Die blaue Fortsetzung ist bedingt durch die prognostizierten Antworten,
   keine Garantie fuer einen sicheren Zug gegen jede gegnerische Antwort.
10. **Serverwechsel.** Portwechsel verwerfen alte Capability-Tokens. Die
    Extension-Portabfrage hat ein Timeout; nach 401 wird einmal neu gekoppelt.
    Normale Statusabfragen schalten keinen privaten Modus eines anderen Clients aus.
11. **Menschliche Analyse.** Beide Oberflaechen zeigen echte Modellwahrscheinlichkeiten
    und `expected_think_time_s`, wenn geliefert. Der Viewer bietet den bereits
    vom Backend unterstuetzten normalen/aggressiven Stil explizit an.
    Keine neu erfundenen Wahrscheinlichkeiten, keine automatische Zugausfuehrung.
12. **CI.** Checkout v7.0.1, setup-python v7.1.0 und CodeQL v4 sind auf den
    verifizierten Upstream-Commit gepinnt. JavaScript-Syntaxfehler brechen
    einzeln ab. Playwright Chromium wird installiert; fehlende Browsertests
    duerfen im CI-Gate nicht still uebersprungen werden. CodeQL-Upload bleibt an.

## Lokal ausgefuehrte Verifikation

Umgebung: Linux, Python 3.13.5, Node 22.16.0 und echtes Headless Chromium.
Es wurde ein aus GitHub-Blobs verifizierter **Teilcheckout** der betroffenen
Dateien benutzt, nicht die vollstaendige gelockte Windows-Projektumgebung.

- 26 Python-/Chromium-Tests bestanden, zusaetzlich 18 unittest-Unterfaelle.
- 19 Node-Tests/Fixtures bestanden: neue Viewer-/Extension-Regressionen und
  vier vorhandene Frontend-, Geometrie-, Insight- und Privatmodus-Fixtures.
- Native Tests simulieren Win32; sie beweisen keine reale HWND-/OBS-Funktion.
- Chromium-Tests nutzen echte DOM-Geometrie, Videoelemente und Canvas-MediaStreams,
  aber simulierte HTTP-Antworten und einen simulierten Display-Picker.
- Neue Regressionen wurden zuerst gegen den alten Code fehlschlagend ausgefuehrt.
- Python-Kompilierung, JavaScript-Syntax und Diff-Whitespace geprueft.

Ruff, Mypy, python-chess und Python 3.12 konnten in dieser isolierten Umgebung
nicht nachinstalliert werden: DNS-Zugriff auf PyPI war nicht verfuegbar.
Deshalb wird hier **kein erfolgreicher Gesamtlauf der Projekt-CI behauptet**.

Die waehrend dieses Audits gestarteten GitHub-Jobs endeten vor ihren Schritten;
Job-Logs waren nicht verfuegbar. Die konkrete Konto-/Runner-/Workflow-Ursache
muss in der GitHub-Actions-Ansicht geprueft werden. Ein temporaerer privater
Source-Snapshot-Workflow wurde wieder entfernt, da er keinen Snapshot liefern konnte.

## Grenzen und weitere Abnahme

- Echte Windows-11-Tests: nativer Fensterstart, DPI 100/125/150 Prozent,
  mehrere Monitore, Browserzoom, OBS und Browser-Bildschirmfreigabe.
- Browser-zu-Bildschirm-Koordinaten verwenden weiterhin eine Browserrahmen-
  Schaetzung, keine autoritative HWND-Kalibrierung. Mixed-DPI-Ausrichtung
  ist deshalb noch nicht als exakt abgenommen zu bezeichnen.
- WDA_EXCLUDEFROMCAPTURE ist ein Windows-Aufnahmeausschluss fuer unterstuetzte
  Capture-Verfahren, kein absoluter Schutz gegen jede Aufnahmeart.
- Der native Renderer ist weiterhin ein globales Overlay. Eine vollstaendige
  parallele Mehrbenutzer-/Mehrfenster-Ownership ist nicht implementiert.
- Keine neue portable Windows-EXE gebaut oder als getestet veroeffentlicht.
- Kein echtes Allie-Modelltraining, kein neuer Humanitaets-Benchmark und kein
  vollstaendiger Last-/Latenzbenchmark durchgefuehrt.
- Torch, Transformers und andere Runtime-Pins sowie uv.lock bleiben erhalten;
  breite Major-Upgrades ohne ladbares Modell und gelockte Tests wurden vermieden.
- CodeQL-Berechtigungen und Branch Protection sind externe GitHub-Einstellungen;
  der Workflow wurde nicht zum Verbergen von Fehlern abgeschwaecht.

## Aktualisieren und vor Ort testen

Im bestehenden Projektordner in PowerShell (nicht in C:\Windows\System32):

```powershell
git switch main
git pull --ff-only origin main
$env:ALLIE_PORT = '8741'
.\START_HIER.bat
```

Alten Server vorher normal beenden. Viewer neu laden. In Edge/Chrome die entpackte
Erweiterung aus `browser/` neu laden und den gleichen Port einstellen.
Eine alte portable EXE wird durch einen Git-Pull nicht automatisch neu gebaut.

Pruefen: privater Schalter -> Startet/Bereit/Ein oder ausdrueckliche Fehlerursache;
kein automatischer sichtbarer Fallback. Aufnahme starten, ablehnen, erneut starten,
Stop waehrend des Pickers und Stop ueber den Browser-Freigabebalken testen.
Openings umstellen und neu laden. Bubbles duerfen keine Felder ueberdecken.
Blauer Pfeil erscheint nur mit einer tatsaechlich gelieferten gueltigen Fortsetzung.

```powershell
$env:ALLIE_REQUIRE_BROWSER_TESTS = '1'
uv sync --frozen --extra quality
uv run --frozen python -m playwright install chromium
uv run --frozen pytest -q
uv run --frozen ruff check backend tools tests
uv run --frozen mypy backend --ignore-missing-imports
node --test tests/*.js
```

## Verglichene Primaerquellen

- Microsoft SetWindowDisplayAffinity:
  https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity
- MDN getDisplayMedia und Capture-Lifecycle (auch ueber Context7):
  https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia
- Python ctypes: https://docs.python.org/3/library/ctypes.html
- Allie Upstream (via Firecrawl): https://github.com/y0mingzhang/allie-v2
- Chessground (via Firecrawl): https://github.com/lichess-org/chessground

Die vorhandene board-lokale SVG-Architektur wurde beibehalten. Fuer ein Overlay
auf fremden Brettern wurde keine zweite komplette Brettbibliothek eingebaut;
das wuerde Abhaengigkeiten, Lizenz- und Integrationsaufwand ohne klaren Nutzen erhoehen.
