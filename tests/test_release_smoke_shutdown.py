import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('smoke', Path(__file__).resolve().parents[1] / 'tools/release_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeShutdownTests(unittest.TestCase):
    def test_real_sleeping_child_is_stopped_without_blocking_on_stdout(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; print("ready", flush=True); time.sleep(60)'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            smoke.stop_process(process)
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_uncooperative_child_is_killed_after_bounded_wait(self):
        process = Mock()
        process.poll.return_value = None
        process.communicate.side_effect = [subprocess.TimeoutExpired('test', 5), ('diagnostic', None)]
        self.assertEqual(smoke.stop_process(process), 'diagnostic')
        process.kill.assert_called_once()
