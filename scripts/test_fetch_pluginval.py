import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from fetch_pluginval import extract


class ToolArchiveChecks(unittest.TestCase):
    def payload(self, name="pluginval"):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr(name, b"synthetic tool fixture, not an executable")
        return memory.getvalue()

    def test_pinned_bytes_extract(self):
        data = self.payload()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "tool"
            extract(data, hashlib.sha256(data).hexdigest(), out)
            self.assertTrue((out / "pluginval").is_file())

    def test_checksum_failure_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "tool"
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                extract(self.payload(), "0" * 64, out)
            self.assertFalse(out.exists())

    def test_archive_escape_is_refused(self):
        data = self.payload("../escape")
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "tool"
            with self.assertRaisesRegex(ValueError, "unsafe tool archive path"):
                extract(data, hashlib.sha256(data).hexdigest(), out)
            self.assertFalse((Path(temporary) / "escape").exists())


if __name__ == "__main__":
    unittest.main()
