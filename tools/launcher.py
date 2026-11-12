"""Windows tray controller for the adjacent reproducible batch workflow."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Thread
from time import sleep
from urllib.error import URLError
from urllib.request import Request, urlopen


def resolve_backend_path(
    script_path: Path,
    *,
    frozen: bool,
    executable: Path,
) -> Path:
    """Locate backend modules in both a source checkout and an onedir bundle."""
    if frozen:
        return executable.resolve().parent / "app" / "backend"
    return script_path.resolve().parents[1] / "backend"


BACKEND = resolve_backend_path(
    Path(__file__),
    frozen=bool(getattr(sys, "frozen", False)),
    executable=Path(sys.executable),
)
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def parse_port(value: object = "8765") -> int:
    """Validate the loopback port without importing the heavyweight backend config."""
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("ALLIE_PORT muss eine ganze Zahl sein") from exc
    if not 1024 <= port <= 65535:
        raise ValueError("ALLIE_PORT muss zwischen 1024 und 65535 liegen")
    return port

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
    "app/release-version.json",
    "runtime/python.exe",
)


class SingleInstanceGuard:
    """Use a Windows named mutex to close the launcher race window."""

    ERROR_ALREADY_EXISTS = 183
    NAME = r'Global\Allie21ChessLiveStudioLauncher'

    def __init__(self) -> None:
        self._handle = None

    def acquire(self) -> bool:
        if os.name != 'nt':
            return True
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, self.NAME)
        if not handle:
            error_code = ctypes.get_last_error()
            raise OSError(error_code, 'CreateMutexW fehlgeschlagen')
        if ctypes.get_last_error() == self.ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None or os.name != 'nt':
            return
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(self._handle)
        self._handle = None


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
        return parse_port(raw)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc


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


def health_snapshot(port: int, *, timeout: float = 0.6) -> dict[str, object] | None:
    """Read the loopback health endpoint without importing the backend.

    The launcher uses this probe to distinguish an already running Allie
    service from an unrelated process that happens to own the configured port.
    A failed or malformed probe is treated as unknown and never as permission
    to terminate the process.
    """
    try:
        request = Request(
            f"http://127.0.0.1:{port}/health",
            headers={"Accept": "application/json", "X-Allie-Launcher": "1"},
        )
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            raw = response.read(64 * 1024)
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def is_allie_service(payload: object) -> bool:
    """Return true only for the signed shape emitted by this Allie server."""
    if not isinstance(payload, dict):
        return False
    return (payload.get("alive") is True
            and isinstance(payload.get("api_version"), int)
            and payload.get("api_version") == 2
            and payload.get("schema_version") == 1
            and isinstance(payload.get("instance_id"), str)
            and len(payload["instance_id"]) >= 16
            and isinstance(payload.get("overlay"), dict))


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
        self.owns_process = False
        self.reused_existing = False

    def start(self):
        if self.process is not None and self.process.poll() is None:
            return self.process
        if not port_available(self.port):
            # Reuse a healthy Allie instance on 8765 (for example after a
            # tray restart).  An unrelated listener remains a hard failure.
            for _ in range(5):
                if is_allie_service(health_snapshot(self.port)):
                    self.reused_existing = True
                    self.owns_process = False
                    self.process = None
                    return None
                # A just-started Allie process may bind before Uvicorn has
                # published /health. Give that own instance a short grace
                # period; an unrelated listener still fails closed.
                sleep(0.2)
            raise RuntimeError(
                f"Port 127.0.0.1:{self.port} ist bereits von einem fremden "
                "Prozess belegt; dieser Prozess wird nicht beendet."
            )
        self.reused_existing = False
        self.owns_process = True
        hidden = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if is_portable_bundle(self.root):
            app_root = self.root / "app"
            runtime_python = self.root / "runtime" / "python.exe"
            environment = os.environ.copy()
            environment["ALLIE_PROJECT_ROOT"] = str(app_root)
            environment["PYTHONPATH"] = str(app_root / "backend")
            environment["ALLIE_PORT"] = str(self.port)
            environment["ALLIE_NO_BROWSER"] = "1"
            self.process = self.process_factory(
                [str(runtime_python), str(app_root / "backend" / "live_server.py")],
                cwd=app_root,
                env=environment,
                creationflags=hidden,
            )
            return self.process
        environment = os.environ.copy()
        environment["ALLIE_PORT"] = str(self.port)
        environment["ALLIE_NO_BROWSER"] = "1"
        self.process = self.process_factory(
            ["cmd.exe", "/d", "/c", str(self.root / "START_HIER.bat")],
            cwd=self.root,
            env=environment,
            creationflags=hidden,
        )
        return self.process

    def open_viewer(self, *_args) -> None:
        self.browser_open(viewer_url(self.port))

    def stop_server(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return
        if self.reused_existing and not self.owns_process:
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
        if self.process is not None and self.owns_process:
            self.process.wait()
            icon.stop()
            return
        if self.reused_existing:
            # A tray restart may attach to a healthy server that we do not
            # own; still close the stale tray icon when that service vanishes.
            while self.reused_existing and is_allie_service(health_snapshot(self.port)):
                sleep(1.0)
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
        return (self.process.returncode if self.process is not None and self.process.returncode is not None else 0)


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
    guard = SingleInstanceGuard()
    try:
        if not guard.acquire():
            error('Allie läuft bereits. Das vorhandene Fenster/Tray-Symbol wird weiterverwendet.')
            return 3
        app = TrayApp(root)
        return app.run()
    except (ImportError, OSError, RuntimeError) as exc:
        if 'app' in locals() and app is not None:
            app.stop_server()
        error(f"Der Start ist fehlgeschlagen:\n\n{exc}")
        return 1
    finally:
        guard.release()


if __name__ == "__main__":
    raise SystemExit(main())
