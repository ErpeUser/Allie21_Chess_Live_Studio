# Allie 2.1 Overlay Release Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den vorhandenen Overlay-Stand bis zu einem lokal verifizierten, releasebereiten Zustand bringen.

**Architecture:** Pfeilpositionierung bleibt an die gemessene Brettfläche gekoppelt; Eröffnungszüge werden aus den vorhandenen TSV-Daten über die tatsächliche Stellung und legale Züge ausgewählt, danach bleibt der bestehende Allie-Fallback unverändert. Manifest, Service Worker und Capture-Schutz werden konsistent geprüft und nur minimal angepasst.

**Tech Stack:** Python 3.12, `python-chess`, FastAPI/Uvicorn, Browser-Userscript/Manifest V3, vorhandene Node-/JS-Tests, Pytest.

**Spec:** Benutzerauftrag in `C:\Users\User\.codex\attachments\82449e7b-7c69-4869-8cdc-903ca8081bbd\pasted-text.txt` und Ziel-Funktion in `C:\Users\User\.codex\attachments\97b616f7-3263-4e17-a220-b15c71bc86ca\pasted-text.txt`.

## Global Constraints

- Keine Änderung an Allie-Modellgewichten, kein Training, keine neue Engine und keine große Abhängigkeit.
- Echte Partiehistorie, Uhren, Spielmodi und Verhalten außerhalb der Buchfortsetzungen erhalten.
- Eröffnungszüge müssen legal sein; Transpositionen dürfen nur über die reale Stellung zusammengeführt werden.
- Capture-Ausschluss darf nur zur Diagnose deaktiviert werden und muss vor finalen Tests aktiv sein.
- Kein erfundenes Repository, kein erfundener Owner, keine Credentials und kein behaupteter Release ohne Verifikation.

## Tasks

- [ ] Read-only Audit und Baseline dokumentieren.
- [ ] Pfeil-DOM/SVG, Koordinaten, Orientierung und Lifecycle analysieren.
- [ ] Eröffnungsdaten, Legalität, Transpositionen, Gewichte und Fallback analysieren.
- [ ] Manifest, Service Worker, Edge-Reload/Cache und Capture-Konfiguration analysieren.
- [ ] Minimalen Fix integrieren und Regressionstests ergänzen.
- [ ] Unabhängige QA sowie Tests/Build/Smoke-Checks durchführen.
- [ ] Capture-Schutz final aktivieren und reproduzierbare README/Release-Notiz ergänzen.
- [ ] Commit/Tag/privaten Release nur bei eindeutigem Remote und erfolgreicher Verifikation durchführen.
