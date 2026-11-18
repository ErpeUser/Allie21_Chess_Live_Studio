"""A delayed message expiry must never restore a hidden native frame."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import native_overlay as overlay
from test_native_overlay import FakeWin32


class PendingTimer:
    def __init__(self, _delay, callback, args=()):
        self.callback = callback
        self.args = args
        self.cancelled = False

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True

    def fire_queued_callback(self):
        # Timer.cancel cannot stop a callback that has already started and is
        # waiting for the renderer lock. Exercise the actual token guard too.
        self.callback(*self.args)


def frame(revision=1, **changes):
    payload = {
        'session_id': 'synthetic-expiry', 'generation': 1,
        'render_revision': revision, 'mode': 'private',
        'geometry': {
            'screen_board': {'left': 100, 'top': 100, 'width': 640, 'height': 640},
            'orientation': 'white',
        },
        'arrows': [{'uci': 'e2e4'}], 'messages': ['Synthetic training message'],
    }
    payload.update(changes)
    return payload


class NativeMessageTimerTests(unittest.TestCase):
    def controller(self):
        controller = overlay.PrivateOverlayController()
        controller._native = overlay.NativeOverlayController(api=FakeWin32())
        self.addCleanup(controller.close)
        return controller

    def test_queued_expiry_cannot_restore_a_newer_hidden_frame(self):
        cases = {
            'not visible': lambda controller: controller.update(frame(2, visible=False)),
            'missing geometry': lambda controller: controller.update(frame(2, geometry={})),
            'wrong payload mode': lambda controller: controller.update(frame(2, mode='normal')),
            'normal mode': lambda controller: controller.set_mode('normal'),
            'clear': lambda controller: controller.clear('synthetic-clear'),
            'reset': lambda controller: controller.reset('synthetic-reset'),
        }
        for name, hide in cases.items():
            with self.subTest(boundary=name), patch.object(overlay, 'Timer', PendingTimer):
                controller = self.controller()
                self.assertTrue(controller.update(frame())['visible'])
                timer = controller._message_timer
                hide(controller)
                self.assertFalse(controller.status()['visible'])
                timer.fire_queued_callback()
                self.assertFalse(controller.status()['visible'], name)
                self.assertEqual(controller.status()['arrow_count'], 0)
                controller.close()

    def test_ignored_stale_hide_does_not_cancel_current_message_expiry(self):
        with patch.object(overlay, 'Timer', PendingTimer):
            controller = self.controller()
            self.assertTrue(controller.update(frame(2))['visible'])
            timer = controller._message_timer
            controller.update(frame(1, visible=False))
            self.assertTrue(controller.status()['visible'])
            timer.fire_queued_callback()
            self.assertTrue(controller.status()['visible'])
            self.assertEqual(controller.status()['arrow_count'], 1)
            self.assertFalse(controller.status()['has_message'])


if __name__ == '__main__':
    unittest.main()
