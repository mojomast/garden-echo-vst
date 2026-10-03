#!/usr/bin/env python3
"""Regression checks that static study data follows immutable genuine input bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("atlas_study", ROOT / "scripts/make_atlas_study_data.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AtlasStudyDataChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The original effects-inputs/ delivery is not part of this checkout.
        # Stage the tracked bank's partial hash-checked archive for tests that
        # can genuinely run, without touching or fabricating missing inputs.
        cls.tmp = tempfile.TemporaryDirectory()
        cls.inputs = Path(cls.tmp.name) / "inputs"
        shutil.copytree(ROOT / "effects-bank/provenance/atlas-assets", cls.inputs)
        shutil.copy2(ROOT / "effects-bank/provenance/atlas-inputs.json", cls.inputs / "atlas-inputs.json")
        index = json.loads((cls.inputs / "atlas-inputs.json").read_text())
        cls.missing = [asset["path"] for row in index["runs"] + [{"assets": index["inputAssets"]}]
                       for asset in row["assets"] if not (cls.inputs / asset["path"]).is_file()]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_generated_header_equals_hash_checked_inputs(self):
        if self.missing:
            self.skipTest("archived bank omits four original input assets; cannot reconstruct generated header")
        actual = (ROOT / "src/AtlasStudyData.h").read_text()
        self.assertEqual(actual, module.generate(self.inputs))
        data = json.loads((self.inputs / "atlas-inputs.json").read_text())
        self.assertEqual(len(data["runs"]), 8)
        self.assertIn(hashlib.sha256((self.inputs / "atlas-inputs.json").read_bytes()).hexdigest(), actual)

    def test_wav_tamper_rejected(self):
        if self.missing:
            self.skipTest("archived bank omits four original input assets; cannot run full verified()")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "inputs"
            shutil.copytree(self.inputs, root)
            file = root / "releases/effects-render-prism/assets/result.wav"
            data = bytearray(file.read_bytes())
            data[-128] ^= 1
            file.chmod(0o644)  # copied archive only; immutable bank remains untouched
            file.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                module.generate(root)

    def test_dense_prism_is_not_falsely_six_sparse_frames(self):
        root = self.inputs
        waves = []
        for kind in ("bloom", "prism", "fracture"):
            samples = module.wav_f32(root / f"releases/effects-render-{kind}/assets/result.wav")
            waves.append(sum(abs(samples[i]) + abs(samples[i + 1]) > 1e-8
                             for i in range(0, len(samples), 2)))
        self.assertEqual(waves[0], 6)
        self.assertGreater(waves[1], 10000)
        self.assertEqual(waves[2], 6)


if __name__ == "__main__":
    unittest.main()
