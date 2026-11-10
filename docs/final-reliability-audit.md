# Erneuter Zuverlaessigkeits-Audit

Datum: 2026-11-10. Gepruefte Remote-Basis:
`fd38d6fd843fd819bd05b2cb2e8be7b5f114e076`, Standardbranch `main`.
Dies ist ein weiterer gezielter Fehlerbehebungsdurchlauf, keine Behauptung,
dass die gesamte Anwendung oder jede Windows-Aufnahmekombination fehlerfrei ist.

## Umgesetzte Korrekturen

1. **MV3-Optionsseite:** Inline-JavaScript wurde durch lokale `connection.js`
   und `options.js` ersetzt. Manifest V3 blockiert die bisherige Inline-Variante.
   Gespeicherte Ports, Validierung und Speicherfehler werden tatsaechlich verarbeitet.
2. **Verbindung testen:** Die Optionsseite prueft den eingestellten Loopback-Port,
   validiert das Allie-Protokoll und bietet einen Viewer-Link. Ein fremder Dienst
   mit HTTP 200 wird nicht als funktionierende Allie-Instanz gemeldet.
3. **Ehrliche Extension-Anzeige:** OK setzt beide Engines voraus. Modellladen,
   Stockfish-Fallback, fehlende Engines und fehlende Verbindung sind unterscheidbar.
   Ein Zeitlimit beendet haengende Abfragen. Portwechsel aktualisieren die Anzeige;
   verspaetete Antworten eines alten Ports duerfen sie nicht ueberschreiben.
4. **Robuste Anmeldung:** Nicht-ASCII- und doppelte Authentifizierungsheader werden
   mit 401 abgelehnt statt einen TypeError/HTTP 500 auszuloesen.
5. **Rate-Limiter:** Jede Policy behaelt ihre eigene Fensterdauer. Kurze Fenster
   loeschen keine langen Budgets. Bei voller Tabelle werden neue IDs abgewiesen,
   anstatt laufende Budgets zu verdraengen und dadurch zurueckzusetzen.
6. **HTTP-Grenze:** Eigenstaendige, typisierte ASGI-Middleware ersetzt die Mutation
   von Starlettes privatem `Request._body`. Auch bei unzutreffender oder fehlender
   Content-Length wird die tatsaechliche Bodygroesse vor der Route begrenzt.
   JSON und JPEG behalten getrennte Limits; unvollstaendige Uploads haben ein Zeitlimit.
7. **Origins und Fehler:** Beschaedigte Origins werden mit 403 beantwortet. Lokale
   Origins muessen zum Zielport und Protokoll passen. Erlaubte Browserclients
   koennen auch Authentifizierungsfehler ueber CORS lesen. Retry-After bleibt erhalten.
8. **Readiness:** Nicht gestartet, laedt und fehlgeschlagen werden unterschieden.
   `/readyz?source=allie`, `?source=stockfish` oder `?source=both` pruefen die
   benoetigte Engine-Kombination. Der Standard bleibt beide Engines.
9. **FEN-Fallback:** Reine FEN-Anfragen werden nicht mehr vom Ladezustand des
   Allie-Modells blockiert. Widerspruechliche PGN/FEN-Eingaben werden vor diesem
   Lade-Gate abgelehnt. Beschaeftigte Analyse antwortet mit Retry-After.
10. **Stockfish-Installation:** Download landet gestreamt auf temporaerem Speicher,
    nicht vollstaendig im RAM. Archiv UND neu extrahierte EXE werden gehasht.
    Eindeutige temporaere Namen und atomarer Austausch schuetzen die alte Datei.
    Fehler/Abbruch hinterlassen keine partielle EXE. CLI-Fehler liefern Exitcode 1.
11. **Erste Modelleinrichtung:** `backend/model_setup.py` prueft standardmaessig
    offline. Nur `--download` laedt die exakt gepinnte Revision und ausschliesslich
    `config.json` und `model.safetensors`, wie im vendorten api.resolve vorgesehen.
    `MODELL_EINRICHTEN.bat` bietet dafuer einen ausdruecklich bestaetigten Einstieg.
    `trust_remote_code=False` und `local_files_only=True` des Laufzeitloaders bleiben.
12. **Tests bereinigt:** Eine alte Assertion verlangte noch preview=False trotz
    blauem Premove; eine andere verlangte das von MV3 verbotene Inline-Script.
    Diese Erwartungen werden durch ausgefuehrte Request-/Speicherpruefungen ersetzt.
    Der Kapazitaetstest prueft Budgeterhalt und Ablauf statt unbegrenztem ID-Wechsel.

## Anwendung

Im vorhandenen Projektordner, nachdem der alte Server beendet wurde:

```powershell
git switch main
git pull --ff-only origin main
.\START_HIER.bat
```

Die entpackte Browser-Erweiterung anschliessend neu laden. In ihren Optionen
Port speichern und **Verbindung testen** verwenden. Der Port muss zu ALLIE_PORT passen.

