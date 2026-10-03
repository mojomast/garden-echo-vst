import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_selected_plugin import build


ROOT = Path(__file__).resolve().parents[1]


class SelectedPluginTests(unittest.TestCase):
    def test_exact_bank_shortlist_and_zero_choice(self):
        bank = ROOT / "effects-bank"
        if not bank.exists():
            self.skipTest("genuine bank built separately; fixture bank tests cover packaging")
        manifest = json.loads((bank / "manifest.json").read_bytes())
        ids = [effect["id"] for effect in manifest["effects"]]
        digest = hashlib.sha256((bank / "manifest.json").read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for included in ([], [ids[1], ids[4]]):
                selection = {"schemaVersion": 1, "bankId": manifest["bankId"], "bankSha256": digest,
                             "selectedEffectIds": included,
                             "decisions": {i: "include" if i in included else "exclude" for i in ids},
                             "notes": {}, "updatedAt": "2026-09-25T12:00:00Z"}
                path = root / ("selection-" + str(len(included)) + ".json")
                path.write_text(json.dumps(selection))
                header = root / ("shortlist-" + str(len(included)) + ".h")
                self.assertEqual(build(bank, path, header)[0], len(included))
                text = header.read_text()
                self.assertIn(digest, text)
                self.assertEqual(text.count("true"), len(included) + 1)  # enabled=true
                self.assertIn("{ " + ",".join("true" if eid in included else "false" for eid in ids) + " }", text)
                with self.assertRaisesRegex(ValueError, "new"):
                    build(bank, path, header)
            tampered = json.loads(path.read_text())
            tampered["bankSha256"] = "0" * 64
            bad = root / "bad.json"
            bad.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "mismatch"):
                build(bank, bad, root / "bad.h")


if __name__ == "__main__":
    unittest.main()
