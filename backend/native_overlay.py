"""Small native Windows overlay used for privacy-safe local annotations.

The module deliberately has no third-party dependency.  On Windows it creates a
top-level, layered, click-through popup and verifies
``WDA_EXCLUDEFROMCAPTURE`` before the window can become visible.  On other
platforms (and whenever that verification fails) the controller stays hidden.

The public controller is intentionally usable from worker threads.  Rendering
itself is kept on the window thread, while :meth:`NativeOverlayController.update`
only validates and publishes an immutable snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import math
import os
from threading import Event, RLock, Thread
from typing import Iterable, Mapping, Sequence


# Window styles and messages.  Keeping the values local makes the module easy
# to inspect and keeps tests independent of a Windows SDK installation.
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = wintypes.HWND(-1)
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_ERASEBKGND = 0x0014
WM_NCHITTEST = 0x0084
WM_APP = 0x8000
WM_APP_RENDER = WM_APP + 21
HTTRANSPARENT = -1
COLOR_KEY = 0x00FF00FF  # magenta, transparent through the color-keyed layer
TRANSPARENT = 1
PS_SOLID = 0
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def is_overlay_update_newer(
    session_id: str,
    generation: int,
    render_revision: int,
    last_by_session: Mapping[str, tuple[int, int]],
) -> bool:
    """Return whether a visual update advances its session's render cursor.

    The pair is deliberately compared lexicographically: a newer generation
    supersedes every revision from an older generation, while duplicate or
    delayed frames in the same generation are rejected.  Session identity is
    part of the cursor map so a fresh session starts at any non-negative pair.
    """

    if not isinstance(session_id, str) or not session_id:
        return False
    try:
        cursor = (int(generation), int(render_revision))
    except (TypeError, ValueError, OverflowError):
        return False
    if min(cursor) < 0:
        return False
    previous = last_by_session.get(session_id)
    return previous is None or cursor > previous

# ``ctypes.wintypes`` does not expose every Win32 handle alias on all Python
# builds.  HANDLE has the same ABI width and keeps module import portable.
HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", _RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", wintypes.BYTE * 32),
    ]


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
    ]


@dataclass(frozen=True)
class OverlayArrow:
    """One arrow in client coordinates (pixels)."""

    start: tuple[float, float]
    end: tuple[float, float]
    color: str = "#16c784"
    width: int = 5


@dataclass(frozen=True)
class OverlaySnapshot:
    arrows: tuple[OverlayArrow, ...] = ()
    message: str = ""
    bounds: tuple[int, int, int, int] | None = None


def _rgb(value: str) -> int:
    """Convert a CSS ``#rrggbb`` colour to the Win32 COLORREF layout."""

    if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
        raise ValueError("overlay color must be #rrggbb")
    try:
        red, green, blue = (int(value[i : i + 2], 16) for i in (1, 3, 5))
    except ValueError as exc:
        raise ValueError("overlay color must be #rrggbb") from exc
    return red | (green << 8) | (blue << 16)


def _number_pair(value: object) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise ValueError("arrow points must contain two numbers")
    point = (float(value[0]), float(value[1]))
    if not all(math.isfinite(item) for item in point):
        raise ValueError("arrow points must be finite")
    return point


def normalize_arrows(arrows: Iterable[OverlayArrow | Mapping[str, object]]) -> tuple[OverlayArrow, ...]:
    """Validate an external arrow payload before it reaches the renderer."""

    normalized: list[OverlayArrow] = []
    for raw in arrows:
        if isinstance(raw, OverlayArrow):
            arrow = raw
        elif isinstance(raw, Mapping):
            start = raw.get("start", raw.get("from"))
            end = raw.get("end", raw.get("to"))
            arrow = OverlayArrow(
                _number_pair(start),
                _number_pair(end),
                str(raw.get("color", "#16c784")),
                int(raw.get("width", 5)),
            )
        else:
            raise ValueError("invalid overlay arrow")
        if not all(math.isfinite(x) for x in (*arrow.start, *arrow.end)):
            raise ValueError("arrow points must be finite")
        _rgb(arrow.color)
        if not 1 <= int(arrow.width) <= 64:
            raise ValueError("arrow width out of range")
        normalized.append(
            OverlayArrow(arrow.start, arrow.end, arrow.color, int(arrow.width))
        )
    return tuple(normalized[:32])


