#!/usr/bin/env python3
"""Metadata and missing-output checks for the native rendering handoff."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_native_stage as stage_tool
from build_effects_bank import SOURCES, cue_bytes, digest


ROOT = Path(__file__).resolve().parent.parent


class NativeStageTests(unittest.TestCase):
    def setUp(self):
        if not (ROOT / "effects-inputs/atlas-inputs.json").is_file():
            self.skipTest("original effects-inputs delivery absent from checkout; cannot rerun native staging")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        self.header = ROOT / "src/AtlasStudyData.h"
        self.atlas = ROOT / "effects-inputs"
        self.core = self.root / "EffectCore.h"
        # Integration is independently owned; the test verifies stage behavior
        # with a core carrying the expected preset order and Atlas references.
        source = (ROOT / "src/EffectCore.h").read_text()
        source += ('\n#include "AtlasStudyData.h"\n'
                   'inline void fixtureControls() { (void) garden::atlasStudy::fields; '
                   '(void) garden::atlasStudy::remoteOnsetSums; '
                   '(void) garden::atlasStudy::measuredCenterComplex; }\n'
                   'inline void atlasMappedPreset() {}\n')
        self.core.write_text(source)
        shutil.copyfile(ROOT / "src/AtlasStudyPresets.h", self.root / "AtlasStudyPresets.h")
        shutil.copyfile(ROOT / "src/PluginProcessor.cpp", self.root / "PluginProcessor.cpp")

    def test_inventory_stable_and_covers_all_eight_runs(self):
        result = stage_tool.prepare(self.atlas, self.header, self.core, self.stage)
        self.assertEqual(json.loads((self.stage / "effects.json").read_text()), result)
        self.assertEqual(len(result["effects"]), 12)
        self.assertEqual([e["studyIndex"] for e in result["effects"]], list(range(1, 13)))
        self.assertEqual(len({e["id"] for e in result["effects"]}), 12)
        self.assertEqual({r for e in result["effects"] for r in e["sourceRunIds"]},
                         {r["id"] for r in json.loads((self.atlas / "atlas-inputs.json").read_text())["runs"]})
        self.assertFalse((self.stage / "renders.json").exists())
        with self.assertRaisesRegex(ValueError, "already exists"):
            stage_tool.prepare(self.atlas, self.header, self.core, self.stage)

    def test_final_requires_real_files_and_explicit_binary(self):
        stage_tool.prepare(self.atlas, self.header, self.core, self.stage)
        binary = self.root / "GardenBankRender"
        with self.assertRaisesRegex(ValueError, "missing"):
            stage_tool.finalize(self.atlas, self.header, self.core, self.stage, binary)
        binary.write_bytes(b"fixture executable bytes")
        with self.assertRaisesRegex(ValueError, "missing file"):
            stage_tool.finalize(self.atlas, self.header, self.core, self.stage, binary)
        self.assertFalse((self.stage / "renders.json").exists())
        for effect in stage_tool.STUDIES:
            for sid, _, _ in SOURCES:
                (self.stage / f"{effect[0]}-{sid}.wav").write_bytes(cue_bytes(sid))
        result = stage_tool.finalize(self.atlas, self.header, self.core, self.stage, binary)
        self.assertEqual(len(result["effects"]), 12)
        self.assertIn("sha256:" + digest(binary.read_bytes()), result["renderImplementation"])
        self.assertEqual(result["effects"][0]["renders"][0]["sha256"], digest(cue_bytes("drum")))
        self.assertEqual(result, json.loads((self.stage / "renders.json").read_text()))

    def test_rejects_stale_header_or_unintegrated_core(self):
        self.core.write_text((ROOT / "src/EffectCore.h").read_text().replace("atlasStudy::", "notIntegrated::")
                             .replace("AtlasStudyData.h", "unrelated.h"))
        with self.assertRaisesRegex(ValueError, "not integrated"):
            stage_tool.prepare(self.atlas, self.header, self.core, self.stage)
        self.core.write_text((ROOT / "src/EffectCore.h").read_text() +
                             '\n#include "AtlasStudyData.h"\ninline void fixtureControls() { '
                             '(void) garden::atlasStudy::fields; (void) garden::atlasStudy::remoteOnsetSums; '
                             '(void) garden::atlasStudy::measuredCenterComplex; }\n'
                             'inline void atlasMappedPreset() {}\n')
        bad = self.root / "bad-header.h"
        bad.write_bytes(self.header.read_bytes() + b"\n// stale")
        with self.assertRaisesRegex(ValueError, "differs"):
            stage_tool.prepare(self.atlas, bad, self.core, self.stage)

    def test_rejects_modified_inventory(self):
        stage_tool.prepare(self.atlas, self.header, self.core, self.stage)
        data = json.loads((self.stage / "effects.json").read_text())
        data["effects"][0]["wet"] = 0.99
        (self.stage / "effects.json").write_text(json.dumps(data))
        binary = self.root / "renderer"
        binary.write_bytes(b"test")
        with self.assertRaisesRegex(ValueError, "differs"):
            stage_tool.finalize(self.atlas, self.header, self.core, self.stage, binary)

    def test_rejects_modified_atlas_asset_bytes(self):
        copied = self.root / "copied-atlas"
        shutil.copytree(self.atlas, copied)
        item = copied / "releases/effects-field-filter/assets/inline-result.json"
        item.chmod(0o644)
        item.write_bytes(item.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            stage_tool.prepare(copied, self.header, self.core, self.stage)
        self.assertFalse((self.stage / "effects.json").exists())


if __name__ == "__main__":
    unittest.main()
