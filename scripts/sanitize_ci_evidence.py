#!/usr/bin/env python3
"""Remap known build paths in a receipt without changing measured test values."""
import argparse
from pathlib import Path


def sanitize(text, root, home=None):
    replacements = [(str(root), "/workspace/garden-echo-vst")]
    if home:
        replacements.append((str(home), "/runner-home"))
    for source, destination in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        variants = {source, source.replace("\\", "/"), source.replace("/", "\\")}
        for variant in sorted(variants, key=len, reverse=True):
            text = text.replace(variant, destination)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    text = args.receipt.read_text(encoding="utf-8", errors="strict")
    args.receipt.write_text(sanitize(text, Path.cwd(), Path.home()), encoding="utf-8")


if __name__ == "__main__":
    main()
