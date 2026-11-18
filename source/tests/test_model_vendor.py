import csv
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source/app/backend"))


class ModelVendorTests(unittest.TestCase):
    def test_model_loader_uses_registered_local_code_and_offline_mode(self):
        import allie_local_server

        fake_model = object()
        allie_local_server._model = None
        with patch("transformers.AutoModel.from_pretrained", return_value=fake_model) as load:
            self.assertIs(allie_local_server.get_model(), fake_model)

        kwargs = load.call_args.kwargs
        self.assertFalse(kwargs["trust_remote_code"])
        self.assertTrue(kwargs["local_files_only"])
        self.assertEqual(kwargs["revision"], allie_local_server.MODEL_REVISION)

    def test_vendor_manifest_rejects_missing_file(self):
        import allie_local_server

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "model.py"
            source.write_text("safe", encoding="utf-8")
            manifest = root / "manifest.csv"
            digest = hashlib.sha256(b"safe").hexdigest()
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["path", "sha256"])
                writer.writeheader()
                writer.writerow({"path": "model.py", "sha256": digest})
            source.unlink()
            with self.assertRaisesRegex(RuntimeError, "missing"):
                allie_local_server.verify_vendor_integrity(root, manifest)

    def test_vendor_manifest_rejects_modified_file(self):
        import allie_local_server

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "model.py"
            source.write_text("changed", encoding="utf-8")
            manifest = root / "manifest.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["path", "sha256"])
                writer.writeheader()
                writer.writerow({"path": "model.py", "sha256": "0" * 64})
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                allie_local_server.verify_vendor_integrity(root, manifest)

    def test_checked_in_vendor_manifest_matches_all_python_modules(self):
        import allie_local_server

        allie_local_server.verify_vendor_integrity()


if __name__ == "__main__":
    unittest.main()
