#!/usr/bin/env python3
"""Record verified kernel lineage and observed artifact hashes, offline.

Artifact hashes do not establish which binary or preset produced a DAW render.
Historical synthetic evidence remains explicitly identified across reruns.
Use --spaces fixtures/synthetic-v1 for an explicitly synthetic diagnostic record.
"""
import argparse
import json
from pathlib import Path

from import_impulse_kernel import sha, verify_snapshot, write_json
from validate_contract import validate

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spaces", type=Path, default=ROOT / "fixtures/recorded-v1")
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/PROVENANCE.json")
    args = parser.parse_args()
    folder = args.spaces.resolve()
    old = json.loads(args.out.read_text()) if args.out.exists() else {}
    historical = old.get("historicalSyntheticArtifactHashes", {})
    if old.get("evidenceMode") == "synthetic":
        historical.update(old.get("artifactHashes", {}))
    files = ["evidence/audio/garden-echo-demo.flac", "evidence/standalone-ui.png",
             "evidence/daw/reaper-editor.png", "evidence/daw/garden-host-render.wav",
             "evidence/daw/garden-host-smoke.rpp"]
    files += sorted(str(p.relative_to(ROOT)) for p in (ROOT / "evidence/audio").glob("*-*.wav"))
    observed = {p: sha(ROOT / p) for p in files if (ROOT / p).is_file()}
    result = {"schemaVersion": 1, "artifactHashes": observed,
              "artifactHashScope": "Observed local bytes only; artifact hashes alone do not establish recorded-kernel native/host verification",
              "historicalSyntheticArtifactHashes": historical,
              "artifactsStillMatchingHistoricalSyntheticEvidence": [p for p, h in observed.items() if historical.get(p) == h],
              "authoringScriptHashes": {"scripts/" + p: sha(ROOT / "scripts" / p) for p in
                                        ("import_impulse_kernel.py", "make_space_header.py", "test_recorded_import.py")}}
    if folder == ROOT / "fixtures/synthetic-v1":
        pack = json.loads((folder / "garden-pack.json").read_text())
        validate(pack, folder)
        assert pack["evidenceMode"] == "synthetic"
        result.update({"evidenceMode": "synthetic", "sourcePack": "fixtures/synthetic-v1/garden-pack.json",
                       "packId": pack["id"], "atlasJobIds": [], "fixtureRunIds": [r["id"] for r in pack["runs"]],
                       "claim": "Explicit synthetic diagnostic fixture selection; no Atlas job for these kernels"})
    else:
        bundle, metadata = verify_snapshot(folder)
        prefix = str(folder.relative_to(ROOT))
        result.update({"evidenceMode": "atlas-recorded", "sourceBundle": prefix + "/bundle.json",
                       "sourceBundleSha256": sha(folder / "bundle.json"), "spacesSha256": sha(folder / "spaces.json"),
                       "atlasJobIds": bundle["atlasJobIds"], "execution": "simulator (aer/emu), not hardware",
                       "remoteRenderCount": 1, "remoteTrajectoryCount": 1, "curatedPresetCount": 3,
                       "claim": bundle["claim"], "remoteVerification": bundle["remoteVerification"],
                       "sourceHashes": {prefix + "/" + p: h for p, h in bundle["sourceFiles"].items()},
                       "kernelHashes": {prefix + "/" + s["file"]: s["kernelSha256"] for s in metadata["spaces"]},
                       "sourceSignal": bundle["sourceSignal"],
                       "truthReview": "evidence/recorded-source-audit.md",
                       "nativeVerificationScope": "This file verifies recorded authoring lineage only; native tests, pluginval and DAW evidence require their own recorded-mode report"})
    write_json(args.out, result)
    print("Recorded", result["evidenceMode"], "kernel provenance and", len(observed), "observed artifact hashes")


if __name__ == "__main__":
    main()
