# Windows Tray Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the EXE alive as a Windows tray controller with open and clean shutdown actions.

**Architecture:** A testable `TrayApp` owns the existing BAT child process. The UI adapter uses pystray; process control, viewer opening, and icon drawing remain small separate functions in `tools/launcher.py`.

**Tech Stack:** Python 3.12, pystray 0.19.5, Pillow 13.0.0, PyInstaller 6.22.3, Windows taskkill

**Spec:** `docs/superpowers/specs/2026-11-08-windows-tray-controller-design.md`

## Global Constraints

- No backend runtime dependency is added.
- Existing `--check` mode remains headless and does not import pystray.
- Shutdown targets only the starter's child PID tree.
- The EXE remains a reproducible one-file windowed launcher.

## Review Focus

- Closing from the menu must terminate descendants, not just the BAT shell.
- A naturally exited server must remove the tray icon.
- `--check` must still work without the GUI build dependencies installed.
- A failed start must display the existing error dialog and not leave a ghost icon.
- Double-click/default menu action must open only `http://127.0.0.1:8765/viewer`.

---

### Task 1: Tray-owned launcher

**Files:**
- Modify: `tools/launcher.py`
- Modify: `tools/build_exe.ps1`
- Modify: `tests/test_offline.py`
- Modify: `README_DE.md`
- Modify: `QUELLEN_LIZENZEN.md`
- Modify: `CHANGELOG.md`
- Modify: `VERSIONEN.md`

**Interfaces:**
- Produces: `TrayApp.start()`, `TrayApp.open_viewer()`, `TrayApp.quit(icon)`, and `create_tray_image()`

- [ ] Write failing tests for process-tree shutdown, viewer opening, icon creation, and preserved check mode.
- [ ] Run focused tests and confirm missing tray behavior fails.
- [ ] Implement the minimal tray controller and lazy pystray import.
- [ ] Pin pystray/Pillow in the isolated PyInstaller build command.
- [ ] Build the EXE and run `--check`.
- [ ] Start the EXE, visually verify the tray icon, invoke its close action, and confirm port 8765 closes.
- [ ] Run the complete short suite and record the final EXE hash.
