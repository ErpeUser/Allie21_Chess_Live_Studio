import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('smoke', Path(__file__).resolve().parents[1] / 'tools/release_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeShutdownTests(unittest.TestCase):
    def test_manifest_rejects_unlisted_files_after_hashes_match(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            expected = bundle / 'app' / 'ok.txt'
            expected.parent.mkdir(parents=True)
            expected.write_bytes(b'legitimate')
            sha = hashlib.sha256(b'legitimate').hexdigest()
            (bundle / 'SHA256SUMS.txt').write_text(f'{sha}  app/ok.txt\n', encoding='utf-8')
            smoke.verify_manifest(bundle)
            (bundle / 'app' / 'unlisted.exe').write_bytes(b'foreign binary')
            with self.assertRaisesRegex(RuntimeError, 'nicht im Manifest|not in manifest|Unlisted'):
                smoke.verify_manifest(bundle)

    def test_manifest_rejects_extra_file_before_hashing_large_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            expected = bundle / 'runtime' / 'large.bin'
            expected.parent.mkdir(parents=True)
            expected.write_bytes(b'file listed in manifest')
            digest = hashlib.sha256(b'file listed in manifest').hexdigest()
            (bundle / 'SHA256SUMS.txt').write_text(
                f'{digest}  runtime/large.bin\n', encoding='utf-8')
            (bundle / 'runtime' / 'unexpected.pyc').write_bytes(b'extra bytecode')
            with (patch.object(smoke.hashlib, 'file_digest',
                               side_effect=AssertionError('hashed too soon')),
                  self.assertRaisesRegex(RuntimeError, 'nicht im Manifest')):
                smoke.verify_manifest(bundle)

    def test_manifest_rejects_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            file = bundle / 'app' / 'ok.txt'
            file.parent.mkdir(parents=True)
            file.write_bytes(b'known')
            row = f'{hashlib.sha256(b"known").hexdigest()}  app/ok.txt\n'
            (bundle / 'SHA256SUMS.txt').write_text(row * 2, encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'Doppelter|doppelt|duplicate'):
                smoke.verify_manifest(bundle)

    def test_manifest_hashes_files_without_loading_entire_payload_to_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            file = bundle / 'app' / 'ok.bin'
            file.parent.mkdir(parents=True)
            file.write_bytes(b'streamed data')
            row = f'{hashlib.sha256(b"streamed data").hexdigest()}  app/ok.bin\n'
            (bundle / 'SHA256SUMS.txt').write_text(row, encoding='utf-8')
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read')):
                smoke.verify_manifest(bundle)

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

    def test_release_rejects_regenerable_stdlib_and_vendor_tests(self):
        self.assertTrue(hasattr(smoke, 'verify_runtime_hygiene'),
                        'Release-Smoketest muss ungenutzte Testartefakte pruefen')
        with tempfile.TemporaryDirectory() as work:
            bundle = Path(work)
            candidates = (
                bundle / 'runtime' / 'Lib' / 'test',
                bundle / 'runtime' / 'Lib' / 'idlelib',
                bundle / 'runtime' / 'Lib' / 'site-packages' / 'numpy' / '_core' / 'tests',
                bundle / 'app' / 'backend' / '__pycache__',
            )
            for candidate in candidates:
                with self.subTest(candidate=candidate):
                    candidate.mkdir(parents=True)
                    with self.assertRaises(RuntimeError):
                        smoke.verify_runtime_hygiene(bundle)
                    candidate.rmdir()
            (bundle / 'runtime' / 'Lib').mkdir(parents=True, exist_ok=True)
            smoke.verify_runtime_hygiene(bundle)

    def test_release_rejects_bytecode_outside_cache_directories(self):
        self.assertTrue(hasattr(smoke, 'verify_runtime_hygiene'),
                        'Release-Smoketest muss vorkompilierten Cache pruefen')
        with tempfile.TemporaryDirectory() as work:
            bundle = Path(work)
            code = bundle / 'runtime' / 'Lib' / 'site-packages' / 'sample.pyc'
            code.parent.mkdir(parents=True)
            code.write_bytes(b'bytecode')
            with self.assertRaises(RuntimeError):
                smoke.verify_runtime_hygiene(bundle)
