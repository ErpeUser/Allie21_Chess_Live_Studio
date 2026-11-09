# Live Stability Milestone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Den ersten sicherheits- und laufzeitkritischen Stabilitätsmeilenstein für Allie21 liefern: per-Run-Capability, Backpressure, nicht blockierende Frame-Verarbeitung und ein strikt validierter Overlay-Vertrag.

**Architecture:** FastAPI bleibt die lokale Grenze. Ein zufälliges Capability-Token wird beim Prozessstart erzeugt und von Viewer/Browser-Clients in geschützten Requests mitgeführt. Analyse und Frame-Erkennung werden durch Semaphoren/Threadpool begrenzt; externe Overlay-Payloads gehen ausschließlich durch verschachtelte Pydantic-Modelle.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Starlette threadpool, Pillow, pytest/unittest, Vanilla JavaScript.

**Spec:** `C:/Users/User/.codex/attachments/2d801a4e-e0eb-4459-b3be-67e9ee5ff601/pasted-text.txt` (Abschnitte 2.1–2.4, 3.1 und Abnahmekriterien).

## Global Constraints

- Mutierende und analyseauslösende lokale API-Aufrufe benötigen ein Capability-Token aus genau einem laufenden Serverprozess.
- `/health` bleibt ohne Token erreichbar; der Token selbst wird nicht über `/health` veröffentlicht.
- Überlast wird mit HTTP 429 beantwortet; keine unbeschränkte Queue.
- `/api/frame` darf die Uvicorn-Eventloop nicht durch Vision/Pillow blockieren.
- Externe Overlay-Payloads verwenden `extra="forbid"`, endliche Koordinaten und begrenzte Listenlängen.
- Die Allie-first-Reihenfolge bleibt unverändert; diese Änderung darf keine Engine-Rangfolge umsortieren.

## Review Focus

- Fehlendes, falsches und abgelaufenes Token: Request wird mit 401 abgelehnt.
- Gleichzeitige Analyse-/Frame-Aufrufe: Überlast wird mit 429 abgelehnt und blockiert nicht den Server.
- Ungültige Geometrie (NaN, Infinity, falsche Form, unbekannte Felder): Validierung schlägt vor dem nativen Overlay fehl.
- Veraltete Browser-Instanz: `instance_id` und `schema_version` sind im Health-/Capability-Vertrag sichtbar.
- JPEG mit Pillow-Decompression-Bomb-Metadaten: kontrollierte 413-Antwort statt Prozessfehler.

### Task 1: Capability- und Instanzgrenze

**Files:**
- Create: `backend/security.py`
- Modify: `backend/live_server.py`
- Modify: `viewer/index.html`
- Modify: `browser/allie21_overlay.user.js`
- Test: `tests/test_http_offline.py`

**Interfaces:**
- `security.CAPABILITY_TOKEN: str`, `security.INSTANCE_ID: str`, `security.API_VERSION: int`.
- `security.require_capability(request) -> None` raises `HTTPException(401)`.
- `GET /api/capability` returns `{token, instance_id, api_version, schema_version}` for an allowed overlay origin.

- [ ] Failing tests for missing/wrong token, capability metadata, and client header propagation.
- [ ] Run the focused HTTP tests and observe the expected failures.
- [ ] Implement token generation, constant-time comparison, protected-path middleware, capability endpoint, and viewer/userscript token propagation.
- [ ] Re-run focused tests to green.

### Task 2: Rate-Limits und Backpressure

**Files:**
- Modify: `backend/security.py`
- Modify: `backend/live_server.py`
- Test: `tests/test_http_offline.py`

**Interfaces:**
- `RequestRateLimiter.allow(key: str, limit: int, window_seconds: float) -> bool`.
- Global non-blocking semaphores limit `/analyze` and `/api/frame` to one active job each.

- [ ] Failing tests for 429 on a second concurrent analysis/frame request and per-session browser-position rate limiting.
- [ ] Run focused tests and observe failure.
- [ ] Implement bounded limiter and `Retry-After` response behavior.
- [ ] Re-run focused tests to green.

### Task 3: Nicht blockierender Frame-Pfad und Pillow-Grenze

**Files:**
- Modify: `backend/live_server.py`
- Modify: `backend/live_session.py`
- Test: `tests/test_http_offline.py`
- Test: `tests/test_offline.py`

**Interfaces:**
- `/api/frame` calls `SESSION.submit_frame` via `starlette.concurrency.run_in_threadpool`.
- Pillow raises `DecompressionBombWarning` as an error and maps it to HTTP 413.

- [ ] Failing test proving `run_in_threadpool` is used and decompression-bomb warnings are controlled.
- [ ] Run tests and observe failure.
- [ ] Implement threadpool dispatch, warning handling, and explicit `Image.MAX_IMAGE_PIXELS`.
- [ ] Re-run focused tests to green.

### Task 4: Strikter Overlay-/Result-Vertrag

**Files:**
- Create: `backend/contracts.py`
- Modify: `backend/live_server.py`
- Test: `tests/test_http_offline.py`

**Interfaces:**
- `Rect`, `Viewport`, `Geometry`, `Arrow`, `VisualUpdateRequest` are Pydantic models with `extra="forbid"`.
- Coordinates must be finite; `arrows` is capped at 8 and messages at 8 × 240 characters.

- [ ] Failing tests for unknown geometry/arrow fields, non-finite coordinates, and valid payload acceptance.
- [ ] Run tests and observe failure.
- [ ] Implement nested models and use them in `/api/overlay/update`.
- [ ] Re-run the full Python suite and verify all existing overlay behavior remains green.

