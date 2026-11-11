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

import ctypes
import logging
import math
import os
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from ctypes import wintypes
from dataclasses import dataclass
from threading import Event, RLock, Thread, current_thread
from typing import Any, cast

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
LOGGER = logging.getLogger(__name__)


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
        ("lPrivate", wintypes.DWORD),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
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
    message_rect: tuple[int, int, int, int] | None = None


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
                int(cast(Any, raw.get("width", 5))),
            )
        else:
            raise TypeError("invalid overlay arrow")
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
        """Declare every used Win32 ABI, including pointer-sized return values.

        ctypes defaults to C int. Leaving a handle argument or result implicit
        truncates values on Win64, sometimes before display affinity is set.
        """
        def bind(library, name, result, *arguments):
            function = getattr(library, name)
            function.argtypes = arguments
            function.restype = result

        u, g, k = self.user32, self.gdi32, self.kernel32
        pointer = ctypes.POINTER
        bind(k, "GetModuleHandleW", wintypes.HMODULE, wintypes.LPCWSTR)
        bind(u, "CreateWindowExW", wintypes.HWND,
             wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
             ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
             wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p)
        bind(u, "RegisterClassExW", wintypes.ATOM, pointer(_WNDCLASSEXW))
        bind(u, "UnregisterClassW", wintypes.BOOL, wintypes.LPCWSTR, wintypes.HINSTANCE)
        bind(u, "LoadCursorW", HCURSOR, wintypes.HINSTANCE, ctypes.c_void_p)
        bind(u, "DefWindowProcW", ctypes.c_ssize_t,
             wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        bind(u, "SetLayeredWindowAttributes", wintypes.BOOL,
             wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD)
        bind(u, "SetWindowDisplayAffinity", wintypes.BOOL, wintypes.HWND, wintypes.DWORD)
        bind(u, "GetWindowDisplayAffinity", wintypes.BOOL, wintypes.HWND, pointer(wintypes.DWORD))
        bind(u, "GetMessageW", ctypes.c_int, pointer(_MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
        bind(u, "TranslateMessage", wintypes.BOOL, pointer(_MSG))
        bind(u, "DispatchMessageW", ctypes.c_ssize_t, pointer(_MSG))
        bind(u, "ShowWindow", wintypes.BOOL, wintypes.HWND, ctypes.c_int)
        bind(u, "SetWindowPos", wintypes.BOOL, wintypes.HWND, wintypes.HWND,
             ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
        bind(u, "PostMessageW", wintypes.BOOL,
             wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        bind(u, "IsWindow", wintypes.BOOL, wintypes.HWND)
        bind(u, "DestroyWindow", wintypes.BOOL, wintypes.HWND)
        bind(u, "PostQuitMessage", None, ctypes.c_int)
        bind(u, "InvalidateRect", wintypes.BOOL, wintypes.HWND, pointer(_RECT), wintypes.BOOL)
        bind(u, "BeginPaint", wintypes.HDC, wintypes.HWND, pointer(_PAINTSTRUCT))
        bind(u, "EndPaint", wintypes.BOOL, wintypes.HWND, pointer(_PAINTSTRUCT))
        bind(u, "FillRect", ctypes.c_int, wintypes.HDC, pointer(_RECT), wintypes.HBRUSH)
        bind(u, "DrawTextW", ctypes.c_int,
             wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, pointer(_RECT), wintypes.UINT)
        bind(u, "MonitorFromRect", wintypes.HANDLE, pointer(_RECT), wintypes.DWORD)
        bind(u, "GetMonitorInfoW", wintypes.BOOL, wintypes.HANDLE, pointer(_MONITORINFO))
        bind(g, "CreatePen", wintypes.HGDIOBJ, ctypes.c_int, ctypes.c_int, wintypes.DWORD)
        bind(g, "CreateSolidBrush", wintypes.HGDIOBJ, wintypes.DWORD)
        bind(g, "CreateFontW", wintypes.HGDIOBJ,
             *([ctypes.c_int] * 5), *([wintypes.DWORD] * 8), wintypes.LPCWSTR)
        bind(g, "DeleteObject", wintypes.BOOL, wintypes.HGDIOBJ)
        bind(g, "SelectObject", wintypes.HGDIOBJ, wintypes.HDC, wintypes.HGDIOBJ)
        bind(g, "MoveToEx", wintypes.BOOL, wintypes.HDC, ctypes.c_int, ctypes.c_int, pointer(_POINT))
        bind(g, "LineTo", wintypes.BOOL, wintypes.HDC, ctypes.c_int, ctypes.c_int)
        bind(g, "Polygon", wintypes.BOOL, wintypes.HDC, pointer(_POINT), ctypes.c_int)
        bind(g, "SetBkMode", ctypes.c_int, wintypes.HDC, ctypes.c_int)
        bind(g, "SetTextColor", wintypes.DWORD, wintypes.HDC, wintypes.DWORD)

    def get_work_area(self, x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
        rectangle = _RECT(x, y, x + width, y + height)
        monitor = self.user32.MonitorFromRect(ctypes.byref(rectangle), 2)
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        if not monitor or not self.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        area = info.rcWork
        return area.left, area.top, area.right, area.bottom

    def create_window(self, controller: NativeOverlayController) -> int:
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
            failure = ctypes.WinError(ctypes.get_last_error())
            self.user32.DestroyWindow(hwnd)
            raise failure
        return int(hwnd)

    def message_loop(self, controller: NativeOverlayController) -> None:
        msg = _MSG()
        while not controller._stop.is_set():
            result = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            if result == 0:
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
        success = self.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            x,
            y,
            width,
            height,
            SWP_NOACTIVATE,
        )
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

    def post_message(self, hwnd: int, message: int, wparam: int, lparam: int) -> None:
        if not self.user32.PostMessageW(hwnd, message, wparam, lparam):
            raise ctypes.WinError(ctypes.get_last_error())

    def destroy_window(self, hwnd: int) -> None:
        if self.user32.IsWindow(hwnd) and not self.user32.DestroyWindow(hwnd):
            raise ctypes.WinError(ctypes.get_last_error())

    def unregister_class(self, name: str) -> None:
        instance = self.kernel32.GetModuleHandleW(None)
        if not self.user32.UnregisterClassW(name, instance):
            code = ctypes.get_last_error()
            if code != 1411:  # ERROR_CLASS_DOES_NOT_EXIST
                raise ctypes.WinError(code)

    def post_quit(self, code: int) -> None:
        self.user32.PostQuitMessage(code)

    def def_window_proc(self, hwnd, message, wparam, lparam):
        return self.user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def invalidate(self, hwnd: int) -> None:
        self.user32.InvalidateRect(hwnd, None, False)

    def begin_paint(self, hwnd: int):
        paint = _PAINTSTRUCT()
        hdc = self.user32.BeginPaint(hwnd, ctypes.byref(paint))
        if not hdc:
            raise ctypes.WinError(ctypes.get_last_error())
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
        sx, sy = (int(round(value)) for value in start)  # noqa: RUF046 - ctypes requires concrete ints
        ex, ey = (int(round(value)) for value in end)  # noqa: RUF046 - ctypes requires concrete ints
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
        brush = self.gdi32.CreateSolidBrush(_color)
        previous = self.gdi32.SelectObject(hdc, brush)
        try:
            self.gdi32.Polygon(hdc, points, 3)
        finally:
            self.gdi32.SelectObject(hdc, previous)
            self.gdi32.DeleteObject(brush)

    def draw_text(self, hdc, message: str, bounds: tuple[int, int, int, int] | None = None) -> None:
        x, y, width, height = bounds or (12, 12, 608, 88)
        background = _RECT(x, y, x + width, y + height)
        brush = self.gdi32.CreateSolidBrush(_rgb("#2a1d17"))
        if not brush:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            self.user32.FillRect(hdc, ctypes.byref(background), brush)
        finally:
            self.gdi32.DeleteObject(brush)
        padding = min(6, max(0, min(width, height) // 4))
        rect = _RECT(x + padding, y + padding, x + width - padding, y + height - padding)
        self.gdi32.SetBkMode(hdc, TRANSPARENT)
        self.gdi32.SetTextColor(hdc, 0x00FFFFFF)
        self.user32.DrawTextW(hdc, message, -1, ctypes.byref(rect), 0x00000010 | 0x00000800)


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
        self._api: Any = api
        self._lock = RLock()
        self._ready = Event()
        self._stop = Event()
        self._thread: Thread | None = None
        self._hwnd: int | None = None
        self._wndproc: Any = None
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

    def _bindings(self) -> Any:
        if self._api is None:
            self._api = _Win32()
        return self._api

    def start(self, timeout: float = 3.0) -> bool:
        """Start the window thread; return false unless capture exclusion verifies."""

        with self._lock:
            if self._started:
                return self._start_result and self.available and not self._stop.is_set()
            if self._api is None and os.name != "nt":
                self._failure_reason = "native_overlay_requires_windows"
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
            with self._lock:
                self._failure_reason = "native_overlay_start_timeout"
                self._stop.set()
                thread = self._thread
                hwnd = self._hwnd
            if hwnd is not None:
                try:
                    self._bindings().post_message(hwnd, WM_CLOSE, 0, 0)
                except Exception as exc:  # noqa: BLE001 - timeout cleanup is best effort
                    LOGGER.warning("Native overlay cleanup failed (timeout): %s", type(exc).__name__)
            self._fail_closed()
            if thread and thread is not current_thread():
                thread.join(max(0.05, min(float(timeout), 2.0)))
        with self._lock:
            return self._start_result and self.available and not self._stop.is_set()

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            thread = self._thread
            hwnd = self._hwnd
            self._stop.set()
        if hwnd is not None:
            try:
                self._bindings().post_message(hwnd, WM_CLOSE, 0, 0)
            except Exception:  # noqa: BLE001,S110 - overlay cleanup is best effort
                pass
        if thread and thread is not current_thread():
            thread.join(max(0.05, float(timeout)))
        with self._lock:
            self._visible = False
            self._start_result = False
            self._capture_excluded = False
            if thread is not None and thread.is_alive():
                # Do not permit another GUI thread to reuse this controller.
                self._started = True
                self._failed_closed = True
                self._failure_reason = "native_overlay_stop_timeout"
            else:
                self._started = False
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
        except Exception:  # noqa: BLE001 - fail closed when Win32 show fails
            self._fail_closed()
            return False

    def hide(self) -> None:
        with self._lock:
            hwnd = self._hwnd
            self._visible = False
        if hwnd is not None:
            try:
                self._bindings().show_window(hwnd, SW_HIDE)
            except Exception:  # noqa: BLE001 - fail closed when Win32 hide fails
                self._fail_closed()

    def update(
        self,
        arrows: Iterable[OverlayArrow | Mapping[str, object]],
        message: str = "",
        bounds: Sequence[int] | None = None,
        message_rect: tuple[int, int, int, int] | None = None,
    ) -> bool:
        """Publish a validated frame and show it only after privacy checks."""

        try:
            normalized = normalize_arrows(arrows)
            rect = None
            if bounds is not None:
                if len(bounds) != 4:
                    raise ValueError("overlay bounds must be x,y,width,height")
                rect = (int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]))
                if rect[2] <= 0 or rect[3] <= 0:
                    raise ValueError("overlay bounds must be positive")
            if message_rect is not None:
                if len(message_rect) != 4 or message_rect[2] <= 0 or message_rect[3] <= 0:
                    raise ValueError("message bounds must be x,y,width,height")
                message_rect = (int(message_rect[0]), int(message_rect[1]),
                                int(message_rect[2]), int(message_rect[3]))
            snapshot = OverlaySnapshot(normalized, str(message)[:500], rect, message_rect)
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
        except Exception:  # noqa: BLE001 - fail closed when Win32 render fails
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
            except Exception:  # noqa: BLE001,S110 - overlay cleanup is best effort
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
        hwnd = None
        api = None
        try:
            api = self._bindings()
            hwnd = api.create_window(self)
            if not hwnd or not self._verify_capture_exclusion(hwnd):
                raise OSError("WDA_EXCLUDEFROMCAPTURE could not be verified")
            if self._stop.is_set():
                destroy = getattr(api, "destroy_window", None)
                if destroy is not None:
                    destroy(hwnd)
                hwnd = None
                return
            with self._lock:
                self._hwnd = hwnd
                self._capture_excluded = True
                self._start_result = True
            api.show_window(hwnd, SW_HIDE)
            self._ready.set()
            api.message_loop(self)
        except Exception as exc:  # noqa: BLE001 - GUI thread must fail closed on any Win32 error
            if hwnd:
                destroy = getattr(api, "destroy_window", None)
                if destroy is not None:
                    try:
                        destroy(hwnd)
                        hwnd = None
                    except Exception as cleanup_exc:  # noqa: BLE001 - cleanup is best effort
                        LOGGER.warning(
                            "Native overlay cleanup failed (window thread): %s",
                            type(cleanup_exc).__name__,
                        )
            with self._lock:
                self._failure_reason = f"{type(exc).__name__}: {exc}"[:240]
                self._fail_locked()
        finally:
            if hwnd is not None:
                destroy = getattr(api, "destroy_window", None)
                if destroy is not None:
                    try:
                        destroy(hwnd)
                    except Exception as cleanup_exc:  # noqa: BLE001 - best effort on GUI owner thread
                        LOGGER.warning("Native overlay final cleanup failed: %s", type(cleanup_exc).__name__)
            unregister = getattr(api, "unregister_class", None)
            if unregister is not None:
                try:
                    unregister(self._class_name)
                except Exception as cleanup_exc:  # noqa: BLE001 - keep failure diagnostic and release waiter
                    LOGGER.warning("Native overlay class cleanup failed: %s", type(cleanup_exc).__name__)
            with self._lock:
                self._visible = False
                self._capture_excluded = False
                self._start_result = False
                self._hwnd = None
                self._started = False
                self._thread = None
            self._ready.set()

    def _window_proc(self, hwnd, message, wparam, lparam):  # pragma: no cover - Win32 callback
        if message == WM_NCHITTEST:
            return HTTRANSPARENT
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_PAINT:
            try:
                self._paint(hwnd)
            except Exception as exc:  # noqa: BLE001 - exceptions must never escape a Win32 callback
                LOGGER.warning("Native overlay painting failed: %s", type(exc).__name__)
                with self._lock:
                    self._failure_reason = "native_overlay_paint_failed"
                self._fail_closed()
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
        try:
            api.fill_color_key(hdc, paint.rcPaint)
            with self._lock:
                snapshot = self._snapshot
            for arrow in snapshot.arrows:
                pen = api.create_pen(arrow.width, _rgb(arrow.color))
                previous = api.select_object(hdc, pen)
                try:
                    api.draw_arrow(hdc, arrow.start, arrow.end, arrow.width, _rgb(arrow.color))
                finally:
                    api.select_object(hdc, previous)
                    api.delete_object(pen)
            if snapshot.message:
                font = api.create_font(18)
                previous = api.select_object(hdc, font)
                try:
                    if snapshot.message_rect is None:
                        api.draw_text(hdc, snapshot.message)
                    else:
                        api.draw_text(hdc, snapshot.message, snapshot.message_rect)
                finally:
                    api.select_object(hdc, previous)
                    api.delete_object(font)
        finally:
            api.end_paint(hwnd, paint)


class PrivateOverlayController:
    """Application-facing privacy router around the native HUD.

    The browser/viewer may publish a visual snapshot, but private mode never
    falls back to DOM/SVG rendering when the protected HWND is unavailable.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        # Cursor acceptance and native application must be ordered together.
        # HTTP requests can finish out of order even when their revisions are
        # monotonic, so a second lock serializes hide/update operations.
        self._render_lock = RLock()
        self._native = NativeOverlayController()
        self._mode = "private"
        # The active session is intentionally separate from the per-session
        # cursor map.  Once a new session publishes a frame, delayed frames
        # from every previous session are ignored even when their revisions
        # are numerically larger.
        self._active_session_id: str | None = None
        self._last_update_by_session: dict[str, tuple[int, int]] = {}
        self._retired_sessions: set[str] = set()
        self._retired_order: deque[str] = deque(maxlen=64)
        self._state = "unsupported" if os.name != "nt" else "starting"
        self._reason = "Windows capture exclusion is unavailable" if os.name != "nt" else "not_started"

    @staticmethod
    def _square_point(square: str, board: Mapping[str, object], orientation: str) -> tuple[float, float]:
        if not isinstance(square, str) or len(square) != 2 or square[0] not in "abcdefgh" or square[1] not in "12345678":
            raise ValueError("invalid chess square")
        rect = tuple(
            float(cast(Any, board[key])) for key in ("left", "top", "width", "height")
        )
        file_index = ord(square[0]) - 97
        rank_index = int(square[1]) - 1
        if orientation == "black":
            file_index = 7 - file_index
        else:
            rank_index = 7 - rank_index
        return (rect[0] + (file_index + .5) * rect[2] / 8, rect[1] + (rank_index + .5) * rect[3] / 8)

    def status(self) -> dict[str, object]:
        with self._lock:
            available, visible = self._native.available, self._native.visible
            state, reason = ("active" if visible else self._state), self._reason
            if self._mode == "private" and not available and state in {"active", "ready"}:
                state = "unavailable"
                reason = self._native._failure_reason or "native_window_stopped"
            snapshot = self._native.snapshot if visible else OverlaySnapshot()
            return {
                "mode": self._mode,
                "state": state,
                "reason": reason,
                "available": available,
                "visible": visible,
                "capture_excluded": available,
                # Keep diagnostics deliberately aggregate: the local status
                # endpoint may confirm that a protected frame was published
                # without exposing move data or board contents.
                "arrow_count": len(snapshot.arrows),
                "bounds": snapshot.bounds,
                "has_message": bool(snapshot.message),
            }

    def _retire_locked(self, session_id: str | None) -> None:
        if not session_id:
            return
        self._retired_sessions.add(session_id)
        try:
            self._retired_order.remove(session_id)
        except ValueError:
            pass
        max_retired = self._retired_order.maxlen or 64
        if len(self._retired_order) >= max_retired:
            oldest = self._retired_order.popleft()
            self._retired_sessions.discard(oldest)
        self._retired_order.append(session_id)

    def set_mode(self, mode: str) -> dict[str, object]:
        if mode not in {"private", "normal"}:
            raise ValueError("overlay mode must be private or normal")
        with self._render_lock:
            with self._lock:
                self._mode = mode
                if mode == "normal":
                    self._active_session_id = None
                    self._last_update_by_session.clear()
                    self._retired_sessions.clear()
                    self._retired_order.clear()
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
            raise TypeError("overlay payload must be an object")
        session_id = payload.get("session_id")
        try:
            generation = int(cast(Any, payload.get("generation", 0)))
            render_revision = int(cast(Any, payload.get("render_revision", 0)))
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
                self._retire_locked(self._active_session_id)
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
        with self._render_lock:
            # A newer request may have advanced the cursor while this request
            # was waiting for the renderer.  Do not apply the old snapshot.
            with self._lock:
                if (self._active_session_id != session_id
                        or self._last_update_by_session.get(session_id)
                        != (generation, render_revision)):
                    self._state, self._reason = "stale", "stale_update_ignored"
                    return self.status()
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
            board_values = tuple(float(cast(Any, board[key])) for key in ("left", "top", "width", "height"))
            if not all(math.isfinite(value) for value in board_values) or min(board_values[2:]) <= 0:
                raise ValueError("invalid screen board rectangle")
            left, top = math.floor(board_values[0]), math.floor(board_values[1])
            width = math.ceil(board_values[0] + board_values[2]) - left
            height = math.ceil(board_values[1] + board_values[3]) - top
            bounds = (left, top, width, height)
            local_board = {"left": board_values[0] - left, "top": board_values[1] - top,
                           "width": board_values[2], "height": board_values[3]}
            arrows: list[dict[str, object]] = []
            raw_arrows = payload.get("arrows", [])
            if not isinstance(raw_arrows, Sequence) or isinstance(raw_arrows, (str, bytes)):
                raw_arrows = ()
            for item in raw_arrows:
                if not isinstance(item, Mapping):
                    continue
                uci = str(item.get("uci", ""))
                if len(uci) < 4:
                    continue
                start = self._square_point(uci[:2], local_board, orientation)
                end = self._square_point(uci[2:4], local_board, orientation)
                arrows.append({"start": start, "end": end, "color": item.get("color", "#16c784"), "width": 5})
            raw_messages = payload.get("messages", [])
            if not isinstance(raw_messages, Sequence) or isinstance(raw_messages, (str, bytes)):
                raw_messages = ()
            message = " · ".join(str(item) for item in raw_messages[:2])
            message_rect = None
            if message:
                # Extend the transparent window beside/below the board, never
                # print over pieces. If no monitor space exists, omit the text.
                api = self._native._bindings()
                get_area = getattr(api, "get_work_area", None)
                try:
                    area = get_area(*bounds) if get_area is not None else None
                except OSError:
                    LOGGER.warning("Native overlay work area unavailable; omitting message panel")
                    area = (left, top, left + width, top + height)
                gap, panel_width, panel_height = 12, 320, 144
                candidates = [
                    (left + width + gap, top, panel_width, min(height, 320)),
                    (left - panel_width - gap, top, panel_width, min(height, 320)),
                    (left, top + height + gap, width, panel_height),
                    (left, top - panel_height - gap, width, panel_height),
                ]
                for px, py, pw, ph in candidates:
                    if area is not None and not (px >= area[0] and py >= area[1]
                            and px + pw <= area[2] and py + ph <= area[3]):
                        continue
                    origin_x, origin_y = min(left, px), min(top, py)
                    bounds = (origin_x, origin_y,
                              max(left + width, px + pw) - origin_x,
                              max(top + height, py + ph) - origin_y)
                    dx, dy = left - origin_x, top - origin_y
                    for arrow in arrows:
                        for key in ("start", "end"):
                            point = cast(tuple[float, float], arrow[key])
                            arrow[key] = (point[0] + dx, point[1] + dy)
                    message_rect = (px - origin_x + 8, py - origin_y + 8,
                                    max(1, pw - 16), max(1, ph - 16))
                    break
                if message_rect is None:
                    message = ""
            if self._native.update(arrows, message=message, bounds=bounds, message_rect=message_rect):
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
        with self._render_lock:
            with self._lock:
                if session_id is not None:
                    if not isinstance(session_id, str) or not session_id:
                        raise ValueError("overlay clear session is invalid")
                    if generation is None or render_revision is None:
                        raise ValueError("overlay clear revisions are required with a session")
                    cursor = (int(generation), int(render_revision))
                    if min(cursor) < 0:
                        raise ValueError("overlay clear revisions are invalid")
                    if session_id in self._retired_sessions:
                        self._state, self._reason = "stale", "retired_session_clear_ignored"
                        return self.status()
                    # A clear from a new, non-retired session starts a new
                    # lifecycle.  Only delayed clears from sessions that were
                    # explicitly retired are ignored; otherwise a legitimate
                    # navigation/refresh could never hide the previous frame.
                    if self._active_session_id and self._active_session_id != session_id:
                        self._retire_locked(self._active_session_id)
                        self._active_session_id = session_id
                    previous = self._last_update_by_session.get(session_id)
                    if previous is not None and cursor < previous:
                        self._state, self._reason = "stale", "stale_clear_ignored"
                        return self.status()
                    self._active_session_id = session_id
                    self._last_update_by_session[session_id] = cursor
                self._state, self._reason = "hidden", str(reason)[:120]
            self._native.hide()
            return self.status()

    def close(self) -> None:
        self._native.stop()
        with self._lock:
            self._state, self._reason = "stopped", "closed"


# Convenient short alias for callers that do not need the longer class name.
NativeOverlay = NativeOverlayController


__all__ = [
    "WDA_EXCLUDEFROMCAPTURE",
    "NativeOverlay",
    "NativeOverlayController",
    "OverlayArrow",
    "OverlaySnapshot",
    "PrivateOverlayController",
    "is_overlay_update_newer",
    "normalize_arrows",
]
