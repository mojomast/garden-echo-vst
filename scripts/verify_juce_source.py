#!/usr/bin/env python3
"""Verify pinned JUCE source, including an unpacked archive without Git history."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "91ad83ae34a81e0833b1a2b0866f54846370ae53"
TREE = "b6a07bec21880a1d7e168c8f256a6e6423ef4df1"
MANIFEST = ROOT / "third_party/juce-8.0.15-source-tree.json"


def git_hash(kind, data):
    return hashlib.sha1(kind + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()


def tree_hash(entries):
    tree = {}
    for name, entry in entries.items():
        parts = PurePosixPath(name).parts
        if not parts or name.startswith("/") or "\\" in name or any(p in ("..", ".git") for p in parts):
            raise ValueError("unsafe dependency source path")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        if parts[-1] in node:
            raise ValueError("duplicate dependency source path")
        node[parts[-1]] = (entry["mode"], entry["blobSha1"])

    def encode(node):
        records = []
        for name, child in node.items():
            if isinstance(child, dict):
                mode, digest, key = "40000", encode(child), name.encode() + b"/"
            else:
                mode, digest = child
                if mode not in ("100644", "100755") or len(digest) != 40:
                    raise ValueError("unsupported dependency source entry")
                key = name.encode()
            records.append((key, mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(digest)))
        return git_hash(b"tree", b"".join(data for _, data in sorted(records)))
    return encode(tree)


def write_manifest(source):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args])
    if git("rev-parse", "HEAD").decode().strip() != COMMIT:
        raise ValueError("cannot generate index from a different JUCE commit")
    entries = {}
    for row in git("ls-tree", "-r", "-z", "HEAD").split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, digest = metadata.decode().split()
        if kind != "blob":
            raise ValueError("dependency submodule is not included source")
        entries[name.decode()] = {"mode": mode, "blobSha1": digest}
    if tree_hash(entries) != TREE:
        raise ValueError("dependency source index does not match pinned tree")
    MANIFEST.write_text(json.dumps({"schemaVersion": 1, "commit": COMMIT,
                                  "gitTreeSha1": TREE, "files": entries},
                                 indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify(source):
    source = Path(source).resolve()
    index = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = index["files"]
    if index["commit"] != COMMIT or index["gitTreeSha1"] != TREE or tree_hash(entries) != TREE:
        raise ValueError("dependency source index identity mismatch")
    for name, record in entries.items():
        path = source / name
        if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("missing/nonregular dependency source: " + name)
        for parent in path.parents:
            if parent == source:
                break
            if parent.is_symlink():
                raise ValueError("symlink dependency source directory")
        size = path.stat().st_size
        digest = hashlib.sha1(b"blob " + str(size).encode() + b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != record["blobSha1"]:
            raise ValueError("dependency source content mismatch: " + name)
    # No unexpected source can enter JUCE's globbed builds. Git metadata is not
    # part of corresponding source and may be absent in an unpacked archive.
    actual = set()
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            raise ValueError("unexpected dependency symlink")
        if path.is_file():
            actual.add(relative.as_posix())
    if actual != set(entries):
        raise ValueError("unexpected/missing files in dependency source tree")
    print(f"PASS: pinned JUCE {COMMIT}; {len(entries)} source blobs and Git tree verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--write-manifest-from-git", action="store_true")
    args = parser.parse_args()
    try:
        if args.write_manifest_from_git:
            write_manifest(args.root)
        verify(args.root)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, "FAIL: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
