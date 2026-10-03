#!/usr/bin/env python3
"""Offline, fail-closed packaging of externally native-rendered effect studies.

The only audio synthesized here is the three original *dry* input cues. Wet WAVs
must be delivered by a separate native renderer with a metadata inventory.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import sys
import wave
from functools import lru_cache
from pathlib import Path

RATE = 48000
FRAMES = RATE * 4
MAX_BYTES = 16_000_000
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
SOURCES = (
    ("drum", "Wood and air", "Original authored drum/transient cue"),
    ("pluck", "Glass pluck", "Original authored tonal/plucked cue"),
    ("chord", "Floating chords", "Original authored sustained/chord cue"),
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def document(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def load_json(data):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, "duplicate JSON key: " + key)
            obj[key] = value
        return obj
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON")))


def safe_file(root, relative):
    require(isinstance(relative, str) and relative and len(relative) <= 240,
            "invalid relative path")
    require(not relative.startswith("/") and "\\" not in relative and ":" not in relative
            and all(p not in ("", ".", "..") for p in relative.split("/")), "unsafe relative path")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()) and path.is_file() and not path.is_symlink(),
            "missing file or symlink escape: " + relative)
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        require(not cursor.is_symlink(), "symlink input path: " + relative)
    require(0 < path.stat().st_size <= MAX_BYTES, "missing or oversized file: " + relative)
    return path


def checked(root, relative, expected):
    require(isinstance(expected, str) and SHA.fullmatch(expected), "invalid SHA256")
    raw = safe_file(root, relative).read_bytes()
    require(digest(raw) == expected, "SHA256 mismatch: " + relative)
    return raw


def cue_pcm(kind):
    samples = bytearray()
    for frame in range(FRAMES):
        t = frame / RATE
        if kind == "drum":
            value = 0.0
            for onset in (0.1, 0.63, 1.14, 1.65, 2.17, 2.68):
                age = t - onset
                if 0 <= age < 0.3:
                    value += 0.55 * math.exp(-24 * age) * (math.sin(2 * math.pi * (90 * age + 130 * age * age))
                                                               + 0.17 * math.sin(2 * math.pi * 1300 * age))
        elif kind == "pluck":
            value = 0.0
            for onset, hz in ((0.08, 220), (0.55, 329.63), (1.06, 392), (1.57, 293.66),
                              (2.08, 440), (2.59, 329.63)):
                age = t - onset
                if 0 <= age < 0.48:
                    value += 0.36 * math.exp(-8 * age) * (math.sin(2 * math.pi * hz * age)
                                                             + 0.25 * math.sin(2 * math.pi * 2 * hz * age))
        else:
            age = t - 0.1
            value = 0.0
            if 0 <= age < 2.95:
                envelope = min(1.0, age / 0.16) * min(1.0, (2.95 - age) / 0.45)
                value = envelope * sum(0.09 * math.sin(2 * math.pi * hz * age)
                                       for hz in (196, 246.94, 293.66, 392))
        left = max(-0.95, min(0.95, value))
        right = left * 0.89  # deliberately fixed stereo balance, no random seeds
        samples.extend(struct.pack("<hh", round(left * 32767), round(right * 32767)))
    return bytes(samples)


@lru_cache(maxsize=3)
def cue_bytes(kind):
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setparams((2, 2, RATE, FRAMES, "NONE", "not compressed"))
        wav.writeframes(cue_pcm(kind))
    return buf.getvalue()


def write_cues(out):
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())), "output must be new/empty")
    out.mkdir(parents=True, exist_ok=True)
    for kind, _, _ in SOURCES:
        (out / (kind + "-dry.wav")).write_bytes(cue_bytes(kind))


def wav_stats(raw):
    require(len(raw) <= MAX_BYTES and len(raw) >= 44 and raw[:4] == b"RIFF"
            and raw[8:12] == b"WAVE" and struct.unpack_from("<I", raw, 4)[0] + 8 == len(raw),
            "invalid RIFF framing")
    pos, chunks = 12, {}
    while pos < len(raw):
        require(pos + 8 <= len(raw), "truncated WAV chunk")
        tag, size = struct.unpack_from("<4sI", raw, pos)
        end = pos + 8 + size
        require(end + (size % 2) <= len(raw), "truncated WAV data")
        require(tag in (b"fmt ", b"data") and tag not in chunks, "unsupported/duplicate WAV chunk")
        chunks[tag] = raw[pos + 8:end]
        pos = end + (size % 2)
    fmt = chunks.get(b"fmt ", b"")
    require(len(fmt) == 16, "WAV must have PCM fmt")
    encoding, channels, rate, byte_rate, align, bits = struct.unpack("<HHIIHH", fmt)
    require(encoding == 1 and channels == 2 and rate == RATE and bits in (16, 24)
            and align == 2 * bits // 8 and byte_rate == RATE * align,
            "WAV must be 48k stereo PCM16/24")
    pcm = chunks.get(b"data", b"")
    require(len(pcm) == FRAMES * align, "WAV must be exactly four seconds including tail")
    if bits == 16:
        values = struct.iter_unpack("<hh", pcm)
    else:
        values = ((int.from_bytes(pcm[i:i + 3], "little", signed=True),
                   int.from_bytes(pcm[i + 3:i + 6], "little", signed=True))
                  for i in range(0, len(pcm), 6))
    scale = 2 ** (bits - 1)
    peak, power, means = 0, 0, [0, 0]
    for l, r in values:
        peak = max(peak, abs(l), abs(r))
        power += l * l + r * r
        means[0] += l
        means[1] += r
    require(scale * 0.001 <= peak < scale * 0.999 and all(abs(v / FRAMES / scale) <= 0.05 for v in means),
            "audio silent, clipped or excessive DC")
    rms = math.sqrt(power / (FRAMES * 2)) / scale
    require(0.0001 <= rms < 1, "audio RMS outside bounds")
    return {"durationSeconds": FRAMES / RATE, "peakDbfs": 20 * math.log10(peak / scale),
            "rmsDbfs": 20 * math.log10(rms)}


def string(value, name, maximum=400):
    require(isinstance(value, str) and 0 < len(value) <= maximum and not any(ord(c) < 32 for c in value),
            "invalid " + name)
    return value


def identifier(value):
    require(isinstance(value, str) and len(value) <= 64 and ID.fullmatch(value), "invalid ID")
    return value


def build(stage, atlas, cues, out):
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())), "output must be new/empty")
    # Reject input/output overlap before reading or writing.
    for root in (stage, atlas, cues):
        require(not out.resolve().is_relative_to(root.resolve()) and not root.resolve().is_relative_to(out.resolve()),
                "output overlaps inputs")
    metadata_bytes = safe_file(stage, "renders.json").read_bytes()
    metadata = load_json(metadata_bytes)
    require(metadata["schemaVersion"] == 1 and isinstance(metadata["effects"], list)
            and len(metadata["effects"]) >= 10, "renderer metadata needs 10+ effects")
    implementation = string(metadata["renderImplementation"], "renderImplementation", 500)
    require(re.search(r"sha256:[0-9a-f]{64}", implementation), "renderImplementation needs explicit binary/source SHA256")
    require(metadata.get("renderOrigin") == "experimental-native-plugin", "native renderOrigin required")
    atlas_bytes = safe_file(atlas, "atlas-inputs.json").read_bytes()
    atlas_doc = load_json(atlas_bytes)
    require(atlas_doc["schemaVersion"] == 1 and isinstance(atlas_doc["runs"], list)
            and atlas_doc["runs"], "lead Atlas runs must actually be delivered")
    copies = {"provenance/render-metadata.json": metadata_bytes,
              "provenance/atlas-inputs.json": atlas_bytes}
    runs, run_ids = [], set()
    for run in atlas_doc["runs"]:
        rid = run["id"]
        require(isinstance(rid, str) and RUN_ID.fullmatch(rid), "invalid run ID")
        require(rid not in run_ids, "duplicate run ID")
        run_ids.add(rid)
        assets = []
        for asset in run["assets"]:
            role = string(asset["role"], "asset role", 100)
            rel = asset["path"]
            raw = checked(atlas, rel, asset["sha256"])
            dest = "provenance/atlas-assets/" + rel
            require(dest not in copies, "duplicate provenance path")
            copies[dest] = raw
            assets.append({"role": role, "path": dest, "sha256": digest(raw)})
        require(assets, "run without delivered assets")
        for key in ("engineId", "jobId", "execution"):
            string(run[key], key, 150)
        require(isinstance(run["params"], dict), "invalid run params")
        runs.append({"id": rid, "engineId": run["engineId"], "jobId": run["jobId"],
                     "params": run["params"], "execution": run["execution"], "assets": assets})
    sources = []
    for sid, name, description in SOURCES:
        raw = cue_bytes(sid)
        require(checked(cues, sid + "-dry.wav", digest(raw)) == raw, "dry cue differs from authored reference")
        path = "audio/" + sid + "-dry.wav"
        copies[path] = raw
        sources.append({"id": sid, "name": name, "description": description, "dryPath": path,
                        "sha256": digest(raw), "durationSeconds": wav_stats(raw)["durationSeconds"]})
    effects, effect_ids = [], set()
    for entry in metadata["effects"]:
        eid = identifier(entry["id"])
        require(eid not in effect_ids, "duplicate effect ID")
        effect_ids.add(eid)
        ids = entry["sourceRunIds"]
        require(isinstance(ids, list) and ids and len(ids) == len(set(ids))
                and all(r in run_ids for r in ids), "effect sourceRunIds must reference delivered runs")
        require(isinstance(entry["parameters"], dict), "parameters must be JSON object")
        rendered = entry["renders"]
        require(isinstance(rendered, list) and len(rendered) == 3, "each effect requires three renders")
        renders = []
        for render in rendered:
            sid = identifier(render["sourceId"])
            require(sid in {s[0] for s in SOURCES} and sid not in {r["sourceId"] for r in renders},
                    "missing/duplicate source render")
            raw = checked(stage, render["path"], render["sha256"])
            dest = "audio/" + eid + "-" + sid + ".wav"
            require(dest not in copies, "duplicate render destination")
            require(digest(raw) != digest(copies["audio/" + sid + "-dry.wav"]),
                    "wet render equals original dry cue")
            stats = wav_stats(raw)
            copies[dest] = raw
            renders.append({"sourceId": sid, "path": dest, "sha256": digest(raw), **stats})
        effects.append({"id": eid, "name": string(entry["name"], "name", 120),
                        "family": string(entry["family"], "family", 80),
                        "description": string(entry["description"], "description"),
                        "atlasRole": string(entry["atlasRole"], "atlasRole"),
                        "localProcessing": string(entry["localProcessing"], "localProcessing"),
                        "parameters": entry["parameters"], "sourceRunIds": ids, "renders": renders})
    manifest = {"schemaVersion": 1, "bankId": "garden-echo-effects-v1", "title": "Garden Echo · Effect studies",
                "renderImplementation": implementation, "sources": sources, "effects": effects, "runs": runs}
    # No partial output on validation errors; input files are rechecked when copied.
    out.mkdir(parents=True, exist_ok=True)
    for relative, raw in copies.items():
        dest = out / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        require(digest(dest.read_bytes()) == digest(raw), "write verification failed")
        dest.chmod(0o444)
    (out / "manifest.json").write_bytes(document(manifest))
    return digest((out / "manifest.json").read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    cue = sub.add_parser("cues", help="author reproducible dry WAVs for external native renderer")
    cue.add_argument("--out", type=Path, required=True)
    bank = sub.add_parser("bank", help="validate and package delivered native renders")
    for name in ("stage", "atlas", "cues", "out"):
        bank.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "cues":
            write_cues(args.out)
            print("Authored three 48k stereo PCM16 dry cues:", args.out)
        else:
            print("Manifest SHA256:", build(args.stage, args.atlas, args.cues, args.out))
    except (ValueError, KeyError, OSError, TypeError, struct.error) as exc:
        print("Rejected: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
