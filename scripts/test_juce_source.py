#!/usr/bin/env python3
"""Small synthetic regressions for offline dependency source verification."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import verify_juce_source as verifier


class JuceSourceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        self.payload = b"fixture dependency source\n"
        (self.root / "CMakeLists.txt").write_bytes(self.payload)
        self.entries = {"CMakeLists.txt": {"mode": "100644", "blobSha1": verifier.git_hash(b"blob", self.payload)}}
        self.tree = verifier.tree_hash(self.entries)
        self.index = Path(self.temp.name) / "index.json"
        self.index.write_text(json.dumps({"commit": verifier.COMMIT, "gitTreeSha1": self.tree, "files": self.entries}))

    def verify(self):
        with patch.object(verifier, "MANIFEST", self.index), patch.object(verifier, "TREE", self.tree), contextlib.redirect_stdout(io.StringIO()):
            verifier.verify(self.root)

    def test_offline_source_without_git_metadata(self):
        self.verify()

    def test_modified_blob_is_rejected(self):
        (self.root / "CMakeLists.txt").write_bytes(b"changed dependency source\n")
        with self.assertRaisesRegex(ValueError, "content mismatch"):
            self.verify()

    def test_extra_globbed_source_is_rejected(self):
        (self.root / "extra.cpp").write_bytes(b"// unexpected\n")
        with self.assertRaisesRegex(ValueError, "unexpected/missing"):
            self.verify()

    def test_wrong_index_tree_is_rejected(self):
        index = json.loads(self.index.read_text())
        index["files"]["CMakeLists.txt"]["blobSha1"] = "0" * 40
        self.index.write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.verify()

    def test_tree_matches_git_with_directory_sorting(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "foo").mkdir()
        (self.root / "foo/bar").write_bytes(b"bar\n")
        (self.root / "foo.txt").write_bytes(b"file\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        expected = subprocess.check_output(["git", "-C", str(self.root), "write-tree"], text=True).strip()
        entries = dict(self.entries)
        entries["foo/bar"] = {"mode": "100644", "blobSha1": verifier.git_hash(b"blob", b"bar\n")}
        entries["foo.txt"] = {"mode": "100644", "blobSha1": verifier.git_hash(b"blob", b"file\n")}
        self.assertEqual(verifier.tree_hash(entries), expected)

    def test_symlink_is_rejected(self):
        try:
            (self.root / "link.cpp").symlink_to(self.root / "CMakeLists.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.verify()


if __name__ == "__main__":
    unittest.main(verbosity=2)
