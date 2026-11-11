# Private- und Share-Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Einen versionierten privaten/Share-Modus mit synchronisiertem Viewer, Edge-Erweiterung, Native-HUD und verifizierbarem Windows-Startpfad ausliefern.

**Architecture:** Das lokale FastAPI-Backend hält den bestätigten Modus mit monotoner Version. Native `private`- und `share`-Renderer teilen denselben Visual-Payload; der Browser-HUD rendert ausschließlich im Share-Modus. Der Tray-Launcher startet eine eigene Instanz oder verwendet einen kompatiblen bestehenden Allie-Dienst.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, ctypes Win32, Manifest V3, vanilla JavaScript, PyInstaller Onedir, pystray.

**Spec:** `docs/superpowers/specs/2026-11-11-overlay-private-share-design.md`

## Global Constraints

- Private ist Standard und fail-closed bei fehlender Capture-Exclusion.
- Share ist explizit und deaktiviert Capture-Exclusion.
- Kein Browser-HUD im privaten Modus.
- Keine automatische Zugausführung.
- Keine fremden Prozesse beenden.
- Bestehende Allie-/Stockfish-/Lichess-/Chess.com-Pipeline erhalten.

## Review Focus

- Versionierter Moduskonflikt: jüngere bestätigte Version gewinnt; veraltete Writes werden sichtbar abgewiesen.
- Abgelaufener Lease: unveränderte Stellung beansprucht ihn erneut und behauptet keinen Erfolg bei Fehlclaim.
- Fremder Dienst auf 8765: Launcher verweist auf Diagnose und killt nichts.
- Share-Quelle `window`: Status behauptet Unterstützung nur bei tatsächlich enthaltenem Browser-HUD.
- Native Affinity-Fehler: privater HUD bleibt verborgen und meldet „Privatmodus nicht verifiziert“.

### Task 1: Backend-Modus und Native-Renderer

**Files:** `backend/native_overlay.py`, `backend/live_server.py`, `backend/contracts.py`, `backend/overlay_lease.py`, `tests/test_native_overlay*.py`, `tests/test_http*.py`

- [ ] `private`/`share` explizit modellieren und Statusdiagnose ergänzen.
- [ ] Capture-Exclusion vor sichtbarem Private-Frame verifizieren; Share sichtbar ohne Exclusion.
- [ ] Modusquelle, Versionskonflikte und Lease-Erneuerung testen.

### Task 2: Viewer und Edge-Synchronisierung

**Files:** `browser/allie21_overlay.user.js`, `browser/background.js`, `browser/connection.js`, `browser/options.*`, `viewer/index.html`, `tests/*.js`

- [ ] Gemeinsamen Modusstatus lesen/schreiben und nach Neustart wiederherstellen.
- [ ] Share-Schalter und eindeutige Statusmeldungen ergänzen.
- [ ] Browser-HUD ausschließlich im Share-Modus aktivieren; Quellenstatus korrekt kennzeichnen.

### Task 3: Launcher, Build und Diagnose

**Files:** `tools/launcher.py`, `tools/build_exe.ps1`, `tools/desktop_shortcut.ps1`, `tools/release_smoke.py`, `.github/workflows/windows-release.yml`, `tests/test_release*`, `docs/*`

- [ ] Eigenen Dienst erkennen/wiederverwenden, fremde Prozesse schützen und Tray-Open/Close bereitstellen.
- [ ] Runtime, Backend, Assets und Edge-Ordner in den Onedir-Build aufnehmen.
- [ ] Health-/Readiness-/Shutdown-Smoke und Versionsnachweis aktualisieren.

### Task 4: Vollständige Verifikation und Push

- [ ] Python-, Node-, Ruff-, Mypy-, Versions- und Diff-Checks ausführen.
- [ ] Windows-only Tests als unexecuted ausweisen, falls keine Windows-Umgebung verfügbar ist.
- [ ] Geänderte Blobs in den bestehenden `main`-Tree schreiben, Commit erstellen, `main` mit Expected-SHA aktualisieren und neuen Head rücklesen.