class _Win32:
    """Late-bound Win32 functions; importing this module remains cross-platform."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("native overlay requires Windows")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
        self._set_dpi_awareness()
        self._configure()

    def _set_dpi_awareness(self) -> None:
        """Make screen coordinates physical and stable across mixed-DPI monitors."""
        try:
            set_context = self.user32.SetProcessDpiAwarenessContext
            set_context.argtypes = (ctypes.c_void_p,)
            set_context.restype = wintypes.BOOL
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4.
            if set_context(ctypes.c_void_p(-4)):
                return
        except (AttributeError, OSError, OverflowError):
            pass
        try:
            shcore = ctypes.WinDLL("shcore", use_last_error=True)
            set_awareness = shcore.SetProcessDpiAwareness
            set_awareness.argtypes = (ctypes.c_int,)
            set_awareness.restype = ctypes.c_long
            if set_awareness(2) == 0:  # PROCESS_PER_MONITOR_DPI_AWARE
                return
        except (AttributeError, OSError):
            pass
        try:
            set_aware = self.user32.SetProcessDPIAware
            set_aware.argtypes = ()
            set_aware.restype = wintypes.BOOL
            set_aware()
        except (AttributeError, OSError):
            pass

    def _configure(self) -> None:
        self.user32.CreateWindowExW.argtypes = (
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
        )
        self.user32.CreateWindowExW.restype = wintypes.HWND
        self.user32.RegisterClassExW.restype = wintypes.ATOM
        self.user32.DefWindowProcW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self.user32.DefWindowProcW.restype = ctypes.c_ssize_t
        self.user32.SetWindowDisplayAffinity.argtypes = (wintypes.HWND, wintypes.DWORD)
        self.user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
        self.user32.GetWindowDisplayAffinity.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        self.user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
        self.user32.GetMessageW.restype = wintypes.BOOL
        self.user32.FillRect.argtypes = (wintypes.HDC, ctypes.POINTER(_RECT), wintypes.HBRUSH)
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self.gdi32.CreatePen.restype = wintypes.HGDIOBJ
        self.gdi32.CreateSolidBrush.restype = wintypes.HGDIOBJ
        self.gdi32.CreateFontW.restype = wintypes.HGDIOBJ
        self.gdi32.DeleteObject.argtypes = (wintypes.HGDIOBJ,)
        self.gdi32.SelectObject.argtypes = (wintypes.HDC, wintypes.HGDIOBJ)

    def create_window(self, controller: "NativeOverlayController") -> int:
        callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
        callback_type = callback_type(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        controller._wndproc = callback_type(controller._window_proc)
        instance = self.kernel32.GetModuleHandleW(None)
        klass = _WNDCLASSEXW(
            ctypes.sizeof(_WNDCLASSEXW),
            0,
            ctypes.cast(controller._wndproc, ctypes.c_void_p),
            0,
            0,
            instance,
            None,
            self.user32.LoadCursorW(None, ctypes.c_void_p(32512)),
            None,
            None,
            controller._class_name,
            None,
        )
        atom = self.user32.RegisterClassExW(ctypes.byref(klass))
        if not atom and ctypes.get_last_error() != 1410:  # ERROR_CLASS_ALREADY_EXISTS
            raise ctypes.WinError(ctypes.get_last_error())
        hwnd = self.user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            controller._class_name,
            controller.title,
            WS_POPUP,
            0,
            0,
            controller.width,
            controller.height,
            None,
            None,
            instance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.user32.SetLayeredWindowAttributes(hwnd, COLOR_KEY, 0, LWA_COLORKEY):
            self.user32.DestroyWindow(hwnd)
            raise ctypes.WinError(ctypes.get_last_error())
        return int(hwnd)

    def message_loop(self, controller: "NativeOverlayController") -> None:
        msg = _MSG()
        while not controller._stop.is_set():
            result = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result <= 0:
                break
            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageW(ctypes.byref(msg))

    def set_window_display_affinity(self, hwnd: int, affinity: int) -> bool:
        return bool(self.user32.SetWindowDisplayAffinity(hwnd, affinity))

    def get_window_display_affinity(self, hwnd: int) -> int | None:
        value = wintypes.DWORD()
        if not self.user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(value)):
            return None
        return int(value.value)

    def show_window(self, hwnd: int, command: int) -> None:
        self.user32.ShowWindow(hwnd, command)

    def move_window(self, hwnd: int, x: int, y: int, width: int, height: int) -> None:
        self.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            x,
            y,
            width,
            height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def post_message(self, hwnd: int, message: int, wparam: int, lparam: int) -> None:
        self.user32.PostMessageW(hwnd, message, wparam, lparam)

    def destroy_window(self, hwnd: int) -> None:
        self.user32.DestroyWindow(hwnd)

    def post_quit(self, code: int) -> None:
        self.user32.PostQuitMessage(code)

    def def_window_proc(self, hwnd, message, wparam, lparam):
        return self.user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def invalidate(self, hwnd: int) -> None:
        self.user32.InvalidateRect(hwnd, None, False)

    def begin_paint(self, hwnd: int):
        paint = _PAINTSTRUCT()
        hdc = self.user32.BeginPaint(hwnd, ctypes.byref(paint))
        return hdc, paint

    def end_paint(self, hwnd: int, paint: _PAINTSTRUCT) -> None:
        self.user32.EndPaint(hwnd, ctypes.byref(paint))

    def fill_color_key(self, hdc, paint_rect: _RECT) -> None:
        brush = self.gdi32.CreateSolidBrush(COLOR_KEY)
        try:
            self.user32.FillRect(hdc, ctypes.byref(paint_rect), brush)
        finally:
            self.gdi32.DeleteObject(brush)

    def create_pen(self, width: int, color: int):
        return self.gdi32.CreatePen(PS_SOLID, width, color)

    def create_font(self, size: int):
        return self.gdi32.CreateFontW(
            -abs(size), 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 0, 0, "Segoe UI"
        )

    def select_object(self, hdc, obj):
        return self.gdi32.SelectObject(hdc, obj)

    def delete_object(self, obj) -> None:
        self.gdi32.DeleteObject(obj)

    def draw_arrow(self, hdc, start: tuple[float, float], end: tuple[float, float], width: int, _color: int) -> None:
        sx, sy = (int(round(value)) for value in start)
        ex, ey = (int(round(value)) for value in end)
        self.gdi32.MoveToEx(hdc, sx, sy, None)
        self.gdi32.LineTo(hdc, ex, ey)
        dx, dy = ex - sx, ey - sy
        length = max(math.hypot(dx, dy), 1.0)
        ux, uy = dx / length, dy / length
        size = max(8.0, min(24.0, width * 3.0))
        left = _POINT(int(ex - ux * size - uy * size * 0.55), int(ey - uy * size + ux * size * 0.55))
        right = _POINT(int(ex - ux * size + uy * size * 0.55), int(ey - uy * size - ux * size * 0.55))
        tip = _POINT(ex, ey)
        points = (_POINT * 3)(tip, left, right)
        self.gdi32.Polygon(hdc, ctypes.byref(points), 3)

    def draw_text(self, hdc, message: str) -> None:
        rect = _RECT(12, 12, 620, 100)
        self.gdi32.SetBkMode(hdc, TRANSPARENT)
        self.gdi32.SetTextColor(hdc, 0x00FFFFFF)
        self.user32.DrawTextW(hdc, message, -1, ctypes.byref(rect), 0x00000000)


class NativeOverlayController:
    """Thread-safe, fail-closed native annotation overlay."""

    def __init__(
        self,
        *,
        title: str = "Allie21 Native Overlay",
        width: int = 640,
        height: int = 640,
        api: object | None = None,
    ) -> None:
        self.title = str(title)[:128]
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self._api = api
        self._lock = RLock()
        self._ready = Event()
        self._stop = Event()
        self._thread: Thread | None = None
        self._hwnd: int | None = None
        self._wndproc = None
        self._class_name = f"Allie21NativeOverlay_{id(self):x}"
        self._snapshot = OverlaySnapshot()
        self._started = False
        self._visible = False
        self._capture_excluded = False
        self._failed_closed = False
        self._start_result = False
        self._failure_reason = ""

    @property
    def available(self) -> bool:
        with self._lock:
            return self._capture_excluded and self._hwnd is not None and not self._failed_closed

    @property
    def visible(self) -> bool:
        with self._lock:
            return self._visible and self.available

    @property
    def failed_closed(self) -> bool:
        with self._lock:
            return self._failed_closed

    @property
    def snapshot(self) -> OverlaySnapshot:
        with self._lock:
            return self._snapshot

    def _bindings(self) -> object:
        if self._api is None:
            self._api = _Win32()
        return self._api

    def start(self, timeout: float = 3.0) -> bool:
        """Start the window thread; return false unless capture exclusion verifies."""

        with self._lock:
            if self._started:
                return self._start_result
            if self._api is None and os.name != "nt":
                self._fail_locked()
                return False
            self._started = True
            self._failed_closed = False
            self._start_result = False
            self._failure_reason = ""
            self._stop.clear()
            self._ready.clear()
            self._thread = Thread(target=self._window_thread, name="allie-native-overlay", daemon=True)
            self._thread.start()
        if not self._ready.wait(max(0.05, float(timeout))):
            self._fail_closed()
        with self._lock:
            return self._start_result

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            thread = self._thread
            hwnd = self._hwnd
            self._stop.set()
        if hwnd is not None:
            try:
                self._bindings().post_message(hwnd, WM_CLOSE, 0, 0)
            except Exception:
                pass
        if thread and thread is not __import__("threading").current_thread():
            thread.join(max(0.05, float(timeout)))
        with self._lock:
            self._visible = False
            self._started = False
            self._capture_excluded = False
            self._hwnd = None
            self._thread = None

    def show(self) -> bool:
        with self._lock:
            if not self.available:
                self._fail_locked()
                return False
            hwnd = self._hwnd
        try:
            self._bindings().show_window(hwnd, SW_SHOWNOACTIVATE)
            with self._lock:
                self._visible = True
            return True
        except Exception:
            self._fail_closed()
            return False

    def hide(self) -> None:
        with self._lock:
            hwnd = self._hwnd
            self._visible = False
        if hwnd is not None:
            try:
                self._bindings().show_window(hwnd, SW_HIDE)
            except Exception:
                self._fail_closed()

    def update(
        self,
        arrows: Iterable[OverlayArrow | Mapping[str, object]],
        message: str = "",
        bounds: Sequence[int] | None = None,
    ) -> bool:
        """Publish a validated frame and show it only after privacy checks."""

        try:
            normalized = normalize_arrows(arrows)
            rect = None
            if bounds is not None:
                if len(bounds) != 4:
                    raise ValueError("overlay bounds must be x,y,width,height")
                rect = tuple(int(item) for item in bounds)
                if rect[2] <= 0 or rect[3] <= 0:
                    raise ValueError("overlay bounds must be positive")
            snapshot = OverlaySnapshot(normalized, str(message)[:500], rect)
        except (TypeError, ValueError, OverflowError):
            self.hide()
            return False
        with self._lock:
            if not self.available:
                self._fail_locked()
                return False
            self._snapshot = snapshot
            hwnd = self._hwnd
        try:
            if snapshot.bounds is not None:
                self._bindings().move_window(hwnd, *snapshot.bounds)
            self._bindings().post_message(hwnd, WM_APP_RENDER, 0, 0)
            return self.show()
        except Exception:
            self._fail_closed()
            return False

    def _fail_locked(self) -> None:
        self._failed_closed = True
        self._visible = False
        self._capture_excluded = False
        self._snapshot = OverlaySnapshot()

    def _fail_closed(self) -> None:
        with self._lock:
            hwnd = self._hwnd
            self._fail_locked()
        if hwnd is not None:
            try:
                self._bindings().show_window(hwnd, SW_HIDE)
            except Exception:
                pass

    def _verify_capture_exclusion(self, hwnd: int) -> bool:
        """Set and read back WDA_EXCLUDEFROMCAPTURE; never trust Set alone."""

        api = self._bindings()
        if not bool(api.set_window_display_affinity(hwnd, WDA_EXCLUDEFROMCAPTURE)):
            return False
        affinity = api.get_window_display_affinity(hwnd)
        return affinity == WDA_EXCLUDEFROMCAPTURE

    # The following methods are used only on the dedicated GUI thread.  The
    # binding object is intentionally small so tests can provide a fake API.
    def _window_thread(self) -> None:
        try:
            api = self._bindings()
            hwnd = api.create_window(self)
            if not hwnd or not self._verify_capture_exclusion(hwnd):
                raise OSError("WDA_EXCLUDEFROMCAPTURE could not be verified")
            with self._lock:
                self._hwnd = hwnd
                self._capture_excluded = True
                self._start_result = True
            api.show_window(hwnd, SW_HIDE)
            self._ready.set()
            api.message_loop(self)
        except Exception as exc:
            with self._lock:
                self._failure_reason = f"{type(exc).__name__}: {exc}"[:240]
                self._fail_locked()
            self._ready.set()
        finally:
            with self._lock:
                self._visible = False
                self._capture_excluded = False

    def _window_proc(self, hwnd, message, wparam, lparam):  # pragma: no cover - Win32 callback
        if message == WM_NCHITTEST:
            return HTTRANSPARENT
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_PAINT:
            self._paint(hwnd)
            return 0
        if message == WM_CLOSE:
            self._bindings().show_window(hwnd, SW_HIDE)
            self._bindings().destroy_window(hwnd)
            return 0
        if message == WM_DESTROY:
            self._bindings().post_quit(0)
            return 0
        if message == WM_APP_RENDER:
            self._bindings().invalidate(hwnd)
            return 0
        return self._bindings().def_window_proc(hwnd, message, wparam, lparam)

    def _paint(self, hwnd):  # pragma: no cover - Win32 GDI callback
        api = self._bindings()
        hdc, paint = api.begin_paint(hwnd)
        objects = []
        try:
            api.fill_color_key(hdc, paint.rcPaint)
            with self._lock:
                snapshot = self._snapshot
            for arrow in snapshot.arrows:
                pen = api.create_pen(arrow.width, _rgb(arrow.color))
                objects.append(pen)
                api.select_object(hdc, pen)
                api.draw_arrow(hdc, arrow.start, arrow.end, arrow.width, _rgb(arrow.color))
            if snapshot.message:
                font = api.create_font(18)
                objects.append(font)
                api.select_object(hdc, font)
                api.draw_text(hdc, snapshot.message)
        finally:
            for obj in objects:
                api.delete_object(obj)
            api.end_paint(hwnd, paint)


class PrivateOverlayController:
    """Application-facing privacy router around the native HUD.

    The browser/viewer may publish a visual snapshot, but private mode never
    falls back to DOM/SVG rendering when the protected HWND is unavailable.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._native = NativeOverlayController()
        self._mode = "private"
        # The active session is intentionally separate from the per-session
        # cursor map.  Once a new session publishes a frame, delayed frames
        # from every previous session are ignored even when their revisions
        # are numerically larger.
        self._active_session_id: str | None = None
        self._last_update_by_session: dict[str, tuple[int, int]] = {}
        self._retired_sessions: set[str] = set()
        self._state = "unsupported" if os.name != "nt" else "starting"
        self._reason = "Windows capture exclusion is unavailable" if os.name != "nt" else "not_started"

    @staticmethod
    def _square_point(square: str, board: Mapping[str, object], orientation: str) -> tuple[float, float]:
        if not isinstance(square, str) or len(square) != 2 or square[0] not in "abcdefgh" or square[1] not in "12345678":
            raise ValueError("invalid chess square")
        rect = (float(board["left"]), float(board["top"]), float(board["width"]), float(board["height"]))
        file_index = ord(square[0]) - 97
        rank_index = int(square[1]) - 1
        if orientation == "black":
            file_index = 7 - file_index
        else:
            rank_index = 7 - rank_index
        return (rect[0] + (file_index + .5) * rect[2] / 8, rect[1] + (rank_index + .5) * rect[3] / 8)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "mode": self._mode,
                "state": "active" if self._native.visible else self._state,
                "reason": self._reason,
                "available": self._native.available,
                "visible": self._native.visible,
                "capture_excluded": self._native.available,
            }

    def set_mode(self, mode: str) -> dict[str, object]:
        if mode not in {"private", "normal"}:
            raise ValueError("overlay mode must be private or normal")
        with self._lock:
            self._mode = mode
            if mode == "normal":
                self._active_session_id = None
                self._last_update_by_session.clear()
                self._retired_sessions.clear()
        if mode == "normal":
            self._native.hide()
            with self._lock:
                self._state, self._reason = "normal", "explicit_normal_mode"
            return self.status()
        if not self._native.start():
            with self._lock:
                detail = getattr(self._native, "_failure_reason", "")
                self._state, self._reason = ("unsupported" if os.name != "nt" else "exclusion_error", detail or "capture_exclusion_not_verified")
            return self.status()
        with self._lock:
            self._state, self._reason = "ready", "capture_exclusion_verified"
        return self.status()

    def update(self, payload: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(payload, Mapping):
            raise ValueError("overlay payload must be an object")
        session_id = payload.get("session_id")
        try:
            generation = int(payload.get("generation", 0))
            render_revision = int(payload.get("render_revision", 0))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("overlay revisions must be integers") from exc
        if not isinstance(session_id, str) or not session_id or generation < 0 or render_revision < 0:
            raise ValueError("overlay session and revisions are invalid")
        with self._lock:
            # A different session is a deliberate lifecycle boundary.  It is
            # allowed to establish a new cursor, but any later frame carrying
            # the old session id is rejected by the active-session check.
            if session_id in self._retired_sessions:
                self._state, self._reason = "stale", "retired_session_ignored"
                return self.status()
            if self._active_session_id is None:
                self._active_session_id = session_id
            elif session_id != self._active_session_id:
                self._retired_sessions.add(self._active_session_id)
                self._active_session_id = session_id
            if not is_overlay_update_newer(
                session_id,
                generation,
                render_revision,
                self._last_update_by_session,
            ):
                self._state, self._reason = "stale", "stale_update_ignored"
                return self.status()
            self._last_update_by_session[session_id] = (generation, render_revision)
            # Keep only a small bounded cursor history.  The active session
            # remains authoritative; old entries are never rendered again.
            if len(self._last_update_by_session) > 8:
                for key in tuple(self._last_update_by_session):
                    if key != self._active_session_id:
                        self._last_update_by_session.pop(key, None)
        if self._mode != "private" or payload.get("mode") not in {"private", "stale", "stopped", "exclusion_error"}:
            self._native.hide()
            return self.status()
        if not self._native.available and not self.set_mode("private").get("available"):
            return self.status()
        mode = str(payload.get("mode", "private"))
        if mode != "private":
            self._native.hide()
            return self.status()
        geometry = payload.get("geometry") or {}
        board = (geometry.get("screen_board") or geometry.get("board")) if isinstance(geometry, Mapping) else None
        if not isinstance(board, Mapping):
            self._native.hide()
            with self._lock:
                self._state, self._reason = "hidden", "missing_board_geometry"
            return self.status()
        orientation = str(geometry.get("orientation", "white")) if isinstance(geometry, Mapping) else "white"
        arrows = []
        for item in payload.get("arrows", []) or []:
            if not isinstance(item, Mapping):
                continue
            uci = str(item.get("uci", ""))
            if len(uci) < 4:
                continue
            start = self._square_point(uci[:2], board, orientation)
            end = self._square_point(uci[2:4], board, orientation)
            arrows.append({"start": start, "end": end, "color": item.get("color", "#16c784"), "width": 5})
        message = " · ".join(str(item) for item in (payload.get("messages") or [])[:2])
        bounds = (int(float(board["left"])), int(float(board["top"])), int(float(board["width"])), int(float(board["height"])))
        if self._native.update(arrows, message=message, bounds=bounds):
            with self._lock:
                self._state, self._reason = "active", "capture_exclusion_verified"
        return self.status()

    def clear(
        self,
        reason: str = "cleared",
        *,
        session_id: str | None = None,
        generation: int | None = None,
        render_revision: int | None = None,
    ) -> dict[str, object]:
        self._native.hide()
        with self._lock:
            if session_id is not None:
                if not isinstance(session_id, str) or not session_id:
                    raise ValueError("overlay clear session is invalid")
                if generation is None or render_revision is None:
                    raise ValueError("overlay clear revisions are required with a session")
                cursor = (int(generation), int(render_revision))
                if min(cursor) < 0:
                    raise ValueError("overlay clear revisions are invalid")
                if self._active_session_id and self._active_session_id != session_id:
                    self._retired_sessions.add(self._active_session_id)
                self._active_session_id = session_id
                self._last_update_by_session[session_id] = cursor
            self._state, self._reason = "hidden", str(reason)[:120]
        return self.status()

    def close(self) -> None:
        self._native.stop()
        with self._lock:
            self._state, self._reason = "stopped", "closed"


# Convenient short alias for callers that do not need the longer class name.
NativeOverlay = NativeOverlayController


__all__ = [
    "PrivateOverlayController",
    "NativeOverlay",
    "NativeOverlayController",
    "OverlayArrow",
    "OverlaySnapshot",
    "normalize_arrows",
    "is_overlay_update_newer",
    "WDA_EXCLUDEFROMCAPTURE",
]
