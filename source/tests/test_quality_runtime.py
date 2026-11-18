"""Exercise the actual PowerShell runtime selector on isolated Windows trees."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = ROOT / 'source/automation' / 'find_quality_sitepackages.ps1'


@unittest.skipUnless(sys.platform == 'win32', 'PowerShell runtime selection runs on Windows')
class QualityRuntimeSelectionTests(unittest.TestCase):
    def run_selector(self, root: Path, state: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
             str(SELECTOR), '-Root', str(root), '-StateRoot', str(state)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            check=False, timeout=15,
        )

    def test_prefers_source_env_then_falls_back_to_release_without_installing_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            state = Path(folder) / 'state'
            source = state / 'environments' / 'source' / 'Lib' / 'site-packages'
            release = (root / 'generated' / 'dist' / 'win' / 'Allie21 Chess Live Studio'
                       / 'runtime' / 'Lib' / 'site-packages')
            source.mkdir(parents=True)
            release.mkdir(parents=True)
            prefer = self.run_selector(root, state)
            self.assertEqual(prefer.returncode, 0, prefer.stderr)
            self.assertEqual(prefer.stdout.strip().casefold(), str(source.resolve()).casefold())

            source.rmdir()
            fallback = self.run_selector(root, state)
            self.assertEqual(fallback.returncode, 0, fallback.stderr)
            self.assertEqual(fallback.stdout.strip().casefold(), str(release.resolve()).casefold())

            release.rmdir()
            missing = self.run_selector(root, state)
            self.assertNotEqual(missing.returncode, 0, 'Missing dependencies must be a hard error')


if __name__ == '__main__':
    unittest.main()
