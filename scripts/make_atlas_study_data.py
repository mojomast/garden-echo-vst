#!/usr/bin/env python3
"""Verify lead-owned Atlas bytes and emit immutable RT-ready numeric data.

No network or mutation of effects-inputs. Core can consume this header with
strictly bounded static arrays, rather than decoding JSON/WAV in processBlock.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def wav_f32(path):
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE" or len(data) != struct.unpack_from("<I", data, 4)[0] + 8:
        raise ValueError(f"not a bounded RIFF WAV: {path}")
    pos = 12
    fmt = payload = None
    while pos + 8 <= len(data):
        kind, size = struct.unpack_from("<4sI", data, pos)
        value = data[pos + 8:pos + 8 + size]
        if len(value) != size:
            raise ValueError("truncated WAV")
        if kind == b"fmt ": fmt = value
        if kind == b"data": payload = value
        pos += 8 + size + size % 2
    if not fmt or payload is None:
        raise ValueError("missing WAV chunks")
    encoding, channels, sr = struct.unpack_from("<HHI", fmt)
    if encoding != 3 or channels != 2 or sr != 22050 or len(payload) != 44100 * 2 * 4:
        raise ValueError("expected exact 2s stereo float32 22050 Atlas render")
    samples = struct.unpack("<" + "f" * (len(payload) // 4), payload)
    if not all(math.isfinite(x) for x in samples):
        raise ValueError("nonfinite Atlas WAV")
    return samples


def verified(root):
    manifest = json.loads((root / "atlas-inputs.json").read_text())
    if manifest.get("schemaVersion") != 1 or len(manifest.get("runs", [])) != 8:
        raise ValueError("expected 8 actual input runs")
    for record in manifest["runs"] + [{"assets": manifest["inputAssets"]}]:
        for asset in record["assets"]:
            relative = Path(asset["path"])
            if relative.is_absolute() or ".." in relative.parts or "\\" in asset["path"]:
                raise ValueError("unsafe asset path")
            file = root / relative
            if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
                raise ValueError("missing or linked source asset")
            if hashlib.sha256(file.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Atlas asset hash mismatch: {relative}")
    return manifest


def f(x):
    if not math.isfinite(x): raise ValueError("nonfinite field")
    return f"{x:.9g}f" if x != int(x) else f"{x:.1f}f"


def generate(root):
    manifest = verified(root)
    runs = {r["id"]: r for r in manifest["runs"]}
    field_rows, wave_rows, trajectory_rows = [], [], []
    for kind in ("filter", "rhythm"):
        record = runs[f"effects-field-{kind}"]
        assert record["engineId"] == "blur-core-v1"
        result = next(a for a in record["assets"] if a["role"] == "result")
        values = json.loads((root / result["path"]).read_text())["output"]
        if len(values) != 16 or any(not 0 <= x <= 1 for x in values):
            raise ValueError("invalid normalized Blur Core field")
        field_rows.append(values)
    for kind in ("bloom", "prism", "fracture"):
        measurement = runs[f"effects-measure-{kind}"]
        rendered = runs[f"effects-render-{kind}"]
        assert measurement["engineId"] == "otoc-echo-v1" and rendered["engineId"] == "retrocausal-echo-v1"
        asset = next(a for a in rendered["assets"] if a["role"] == "result")
        samples = wav_f32(root / asset["path"])
        params = rendered["params"]
        step = params["master_ms"] / 6 / 1000
        row = []
        for depth in range(1, 7):
            center = round(step * depth * 22050)
            # Short signed onset-integral captures phase-tail as well as exact
            # impulses; local DSP still is NOT a remote renderer on music.
            end = min(center + 128, 44100)
            channel = [sum(samples[2 * i + c] for i in range(center, end)) for c in range(2)]
            row.append([max(-1.0, min(1.0, v)) for v in channel])
        wave_rows.append(row)
        m_asset = next(a for a in measurement["assets"] if a["role"] == "result")
        m = json.loads((root / m_asset["path"]).read_text())["output"]["data"]
        r_asset = next(a for a in rendered["assets"] if a["role"] == "ir")
        ir = json.loads((root / r_asset["path"]).read_text())["data"]
        if m["series"] != ir["series"]:
            raise ValueError("measured trajectory differs from supplied render IR")
        trajectory_rows.append([[m["series"][key][2][depth] for key in ("F_re", "F_im")]
                                for depth in range(6)])
    def array2(rows):
        return ",\n".join("    {{ " + ", ".join("{{ " + ", ".join(f(x) for x in pair) + " }}" for pair in row) + " }}" for row in rows)
    hashes = [hashlib.sha256((root / "atlas-inputs.json").read_bytes()).hexdigest()]
    for name in ("bloom", "prism", "fracture"):
        hashes.append(next(a["sha256"] for a in runs[f"effects-render-{name}"]["assets"] if a["role"] == "result"))
    return ("// GENERATED by scripts/make_atlas_study_data.py from lead-owned hash-checked Atlas assets.\n"
            "// Atlas output guides LOCAL classical DSP; no hardware/remote-plugin processing claim.\n"
            "#pragma once\n#include <array>\nnamespace garden::atlasStudy {\n"
            "inline constexpr const char* manifestSha256 = \"" + hashes[0] + "\";\n"
            "inline constexpr std::array<const char*, 3> renderedWavSha256 {{ " + ", ".join('"' + x + '"' for x in hashes[1:]) + " }};\n"
            "inline constexpr std::array<std::array<float, 16>, 2> fields {{\n"
            + ",\n".join("    {{ " + ", ".join(f(x) for x in row) + " }}" for row in field_rows)
            + "\n}};\n"
            "inline constexpr std::array<std::array<std::array<float, 2>, 6>, 3> remoteOnsetSums {{\n"
            + array2(wave_rows) + "\n}};\n"
            "inline constexpr std::array<std::array<std::array<float, 2>, 6>, 3> measuredCenterComplex {{\n"
            + array2(trajectory_rows) + "\n}};\n}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, default=Path("effects-inputs"))
    p.add_argument("--out", type=Path, default=Path("src/AtlasStudyData.h"))
    args = p.parse_args()
    text = generate(args.inputs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(args.out, hashlib.sha256(text.encode()).hexdigest())
