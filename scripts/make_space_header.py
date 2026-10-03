#!/usr/bin/env python3
"""Generate compiled, checksummed space descriptors from the immutable fixture."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
fixture = root / "fixtures" / "synthetic-v1"
folder = Path(sys.argv[1]).resolve()
pack = json.loads((fixture / "garden-pack.json").read_text())
metadata = json.loads((folder / "spaces.json").read_text())
for asset in pack["assets"]:
    path = fixture / asset["path"]
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]

if folder == fixture:
    assert metadata["evidenceMode"] == "synthetic"
else:
    # The synthetic diagnostic has no recorded GardenPack dependency. Import
    # the recorded verifier only when that mode is selected; it additionally
    # requires jsonschema in the Python interpreter chosen by CMake.
    from import_impulse_kernel import verify_snapshot
    manifest, metadata = verify_snapshot(folder)
assert [s["id"] for s in metadata["spaces"]] == ["leaf-chamber", "moss-arcade", "rain-canopy"]
for space in metadata["spaces"]:
    path = folder / (space["id"] + ".wav")
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == space["kernelSha256"]
    space.setdefault("provenance", "SYNTHETIC FIXTURE / authored FIR + unit-impulse path / no Atlas job")
spaces = metadata["spaces"] + [{"id": "identity", "name": "Unit impulse", "description": "diagnostic alignment (not a garden)", "kernelSha256": next(a["sha256"] for a in pack["assets"] if a["id"] == "identity"), "tapsSecondsLeftRight": [], "provenance": "SYNTHETIC unit-impulse diagnostic / not an Atlas job"}]
out = Path(sys.argv[2])
out.parent.mkdir(parents=True, exist_ok=True)
lines = ['#pragma once', '#include <array>', '#include <cstddef>', 'namespace garden {',
         'struct SpaceInfo { const char* id; const char* name; const char* description; const char* sha256; const char* provenance; std::array<std::array<float, 3>, 3> taps; };',
         'inline constexpr std::array<SpaceInfo, 4> spaces {{']
for space in spaces:
    taps = list(space['tapsSecondsLeftRight'])
    taps += [[0, 0, 0]] * (3 - len(taps))
    tap_code = '{{' + ', '.join('{{' + ', '.join(f'{float(v):.7f}f' for v in tap) + '}}' for tap in taps) + '}}'
    fields = [json.dumps(space[k]) for k in ('id', 'name', 'description', 'kernelSha256', 'provenance')]
    lines.append('    {' + ', '.join(fields) + ', ' + tap_code + '},')
lines += ['}};', '} // namespace garden', '']
out.write_text('\n'.join(lines))
print('Verified', metadata['evidenceMode'], 'spaces plus synthetic identity diagnostic; generated', out)
