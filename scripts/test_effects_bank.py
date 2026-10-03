#!/usr/bin/env python3
"""Fixture-only checks; generated wet bytes are NOT native renders or job evidence."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from build_effects_bank import (build, cue_bytes, digest, document, safe_file, wav_stats,
                                write_cues)
from install_effects_selection import install


class OfflineBankChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="effects-fixture-")
        cls.root = Path(cls.tmp.name)
        cls.stage, cls.atlas, cls.cues = (cls.root / name for name in ("stage", "atlas", "cues"))
        cls.stage.mkdir()
        cls.atlas.mkdir()
        write_cues(cls.cues)
        (cls.atlas / "trajectory.json").write_bytes(b'{"fixture":true}\n')
        asset = {"role": "fixture-trajectory", "path": "trajectory.json",
                 "sha256": digest((cls.atlas / "trajectory.json").read_bytes())}
        (cls.atlas / "atlas-inputs.json").write_bytes(document({"schemaVersion": 1,
            "runs": [{"id": "fixture-only", "engineId": "fixture-engine", "jobId": "fixture-job",
                      "params": {}, "execution": "simulator", "assets": [asset]}]}))
        # Slightly modified cues are development fixtures, never native renders.
        effects = []
        for index in range(10):
            eid = "fixture-effect-" + str(index)
            renders = []
            for sid in ("drum", "pluck", "chord"):
                relative = eid + "-" + sid + ".wav"
                raw = bytearray(cue_bytes(sid))
                value = struct.unpack_from("<h", raw, 44 + 4800 * 4)[0]
                struct.pack_into("<h", raw, 44 + 4800 * 4, value + index + 1)
                raw = bytes(raw)
                (cls.stage / relative).write_bytes(raw)
                renders.append({"sourceId": sid, "path": relative, "sha256": digest(raw)})
            effects.append({"id": eid, "name": eid, "family": "fixture", "description": "Test only",
                "atlasRole": "No real lineage: fixture only", "localProcessing": "Fixture copy, not native DSP",
                "parameters": {}, "sourceRunIds": ["fixture-only"], "renders": renders})
        cls.metadata = {"schemaVersion": 1, "renderOrigin": "experimental-native-plugin",
                        "renderImplementation": "Fixture fake executable sha256:" + "a" * 64,
                        "effects": effects}
        (cls.stage / "renders.json").write_bytes(document(cls.metadata))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dry_cues_repeatable_distinct_and_bounded(self):
        hashes = set()
        for sid in ("drum", "pluck", "chord"):
            raw = (self.cues / (sid + "-dry.wav")).read_bytes()
            self.assertEqual(raw, cue_bytes(sid))
            self.assertEqual(wav_stats(raw)["durationSeconds"], 4)
            hashes.add(digest(raw))
        self.assertEqual(len(hashes), 3)

    def test_native_pcm24_validation(self):
        import io
        import wave
        source = cue_bytes("pluck")
        with wave.open(io.BytesIO(source), "rb") as stream:
            pcm16 = stream.readframes(stream.getnframes())
        pcm24 = b"".join((sample * 256).to_bytes(3, "little", signed=True)
                         for (sample,) in struct.iter_unpack("<h", pcm16))
        output = io.BytesIO()
        with wave.open(output, "wb") as stream:
            stream.setparams((2, 3, 48000, 192000, "NONE", "not compressed"))
            stream.writeframes(pcm24)
        self.assertEqual(wav_stats(output.getvalue())["durationSeconds"], 4)

    def test_complete_fixture_bank_and_zero_selection(self):
        bank = self.root / "bank"
        sha = build(self.stage, self.atlas, self.cues, bank)
        self.addCleanup(lambda: __import__("shutil").rmtree(bank))
        self.assertEqual(sha, digest((bank / "manifest.json").read_bytes()))
        manifest = json.loads((bank / "manifest.json").read_bytes())
        self.assertEqual(len(manifest["effects"]), 10)
        self.assertEqual(len(manifest["effects"][0]["renders"]), 3)
        self.assertEqual((bank / "provenance/atlas-assets/trajectory.json").read_bytes(),
                         (self.atlas / "trajectory.json").read_bytes())
        ids = [effect["id"] for effect in manifest["effects"]]
        selection = {"schemaVersion": 1, "bankId": manifest["bankId"], "bankSha256": sha,
                     "selectedEffectIds": [], "decisions": dict.fromkeys(ids, "undecided"),
                     "notes": {}, "updatedAt": "2026-09-25T12:00:00Z"}
        path = self.root / "selection.json"
        path.write_bytes(document(selection))
        config = self.root / "installed.json"
        self.addCleanup(config.unlink)
        self.assertEqual(install(bank, path, config), 0)
        self.assertEqual(json.loads(config.read_bytes())["selectedEffectIds"], [])
        with self.assertRaisesRegex(ValueError, "already exists"):
            install(bank, path, config)
        selection["selectedEffectIds"] = [ids[0]]
        path.write_bytes(document(selection))
        with self.assertRaisesRegex(ValueError, "exactly match"):
            install(bank, path, self.root / "bad-config.json")
        selection["decisions"][ids[0]] = "include"
        selection["notes"][ids[0]] = "x" * 1001
        path.write_bytes(document(selection))
        with self.assertRaisesRegex(ValueError, "notes"):
            install(bank, path, self.root / "bad-config.json")
        selection["notes"][ids[0]] = "Owner listening note"
        path.write_bytes(document(selection))
        approved = self.root / "one.json"
        self.addCleanup(approved.unlink)
        self.assertEqual(install(bank, path, approved), 1)
        selection["bankSha256"] = "0" * 64
        path.write_bytes(document(selection))
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            install(bank, path, self.root / "bad-config.json")

    def test_reject_missing_or_tampered_render_before_creating_bank(self):
        render = self.stage / "fixture-effect-0-drum.wav"
        raw = render.read_bytes()
        try:
            render.write_bytes(raw[:-2])
            dest = self.root / "reject"
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                build(self.stage, self.atlas, self.cues, dest)
            self.assertFalse(dest.exists())
        finally:
            render.write_bytes(raw)

    def test_reject_invalid_riff_and_unsafe_paths(self):
        with self.assertRaisesRegex(ValueError, "unsafe relative"):
            safe_file(self.stage, "../atlas/atlas-inputs.json")
        fixture = self.root / "bad-float.wav"
        raw = bytearray((self.cues / "pluck-dry.wav").read_bytes())
        struct.pack_into("<I", raw, 4, 2)
        with self.assertRaisesRegex(ValueError, "RIFF"):
            wav_stats(raw)
        fixture.write_bytes(raw)
        self.assertTrue(fixture.exists())

    def test_reject_tampered_atlas_asset_and_symlink(self):
        path = self.atlas / "trajectory.json"
        original = path.read_bytes()
        try:
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                build(self.stage, self.atlas, self.cues, self.root / "bad-atlas")
            self.assertFalse((self.root / "bad-atlas").exists())
        finally:
            path.write_bytes(original)
        shortcut = self.stage / "alias.wav"
        shortcut.symlink_to(self.stage / "fixture-effect-0-drum.wav")
        self.addCleanup(shortcut.unlink)
        with self.assertRaisesRegex(ValueError, "symlink"):
            safe_file(self.stage, "alias.wav")


if __name__ == "__main__":
    unittest.main(verbosity=2)
