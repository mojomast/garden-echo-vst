#!/usr/bin/env python3
"""Independently check every ZIP payload against its embedded SHA-256 index."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


SENSITIVE_PATTERNS = {
    "private Tailnet hostname": re.compile(rb"(?i)[a-z0-9.-]+\.ts\.net(?::[0-9]+)?"),
    "Tailscale IPv4": re.compile(rb"(?<![0-9])100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])(?:\.[0-9]{1,3}){2}(?![0-9])"),
    "Tailscale IPv6": re.compile(rb"(?i)fd7a:" rb"115c:" rb"a1e0(?::[0-9a-f]+)*"),
    "personal home path": re.compile(rb"/" rb"home/[A-Za-z0-9._-]+"),
    "email address": re.compile(rb"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])"),
    "authorization header value": re.compile(rb"(?i)authorization\s*:\s*(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+"),
    "signed URL query": re.compile(rb"(?i)(?:x-amz-signature|x-goog-signature|signature)=[A-Za-z0-9%._~+-]+"),
}


def scan_text_payload(name, payload):
    if b"\0" in payload[:8192]:
        return False
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError:
        return False
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(payload):
            raise ValueError(f"sensitive text ({label}) in: {name}")
    return True


def verify(archive):
    text_payloads = 0
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or "manifest.sha256.json" not in names:
            raise ValueError("duplicate/missing archive entries")
        manifest = json.loads(z.read("manifest.sha256.json"))
        files = manifest["files"]
        if set(names) != (set(files) | {"manifest.sha256.json"}):
            raise ValueError("archive/index file mismatch")
        for name, record in files.items():
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise ValueError("unsafe path: " + name)
            payload = z.read(name)
            if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                raise ValueError("file digest/length mismatch: " + name)
            text_payloads += int(scan_text_payload(name, payload))
        bundle = {name.removeprefix("Garden Echo.vst3/"): record["sha256"]
                  for name, record in files.items() if name.startswith("Garden Echo.vst3/")}
        canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
        if hashlib.sha256(canonical).hexdigest() != manifest["vst3BundleTreeSha256"]:
            raise ValueError("bundle digest mismatch")
        modules = [value for name, value in bundle.items() if name.startswith("Contents/x86_64-linux/") and name.endswith(".so")]
        if modules != [manifest["vst3ModuleSha256"]]:
            raise ValueError("module digest mismatch")
    checksum = archive.with_name(archive.name + ".sha256")
    expected = checksum.read_text().split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError("archive checksum mismatch")
    print(f"PASS: {len(files)} payloads, {text_payloads} UTF-8 text payloads sanitized, VST3 module, bundle tree and archive SHA-256")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        verify(args.archive)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        sys.exit("FAIL archive: " + str(error))
