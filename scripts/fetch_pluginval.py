#!/usr/bin/env python3
"""Fetch official pluginval 1.0.4 bytes pinned by SHA-256; never publish the tool."""
import argparse
import hashlib
import io
from pathlib import Path, PurePosixPath
import stat
import urllib.request
import zipfile

ASSETS = {
    "linux-x86_64": ("Linux", "c01c49d8063965c4c2dea8324468336768f5c9139e0b1caebde14c2400b55352", "pluginval"),
    "windows-x64": ("Windows", "c08e61ce3b96db41636f8ec7e76f4c7e2c13ebdac7fa1b5a1f52b4f32ec715ab", "pluginval.exe"),
    "macos-universal": ("macOS", "3c4c533bda0c5059eea3ddaea752d757ee2025041f0f47e6bcb0e87f6082b29f", "pluginval.app/Contents/MacOS/pluginval"),
}


def extract(data, expected, destination):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("pluginval release checksum mismatch")
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        total = 0
        for item in archive.infolist():
            name = PurePosixPath(item.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in item.filename or ":" in item.filename:
                raise ValueError("unsafe tool archive path")
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("tool archive symlink refused")
            if item.is_dir():
                continue
            total += item.file_size
            if item.file_size > 64 * 1024 * 1024 or total > 128 * 1024 * 1024:
                raise ValueError("oversized tool archive")
            path = destination.joinpath(*name.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(archive.read(item))
            path.chmod(0o755 if mode & 0o111 else 0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=ASSETS, required=True)
    parser.add_argument("--out", type=Path, default=Path("build/tools/pluginval"))
    args = parser.parse_args()
    platform, checksum, executable = ASSETS[args.platform]
    url = f"https://github.com/Tracktion/pluginval/releases/download/v1.0.4/pluginval_{platform}.zip"
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        parser.error("oversized pluginval download")
    extract(data, checksum, args.out)
    target = args.out / executable
    if not target.is_file():
        parser.error("pinned release is missing the expected executable")
    print(target.as_posix())


if __name__ == "__main__":
    main()
