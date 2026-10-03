#!/usr/bin/env python3
"""Validate an owner-exported selection against exact bank bytes; install offline config."""
import argparse
import datetime
import json
import sys
from pathlib import Path

from build_effects_bank import (RUN_ID, SHA, checked, digest, document, identifier, load_json,
                                require, safe_file, string, wav_stats)


def validate_bank(bank, raw, claimed_sha):
    require(SHA.fullmatch(claimed_sha) and digest(raw) == claimed_sha, "bank manifest SHA256 mismatch")
    manifest = load_json(raw)
    require(manifest["schemaVersion"] == 1 and manifest["bankId"] == "garden-echo-effects-v1",
            "unsupported bank")
    require(len(manifest["sources"]) == 3 and len(manifest["effects"]) >= 10 and manifest["runs"],
            "incomplete bank")
    paths = set()
    def asset(path, sha):
        require(path not in paths, "duplicate bank asset")
        paths.add(path)
        return checked(bank, path, sha)
    ids = set()
    for src in manifest["sources"]:
        sid = identifier(src["id"])
        require(sid not in ids, "duplicate source ID")
        ids.add(sid)
        stats = wav_stats(asset(src["dryPath"], src["sha256"]))
        require(stats["durationSeconds"] == src["durationSeconds"], "dry duration mismatch")
    require(ids == {"drum", "pluck", "chord"}, "unexpected dry sources")
    run_ids = set()
    for run in manifest["runs"]:
        rid = run["id"]
        require(isinstance(rid, str) and RUN_ID.fullmatch(rid), "invalid run ID")
        require(rid not in run_ids and run["assets"], "duplicate/empty run")
        run_ids.add(rid)
        for entry in run["assets"]:
            require(entry["path"].startswith("provenance/atlas-assets/"), "invalid run asset location")
            asset(entry["path"], entry["sha256"])
    asset("provenance/atlas-inputs.json", digest(safe_file(bank, "provenance/atlas-inputs.json").read_bytes()))
    provenance = load_json(safe_file(bank, "provenance/atlas-inputs.json").read_bytes())
    require(provenance["schemaVersion"] == 1 and provenance["runs"], "invalid provenance")
    require({r["id"] for r in provenance["runs"]} == run_ids, "provenance run mismatch")
    for run in manifest["runs"]:
        original = next(r for r in provenance["runs"] if r["id"] == run["id"])
        require(all(original[k] == run[k] for k in ("engineId", "jobId", "params", "execution")),
                "run attribution mismatch")
        require(len(original["assets"]) == len(run["assets"]), "run assets mismatch")
        for source_asset, copied in zip(original["assets"], run["assets"]):
            require(copied == {"role": source_asset["role"],
                               "path": "provenance/atlas-assets/" + source_asset["path"],
                               "sha256": source_asset["sha256"]}, "run asset attribution mismatch")
    renderer_raw = safe_file(bank, "provenance/render-metadata.json").read_bytes()
    renderer = load_json(renderer_raw)
    require(renderer["renderImplementation"] == manifest["renderImplementation"]
            and renderer["renderOrigin"] == "experimental-native-plugin", "renderer attribution mismatch")
    effect_ids = set()
    require(len(renderer["effects"]) == len(manifest["effects"]), "renderer effect count mismatch")
    for effect, original in zip(manifest["effects"], renderer["effects"]):
        eid = identifier(effect["id"])
        require(eid not in effect_ids and eid == original["id"], "duplicate/mismatched effect ID")
        effect_ids.add(eid)
        require(effect["sourceRunIds"] and all(r in run_ids for r in effect["sourceRunIds"]),
                "unattributed effect")
        require(effect["sourceRunIds"] == original["sourceRunIds"], "effect lineage mismatch")
        require(len(effect["renders"]) == len(original["renders"]) == 3, "incomplete effect renders")
        seen = set()
        for render, external in zip(effect["renders"], original["renders"]):
            sid = identifier(render["sourceId"])
            require(sid in ids and sid not in seen and sid == external["sourceId"], "bad source mapping")
            seen.add(sid)
            require(render["path"] == "audio/" + eid + "-" + sid + ".wav"
                    and render["sha256"] == external["sha256"], "render attribution mismatch")
            stats = wav_stats(asset(render["path"], render["sha256"]))
            require(all(abs(stats[k] - render[k]) < 1e-8 for k in stats), "render metrics mismatch")
    return manifest, effect_ids


def install(bank, selection_path, output):
    require(not output.exists(), "config already exists; immutable export requires new path")
    raw = safe_file(bank, "manifest.json").read_bytes()
    require(selection_path.is_file() and not selection_path.is_symlink()
            and selection_path.stat().st_size <= 100_000, "invalid selection file")
    selection = load_json(selection_path.read_bytes())
    require(isinstance(selection, dict) and set(selection) == {"schemaVersion", "bankId", "bankSha256",
            "selectedEffectIds", "decisions", "notes", "updatedAt"}, "selection schema mismatch")
    manifest, ids = validate_bank(bank, raw, selection["bankSha256"])
    require(selection["schemaVersion"] == 1 and selection["bankId"] == manifest["bankId"],
            "selection bank identity mismatch")
    selected = selection["selectedEffectIds"]
    require(isinstance(selected, list) and len(selected) == len(set(selected)) and all(e in ids for e in selected),
            "invalid selectedEffectIds")
    decisions, notes = selection["decisions"], selection["notes"]
    require(isinstance(decisions, dict) and set(decisions) == ids
            and all(v in ("include", "exclude", "undecided") for v in decisions.values()),
            "missing/invalid decisions")
    require({e for e in ids if decisions[e] == "include"} == set(selected),
            "selected IDs must exactly match explicit include decisions")
    require(isinstance(notes, dict) and set(notes) <= ids
            and all(isinstance(v, str) and len(v) <= 1000 and "\0" not in v for v in notes.values())
            and sum(len(v) for v in notes.values()) <= 10000,
            "invalid/bounded notes")
    timestamp = string(selection["updatedAt"], "updatedAt", 80)
    try:
        dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        require(dt.tzinfo is not None, "updatedAt needs timezone")
    except ValueError as exc:
        raise ValueError("invalid updatedAt") from exc
    config = {"schemaVersion": 1, "bankId": manifest["bankId"], "bankSha256": digest(raw),
              "selectedEffectIds": selected, "decisions": decisions, "notes": notes,
              "updatedAt": timestamp, "installMode": "owner-exported-offline-selection",
              "approval": "selection export only; no automatic plugin activation or owner approval inferred"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(document(config))
    output.chmod(0o444)
    return len(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print("Installed offline config; explicitly selected:", install(args.bank, args.selection, args.out))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print("Rejected: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