Fehlen beim ersten Start die Allie-Gewichte, nach Einrichtung der Python-Umgebung:

```powershell
.\MODELL_EINRICHTEN.bat
```

Alternativ mit dem bereits eingerichteten Projektinterpreter:

```powershell
.\.allie-venv\Scripts\python.exe backend\model_setup.py --download
```

Danach den Server neu starten. Ohne --download wird nur der lokale Cache geprueft.
Die Dateipruefung ist kein Inferenztest und kein unabhaengiger Vollhash-Beweis fuer
alle Gewichte. Es wurde hier kein grosser Modelldownload durchgefuehrt.

## Verifikation und Grenzen

- 46 gezielte Python-Tests plus 8 Unittest-Unterfaelle bestanden.
- 12 Tests der tatsaechlichen Extension-Skripte unter Node bestanden.
- 3 weitere Node-Tests fuehrten den unveraenderten, aus GitHub gelesenen
  analyze()-Funktionsausschnitt aus. Eine Mutation zur alten preview=False-Logik
  wurde vom Test erkannt. Dies ist kein kompletter Browser-Userscript-Lauf.
- Ein echter lokaler Uvicorn-/HTTP-Test pruefte Chunked-Body-Replay,
  Nicht-ASCII-Authentifizierung und CORS-Fehlerheader.
- Neue Regressionsfaelle wurden vor den jeweiligen Implementierungen fehlschlagend
  ausgefuehrt; die Body-/Origin-Luecken zusaetzlich gegen die alte Middleware.
- Python-Kompilierung, JavaScript-Syntax und Diff-Whitespace geprueft.
- Review war ein separater Selbstreview; kein unabhaengiger Reviewer verfuegbar.

Die lokale Umgebung war Python 3.13 und eine **hashverifizierte Auswahl** von
Repository-Dateien, nicht der komplette gelockte Python-3.12-Windows-Checkout.
Die vollstaendige pytest-Ausfuehrung scheiterte deshalb bei der Sammlung der
bestehenden HTTP-/Offline-Tests an fehlenden allie_local_server-/vision-Modulen.
Die neuen echten Chromium-Tests konnten nicht navigieren:
`net::ERR_BLOCKED_BY_ADMINISTRATOR`, auch fuer localhost. Diese Richtlinie wurde
nicht umgangen und der Fehler nicht als bestandener Test ausgegeben.
Ruff, Mypy und python-chess waren lokal nicht installierbar; PyPI-DNS war gesperrt.

Es wurde kein Modell geladen, keine Windows-EXE gebaut und kein OBS-, HWND-,
Mixed-DPI- oder Capture-Exclusion-Test auf Windows durchgefuehrt.
Neue Testdateien werden vom bestehenden CI-Discovery mitgenommen; die gesamte
Remote-CI muss separat nachweislich laufen. Ein gepushter Commit allein ist kein
Nachweis einer erfolgreichen CI oder Release-Abnahme.

## Bewusst nicht als erledigt ausgegeben

- Autoritative HWND-/Browser-Koordinatenkalibrierung und parallele Session-Ownership.
- Vollstaendiges Pairing-Protokoll; die vorhandene Origin-/Capability-Architektur bleibt.
- Strengere Viewer-CSP ohne unsafe-inline und vollstaendige Frontend-Modularisierung.
- Voller Runtime-Dependency-Audit, modellkompatible Major-Upgrades, Last-/Latenzbenchmark.
- Vollstaendige Windows-/Edge-/OBS- und portable Release-Abnahme.
- Repository-Administration, Branch Protection und Code-Scanning-Freischaltung.
- Die allgemeine Statusbeschriftung des Viewers ist weiterhin weniger detailliert
  als API und neue Extension-Anzeige; kein Erfolg der echten Modelle wird behauptet.

Keine neuen Runtime-Abhaengigkeiten wurden hinzugefuegt. Modell-, Engine- und
Paket-Pins sowie uv.lock bleiben erhalten. Ein Framework-/Engine-Austausch ohne
messbaren Nutzen wurde vermieden. Nur verifizierte Aenderungen am Standardbranch;
keine History-Umschreibung und keine Loeschung ungemergter fremder Arbeit.

## Recherchebasis

- Chrome MV3 CSP: https://developer.chrome.com/docs/extensions/reference/manifest/content-security-policy
- Starlette ASGI-Middleware: https://github.com/kludex/starlette/blob/main/docs/middleware.md
- Hugging Face Download/Cache: https://huggingface.co/docs/huggingface_hub/guides/download
- Allie-Referenz: https://github.com/y0mingzhang/allie-v2
- Gepinnter vendorter Loader: backend/vendor/allie_model/api.py und modeling_allie.py

Die Referenzen wurden mit Firecrawl, Context7 und offiziellen Dokumentationen
abgeglichen. Neue APIs wurden nicht ungeprueft als vorhanden vorausgesetzt;
insbesondere basiert die HTTP-Grenze auf oeffentlichen ASGI receive/send-Vertraegen.
