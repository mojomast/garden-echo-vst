#!/usr/bin/env python3
"""Reproducible *synthetic* unit-impulse fixtures. No Atlas calls or claims.

The impulse is a single 1.0 sample followed by zeroes. These kernels are
authored mathematical FIR sequences, NOT outputs of an Atlas process job.
"""
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "synthetic-v1"
RATE = 48_000
MOTHBAKE = "b36ac00286f63c3ee4d57a632fb8909c2d189f72"
SPACES = (
    ("leaf-chamber", "Leaf Chamber", 0.55, 431, ((0.083, 0.32, -0.08), (0.167, -0.20, 0.24), (0.293, 0.12, 0.18)), "tight foliage reflections"),
    ("moss-arcade", "Moss Arcade", 1.10, 702, ((0.117, -0.25, 0.34), (0.303, 0.27, -0.16), (0.511, -0.15, 0.22)), "stone-and-moss alternating arches"),
    ("rain-canopy", "Rain Canopy", 1.55, 991, ((0.061, 0.20, 0.06), (0.241, -0.10, 0.25), (0.619, 0.13, -0.19)), "wide, soft dripping canopy"),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wav(path, channels):
    """Write bounded stereo 32-bit PCM. 32-bit avoids clipping tiny tail values."""
    count = len(channels[0])
    assert all(len(channel) == count for channel in channels)
    with wave.open(str(path), "wb") as file:
        file.setparams((len(channels), 4, RATE, count, "NONE", "not compressed"))
        for frame in zip(*channels):
            file.writeframesraw(struct.pack("<" + "i" * len(frame), *(round(max(-1.0, min(1.0, x)) * 2147483647) for x in frame)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    impulse = [0.0] * RATE
    impulse[0] = 1.0
    wav(OUT / "unit-impulse.wav", (impulse, impulse))
    inputs = sha(OUT / "unit-impulse.wav")
    assets = [{"id": "unit-impulse", "role": "unit-impulse", "path": "unit-impulse.wav", "mime": "audio/wav", "sha256": inputs, "sourceRunIds": []}]
    runs = []
    metadata = {"evidenceMode": "synthetic", "sampleRate": RATE, "unitImpulseSha256": inputs, "spaces": []}
    # A single-frame diagnostic identity kernel is distinct from the bounded
    # one-second impulse submitted to an offline impulse-rendering workflow.
    wav(OUT / "identity.wav", ([1.0], [1.0]))
    identity_hash = sha(OUT / "identity.wav")
    assets.append({"id": "identity", "role": "unit-test-kernel", "path": "identity.wav", "mime": "audio/wav", "sha256": identity_hash, "sourceRunIds": ["synthetic-identity-v1"]})
    runs.append({"id": "synthetic-identity-v1", "engineId": "local-identity-fir-v1", "execution": "unknown", "parameters": {"numberOfNonzeroSamples": 1}, "inputSha256": [inputs], "outputSha256": [identity_hash], "jobId": None})
    for slug, name, duration, seed, taps, note in SPACES:
        samples = round(duration * RATE)
        channels = [[0.0] * samples for _ in range(2)]
        # The first sample is an exact unit response. Echoes, rather than a
        # pre-existing processed song, make up the rest of the FIR kernel.
        for channel in channels:
            channel[0] = 1.0
        for time, left, right in taps:
            position = round(time * RATE)
            channels[0][position] += left
            channels[1][position] += right
        rng = random.Random(seed)
        # Sparse, decaying scattering: deterministic, band-limited by an
        # exponential one-pole low-pass filter on the noise impulses.
        for channel in range(2):
            smooth = 0.0
            for i in range(1200, samples):
                excitation = rng.uniform(-1.0, 1.0) if i % 97 == 0 else 0.0
                smooth = 0.78 * smooth + 0.22 * excitation
                channels[channel][i] += 0.14 * smooth * math.exp(-4.5 * i / samples)
        peak = max(abs(x) for c in channels for x in c)
        assert peak <= 1.0
        filename = f"{slug}.wav"
        wav(OUT / filename, channels)
        digest = sha(OUT / filename)
        run = f"synthetic-{slug}-fir-v1"
        assets.append({"id": slug, "role": "impulse-based-creative-kernel", "path": filename, "mime": "audio/wav", "sha256": digest, "sourceRunIds": [run]})
        runs.append({"id": run, "engineId": "local-synthetic-fir-v1", "execution": "unknown", "parameters": {"seed": seed, "durationSeconds": duration, "taps": taps}, "inputSha256": [inputs], "outputSha256": [digest], "jobId": None})
        metadata["spaces"].append({"id": slug, "name": name, "description": note, "kernelSha256": digest, "lengthSamples": samples, "peakBeforeNormalisation": peak, "gainApplied": 1.0, "tapsSecondsLeftRight": taps, "provenance": "SYNTHETIC deterministic FIR; no Atlas job"})
    pack = {"schemaVersion": 1, "id": "garden-echo-synthetic-v1", "producer": "Garden Echo fixture generator v1", "evidenceMode": "synthetic", "mothbakeCommit": MOTHBAKE, "assets": assets, "runs": runs}
    (OUT / "garden-pack.json").write_text(json.dumps(pack, indent=2) + "\n")
    (OUT / "spaces.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("SYNTHETIC ONLY:", OUT, "unit impulse", inputs, "3 FIR kernels")


if __name__ == "__main__":
    main()
