"""Cross-platform tests for the optional ctypes-only native overlay."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from native_overlay import (
    HTTRANSPARENT,
    WDA_EXCLUDEFROMCAPTURE,
    WDA_NONE,
    NativeOverlayController,
    OverlayArrow,
    PrivateOverlayController,
    is_overlay_update_newer,
    normalize_arrows,
)


class FakeWin32:
    def __init__(self, *, set_affinity=True, affinity=WDA_EXCLUDEFROMCAPTURE):
        self.set_affinity_result = set_affinity
        self.affinity = affinity
        self.calls = []

    def create_window(self, _controller):
        self.calls.append(("create_window",))
        return 42

    def set_window_display_affinity(self, hwnd, value):
        self.calls.append(("set_affinity", hwnd, value))
        return self.set_affinity_result

    def get_window_display_affinity(self, hwnd):
        self.calls.append(("get_affinity", hwnd))
        return self.affinity

    def show_window(self, hwnd, command):
        self.calls.append(("show_window", hwnd, command))

    def move_window(self, hwnd, x, y, width, height):
        self.calls.append(("move_window", hwnd, x, y, width, height))

    def post_message(self, hwnd, message, wparam, lparam):
        self.calls.append(("post_message", hwnd, message, wparam, lparam))

    def message_loop(self, controller):
        controller._stop.wait(1.0)


class NativeOverlayTests(unittest.TestCase):
    def test_overlay_update_order_is_monotonic_per_session(self):
        self.assertTrue(is_overlay_update_newer('s', 2, 1, {'s': (1, 99)}))
        self.assertFalse(is_overlay_update_newer('s', 1, 100, {'s': (2, 1)}))
        self.assertFalse(is_overlay_update_newer('s', 2, 1, {'s': (2, 1)}))
        self.assertTrue(is_overlay_update_newer('other', 0, 1, {'s': (99, 9)}))
    def test_normalize_arrows_accepts_mapping_and_caps_payload(self):
        arrows = normalize_arrows(
            {"from": (1, 2), "to": (30, 40), "color": "#2f80ed", "width": 7}
            for _ in range(40)
        )
        self.assertEqual(len(arrows), 32)
        self.assertEqual(arrows[0], OverlayArrow((1.0, 2.0), (30.0, 40.0), "#2f80ed", 7))

    def test_normalize_arrows_rejects_non_finite_or_invalid_colour(self):
        with self.assertRaises(ValueError):
            normalize_arrows([{"start": (float("nan"), 2), "end": (3, 4)}])
        with self.assertRaises(ValueError):
            normalize_arrows([{"start": (1, 2), "end": (3, 4), "color": "red"}])

    def test_affinity_must_be_set_and_read_back_exactly(self):
        fake = FakeWin32()
        controller = NativeOverlayController(api=fake)
        self.assertTrue(controller._verify_capture_exclusion(42))
        self.assertIn(("set_affinity", 42, WDA_EXCLUDEFROMCAPTURE), fake.calls)

        fake_bad = FakeWin32(affinity=0)
        self.assertFalse(NativeOverlayController(api=fake_bad)._verify_capture_exclusion(42))

    def test_share_policy_disables_capture_exclusion_and_verifies_none(self):
        fake = FakeWin32(affinity=WDA_NONE)
        controller = NativeOverlayController(api=fake)
        self.assertTrue(controller.start(capture_exclusion=False))
        self.assertTrue(controller.available)
        self.assertFalse(controller.capture_excluded)
        self.assertIn(("set_affinity", 42, WDA_NONE), fake.calls)
        controller.stop()

    def test_private_router_reports_distinct_share_status(self):
        fake = FakeWin32(affinity=WDA_NONE)
        router = PrivateOverlayController()
        router._native = NativeOverlayController(api=fake)
        status = router.set_mode("share")
        self.assertEqual(status["mode"], "share")
        self.assertTrue(status["available"])
        self.assertTrue(status["share_visible"])
        self.assertEqual(status["reason"], "share_mode_capture_enabled")
        self.assertIn("Share-Modus", status["status_text"])
        router.close()

    def test_mocked_controller_is_thread_safe_and_renders_only_after_verification(self):
        fake = FakeWin32()
        controller = NativeOverlayController(api=fake)
        self.assertTrue(controller.start())
        self.assertTrue(controller.available)
        self.assertTrue(
            controller.update(
                [{"start": (5, 6), "end": (70, 80), "color": "#16c784"}],
                "Allie bereit",
                bounds=(10, 20, 300, 300),
            )
        )
        self.assertTrue(controller.visible)
        self.assertEqual(controller.snapshot.message, "Allie bereit")
        self.assertIn(("move_window", 42, 10, 20, 300, 300), fake.calls)
        controller.hide()
        self.assertFalse(controller.visible)
        controller.stop()
        self.assertFalse(controller.available)

    def test_affinity_failure_stays_hidden_fail_closed(self):
        fake = FakeWin32(set_affinity=False)
        controller = NativeOverlayController(api=fake)
        self.assertFalse(controller.start())
        self.assertTrue(controller.failed_closed)
        self.assertFalse(controller.visible)
        self.assertFalse(controller.update([], "must not render"))
        # A failed GUI-thread start must not poison the controller forever;
        # after the underlying affinity problem is repaired, a retry is valid.
        fake.set_affinity_result = True
        self.assertTrue(controller.start())
        controller.stop()

    @unittest.skipIf(os.name == "nt", "non-Windows fallback is only tested off Windows")
    def test_non_windows_without_injected_api_fails_closed(self):
        controller = NativeOverlayController()
        self.assertFalse(controller.start())
        self.assertTrue(controller.failed_closed)
        self.assertFalse(controller.update([], "hidden"))

    def test_click_through_constant_is_explicit(self):
        self.assertEqual(HTTRANSPARENT, -1)

    def test_private_controller_rejects_delayed_frames_and_retired_sessions(self):
        private = PrivateOverlayController()
        fake = FakeWin32()
        private._native = NativeOverlayController(api=fake)
        geometry = {'board': {'left': 10, 'top': 20, 'width': 320, 'height': 320}, 'orientation': 'white'}
        first = {'session_id': 's1', 'generation': 1, 'render_revision': 1,
                 'mode': 'private', 'geometry': geometry,
                 'arrows': [{'uci': 'e2e4', 'color': '#16c784'}]}
        self.assertEqual(private.update(first)['state'], 'active')
        snapshot = private._native.snapshot
        delayed = dict(first, arrows=[{'uci': 'a1a2', 'color': '#ef3340'}])
        self.assertEqual(private.update(delayed)['reason'], 'stale_update_ignored')
        self.assertEqual(private._native.snapshot, snapshot)
        newer = dict(first, session_id='s2', generation=0, render_revision=1)
        self.assertEqual(private.update(newer)['state'], 'active')
        current = private._native.snapshot
        retired = dict(first, generation=99, render_revision=99)
        self.assertEqual(private.update(retired)['reason'], 'retired_session_ignored')
        self.assertEqual(private._native.snapshot, current)
        private.close()

    def test_claimed_session_can_resume_after_global_reset(self):
        private = PrivateOverlayController()
        fake = FakeWin32()
        private._native = NativeOverlayController(api=fake)
        geometry = {'board': {'left': 10, 'top': 20, 'width': 320, 'height': 320}, 'orientation': 'white'}
        frame = {'session_id': 'viewer-session', 'generation': 1, 'render_revision': 1,
                 'mode': 'private', 'geometry': geometry, 'arrows': []}
        self.assertEqual(private.update(frame)['state'], 'active')
        private.reset('session-stop')
        self.assertEqual(private.update(frame)['reason'], 'retired_session_ignored')

        private.resume_session('viewer-session')

        resumed = dict(frame, generation=0, render_revision=1)
        self.assertEqual(private.update(resumed)['state'], 'active')
        private.close()

    def test_clear_with_new_session_retires_old_frames(self):
        private = PrivateOverlayController()
        fake = FakeWin32()
        private._native = NativeOverlayController(api=fake)
        geometry = {'board': {'left': 10, 'top': 20, 'width': 320, 'height': 320}, 'orientation': 'white'}
        first = {'session_id': 'old', 'generation': 1, 'render_revision': 2,
                 'mode': 'private', 'geometry': geometry,
                 'arrows': [{'uci': 'e2e4', 'color': '#16c784'}]}
        self.assertEqual(private.update(first)['state'], 'active')
        private.clear('navigation', session_id='new', generation=0, render_revision=1)
        delayed = dict(first, generation=99, render_revision=99)
        self.assertEqual(private.update(delayed)['reason'], 'retired_session_ignored')
        private.close()

    def test_stale_clear_cannot_reactivate_retired_session_or_rewind_cursor(self):
        private = PrivateOverlayController()
        fake = FakeWin32()
        private._native = NativeOverlayController(api=fake)
        geometry = {'board': {'left': 10, 'top': 20, 'width': 320, 'height': 320}, 'orientation': 'white'}
        first = {'session_id': 'first', 'generation': 2, 'render_revision': 4,
                 'mode': 'private', 'geometry': geometry, 'arrows': []}
        second = dict(first, session_id='second', generation=3, render_revision=1)
        self.assertEqual(private.update(first)['state'], 'active')
        self.assertEqual(private.update(second)['state'], 'active')
        private.clear('old-clear', session_id='first', generation=1, render_revision=1)
        self.assertEqual(private.update(first)['reason'], 'retired_session_ignored')
        self.assertEqual(private.update(dict(second, render_revision=0))['reason'], 'stale_update_ignored')
        private.close()

    def test_retired_session_tombstones_survive_more_than_sixty_four_switches(self):
        private = PrivateOverlayController()
        fake = FakeWin32()
        private._native = NativeOverlayController(api=fake)
        geometry = {'board': {'left': 10, 'top': 20, 'width': 320, 'height': 320}, 'orientation': 'white'}
        first = {'session_id': 's0', 'generation': 1, 'render_revision': 1,
                 'mode': 'private', 'geometry': geometry, 'arrows': []}
        self.assertEqual(private.update(first)['state'], 'active')
        for index in range(1, 70):
            current = dict(first, session_id=f's{index}', generation=0, render_revision=index)
            self.assertEqual(private.update(current)['state'], 'active')
        replay = dict(first, generation=999, render_revision=999)
        self.assertEqual(private.update(replay)['reason'], 'retired_session_ignored')
        private.close()

    def test_mode_switch_keeps_old_render_cursor(self):
        private = PrivateOverlayController()
        fake = FakeWin32()
        private._native = NativeOverlayController(api=fake)
        geometry = {'board': {'left': 10, 'top': 20, 'width': 320, 'height': 320}, 'orientation': 'white'}
        frame = {'session_id': 'same', 'generation': 4, 'render_revision': 7,
                 'mode': 'private', 'geometry': geometry, 'arrows': []}
        self.assertEqual(private.update(frame)['state'], 'active')
        private.set_mode('normal')
        private.set_mode('private')
        self.assertEqual(private.update(frame)['reason'], 'stale_update_ignored')
        private.close()


if __name__ == "__main__":
    unittest.main()
