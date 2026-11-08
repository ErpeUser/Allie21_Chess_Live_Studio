# Windows-Tray-Steuerung

## Ziel

Solange Allie über die Windows-EXE läuft, erscheint ein Symbol im Infobereich. Ein Doppelklick beziehungsweise „Allie öffnen“ öffnet den lokalen Viewer. „Allie beenden“ beendet ausschließlich den von dieser EXE gestarteten Allie-Prozessbaum und entfernt das Symbol.

## Ansatz

Der vorhandene kleine PyInstaller-Starter bleibt während der Laufzeit aktiv und verwaltet die vorhandene BAT-Kette als Kindprozess. `pystray==0.19.5` liefert die native Windows-Infobereich-Integration; Pillow zeichnet ein kleines Allie-Schachsymbol zur Laufzeit. Beide Komponenten werden nur in die EXE eingebaut und nicht als Backend-Laufzeitabhängigkeit ergänzt.

## Grenzen

- Die bestehende Konsole bleibt für Installation und verständliche Startfehler sichtbar.
- Das Tray-Symbol führt keine Schachzüge aus und verändert keine Browserseite.
- Beenden trifft nur den Prozessbaum des vom Starter erzeugten BAT-Prozesses.
- Schließt der BAT-/Serverprozess anderweitig, verschwindet das Symbol automatisch.

## Verworfene Ansätze

- Eigene `Shell_NotifyIcon`-Implementierung: mehr Windows-spezifischer Wartungscode.
- Tray-Logik im Backend: würde BAT/uv/Installationsfehler nicht vollständig besitzen und sauber schließen können.
