# Main, Codex und Windows aktualisieren

Der Prüfbranch vom 15. November 2026 trägt App/Userscript **11.2.25** und Extension **11.2.25.0**. Er ist noch keine lokale Installation oder Windows-Freigabe. [Prüfbelege und offene Abnahmen](six-agent-20261115/README.md) müssen vor einer gesonderten lokalen Aktualisierung beachtet werden; die folgenden Befehle wurden durch den Cloud-Prüflauf nicht ausgeführt.

## Einmalig auf deinem Windows-PC

Allie im Infobereich beenden. Im echten Git-Checkout, nicht in einer ZIP-Kopie:

```powershell
git pull --ff-only origin main
.\UPDATE_ALLIE.cmd
```

Voraussetzungen: Git, angemeldete GitHub CLI (`gh auth login`), Python 3.10+ oder
uv, sowie uv/uvx im PATH fuer den bestehenden Python-3.12-Build. Der Build kann
Netzwerk fuer gesperrte Pakete und Stockfish brauchen. Modellgewichte werden dabei
nicht geladen. Git/gh verwalten die Anmeldung; keine Tokens im Repository.

Der erste Aufruf installiert repository-lokale Git-Hooks, sofern keine eigenen
Hooks vorhanden sind. Danach laufen sie nach main-Merge/Fast-forward oder Rewrite.
Ein `git pull` ohne Aenderungen startet keinen Git-Hook: fuer wirklich jeden
Abgleich UPDATE_ALLIE.cmd benutzen. Fremde Branches werden nicht automatisch
ausgecheckt. Lokale Aenderungen werden nicht geloescht oder automatisch gestasht.

## Edge erstmalig umstellen

Nach einer gesonderten lokalen Installation unter `edge://extensions` die neue Version **11.2.25** neu laden. Fuer einen
festen Installationspfad die entpackte Erweiterung aus
`%LOCALAPPDATA%\Allie21\EdgeOverlay` laden; dieser Ordner entsteht beim erfolgreichen
lokalen Update. Der echte Checkout-Ordner `browser/` funktioniert ebenfalls.
Eine andere alte ZIP-Kopie wird durch einen Git-Pull nicht aktualisiert.
Die ID bleibt `omboihgfgofgmidefcpkihgglhkiielo`, ohne zusaetzliche Berechtigungen.

Ab dieser Version prueft die entpackte Erweiterung bei ihren normalen Alarmen
Version und Fertig-Marker der lokalen Dateien. Bei einem fertigen Update wird die
Erweiterung neu geladen. Offene Schach-Tabs danach selbst neu laden; laufende
Spiele werden nicht durch automatische Tab-Reloads unterbrochen. Store-Erweiterungen
werden nicht ueber diesen Entwicklungs-Updater verwaltet. Die Automatik ist in den
Optionen abschaltbar. Das erste Neuladen der alten 11.2.23 bleibt manuell notwendig.

## Was UPDATE_ALLIE.cmd macht

1. Prueft erwartetes origin, main, sauberen Checkout und parallele Updates.
2. Bearbeitet alle offenen main-PRs. Interne, nicht als Draft markierte, konfliktfreie
   PRs werden nur mit erfolgreichen vorhandenen Windows-, Wartungs-, Secret- und
   CodeQL-Checks und ohne offene Review-Aenderungsanforderung gemergt. Veraltete
   interne Branches werden aktualisiert und fuer neue Checks zurueckgestellt.
   Ein blockierter PR verhindert nicht die Pruefung der restlichen PRs. Es wird
   kein KI-Agent heimlich gestartet und kein fehlgeschlagener Test umgangen.
3. Aktualisiert main mit --ff-only. Loescht nur Branches, deren kompletter Tip in
   origin/main enthalten ist und die weder geschuetzt sind noch einen offenen PR
   haben. Eine SHA-Lease verhindert die Loeschung zwischenzeitlich neuer Pushes.
   main/master/develop/dev und release/* bleiben erhalten. Kein branch -D.
4. Startet fuer das Deployment einen frischen Python-Prozess, damit neue Scripts
   nach dem Pull verwendet werden. Inhalts-Hashes entscheiden ueber einen Neubau.
   Ein unveraenderter bestehender Build wird dennoch erneut geprueft.
5. Baut bei Bedarf in einem getrennten Verzeichnis. Gesperrte Dependencies,
   Stockfish-Hash, Runtime-Inventar, SHA256SUMS und HTTP-Serverstart werden geprueft.
   Erst dann wird der komplette portable Ordner ersetzt. Der vorige Stand bleibt
   im Bericht genannten .build-Pfad erhalten; eine fehlgeschlagene Umbenennung
   stellt den alten Ordner wieder her.
6. Aktualisiert die Desktop-Verknuepfung zur EXE im kompletten release-Ordner und
   den stabilen Edge-Ordner einschliesslich Dateiloeschungen. Eine einzelne EXE
   auf dem Desktop waere bei diesem onedir-Aufbau unvollstaendig.

## Service Worker: Inaktiv

Das ist der normale Manifest-V3-Ruhezustand. Es gibt keinen Dauer-Keepalive.
Ein Klick auf das Allie-Symbol oeffnet Verbindung/Updates. **Worker aufwecken und
 testen** prueft die Erweiterung; **Server-Verbindung testen** prueft separat
localhost. Angezeigt wird die wirklich geladene Erweiterungsversion.

Die Erweiterungsshell dieses Prüfbranches ist 11.2.25.0; Anwendung und standalone Userscript sind
11.2.25. Die Versionen müssen bei einer späteren Veröffentlichung zusammenpassen. Der Wartungsstand ersetzt
nicht den separaten frueheren Pfeilfix-Download: er aendert Wartung, Build und
Worker-Lifecycle, nicht die gesamte Analyse-/Pfeilpipeline. Ein aufgewachter
Worker allein bestaetigt keine funktionierende Pfeilanzeige.

## Codex und CI

AGENTS.md enthaelt die Arbeitsregeln. In der Codex-Umgebung `.codex/setup.sh` als
Setup und `.codex/maintenance.sh` als Wartung konfigurieren. Fuer Git-only-Wartung
steht der oben dokumentierte maintain.py-Aufruf bereit. Der manuell startbare
Workflow **Windows portable build** erzeugt ein komplettes ZIP-Artefakt inklusive
SHA256-Datei; er installiert nichts auf deinem PC. CI fuehrt zusaetzlich die neuen
Wartungstests aus. Das Vorhandensein eines Workflows bedeutet nicht, dass er bereits
erfolgreich ausgefuehrt wurde.

## Berichte, Wiederholung und Fehler

`.build/maintenance-report.json` nennt gemergte/blockierte PRs, entfernte/erhaltene
Branches, Commit, Backup- und Erweiterungspfad. Exit 0: abgeschlossen, 2: blockierte
PRs bleiben offen, 1: Fehler. Rote/nicht gestartete GitHub-Checks sind kein Pass.
Neubau erzwingen: `UPDATE_ALLIE.cmd --force-build`.
Nur lokalen Build aktualisieren: `python tools/maintain.py --deploy-only`.

Bei gesperrten Windows-Dateien Allie beenden und erneut ausfuehren; fremde Prozesse
werden nicht zwangsbeendet. Nach einem Absturz .build/maintenance.lock erst nach
Pruefung entfernen, dass kein Updater mehr laeuft. Grosse vorige Bundles bleiben
zur Sicherheit erhalten und koennen nach eigener Abnahme manuell entfernt werden.
Vorhandene fremde Desktop-EXEs und eigene Git-Hooks werden nicht blind geloescht.
