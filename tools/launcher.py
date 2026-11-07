"""Tiny Windows launcher for the adjacent reproducible batch workflow."""
from __future__ import annotations

import ctypes
from pathlib import Path
import subprocess
import sys


TITLE = "Allie21 Chess Live Studio"
REQUIRED = (
    "START_HIER.bat",
    "pyproject.toml",
    "uv.lock",
    "backend/live_server.py",
)


def project_root() -> Path:
    executable = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
    return executable.resolve().parent if getattr(sys, "frozen", False) else executable.resolve().parents[1]


def validate(root: Path) -> list[str]:
    return [name for name in REQUIRED if not (root / name).is_file()]


def error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, TITLE, 0x10)


def main() -> int:
    root = project_root()
    missing = validate(root)
    if missing:
        if "--check" not in sys.argv:
            error("Diese Dateien fehlen neben der EXE:\n\n" + "\n".join(missing))
        return 2
    if "--check" in sys.argv:
        if sys.stdout is not None:
            print(f"{TITLE}: OK ({root})")
        return 0
    try:
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", str(root / "START_HIER.bat")],
            cwd=root,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError as exc:
        error(f"Der Start ist fehlgeschlagen:\n\n{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
