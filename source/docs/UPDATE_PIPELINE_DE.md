# Main, Codex und Windows aktualisieren

Der öffentliche `main`-Quellstand trägt App/Userscript **11.2.26** und Extension **11.2.26.0**. Die folgenden Befehle aktualisieren die lokale Windows-Installation; sie werden durch einen Cloud-Prüflauf nicht ausgeführt. Native Browser- und Windows-Abnahmen müssen weiterhin am Benutzer-PC geprüft werden.

## Einmalig auf deinem Windows-PC

Allie im Infobereich beenden. Im echten Git-Checkout, nicht in einer ZIP-Kopie:

```powershell
git status --porcelain=v1 -uall
git branch --show-current
git fetch --no-tags origin main
# Nur bei sauberem main und bestaetigtem Fast-Forward:
git merge --ff-only origin/main
.\UPDATE_ALLIE.cmd
```

Voraussetzungen: Git, angemeldete GitHub CLI (`gh auth login`), Python 3.10+ oder
uv, sowie uv/uvx im PATH fuer den bestehenden Python-3.12-Build. Der Build kann
Netzwerk fuer gesperrte Pakete und Stockfish brauchen. Modellgewichte werden dabei
nicht geladen. Git/gh verwalten die Anmeldung; keine Tokens im Repository.

Der erste Aufruf installiert repository-lokale Git-Hooks, sofern keine eigenen
Hooks vorhanden sind. Danach pruefen die Hooks nur die Struktur nach Merge/Rewrite;
sie starten keine Updates, Deployments oder GitHub-Aenderungen.
Ein `git pull` ohne Aenderungen startet keinen Git-Hook: fuer wirklich jeden
Abgleich UPDATE_ALLIE.cmd benutzen. Fremde Branches werden nicht automatisch
ausgecheckt. Lokale Aenderungen werden nicht geloescht oder automatisch gestasht.

## Edge erstmalig umstellen

Nach einer gesonderten lokalen Installation unter `edge://extensions` die neue Version **11.2.26** neu laden. Fuer einen
festen Installationspfad die entpackte Erweiterung aus
`%LOCALAPPDATA%\Allie21\EdgeOverlay` laden; dieser Ordner entsteht beim erfolgreichen
lokalen Update. Der echte Checkout-Ordner `source/app/browser/` funktioniert ebenfalls.
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
2. Liest alle Remote-Branches und alle main-PRs. Der Bericht kennzeichnet bereits
   integrierte Branches, neuere Fassungen und divergierte Fixes zum Kombinieren.
3. Prueft offene main-PRs auf vorhandene Checks, Konflikte und Reviews. Es wird
   kein PR automatisch aktualisiert, gemergt oder geschlossen.
4. Aktualisiert ein sauberes main ausschliesslich per Fast-Forward.
   Vollstaendig gemergte Branches werden nur als Loeschkandidaten berichtet;
   keine lokalen oder entfernten Branches werden automatisch geloescht.
5. Startet fuer das Deployment einen frischen Python-Prozess, damit neue Scripts
   nach dem Pull verwendet werden. Inhalts-Hashes entscheiden ueber einen Neubau.
   Ein unveraenderter bestehender Build wird dennoch erneut geprueft.
6. Baut bei Bedarf in einem getrennten Verzeichnis. Gesperrte Dependencies,
   Stockfish-Hash, Runtime-Inventar, SHA256SUMS und HTTP-Serverstart werden geprueft.
   Erst dann wird der komplette portable Ordner ersetzt. Der vorige Stand bleibt
   im Bericht genannten lokalen Zustandsordner unter `generated/protected/maintenance` erhalten; eine fehlgeschlagene Umbenennung
   stellt den alten Ordner wieder her.
7. Aktualisiert die Desktop-Verknuepfung zur EXE im kompletten release-Ordner und
   den stabilen Edge-Ordner einschliesslich Dateiloeschungen. Eine einzelne EXE
   auf dem Desktop waere bei diesem onedir-Aufbau unvollstaendig.

## Service Worker: Inaktiv

Das ist der normale Manifest-V3-Ruhezustand. Es gibt keinen Dauer-Keepalive.
Ein Klick auf das Allie-Symbol oeffnet Verbindung/Updates. **Worker aufwecken und
 testen** prueft die Erweiterung; **Server-Verbindung testen** prueft separat
localhost. Angezeigt wird die wirklich geladene Erweiterungsversion.

Die Erweiterungsshell ist 11.2.26.0; Anwendung und standalone Userscript sind
11.2.26. Dieser Stand enthält auch den Remis-Pfeilfix, adaptive Eröffnungen und
Ragebait. Nach dem Update die geladene Version in Edge und die Pfeile an einer
bestätigten aktuellen Brettstellung prüfen. Ein aufgewachter Worker allein
bestaetigt keine funktionierende Pfeilanzeige.

## Codex und CI

AGENTS.md enthaelt die Arbeitsregeln. In der Codex-Umgebung `source/automation/agents/setup.sh` als
Setup und `source/automation/agents/maintenance.sh` als Wartung konfigurieren. Fuer Git-only-Wartung
steht der oben dokumentierte maintain.py-Aufruf bereit. Die Optionen
--process-prs und --cleanup erzeugen ausschliesslich Berichte. Der manuell startbare
Workflow **Windows portable build** erzeugt ein komplettes ZIP-Artefakt inklusive
SHA256-Datei; er installiert nichts auf deinem PC. CI fuehrt zusaetzlich die neuen
Wartungstests aus. Das Vorhandensein eines Workflows bedeutet nicht, dass er bereits
erfolgreich ausgefuehrt wurde.

## Berichte, Wiederholung und Fehler

`generated/protected/maintenance/maintenance-report.json` nennt gemergte/blockierte PRs, entfernte/erhaltene
Branches, Commit, Backup- und Erweiterungspfad. Exit 0: abgeschlossen, 2: blockierte
PRs bleiben offen, 1: Fehler. Review- und Cleanup-Kandidaten sind keine Freigabe. Rote/nicht gestartete GitHub-Checks sind kein Pass.
Neubau erzwingen: `UPDATE_ALLIE.cmd --force-build`.
Nur lokalen Build aktualisieren: `python source/automation/maintain.py --deploy-only`.

Bei gesperrten Windows-Dateien Allie beenden und erneut ausfuehren; fremde Prozesse
werden nicht zwangsbeendet. Nach einem Absturz `generated/protected/maintenance/maintenance.lock` erst nach
Pruefung entfernen, dass kein Updater mehr laeuft. Grosse vorige Bundles bleiben
zur Sicherheit erhalten und koennen nach eigener Abnahme manuell entfernt werden.
Vorhandene fremde Desktop-EXEs und eigene Git-Hooks werden nicht blind geloescht.
