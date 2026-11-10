"""Installer uses real ZIPs/files; only the external download is simulated."""
from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import download_stockfish as installer


def archive(executable=b'verified-engine', second=False):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr('stockfish/stockfish.exe', executable)
        if second:
            output.writestr('other/stockfish.exe', executable)
    return data.getvalue()


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.dest = Path(self.directory.name)
        self.target = self.dest / 'stockfish.exe'
        self.target.write_bytes(b'old-engine')

    def install(self, zipped, expected_exe, response=None):
        with (patch.object(installer, 'DEST', self.dest),
              patch.object(installer.os, 'name', 'nt'),
              patch.object(installer, 'EXPECTED_SHA256', hashlib.sha256(zipped).hexdigest()),
              patch.object(installer, 'EXPECTED_EXE_SHA256', hashlib.sha256(expected_exe).hexdigest()),
              patch.object(installer, 'urlopen', return_value=response or io.BytesIO(zipped))):
            return installer.download()

    def test_wrong_extracted_hash_never_replaces_installed_executable(self):
        with self.assertRaises(RuntimeError):
            self.install(archive(b'wrong-engine'), b'verified-engine')
        self.assertEqual(self.target.read_bytes(), b'old-engine')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['stockfish.exe'])

    def test_valid_archive_installs_verified_executable_atomically(self):
        self.assertTrue(self.install(archive(), b'verified-engine'))
        self.assertEqual(self.target.read_bytes(), b'verified-engine')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['stockfish.exe'])

    def test_verified_installed_executable_avoids_network(self):
        self.target.write_bytes(b'verified-engine')
        with (patch.object(installer, 'DEST', self.dest),
              patch.object(installer.os, 'name', 'nt'),
              patch.object(installer, 'EXPECTED_EXE_SHA256', hashlib.sha256(b'verified-engine').hexdigest()),
              patch.object(installer, 'urlopen', side_effect=AssertionError('network is unnecessary'))):
            self.assertTrue(installer.download())

    def test_multiple_executables_are_rejected_instead_of_guessing(self):
        with self.assertRaises(RuntimeError):
            self.install(archive(second=True), b'verified-engine')
        self.assertEqual(self.target.read_bytes(), b'old-engine')

    def test_download_is_streamed_in_small_chunks(self):
        class ChunkResponse(io.BytesIO):
            def read(self, size=-1):
                if size < 0 or size > 1024 * 1024:
                    raise AssertionError('unbounded archive buffering')
                return super().read(size)
        zipped = archive()
        self.assertTrue(self.install(zipped, b'verified-engine', ChunkResponse(zipped)))

    def test_corrupt_archive_preserves_previous_executable(self):
        with self.assertRaises((RuntimeError, zipfile.BadZipFile)):
            self.install(b'not a zip', b'verified-engine')
        self.assertEqual(self.target.read_bytes(), b'old-engine')

    def test_network_failure_keeps_previous_file_and_cleans_temporary_data(self):
        class BrokenResponse(io.BytesIO):
            def read(self, size=-1):
                raise OSError('network interrupted')
        zipped = archive()
        with self.assertRaises(OSError):
            self.install(zipped, b'verified-engine', BrokenResponse(zipped))
        self.assertEqual(self.target.read_bytes(), b'old-engine')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['stockfish.exe'])

    def test_extraction_size_limit_keeps_previous_file(self):
        with patch.object(installer, 'MAX_EXE_SIZE', 4), self.assertRaises(RuntimeError):
            self.install(archive(), b'verified-engine')
        self.assertEqual(self.target.read_bytes(), b'old-engine')
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['stockfish.exe'])

    @unittest.skipIf(sys.platform == 'win32', 'unsupported-platform exit is tested on non-Windows')
    def test_unsupported_platform_does_not_exit_success(self):
        result = subprocess.run([sys.executable, installer.__file__], capture_output=True, timeout=5, check=False)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
