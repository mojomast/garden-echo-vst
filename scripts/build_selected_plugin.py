#!/usr/bin/env python3
"""NON-SHIP developer tool: validated compile-time candidate-menu shortlist.

The default shipped build includes all twelve studies. Neither this script
nor a selection export installs/swaps an existing plugin.
Run the explicit CMake command in docs only after owner review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from install_effects_selection import install
from prepare_native_stage import STUDIES


def build(bank, selection, out):
    if out.exists() or not out.name.endswith(".h"):
        raise ValueError("selected header path must be a new .h file")
    out.parent.mkdir(parents=True, exist_ok=True)
    config = out.with_suffix(".selection.json")
    if config.exists():
        raise ValueError("selection configuration already exists")
    install(bank, selection, config)  # validates ALL bank bytes/lineage/decisions
    doc = json.loads(config.read_bytes())
    bank_sha = doc["bankSha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", bank_sha)
    selected = set(doc["selectedEffectIds"])
    identities = [study[0] for study in STUDIES]
    if set(selected) - set(identities):
        raise ValueError("selection ID not in compiled fixed plugin catalog")
    values = ",".join("true" if eid in selected else "false" for eid in identities)
    raw = ("// Owner-exported shortlist, validated against exact bank bytes; no approval implied.\n"
           "#pragma once\n#include <array>\nnamespace garden::selection {\n"
           "inline constexpr bool enabled = true;\n"
           f'inline constexpr const char* bankSha256 = "{bank_sha}";\n'
           f"inline constexpr std::array<bool, 12> allowed {{{{ {values} }}}};\n"
           "}\n").encode()
    with out.open("xb") as target:
        target.write(raw)
    out.chmod(0o444)
    return len(selected), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        count, digest = build(args.bank, args.selection, args.out)
        print(f"Shortlist header: {args.out}; {count} explicit choices; sha256:{digest}")
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, "Rejected: " + str(exc) + "\n")


if __name__ == "__main__":
    sys.exit(main())
