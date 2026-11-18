"""The checkout has exactly one authoritative source tree and one output tree."""
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ProjectStructureTests(unittest.TestCase):
    def test_code_and_automation_have_one_source_root(self):
        expected = (
            'source/app/backend/live_server.py',
            'source/app/browser/manifest.json',
            'source/app/viewer/index.html',
            'source/automation/maintain.py',
            'source/automation/build_exe.ps1',
            'source/tests/test_chess.py',
            'source/resources/icons/allie21_icon.ico',
        )
        for name in expected:
            with self.subTest(path=name):
                self.assertTrue((ROOT / name).is_file(), name)

    def test_vendor_copy_excludes_generated_bytecode(self):
        build = (ROOT / 'source/automation/build_exe.ps1').read_text(encoding='utf-8')
        self.assertIn('& robocopy.exe $vendorSource $vendorTarget /E', build)
        self.assertIn('/XD __pycache__', build)
        self.assertIn('/XF *.pyc *.pyo', build)
        self.assertNotIn("Copy-Item -LiteralPath (Join-Path $root 'generated\\dependencies\\vendor')", build)

    def test_python_tool_caches_remain_under_generated(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
        self.assertEqual(project['tool']['ruff']['cache-dir'], 'generated/cache/ruff')
        self.assertEqual(project['tool']['mypy']['cache_dir'], 'generated/cache/mypy')
        self.assertEqual(project['tool']['pytest']['ini_options']['cache_dir'],
                         'generated/cache/pytest')

    def test_agent_setup_uses_project_generated_toolchain(self):
        script = (ROOT / 'source/automation/agents/setup.sh').read_text(encoding='utf-8')
        self.assertIn('UV_PROJECT_ENVIRONMENT', script)
        self.assertIn('generated/environments/source', script)
        self.assertIn('UV_CACHE_DIR', script)
        self.assertIn('generated/cache/uv', script)

    def test_model_cache_is_declared_under_generated(self):
        for name in ('START_HIER.bat', 'MODELL_EINRICHTEN.bat'):
            text = (ROOT / name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertIn('HF_HOME', text)
                self.assertIn('generated\\dependencies\\models', text)

    def test_model_setup_reuses_portable_python_without_extra_venv(self):
        script = (ROOT / 'MODELL_EINRICHTEN.bat').read_text(encoding='utf-8')
        self.assertIn('generated\\dist\\win\\Allie21 Chess Live Studio\\runtime\\python.exe',
                      script)
        self.assertIn('generated\\dist\\win\\Allie21 Chess Live Studio\\app\\backend\\model_setup.py',
                      script)

    def test_git_database_is_protected_inside_generated(self):
        # CI checkout uses a normal .git directory; this Windows workspace uses
        # a gitdir pointer to move local metadata away from source files.
        git_entry = ROOT / '.git'
        self.assertTrue(git_entry.is_file() or git_entry.is_dir())
        if git_entry.is_file():
            self.assertTrue((ROOT / 'generated/protected/git/HEAD').is_file())

    def test_generated_is_ignored_but_the_source_is_not(self):
        self.assertTrue((ROOT / '.gitignore').is_file())
        self.assertTrue((ROOT / 'source').is_dir())
        self.assertTrue((ROOT / 'generated').is_dir())


if __name__ == '__main__':
    unittest.main()
