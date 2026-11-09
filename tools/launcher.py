"""Windows tray controller for the adjacent reproducible batch workflow."""
from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Thread

TITLE = "Allie21 Chess Live Studio"
DEFAULT_PORT = 8765
REQUIRED = (
    "START_HIER.bat",
    "pyproject.toml",
    "uv.lock",
    "backend/live_server.py",
)
PORTABLE_REQUIRED = (
    "app/backend/live_server.py",
    "app/viewer/index.html",
    "runtime/python.exe",
)


def is_portable_bundle(root: Path) -> bool:
    """Return whether *root* is a self-contained release directory."""
    return all((root / name).is_file() for name in PORTABLE_REQUIRED)


def find_project_root(start: Path) -> Path:
    """Find the checkout above either the source file or an onedir bundle."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if all((candidate / name).is_file() for name in REQUIRED):
            return candidate
    return start


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).parent
        if is_portable_bundle(executable_root):
            return executable_root
        return find_project_root(executable_root)
    return find_project_root(Path(__file__).parents[1])


def validate(root: Path) -> list[str]:
    if is_portable_bundle(root):
        return []
    return [name for name in REQUIRED if not (root / name).is_file()]


def configured_port() -> int:
    """Return the validated loopback port shared by launcher and server."""
    raw = os.environ.get("ALLIE_PORT", str(DEFAULT_PORT)).strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError("ALLIE_PORT muss eine ganze Zahl sein") from exc
    if not 1024 <= port <= 65535:
        raise RuntimeError("ALLIE_PORT muss zwischen 1024 und 65535 liegen")
    return port


def viewer_url(port: int | None = None) -> str:
    return f"http://127.0.0.1:{port if port is not None else configured_port()}/viewer"


def port_available(port: int) -> bool:
    """Fail closed when another local process already owns the server port."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None and os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        probe.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, TITLE, 0x10)


def create_tray_image():
    """Draw a compact Allie pawn icon without shipping another asset file."""
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), (8, 24, 38, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, 61, 61), radius=14, fill=(14, 43, 63, 255))
    draw.ellipse((20, 9, 44, 33), fill=(82, 211, 173, 255))
    draw.rounded_rectangle((24, 27, 40, 47), radius=6, fill=(238, 249, 255, 255))
    draw.polygon(((18, 51), (46, 51), (52, 58), (12, 58)), fill=(238, 249, 255, 255))
    return image


class TrayApp:
    def __init__(self, root: Path, process_factory=None, command_runner=None,
                 browser_open=None):
        self.root = root
        self.port = configured_port()
        self.process_factory = process_factory or subprocess.Popen
        self.command_runner = command_runner or subprocess.run
        self.browser_open = browser_open or webbrowser.open
        self.process = None

    def start(self):
        if not port_available(self.port):
            raise RuntimeError(
                f"Port 127.0.0.1:{self.port} ist bereits belegt; "
                "Allie startet aus Sicherheitsgründen nicht."
            )
        if is_portable_bundle(self.root):
            app_root = self.root / "app"
            runtime_python = self.root / "runtime" / "python.exe"
            environment = os.environ.copy()
            environment["ALLIE_PROJECT_ROOT"] = str(app_root)
            environment["PYTHONPATH"] = str(app_root / "backend")
            environment["ALLIE_PORT"] = str(self.port)
            self.process = self.process_factory(
                [str(runtime_python), str(app_root / "backend" / "live_server.py")],
                cwd=app_root,
                env=environment,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return self.process
        environment = os.environ.copy()
        environment["ALLIE_PORT"] = str(self.port)
        self.process = self.process_factory(
            ["cmd.exe", "/d", "/c", str(self.root / "START_HIER.bat")],
            cwd=self.root,
            env=environment,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return self.process

    def open_viewer(self, *_args) -> None:
        self.browser_open(viewer_url(self.port))

    def stop_server(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return
        result = self.command_runner(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        if result.returncode and process.poll() is None:
            process.terminate()

    def quit(self, icon, *_args) -> None:
        self.stop_server()
        icon.stop()

    def watch(self, icon) -> None:
        if self.process is not None:
            self.process.wait()
        icon.stop()

    def run(self) -> int:
        import pystray

        self.start()
        menu = pystray.Menu(
            pystray.MenuItem("Allie öffnen", self.open_viewer, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Allie beenden", self.quit),
        )
        icon = pystray.Icon("allie21", create_tray_image(), "Allie 2.1 läuft", menu)

        def setup(ready_icon):
            ready_icon.visible = True
            Thread(target=self.watch, args=(ready_icon,), daemon=True).start()

        try:
            icon.run(setup=setup)
        finally:
            self.stop_server()
        return self.process.returncode or 0


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
    app = None
    try:
        app = TrayApp(root)
        return app.run()
    except (ImportError, OSError, RuntimeError) as exc:
        if app is not None:
            app.stop_server()
        error(f"Der Start ist fehlgeschlagen:\n\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
