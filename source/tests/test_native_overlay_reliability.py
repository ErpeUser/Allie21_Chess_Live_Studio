"""Regressions for Win64 ABI, screen/client geometry and native resource ownership."""
from __future__ import annotations

import ctypes
import sys
import threading
import unittest
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import native_overlay as overlay
from test_native_overlay import FakeWin32


class Function:
    def __init__(self, result=1):
        self.argtypes = None
        self.restype = ctypes.c_int
        self.result = result
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.result


class Library:
    def __getattr__(self, name):
        value = Function()
        setattr(self, name, value)
        return value


class NativeReliabilityTests(unittest.TestCase):
    def test_native_message_expires_without_removing_arrows(self):
        class FakeTimer:
            instances: ClassVar[list[object]] = []

            def __init__(self, _delay, callback, args=()):
                self.callback = callback
                self.args = args
                self.cancelled = False
                type(self).instances.append(self)

            def start(self):
                return None

            def cancel(self):
                self.cancelled = True

            def fire(self):
                if not self.cancelled:
                    self.callback(*self.args)

        private = overlay.PrivateOverlayController()
        private._native = overlay.NativeOverlayController(api=FakeWin32())
        original_timer = overlay.Timer
        overlay.Timer = FakeTimer
        try:
            private.update({
                'session_id': 'expiry', 'generation': 1, 'render_revision': 1,
                'mode': 'private', 'geometry': {
                    'screen_board': {'left': 200, 'top': 100, 'width': 640, 'height': 640},
                    'orientation': 'white',
                }, 'arrows': [{'uci': 'e2e4'}], 'messages': ['Develop your pieces.'],
            })
            timer = FakeTimer.instances[-1]
            self.assertTrue(private._native.snapshot.message)
            timer.fire()
            self.assertEqual(private._native.snapshot.message, '')
            self.assertEqual(len(private._native.snapshot.arrows), 1)
        finally:
            overlay.Timer = original_timer
            private.close()

    def test_all_handle_apis_have_explicit_pointer_width_signatures(self):
        api = overlay._Win32.__new__(overlay._Win32)
        api.user32, api.gdi32, api.kernel32 = Library(), Library(), Library()
        api._configure()
        returns = {
            ("user32", "LoadCursorW"): overlay.HCURSOR,
            ("user32", "BeginPaint"): wintypes.HDC,
            ("user32", "DispatchMessageW"): ctypes.c_ssize_t,
            ("gdi32", "SelectObject"): wintypes.HGDIOBJ,
        }
        for (library, name), expected in returns.items():
            with self.subTest(name=name):
                function = getattr(getattr(api, library), name)
                self.assertIs(function.restype, expected)
                self.assertIsNotNone(function.argtypes)
        for name in ("SetLayeredWindowAttributes", "DestroyWindow", "ShowWindow",
                     "SetWindowPos", "PostMessageW", "GetMessageW", "TranslateMessage",
                     "EndPaint", "InvalidateRect", "DrawTextW", "RegisterClassExW"):
            with self.subTest(name=name):
                self.assertIsNotNone(getattr(api.user32, name).argtypes)
        self.assertIs(api.user32.SetLayeredWindowAttributes.argtypes[0], wintypes.HWND)
        self.assertEqual(api.kernel32.GetModuleHandleW.argtypes, (wintypes.LPCWSTR,))

    def test_show_window_forces_visibility_when_windows_keeps_popup_hidden(self):
        api = overlay._Win32.__new__(overlay._Win32)
        api.user32 = Library()
        class Visibility:
            def __init__(self):
                self.calls = []
            def __call__(self, hwnd):
                self.calls.append(hwnd)
                return 1
        api.user32.IsWindowVisible = Visibility()
        api.user32.ShowWindow.result = 1
        api.user32.SetWindowPos.result = 1
        api.show_window(42, overlay.SW_SHOWNOACTIVATE)
        self.assertEqual(len(api.user32.SetWindowPos.calls), 1)
        self.assertEqual(api.user32.SetWindowPos.calls[0][0], 42)
        self.assertEqual(api.user32.SetWindowPos.calls[0][-1], overlay.SWP_NOSIZE | overlay.SWP_NOMOVE | overlay.SWP_NOACTIVATE | overlay.SWP_SHOWWINDOW)

    def test_show_window_reasserts_topmost_when_popup_is_already_visible(self):
        api = overlay._Win32.__new__(overlay._Win32)
        api.user32 = Library()
        api.user32.IsWindowVisible.result = 1
        api.show_window(42, overlay.SW_SHOWNOACTIVATE)
        self.assertEqual(len(api.user32.SetWindowPos.calls), 1)
        self.assertEqual(api.user32.SetWindowPos.calls[0][1], overlay.HWND_TOPMOST)

    def test_topmost_reasserts_window_order(self):
        api = overlay._Win32.__new__(overlay._Win32)
        api.user32 = Library()
        api.user32.SetWindowPos.result = 1
        api.keep_topmost(42)
        self.assertEqual(api.user32.SetWindowPos.calls[0][1], overlay.HWND_TOPMOST)

    def test_message_structure_contains_reserved_private_field(self):
        self.assertEqual(overlay._MSG._fields_[-1], ("lPrivate", wintypes.DWORD))

    def test_native_coordinates_are_relative_to_window_not_screen(self):
        for left, top, orientation, expected in (
            (900, 300, "white", (40.0, 600.0)),
            (-900, -300, "white", (40.0, 600.0)),
            (900, 300, "black", (600.0, 40.0)),
        ):
            with self.subTest(left=left, orientation=orientation):
                private = overlay.PrivateOverlayController()
                private._native = overlay.NativeOverlayController(api=FakeWin32())
                try:
                    result = private.update({
                        "session_id": "geometry", "generation": 1, "render_revision": 1,
                        "mode": "private", "geometry": {
                            "screen_board": {"left": left, "top": top, "width": 640, "height": 640},
                            "orientation": orientation,
                        }, "arrows": [{"uci": "a1a2", "color": "#2f80ed"}],
                    })
                    self.assertTrue(result["available"])
                    bounds = private._native.snapshot.bounds
                    self.assertEqual(bounds[:2], (left, top))
                    self.assertGreaterEqual(bounds[2], 640)
                    self.assertGreaterEqual(bounds[3], 640)
                    self.assertEqual(private._native.snapshot.arrows[0].start, expected)
                finally:
                    private.close()

    def test_message_panel_is_outside_chessboard(self):
        private = overlay.PrivateOverlayController()
        fake = FakeWin32()
        fake.get_work_area = lambda *_: (0, 0, 1920, 1080)
        private._native = overlay.NativeOverlayController(api=fake)
        try:
            private.update({
                "session_id": "message", "generation": 1, "render_revision": 1,
                "mode": "private", "geometry": {
                    "screen_board": {"left": 900, "top": 300, "width": 640, "height": 640},
                    "orientation": "white",
                }, "arrows": [{"uci": "e2e4"}], "messages": ["Develop your pieces."],
            })
            snapshot = private._native.snapshot
            self.assertIsNotNone(getattr(snapshot, "message_rect", None))
            x, y, width, height = snapshot.bounds
            mx, my, mw, mh = snapshot.message_rect
            board_left, board_top = 900 - x, 300 - y
            overlaps = (mx < board_left + 640 and mx + mw > board_left
                        and my < board_top + 640 and my + mh > board_top)
            self.assertFalse(overlaps)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + width, 1920)
            self.assertLessEqual(y + height, 1080)
        finally:
            private.close()

    def test_native_hud_adds_compact_chip_without_plan_messages(self):
        private = overlay.PrivateOverlayController()
        fake = FakeWin32()
        private._native = overlay.NativeOverlayController(api=fake)
        try:
            private.update({
                "session_id": "chip", "generation": 1, "render_revision": 1,
                "mode": "private", "geometry": {
                    "screen_board": {"left": 200, "top": 100, "width": 640, "height": 640},
                    "orientation": "white",
                }, "arrows": [{"uci": "e2e4"}],
            })
            snapshot = private._native.snapshot
            self.assertTrue(snapshot.message.startswith("Allie · Analyse"))
            self.assertIsNotNone(snapshot.message_rect)
        finally:
            private.close()

    def test_paint_restores_selected_objects_before_deleting_them(self):
        calls = []
        selected = {"pen": 11, "font": 12}
        def select(_hdc, value):
            kind = "pen" if value in (11, 21) else "font"
            old = selected[kind]
            selected[kind] = value
            calls.append(("select", value))
            return old
        def delete(value):
            self.assertNotIn(value, selected.values(), "GDI object deleted while still selected")
            calls.append(("delete", value))
        api = SimpleNamespace(
            begin_paint=lambda _: (99, SimpleNamespace(rcPaint=None)),
            fill_color_key=lambda *_: None,
            create_pen=lambda *_: 21,
            create_font=lambda *_: 22,
            select_object=select,
            draw_arrow=lambda *_: None,
            draw_text=lambda *_: None,
            delete_object=delete,
            end_paint=lambda *_: calls.append(("end",)),
        )
        controller = overlay.NativeOverlayController(api=api)
        controller._snapshot = overlay.OverlaySnapshot((overlay.OverlayArrow((0, 0), (10, 10)),), "test")
        controller._paint(42)
        self.assertEqual(selected, {"pen": 11, "font": 12})
        self.assertIn(("delete", 21), calls)
        self.assertIn(("delete", 22), calls)
        self.assertEqual(calls[-1], ("end",))

    def test_arrowhead_uses_requested_brush_and_restores_previous_brush(self):
        api = overlay._Win32.__new__(overlay._Win32)
        api.gdi32 = Library()
        api.gdi32.CreateSolidBrush.result = 77
        api.gdi32.SelectObject.result = 88
        api.draw_arrow(99, (0, 0), (20, 20), 5, 0x00ED802F)
        self.assertEqual(api.gdi32.CreateSolidBrush.calls, [(0x00ED802F,)])
        self.assertEqual(api.gdi32.SelectObject.calls, [(99, 77), (99, 88)])
        self.assertEqual(api.gdi32.DeleteObject.calls, [(77,)])

    def test_outside_message_has_a_bounded_background_brush(self):
        api = overlay._Win32.__new__(overlay._Win32)
        api.gdi32, api.user32 = Library(), Library()
        api.gdi32.CreateSolidBrush.result = 77
        api.draw_text(99, "Plan", (650, 8, 300, 120))
        self.assertEqual(len(api.user32.FillRect.calls), 1)
        self.assertEqual(api.gdi32.DeleteObject.calls, [(77,)])
        self.assertEqual(len(api.user32.DrawTextW.calls), 1)

    def test_window_class_is_released_before_controller_is_restarted(self):
        class ClassTrackingWin32(FakeWin32):
            def destroy_window(self, hwnd):
                self.calls.append(("destroy_window", hwnd))
            def unregister_class(self, name):
                self.calls.append(("unregister_class", name))
        fake = ClassTrackingWin32()
        controller = overlay.NativeOverlayController(api=fake)
        self.assertTrue(controller.start())
        controller.stop()
        self.assertIn(("unregister_class", controller._class_name), fake.calls)
        self.assertFalse(controller._start_result)
        self.assertTrue(controller.start())
        controller.stop()
        self.assertEqual(sum(item[0] == "unregister_class" for item in fake.calls), 2)

    def test_payload_visibility_is_fail_closed_for_native_hud(self):
        private = overlay.PrivateOverlayController()
        private._native = overlay.NativeOverlayController(api=FakeWin32())
        try:
            result = private.update({
                'session_id': 'visibility', 'generation': 1, 'render_revision': 1,
                'mode': 'private', 'visible': False,
                'geometry': {'screen_board': {'left': 100, 'top': 100, 'width': 640, 'height': 640}, 'orientation': 'white'},
                'arrows': [{'uci': 'e2e4'}],
            })
            self.assertFalse(result['visible'])
            self.assertEqual(result['reason'], 'payload_not_visible')
        finally:
            private.close()

    def test_reset_retires_session_and_hides_delayed_overlay_updates(self):
        private = overlay.PrivateOverlayController()
        private._native = overlay.NativeOverlayController(api=FakeWin32())
        try:
            private.update({
                'session_id': 'reset-session', 'generation': 1, 'render_revision': 1,
                'mode': 'private', 'geometry': {
                    'screen_board': {'left': 100, 'top': 100, 'width': 640, 'height': 640},
                    'orientation': 'white',
                }, 'arrows': [{'uci': 'e2e4'}],
            })
            self.assertEqual(private.status()['state'], 'active')
            private.reset('session-stop')
            self.assertEqual(private.status()['state'], 'hidden')
            stale = private.update({
                'session_id': 'reset-session', 'generation': 2, 'render_revision': 2,
                'mode': 'private', 'geometry': {
                    'screen_board': {'left': 100, 'top': 100, 'width': 640, 'height': 640},
                    'orientation': 'white',
                }, 'arrows': [{'uci': 'e2e4'}],
            })
            self.assertEqual(stale['reason'], 'retired_session_ignored')
            self.assertFalse(stale['visible'])
        finally:
            private.close()
    def test_status_does_not_report_active_after_native_window_dies(self):
        private = overlay.PrivateOverlayController()
        private._state = "active"
        private._reason = "capture_exclusion_verified"
        self.assertNotEqual(private.status()["state"], "active")
        self.assertFalse(private.status()["available"])

    def test_stop_timeout_does_not_allow_second_window_thread(self):
        release = threading.Event()
        class StubbornWin32(FakeWin32):
            def message_loop(self, _controller):
                release.wait(2)
        fake = StubbornWin32()
        controller = overlay.NativeOverlayController(api=fake)
        try:
            self.assertTrue(controller.start())
            thread = controller._thread
            controller.stop(timeout=0.05)
            self.assertIs(controller._thread, thread)
            self.assertFalse(controller.start(timeout=0.05))
            self.assertEqual(sum(call[0] == "create_window" for call in fake.calls), 1)
        finally:
            release.set()
            if controller._thread:
                controller._thread.join(2)
            controller.stop()


if __name__ == "__main__":
    unittest.main()
