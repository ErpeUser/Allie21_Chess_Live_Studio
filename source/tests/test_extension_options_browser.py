"""Run the actual options page under the real MV3 script CSP in Chromium."""
from __future__ import annotations

import functools
import os
import shutil
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class OptionsHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Content-Security-Policy', "script-src 'self'; object-src 'self'")
        super().end_headers()

    def log_message(self, *_args):
        pass


class ExtensionOptionsBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
            cls.playwright = sync_playwright().start()
            executable = os.environ.get('ALLIE_BROWSER_EXECUTABLE') or shutil.which('chromium')
            cls.browser = cls.playwright.chromium.launch(
                headless=True, executable_path=executable, args=['--no-sandbox'])
        except Exception as exc:
            if hasattr(cls, 'playwright'):
                cls.playwright.stop()
            if os.environ.get('ALLIE_REQUIRE_BROWSER_TESTS') == '1':
                raise RuntimeError('Required Chromium options tests unavailable') from exc
            raise unittest.SkipTest('Chromium options tests unavailable') from exc
        handler = functools.partial(OptionsHandler, directory=str(ROOT / 'source/app/browser'))
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/options.html'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.add_init_script('''
          window.__stored = {port: 8741};
          window.__storageError = null;
          window.chrome = window.chrome || {};
          chrome.runtime = {lastError: null};
          chrome.storage = {local: {
            get(defaults, callback) { callback({...defaults, ...window.__stored}); },
            set(values, callback) {
              chrome.runtime.lastError = window.__storageError;
              if (!chrome.runtime.lastError) Object.assign(window.__stored, values);
              callback(); chrome.runtime.lastError = null;
            }
          }};
        ''')
        self.page.goto(self.url)

    def tearDown(self):
        self.page.close()

    def test_saved_port_loads_under_mv3_csp(self):
        self.assertEqual(self.page.locator('#port').input_value(), '8741')

    def test_save_uses_input_and_confirms_only_after_storage_succeeds(self):
        self.page.locator('#port').fill('18765')
        self.page.locator('#save').click()
        self.assertEqual(self.page.evaluate('window.__stored.port'), 18765)
        self.assertIn('18765', self.page.locator('#status').inner_text())

    def test_invalid_port_does_not_overwrite_saved_configuration(self):
        self.page.locator('#port').fill('80')
        self.page.locator('#save').click()
        self.assertEqual(self.page.evaluate('window.__stored.port'), 8741)
        self.assertIn('1024', self.page.locator('#status').inner_text())

    def test_storage_failure_does_not_report_success(self):
        self.page.evaluate("window.__storageError = {message: 'storage unavailable'}")
        self.page.locator('#port').fill('18765')
        self.page.locator('#save').click()
        self.assertEqual(self.page.evaluate('window.__stored.port'), 8741)
        self.assertNotIn('Gespeichert.', self.page.locator('#status').inner_text())
        self.assertTrue(self.page.locator('#status').inner_text())


if __name__ == '__main__':
    unittest.main()
