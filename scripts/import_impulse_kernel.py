#!/usr/bin/env python3
"""Deterministic offline import of the reviewed explicit-impulse Atlas release.

--source-root is the hub or this snapshot's sources/ directory. No network calls.
Three local DSP variations share ONE render and ONE measured trajectory. This
is a build snapshot, not a new GardenPack, room measurement or LTI certification.
"""
import argparse
import hashlib
import json
import math
import struct
import sys
import wave
from pathlib import Path

from jsonschema.exceptions import ValidationError
from validate_contract import validate

PIN = "b36ac00286f63c3ee4d57a632fb8909c2d189f72"
KIND = "Garden Echo recorded kernel build snapshot; not a GardenPack"
PACKS = {
    "echo-explicit-impulse": ("be5314372045ac92d7b5d3c2ecd6d7566de2913a0546d81e80a74973fec12c3a",
                              "1c7f2c4b-e11f-4d06-92e6-88356c6c6777", "retrocausal-echo-v1"),
    "echo-measure": ("a1e7fcc86ef043ed7129d6c83841ff34826d914a21be3d230a81e7ce5e02cbda",
                     "5e4da3b1-32fc-4b67-96e7-cb4fbb422249", "otoc-echo-v1"),
}
INPUTS = {
    "unit-impulse-float32.wav": "61f315bb803843cf4218267115ca09eb39c4cd34ee37e229e514b5c2243a637d",
    "unit-impulse-float32.lineage.json": "77aa6e4c73d4d59a45c76dbc7725798392c6add437cdb7f81168bf6a31dcc8cb",
    "echo-trajectory.json": "ae7549afcd890bef2274361c8b0aef888777729c5b97e07db8bffc5b85526d11",
    "echo-trajectory.lineage.json": "968b7ceacede96168e7793b52e682cfc4d0e2dda23caaee79a213fc0249e5b50",
}
NAMES = {"leaf-chamber": "Leaf Chamber", "moss-arcade": "Moss Arcade", "rain-canopy": "Rain Canopy"}
MAX_BYTES = 12_000_000
# These are the archived metadata values for the hash-pinned render, not DSP
# coefficients. Apple's libm and glibc round log10 differently by one ULP for
# two gains; keeping the reviewed dB spellings makes bundle.json reproducible.
# The exact gain pins below prevent a new render/transform from inheriting old
# metadata, and the log10 check guards against a mistyped archived dB value.
RECORDED_GAIN_DB = {
    "leaf-chamber": ("0x1.e12a089ad85c3p-2", "-0x1.a3d9388326201p+2"),
    "moss-arcade": ("0x1.143589f5c58d9p-1", "-0x1.5714b32beecd7p+2"),
    "rain-canopy": ("0x1.3daa0906e875ap-1", "-0x1.09589de6b888fp+2"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and ".." not in p.parts and "\\" not in relative and ":" not in relative,
            "unsafe relative path")
    path = root / p
    require(path.resolve().is_relative_to(root.resolve()), "symlink escape")
    require(path.is_file() and path.stat().st_size <= MAX_BYTES, "missing or oversized source: " + relative)
    return path


def read_wav(path):
    """Strict little-endian RIFF PCM16/24/32 or IEEE-float32, 1/2ch, <=2s.

    Python's standard wave module does not decode format tag 3 here.
    Validate byte rate, framing and optional fact count before unpacking; never
    reinterpret IEEE floats as signed PCM integers or silently clamp samples.
    """
    require(path.stat().st_size <= MAX_BYTES, "WAV exceeds 12MB input bound")
    raw = path.read_bytes()
    require(len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE", "not RIFF/WAVE")
    require(struct.unpack_from("<I", raw, 4)[0] + 8 == len(raw), "RIFF size/trailing bytes mismatch")
    chunks = {}
    pos = 12
    while pos < len(raw):
        require(pos + 8 <= len(raw), "truncated chunk header")
        tag, size = struct.unpack_from("<4sI", raw, pos)
        end = pos + 8 + size
        require(end + size % 2 <= len(raw), "truncated chunk")
        if tag in (b"fmt ", b"data", b"fact"):
            require(tag not in chunks, "duplicate WAV chunk")
            chunks[tag] = raw[pos + 8:end]
        pos = end + size % 2
    require(b"fmt " in chunks and b"data" in chunks, "missing fmt/data")
    fmt = chunks[b"fmt "]
    require(len(fmt) in (16, 18), "unsupported fmt chunk length")
    encoding, channels, rate, byte_rate, align, bits = struct.unpack_from("<HHIIHH", fmt)
    require(len(fmt) == 16 or fmt[16:] == b"\0\0", "unsupported WAV extension")
    require(channels in (1, 2) and rate in (22050, 44100, 48000, 96000), "unsupported channels/sample rate")
    require((encoding == 1 and bits in (16, 24, 32)) or (encoding == 3 and bits == 32), "unsupported WAV encoding")
    width = bits // 8
    require(align == channels * width and byte_rate == rate * align, "invalid WAV alignment/byte rate")
    data = chunks[b"data"]
    require(len(data) % align == 0, "partial WAV frame")
    frames = len(data) // align
    require(1 <= frames <= rate * 2, "WAV duration outside 1 sample..2 seconds")
    if b"fact" in chunks:
        fact = chunks[b"fact"]
        require(len(fact) == 4 and struct.unpack("<I", fact)[0] == frames, "fact frame count mismatch")
    if encoding == 3:
        values = [v[0] for v in struct.iter_unpack("<f", data)]
    elif bits == 24:
        values = [int.from_bytes(data[i:i + 3], "little", signed=True) / 8388608.0
                  for i in range(0, len(data), 3)]
    else:
        values = [v[0] / (2 ** (bits - 1)) for v in struct.iter_unpack("<h" if bits == 16 else "<i", data)]
    require(all(math.isfinite(v) and abs(v) <= 1 for v in values), "non-finite or out-of-range WAV sample")
    return channels, rate, frames, values


def check_impulse(wav):
    channels, rate, frames, values = wav
    require((channels, rate, frames) == (1, 22050, 44100), "unexpected unit-impulse format")
    require(values[0] == 1.0 and all(v == 0 for v in values[1:]), "input is not an exact single unit impulse")


def signal_stats(wav):
    channels, rate, frames, values = wav
    return {"channels": channels, "sampleRate": rate, "frames": frames,
            "durationSeconds": frames / rate, "peak": max(map(abs, values)),
            "rms": math.sqrt(math.fsum(v * v for v in values) / len(values)),
            "meanPerChannel": [math.fsum(values[c::channels]) / frames for c in range(channels)],
            "l1PerChannel": [math.fsum(map(abs, values[c::channels])) for c in range(channels)],
            "nonzeroSamples": sum(v != 0 for v in values),
            "clippedSamples": sum(abs(v) >= 1 for v in values), "allFinite": True}


def events(wav):
    channels, rate, frames, values = wav
    require(channels == 2, "curation requires stereo")
    return [(i, values[2 * i], values[2 * i + 1]) for i in range(frames)
            if values[2 * i] != 0 or values[2 * i + 1] != 0]


def verify_sources(root):
    """Hash pins + schema + hub's archived remote attestation + actual lineage."""
    files = {}

    def load(relative, expected=None, as_json=True):
        path = safe_file(root, relative)
        digest = sha(path)
        require(expected is None or digest == expected, "source hash mismatch: " + relative)
        files[relative] = digest
        return json.loads(path.read_text()) if as_json else path

    index = load("RELEASE_INDEX.json")
    attestation = load("evidence/atlas-release-verification.json")
    packs = {}
    for name, (digest, job, engine) in PACKS.items():
        relative = "releases/" + name + "/pack.json"
        pack = load(relative, digest)
        # Preflight size/path before the shared schema validator reads assets.
        for asset in pack["assets"]:
            load("releases/" + name + "/" + asset["path"], asset["sha256"], False)
        validate(pack, root / "releases" / name)
        require(pack["id"] == name and pack["mothbakeCommit"] == PIN and pack["evidenceMode"] == "atlas-live",
                "unexpected source pack identity")
        require(len(pack["runs"]) == 1, "expected one run per pack")
        run = pack["runs"][0]
        require((run["jobId"], run["engineId"], run["execution"]) == (job, engine, "simulator"), "run identity mismatch")
        indexed = [p for p in index["packs"] if p["id"] == name]
        attested = [p for p in attestation["packs"] if p["id"] == name]
        require(len(indexed) == len(attested) == 1, "missing/duplicate release attestation")
        release, proof = indexed[0], attested[0]
        require(release["packSha256"] == proof["packSha256"] == digest and
                release["jobId"] == proof["jobId"] == job and proof["status"] == "completed", "attestation mismatch")
        for asset in pack["assets"]:
            require(asset["sha256"] in run["outputSha256"] and asset["sourceRunIds"] == [run["id"]], "output linkage mismatch")
            require(any(a["path"] == "releases/" + name + "/" + asset["path"] and a["sha256"] == asset["sha256"]
                        for a in release["assets"]), "release asset mismatch")
            require(any(a["assetId"] == asset["id"] and a["sha256"] == asset["sha256"] and a["remoteMatches"] is True
                        for a in proof["assets"]), "remote attestation asset mismatch")
        packs[name] = pack
    for name, digest in INPUTS.items():
        load("live-jobs/inputs/" + name, digest, False)
    inputs = root / "live-jobs/inputs"
    trajectory = json.loads((inputs / "echo-trajectory.json").read_text())
    source = json.loads((root / "releases/echo-measure/assets/inline-result.json").read_text())["output"]
    returned = json.loads((root / "releases/echo-explicit-impulse/assets/ir.json").read_text())
    require(trajectory == source and returned["data"] == source["data"], "trajectory extraction/reuse mismatch")
    require(source["result_type"] == "trajectory" and source["schema_version"] == 1, "trajectory schema mismatch")
    require(source["data"]["sites"] == source["data"]["steps"] == 4, "unexpected trajectory dimensions")
    for matrix in source["data"]["series"].values():
        require(len(matrix) == 4 and all(len(row) == 4 and all(math.isfinite(v) for v in row) for row in matrix),
                "invalid trajectory samples")
    for document in (source, returned):
        p = document["provenance"]
        require(p["backend"] == "aer" and p["mode"] == "emu" and p["qpu_job_id"] is None, "unexpected execution evidence")
    run = packs["echo-explicit-impulse"]["runs"][0]
    require(set(run["inputSha256"]) == {INPUTS["unit-impulse-float32.wav"], INPUTS["echo-trajectory.json"]},
            "unit impulse and cross-pack trajectory must both be render inputs")
    check_impulse(read_wav(inputs / "unit-impulse-float32.wav"))
    render = read_wav(root / "releases/echo-explicit-impulse/assets/result.wav")
    require(render[:3] == (2, 22050, 44100), "unexpected render format")
    stats = signal_stats(render)
    require(0.01 < stats["peak"] < 1 and stats["clippedSamples"] == 0, "silent/clipped source render")
    require(len(events(render)) == 4, "reviewed sparse render must have four occupied frames")
    taps = json.loads((root / "releases/echo-explicit-impulse/assets/taps.json").read_text())
    require(taps["provenance"]["ir_source"] == "supplied" and taps["data"]["rendered"] == "processed_input", "wrong render source")
    params = taps["extras"]["params"]
    require(params["mix"] == 1 and params["feedback"] == 0 and params["diffusion_ms"] == 0
            and params["negative_mode"] == "invert" and params["tail_ms"] == 0, "unexpected effective renderer settings")
    return files, packs, render, taps


def write_json(path, data):
    path.write_bytes((json.dumps(data, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def recorded_gain_db(slug, gain):
    gain_hex, db_hex = RECORDED_GAIN_DB[slug]
    require(gain.hex() == gain_hex, "recorded normalization gain changed: " + slug)
    db = float.fromhex(db_hex)
    require(abs(20 * math.log10(gain) - db) <= 2 * math.ulp(db),
            "recorded gain dB is inconsistent: " + slug)
    return db


def curate(slug, render, output):
    """Delay-event remapping is intentional local DSP, not waveform SRC.

    Preserve individual discrete coefficients (no rate/amplitude scaling).
    Nearest-frame ties-to-even rounding is implemented with integer arithmetic.
    """
    channels, rate, frames, _ = render
    numerator, denominator, damping, polarity, swap = {
        "leaf-chamber": (1, 1, 1.0, 1, False),
        "moss-arcade": (2, 3, 0.875, 1, False),
        "rain-canopy": (5, 4, 0.75, -1, True),
    }[slug]
    values = [0.0] * (frames * channels)
    for rank, (frame, left, right) in enumerate(events(render)):
        quotient, remainder = divmod(frame * numerator, denominator)
        dest = quotient + int(2 * remainder > denominator or (2 * remainder == denominator and quotient % 2))
        require(0 <= dest < frames, "retimed event exceeds bounded kernel length")
        if swap:
            left, right = right, left
        for c, value in enumerate((left, right)):
            values[2 * dest + c] += value * polarity * damping ** rank
    peak = max(map(abs, values))
    l1 = max(math.fsum(map(abs, values[c::2])) for c in range(2))
    gain = min(1.0, 0.8 / peak, 0.85 / l1)
    # PCM32 with 2^31 scaling; rounding error is measured again after decoding.
    integers = [round(v * gain * 2147483648) for v in values]
    require(all(-2147483648 < v < 2147483648 for v in integers), "quantized sample clipped")
    with wave.open(str(output), "wb") as wav:
        wav.setparams((2, 4, rate, frames, "NONE", "not compressed"))
        wav.writeframes(struct.pack("<" + "i" * len(integers), *integers))
    final = read_wav(output)
    stats = signal_stats(final)
    require(stats["peak"] < 0.800000001 and max(stats["l1PerChannel"]) < 0.850000002, "normalization bound failed")
    actual_events = events(final)
    strongest = sorted(sorted(actual_events, key=lambda e: (-max(abs(e[1]), abs(e[2])), e[0]))[:3])
    return {"id": slug, "file": output.name, "stagedKernelSha256": sha(output),
            "sampleRate": rate, "frames": frames, "gainApplied": gain,
            "gainDb": recorded_gain_db(slug, gain), "originalPeak": max(map(abs, render[3])),
            "transform": {"version": 1, "source": "actual decoded remote result.wav nonzero frames",
                          "timeScaleNumerator": numerator, "timeScaleDenominator": denominator,
                          "delayRounding": "nearest frame, ties to even",
                          "dampingPerEvent": damping, "dampingExponent": "zero-based occupied-frame rank",
                          "polarity": polarity, "swapStereo": swap,
                          "resampling": "none: source and output remain 22050 Hz; sparse delay retiming only",
                          "normalization": "min(1, 0.8/peak, 0.85/max_channel_sum_abs) before PCM quantization",
                          "preGainPeak": peak, "preGainMaxChannelL1": l1,
                          "encoding": "PCM32 little endian; round-to-even(sample * 2^31), no clipping",
                          "length": "retain original 44100 frames, zero fill, no truncated events"},
            "signal": stats,
            "allEventsFrameLeftRight": actual_events,
            "tapsSecondsLeftRight": [[i / rate, l, r] for i, l, r in strongest],
            "tapMethod": "three strongest occupied frames of final decoded PCM WAV, chronological; full four events also archived"}


def build_snapshot(source_root, out):
    source_root, out = source_root.resolve(), out.absolute()
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())), "output must be a new/empty folder")
    require(not out.resolve().is_relative_to(source_root / "releases"), "cannot write into source releases")
    files, packs, render, taps = verify_sources(source_root)
    out.mkdir(parents=True, exist_ok=True)
    for relative, digest in files.items():
        dest = out / "sources" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(safe_file(source_root, relative).read_bytes())
        require(sha(dest) == digest, "source changed while copying")
        dest.chmod(0o444)
    metadata = {"evidenceMode": "atlas-recorded", "spaces": []}
    run = packs["echo-explicit-impulse"]["runs"][0]
    bundle = {"schemaVersion": 1, "kind": KIND, "evidenceMode": "atlas-recorded", "mothbakeCommit": PIN,
              "claim": "Three locally curated sparse creative kernels from one remote explicit-unit-impulse render and one simulator trajectory; not independent experiments or measured rooms",
              "remoteRenderCount": 1, "remoteTrajectoryCount": 1,
              "atlasJobIds": [p["runs"][0]["jobId"] for p in packs.values()],
              "sourceFiles": {"sources/" + p: digest for p, digest in sorted(files.items())},
              "sourceSignal": signal_stats(render), "sourceEventsFrameLeftRight": events(render),
              "renderParametersRequested": run["parameters"],
              "renderParametersEffective": taps["extras"]["params"],
              "remoteVerification": "Archived hub GET/re-download attestation; this importer performs offline verification only",
              "spaces": []}
    descriptions = {"leaf-chamber": "Original timing / sparse signed echo",
                    "moss-arcade": "Two-thirds timing / gently damped echo",
                    "rain-canopy": "Slower inverted / damped stereo swap"}
    for slug, name in NAMES.items():
        data = curate(slug, render, out / (slug + ".wav"))
        data.update({"packId": packs["echo-explicit-impulse"]["id"], "jobId": run["jobId"],
                     "sourceRunId": run["id"], "unitImpulseSha256": INPUTS["unit-impulse-float32.wav"],
                     "trajectoryInputSha256": INPUTS["echo-trajectory.json"],
                     "trajectoryJobId": PACKS["echo-measure"][1],
                     "originalRenderSha256": files["releases/echo-explicit-impulse/assets/result.wav"]})
        bundle["spaces"].append(data)
        metadata["spaces"].append({"id": slug, "name": name, "file": slug + ".wav",
                                   "description": descriptions[slug], "kernelSha256": data["stagedKernelSha256"],
                                   "tapsSecondsLeftRight": data["tapsSecondsLeftRight"],
                                   "provenance": "ATLAS RECORDED / local variation of ONE impulse render / simulator / job " + run["jobId"]})
    require(len({s["stagedKernelSha256"] for s in bundle["spaces"]}) == 3, "curated kernels must be distinct")
    write_json(out / "spaces.json", metadata)
    write_json(out / "bundle.json", bundle)
    print("Verified and imported 3 local variations / 1 remote render / 1 trajectory:", out)


def verify_snapshot(folder):
    """Validate the archived lineage and final WAV/metadata links for consumers."""
    manifest = json.loads((folder / "bundle.json").read_text())
    metadata = json.loads((folder / "spaces.json").read_text())
    require(manifest["kind"] == KIND and metadata["evidenceMode"] == "atlas-recorded", "not a recorded snapshot")
    files, packs, render, _ = verify_sources(folder / "sources")
    require(manifest["sourceFiles"] == {"sources/" + p: digest for p, digest in files.items()}, "archive inventory mismatch")
    require(manifest["remoteRenderCount"] == manifest["remoteTrajectoryCount"] == 1, "incorrect experiment count")
    require(manifest["atlasJobIds"] == [p["runs"][0]["jobId"] for p in packs.values()], "incorrect job list")
    require([s["id"] for s in manifest["spaces"]] == [s["id"] for s in metadata["spaces"]] == list(NAMES), "space list mismatch")
    require(manifest["sourceSignal"] == signal_stats(render), "source signal metadata mismatch")
    hashes = set()
    for item, space in zip(manifest["spaces"], metadata["spaces"]):
        require(item["file"] == space["file"] == item["id"] + ".wav", "WAV filename mismatch")
        path = safe_file(folder, item["file"])
        require(sha(path) == item["stagedKernelSha256"] == space["kernelSha256"], "kernel hash mismatch")
        require(item["originalRenderSha256"] == files["releases/echo-explicit-impulse/assets/result.wav"]
                and item["unitImpulseSha256"] == INPUTS["unit-impulse-float32.wav"]
                and item["trajectoryInputSha256"] == INPUTS["echo-trajectory.json"]
                and item["jobId"] == PACKS["echo-explicit-impulse"][1]
                and item["trajectoryJobId"] == PACKS["echo-measure"][1], "derived source linkage mismatch")
        final = read_wav(path)
        require(final[:3] == (2, 22050, 44100), "unexpected final WAV format")
        stats = signal_stats(final)
        require(stats == item["signal"] and stats["clippedSamples"] == 0
                and max(stats["l1PerChannel"]) < 0.850000002, "final signal bounds/metadata mismatch")
        actual = events(final)
        require([list(e) for e in actual] == item["allEventsFrameLeftRight"], "final events mismatch")
        strongest = sorted(sorted(actual, key=lambda e: (-max(abs(e[1]), abs(e[2])), e[0]))[:3])
        measured = [[i / final[1], l, r] for i, l, r in strongest]
        require(measured == item["tapsSecondsLeftRight"] == space["tapsSecondsLeftRight"], "final tap map mismatch")
        hashes.add(sha(path))
    require(len(hashes) == 3, "curated kernels are not distinct")
    return manifest, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="hub directory or recorded-v1/sources")
    parser.add_argument("--out", type=Path, required=True, help="new empty build snapshot folder")
    args = parser.parse_args()
    try:
        build_snapshot(args.source_root, args.out)
    except (ValueError, KeyError, AssertionError, OSError, struct.error, wave.Error, ValidationError) as exc:
        print("Import rejected: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
