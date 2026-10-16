"""Exercise recovery failure paths without downloading or changing project models."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import configure


class ConfigureOcrTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.model = Path(self.temp.name) / "model"
        self.source = Path(self.temp.name) / "source"
        self.source.mkdir()
        self.data = {"det.onnx": b"detector", "rec.onnx": b"recognizer", "keys.txt": b"keys"}
        manifest = {
            "repository": "example/models",
            "revision": "pinned-revision",
            "path": "OCR/small",
            "files": [
                {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in self.data.items()
            ],
        }
        self.addCleanup(patch.stopall)
        patch.object(configure, "MANIFEST", manifest).start()
        for name, data in self.data.items():
            (self.source / name).write_bytes(data)

    def test_partial_directory_recovers_missing_files_and_preserves_valid_file(self):
        self.model.mkdir()
        existing = self.model / "det.onnx"
        existing.write_bytes(self.data[existing.name])
        old_mtime = existing.stat().st_mtime_ns
        configure.configure_ocr_model(self.model, source_dir=self.source)
        self.assertEqual(old_mtime, existing.stat().st_mtime_ns)
        configure.configure_ocr_model(self.model, check=True)

    def test_valid_destination_needs_no_submodule_or_network(self):
        configure.configure_ocr_model(self.model, source_dir=self.source)
        with patch.object(configure, "urlopen", side_effect=AssertionError("unexpected network")):
            configure.configure_ocr_model(self.model, source_dir=Path(self.temp.name) / "absent", download=True)

    def test_corrupt_existing_file_is_preserved_even_with_download(self):
        self.model.mkdir()
        existing = self.model / "det.onnx"
        existing.write_bytes(b"bad-data")  # Same size: exercise hash verification.
        with patch.object(configure, "urlopen") as download:
            with self.assertRaisesRegex(ValueError, "SHA256"):
                configure.configure_ocr_model(self.model, download=True)
        download.assert_not_called()
        self.assertEqual(b"bad-data", existing.read_bytes())

    def test_failed_download_does_not_publish_partial_models(self):
        with patch.object(configure, "urlopen", side_effect=[io.BytesIO(b"detector"), io.BytesIO(b"wrong")]):
            with self.assertRaises(ValueError):
                configure.configure_ocr_model(self.model, download=True)
        self.assertFalse(self.model.exists())

    def test_read_only_check_does_not_create_missing_directory(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            configure.configure_ocr_model(self.model, check=True)
        self.assertFalse(self.model.exists())


if __name__ == "__main__":
    unittest.main()
