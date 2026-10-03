#!/usr/bin/env python3
"""Cross-check fixture, proof WAV framing and observed artifact hashes.

In particular reject files with valid-looking RIFF headers followed by
appended, unframed data: an actual development bug this independent check
caught during repeated offline renders.
"""
import argparse
import hashlib
import json
import struct
import wave
from pathlib import Path

from validate_contract import validate
from import_impulse_kernel import verify_snapshot

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--spaces", type=Path, default=root / "fixtures/recorded-v1")
args = parser.parse_args()
fixture = root / "fixtures/synthetic-v1"
pack = json.loads((fixture / "garden-pack.json").read_text())
assert validate(pack, fixture) and pack["evidenceMode"] == "synthetic"
if args.spaces.resolve() == fixture:
    mode = "synthetic"
else:
    verify_snapshot(args.spaces.resolve())
    mode = "atlas-recorded"
with wave.open(str(fixture / "unit-impulse.wav")) as impulse:
    assert impulse.getparams()[:4] == (2, 4, 48000, 48000)
    frames = impulse.readframes(48000)
    assert struct.unpack_from("<ii", frames) == (2147483647, 2147483647)
    assert not any(frames[8:]), "unit impulse has more than one nonzero frame"


def wav(path, rate, frames):
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    assert struct.unpack_from("<I", data, 4)[0] + 8 == len(data), f"trailing unframed bytes: {path}"
    with wave.open(str(path)) as file:
        assert (file.getnchannels(), file.getsampwidth(), file.getframerate(), file.getnframes()) == (2, 3, rate, frames)
        return file.readframes(file.getnframes())


dry = set()
wet = set()
for space in ("leaf-chamber", "moss-arcade", "rain-canopy"):
    d = wav(root / f"evidence/audio/{space}-dry.wav", 48000, 168000)
    w = wav(root / f"evidence/audio/{space}-wet.wav", 48000, 168000)
    dry.add(hashlib.sha256(d).hexdigest())
    wet.add(hashlib.sha256(w).hexdigest())
    assert d != w
assert len(dry) == 1 and len(wet) == 3, "dry phrases must match and spaces must be distinct"
host = wav(root / "evidence/daw/garden-host-render.wav", 44100, 154350)
assert any(host) and (root / "evidence/daw/reaper-editor.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

provenance = json.loads((root / "evidence/PROVENANCE.json").read_text())
assert provenance["evidenceMode"] == mode
if mode == "atlas-recorded":
    assert provenance["remoteRenderCount"] == provenance["remoteTrajectoryCount"] == 1
    for relative, expected in {**provenance["sourceHashes"], **provenance["kernelHashes"]}.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
else:
    assert provenance["atlasJobIds"] == []
for relative, expected in provenance["artifactHashes"].items():
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
print("PASS", mode, "kernel lineage, exact diagnostic impulse, RIFF lengths, distinct wet files, nonempty host output and observed hashes; host attribution requires separate native evidence")
