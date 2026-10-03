#!/usr/bin/env python3
"""Prepare native effect study inventory, then hash only existing native renders.

Usage:
  python3 scripts/prepare_native_stage.py prepare --atlas effects-inputs --header src/AtlasStudyData.h --core src/EffectCore.h --stage build/native-stage
  GardenBankRender build/effects-cues build/native-stage build/native-stage/effects.json
  python3 scripts/prepare_native_stage.py finalize --atlas effects-inputs --header src/AtlasStudyData.h --core src/EffectCore.h --stage build/native-stage --renderer build/GardenBankRender
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from build_effects_bank import SOURCES, checked, digest, document, load_json, require, safe_file, wav_stats
from make_atlas_study_data import generate, verified


# Order is the one-based native study selector. These are independent local DSP
# studies; the Atlas study family beside each is source lineage, not a promise
# that a remote service processed the dry cues.
STUDIES = (
    ("terrace", "Terrace Multitap", "Sparse early-reflection delay", "bloom"),
    ("crossing", "Crossing Ping-Pong", "Cross-coupled stereo repeats", "prism"),
    ("amber", "Amber Dub", "Dark low-pass feedback echo", "fracture"),
    ("petal", "Petal Chorus", "Short quadrature modulated delay", "bloom"),
    ("canopy", "Canopy Ensemble", "Three detuned delay voices", "prism"),
    ("ribbon", "Ribbon Flanger", "Short swept feedback comb", "fracture"),
    ("wire", "Wire Resonator", "Tuned damped comb resonance", "bloom"),
    ("mist", "Mist Diffuser", "Cascaded stereo all-pass dispersion", "prism"),
    ("lantern", "Lantern Tremolo Echo", "Opposed stereo amplitude pulses", "fracture"),
    ("brook", "Brook Filter Sweep", "Field-driven low-pass motion with short echo", "bloom"),
    ("prism", "Prism Stereo Doubler", "Asymmetric short stereo delays", "prism"),
    ("steps", "Steps Rhythmic Taps", "Signed syncopated delay pattern", "fracture"),
)

FAMILIES = ("Multitap", "Ping-Pong", "Dub Delay", "Chorus", "Ensemble", "Flanger",
            "Resonator", "Diffusion", "Tremolo Echo", "Filter Echo", "Doubler", "Rhythmic Delay")


def source_ids(kind):
    return ["effects-measure-" + kind, "effects-render-" + kind,
            "effects-field-filter", "effects-field-rhythm"]


def inputs(atlas, header, core):
    manifest = verified(atlas)  # all run and input asset bytes checked against the lead's SHA256
    runs = {r["id"]: r for r in manifest["runs"]}
    expected = {"effects-field-" + k for k in ("filter", "rhythm")}
    expected |= {"effects-" + prefix + "-" + k for prefix in ("measure", "render")
                 for k in ("bloom", "prism", "fracture")}
    require(len(runs) == len(manifest["runs"]) == 8 and set(runs) == expected,
            "expected eight distinct delivered study runs")
    for run in runs.values():
        require(run.get("jobId") and run.get("execution") == "simulator", "missing real simulator job attribution")
    require(header.is_file() and not header.is_symlink(), "missing generated Atlas header")
    require(header.read_bytes() == generate(atlas).encode(), "Atlas header differs from verified generated data")
    require(core.is_file() and not core.is_symlink(), "missing native study core")
    text = core.read_text()
    ids = re.findall(r'\{\s*"([a-z][a-z0-9-]*)"\s*,\s*"', text)
    require(ids[:len(STUDIES)] == [row[0] for row in STUDIES], "native preset order differs from metadata studyIndex")
    # Do not present the header's control values as active until the native core
    # actually references them. This also catches a stale, unintegrated core.
    # The tiny static sample processor reads the two 16-cell envelopes, while
    # its installed presets map the three measured/waveform sources before play.
    # Check both codepaths, not merely a source comment with provenance words.
    mapped = core.with_name("AtlasStudyPresets.h")
    processor = core.with_name("PluginProcessor.cpp")
    extra = (mapped.read_text() if mapped.is_file() else "") + (processor.read_text() if processor.is_file() else "")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text + extra, flags=re.DOTALL)
    require('include "AtlasStudyData.h"' in text and all("atlasStudy::" + key in code for key in
            ("fields", "remoteOnsetSums", "measuredCenterComplex")) and
            ("atlasMappedPreset" in code),
            "native core has not integrated all generated Atlas controls")
    return manifest


def inventory(atlas, header, core):
    inputs(atlas, header, core)
    effects = []
    for index, (eid, name, description, kind) in enumerate(STUDIES, 1):
        atlas_role = ("OTOC measured complex trajectory and linked Retro 22.05 kHz float WAV for " + kind +
                      " provide six signed stereo 128-frame onset sums. Both Blur Core 16-step fields guide "
                      "bounded controls; fields cycle as envelopes in studies 9/10. Classical local DSP, "
                      "not remote processing of music. Prism's dense phase-mode WAV is NOT fully convolved "
                      "or represented as a literal six-tap IR.")
        effects.append({"id": eid, "name": name, "family": FAMILIES[index - 1],
                        "description": description, "atlasRole": atlas_role,
                        "localProcessing": ("Native classical DSP study: " + description.lower() +
                                            "; wet/dry 0.55, predelay 0 ms, SAME +4 dB audition trim on every wet "
                                            "render (dry cues untrimmed). Four-second cues include tails; "
                                            "no per-effect/file normalization. Dry/wet loudness only approximately matched."),
                        "parameters": {"studyIndex": index, "wet": 0.55, "predelayMs": 0, "trimDb": 4,
                                       "auditionGainDb": 4},
                        "sourceRunIds": source_ids(kind), "studyIndex": index, "wet": 0.55, "trim": 4.0})
    require(set().union(*(set(e["sourceRunIds"]) for e in effects)) ==
            {r["id"] for r in load_json((atlas / "atlas-inputs.json").read_bytes())["runs"]},
            "not all delivered runs represented")
    return {"schemaVersion": 1, "effects": effects}


def write_new(path, raw):
    require(not path.exists() and not path.is_symlink(), "output already exists: " + str(path))
    path.write_bytes(raw)


def separate_stage(atlas, header, core, stage):
    stage_path = stage.resolve()
    require(not stage_path.is_relative_to(atlas.resolve()) and
            not atlas.resolve().is_relative_to(stage_path) and
            not header.resolve().is_relative_to(stage_path) and
            not core.resolve().is_relative_to(stage_path), "stage overlaps inputs")


def prepare(atlas, header, core, stage):
    separate_stage(atlas, header, core, stage)
    metadata = inventory(atlas, header, core)
    require(not stage.exists() or stage.is_dir(), "stage is not a directory")
    stage.mkdir(parents=True, exist_ok=True)
    write_new(stage / "effects.json", document(metadata))
    return metadata


def finalize(atlas, header, core, stage, renderer):
    separate_stage(atlas, header, core, stage)
    expected = inventory(atlas, header, core)
    supplied = load_json(safe_file(stage, "effects.json").read_bytes())
    require(supplied == expected, "effects.json differs from current verified source inventory")
    require(renderer.is_file() and not renderer.is_symlink() and renderer.stat().st_size > 0,
            "explicit native renderer binary is missing")
    require(not (stage / "renders.json").exists(), "renders.json already exists")
    for effect in expected["effects"]:
        renders = []
        for sid, _, _ in SOURCES:
            path = effect["id"] + "-" + sid + ".wav"
            raw = safe_file(stage, path).read_bytes()
            wav_stats(raw)
            renders.append({"sourceId": sid, "path": path, "sha256": digest(raw)})
        effect["renders"] = renders
        del effect["studyIndex"], effect["wet"], effect["trim"]
    expected["renderOrigin"] = "experimental-native-plugin"
    expected["renderImplementation"] = ("GardenBankRender executable sha256:" +
                                         digest(renderer.read_bytes()) + "; generated AtlasStudyData.h sha256:" +
                                         digest(header.read_bytes()) + "; native EffectCore.h sha256:" +
                                         digest(core.read_bytes()) + "; AtlasStudyPresets.h sha256:" +
                                         digest(core.with_name("AtlasStudyPresets.h").read_bytes()) +
                                         "; PluginProcessor.cpp sha256:" +
                                         digest(core.with_name("PluginProcessor.cpp").read_bytes()))
    write_new(stage / "renders.json", document(expected))
    return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "finalize"))
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--renderer", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            require(args.renderer is None, "--renderer belongs to finalize")
            prepare(args.atlas, args.header, args.core, args.stage)
        else:
            require(args.renderer is not None, "finalize requires --renderer")
            finalize(args.atlas, args.header, args.core, args.stage, args.renderer)
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError) as exc:
        parser.exit(2, "Rejected: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
