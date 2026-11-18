"""Regression checks for the canonical Git policy gate."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_repository_policy", ROOT / "source/automation/check_repository_policy.py"
)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class RepositoryPolicyTests(unittest.TestCase):
    def test_allowed_source_and_vendor(self):
        for path in ("AGENTS.md", ".github/workflows/ci.yml",
                     "source/app/backend/live_server.py", "source/tests/test_chess.py",
                     "source/automation/maintain.py",
                     "generated/dependencies/vendor/allie_model/model.py"):
            with self.subTest(path=path):
                self.assertTrue(policy.allowed_path(path))

    def test_untracked_output_and_nested_repository_rejected(self):
        for path in ("generated/protected/git/HEAD", "generated/dist/file.exe",
                     "generated/dependencies/models/weights.safetensors",
                     "source/app/backend/__pycache__/x.pyc", "source/node_modules/x.js",
                     "source/app/browser/allie-build.json", ".github/workflows/extra.yml",
                     "source/app/other/extra.py", "source/app/backend/.git/config",
                     "nested/.git/config"):
            with self.subTest(path=path):
                self.assertFalse(policy.allowed_path(path))

    def test_index_rejects_symlinks_submodules_conflicts(self):
        records = (b"120000 " + b"a"*40 + b" 0\tsource/app/backend/link.py\0"
                   + b"160000 " + b"b"*40 + b" 0\tsource/app/backend/submodule\0"
                   + b"100644 " + b"c"*40 + b" 2\tsource/tests/conflict.py\0")
        errors = policy.validate_index(records)
        self.assertEqual(len(errors), 3)

    def test_local_index_and_ignore_contract(self):
        self.assertEqual(policy.main(), 0)


if __name__ == "__main__":
    unittest.main()
