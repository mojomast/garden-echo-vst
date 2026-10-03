#!/usr/bin/env python3
"""Offline regression checks for the real source's unusual encoding and lineage."""
import contextlib
import io
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from import_impulse_kernel import (build_snapshot, check_impulse, events, read_wav,
                                   safe_file, sha, verify_snapshot, verify_sources)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/recorded-v1"
SOURCES = FIXTURE / "sources"


class RecordedImportChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="import-check-", dir=ROOT / "scripts")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def copy_sources(self):
        dest = self.work / "sources"
        shutil.copytree(SOURCES, dest)
        for path in dest.rglob("*"):
            if path.is_file():
                path.chmod(0o644)
        return dest

    def test_exact_float_input_and_actual_source_coefficients(self):
        impulse = read_wav(SOURCES / "live-jobs/inputs/unit-impulse-float32.wav")
        check_impulse(impulse)
        self.assertEqual(sum(v != 0 for v in impulse[3]), 1)
        render = read_wav(SOURCES / "releases/echo-explicit-impulse/assets/result.wav")
        self.assertEqual(render[:3], (2, 22050, 44100))
        self.assertEqual([e[0] for e in events(render)], [3969, 7938, 11907, 15876])
        self.assertEqual(render[3][7938 * 2 + 1], -0.7557339668273926)
        self.assertEqual(sum(v != 0 for v in render[3]), 8)

    def test_rebuild_is_byte_identical_and_sources_read_only(self):
        output = self.work / "rebuilt"
        with contextlib.redirect_stdout(io.StringIO()):
            build_snapshot(SOURCES, output)
        expected = {str(p.relative_to(FIXTURE)): sha(p) for p in FIXTURE.rglob("*") if p.is_file()}
        actual = {str(p.relative_to(output)): sha(p) for p in output.rglob("*") if p.is_file()}
        self.assertEqual(actual, expected)
        self.assertTrue(all(p.stat().st_mode & 0o222 == 0 for p in (output / "sources").rglob("*") if p.is_file()))
        verify_snapshot(output)

    def test_final_taps_and_transform_are_actual_audio(self):
        bundle, metadata = verify_snapshot(FIXTURE)
        times = {"leaf-chamber": [3969, 7938, 11907, 15876],
                 "moss-arcade": [2646, 5292, 7938, 10584],
                 "rain-canopy": [4961, 9922, 14884, 19845]}
        source_events = events(read_wav(SOURCES / "releases/echo-explicit-impulse/assets/result.wav"))
        for item in bundle["spaces"]:
            wav = read_wav(FIXTURE / item["file"])
            actual = events(wav)
            self.assertEqual([e[0] for e in actual], times[item["id"]])
            transform = item["transform"]
            for rank, (event, source) in enumerate(zip(actual, source_events)):
                pair = source[1:][::-1] if transform["swapStereo"] else source[1:]
                for c in range(2):
                    expected = pair[c] * transform["polarity"] * transform["dampingPerEvent"] ** rank * item["gainApplied"]
                    self.assertAlmostEqual(event[c + 1], expected, delta=0.5 / 2147483648)
            # The channel l1 sum bounds convolution of any input <=1 at native rate.
            for c in range(2):
                self.assertLessEqual(math.fsum(abs(v) for v in wav[3][c::2]), 0.850000002)

    def test_tampered_input_hash_rejected_cli_exit_2(self):
        root = self.copy_sources()
        path = root / "live-jobs/inputs/unit-impulse-float32.wav"
        data = bytearray(path.read_bytes())
        data[-4:] = struct.pack("<f", 0.25)
        path.write_bytes(data)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/import_impulse_kernel.py"),
                                 "--source-root", str(root), "--out", str(self.work / "out")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("source hash mismatch", result.stderr)
        self.assertFalse((self.work / "out").exists())

    def test_tampered_render_or_trajectory_or_pack_rejected(self):
        root = self.copy_sources()
        for name in ("releases/echo-explicit-impulse/assets/result.wav", "live-jobs/inputs/echo-trajectory.json",
                     "releases/echo-measure/pack.json"):
            with self.subTest(name=name):
                path = root / name
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                    verify_sources(root)
                path.write_bytes(original)

    def test_attestation_cannot_be_missing_or_claim_failed_job(self):
        root = self.copy_sources()
        path = root / "evidence/atlas-release-verification.json"
        document = json.loads(path.read_text())
        next(p for p in document["packs"] if p["id"] == "echo-explicit-impulse")["status"] = "failed"
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "attestation mismatch"):
            verify_sources(root)

    def test_reject_non_impulse_even_without_hash_layer(self):
        channels, rate, frames, values = read_wav(SOURCES / "live-jobs/inputs/unit-impulse-float32.wav")
        for first, later in ((0.5, 0.0), (1.0, 0.1)):
            values[0], values[100] = first, later
            with self.assertRaisesRegex(ValueError, "not an exact single unit impulse"):
                check_impulse((channels, rate, frames, values))

    def test_reject_bad_float_samples_and_wav_framing(self):
        original = (SOURCES / "live-jobs/inputs/unit-impulse-float32.wav").read_bytes()
        path = self.work / "bad.wav"
        for sample in (float("nan"), float("inf"), -float("inf"), 1.01, -1.01):
            with self.subTest(sample=sample):
                data = bytearray(original)
                data[-4:] = struct.pack("<f", sample)
                path.write_bytes(data)
                with self.assertRaisesRegex(ValueError, "non-finite or out-of-range"):
                    read_wav(path)
        for data in (original[:-1], original + b"extra"):
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "RIFF size/trailing"):
                read_wav(path)
        data = bytearray(original)
        struct.pack_into("<I", data, 28, 1)  # byte rate
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "alignment/byte rate"):
            read_wav(path)
        data = bytearray(original)
        struct.pack_into("<I", data, 44, 1)  # fact frame count
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "fact frame count"):
            read_wav(path)

    def test_reject_traversal_and_symlink_escape(self):
        with self.assertRaisesRegex(ValueError, "unsafe relative"):
            safe_file(SOURCES, "../spaces.json")
        (self.work / "escape").symlink_to(SOURCES / "RELEASE_INDEX.json")
        with self.assertRaisesRegex(ValueError, "symlink escape"):
            safe_file(self.work, "escape")

    def test_existing_snapshot_not_overwritten(self):
        with self.assertRaisesRegex(ValueError, "new/empty"):
            build_snapshot(SOURCES, FIXTURE)

    def test_tampered_final_tap_map_rejected(self):
        output = self.work / "snapshot"
        shutil.copytree(FIXTURE, output)
        path = output / "spaces.json"
        metadata = json.loads(path.read_text())
        metadata["spaces"][0]["tapsSecondsLeftRight"][0][1] += 0.01
        path.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "tap map mismatch"):
            verify_snapshot(output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
