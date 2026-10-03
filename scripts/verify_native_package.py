#!/usr/bin/env python3
"""Independently verify a Garden Echo binary/source ZIP pair and SHA-256 sidecars.

Use --repo and --juce-root to compare every packaged source byte to the exact
local Git commits. Without them, commit IDs are checked as declarations only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import zipfile

VERSION = "0.2.0-rc.1"
JUCE_COMMIT = "91ad83ae34a81e0833b1a2b0866f54846370ae53"
PLATFORMS = ("linux-x86_64", "windows-x64", "macos-universal")
MAX_FILES = 100000
MAX_ENTRY = 1024 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def demand(ok, message):
    if not ok:
        raise ValueError(message)


def safe_path(name):
    demand(isinstance(name, str) and name and len(name) <= 1024 and
           not name.startswith("/") and not re.match(r"^[A-Za-z]:", name) and
           "\\" not in name and all(part not in ("", ".", "..") for part in name.split("/")) and
           not any(ord(c) < 32 or ord(c) == 127 for c in name),
           "unsafe ZIP path: " + repr(name))


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        demand(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_json,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON: " + value)))


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar(path):
    check = path.with_name(path.name + ".sha256")
    demand(check.is_file() and not check.is_symlink(), "missing checksum sidecar: " + str(check))
    text = check.read_bytes()
    demand(len(text) < 256 and text.isascii(), "invalid checksum sidecar")
    match = re.fullmatch(rb"([0-9a-f]{64})  ([^\r\n]+)\n", text)
    demand(match is not None and match[2].decode("ascii") == path.name,
           "checksum sidecar filename/format mismatch: " + str(check))
    demand(hash_file(path) == match[1].decode("ascii"), "ZIP checksum mismatch: " + str(path))


def archive(path, kind, platform, commit):
    demand(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_TOTAL,
           "missing, symlink or oversized ZIP: " + str(path))
    base = f"Garden-Echo-{VERSION}-{platform}"
    expected = base + (".zip" if kind == "binary" else "-source.zip")
    demand(path.name == expected, "unexpected ZIP filename: " + path.name)
    sidecar(path)
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        demand(len(entries) <= MAX_FILES and len(entries) >= 2, "invalid ZIP entry count")
        names = [info.filename for info in entries]
        demand(len(set(names)) == len(names) and "manifest.sha256.json" in names,
               "duplicate entries or missing manifest")
        total = 0
        for info in entries:
            safe_path(info.filename)
            mode = info.external_attr >> 16
            demand(not info.is_dir() and stat.S_IFMT(mode) == stat.S_IFREG and
                   info.create_system == 3 and mode & 0o7000 == 0,
                   "directory, link or special ZIP entry: " + info.filename)
            demand(info.flag_bits & 1 == 0 and info.compress_type == zipfile.ZIP_DEFLATED,
                   "encrypted or unsupported ZIP entry: " + info.filename)
            demand(info.file_size <= MAX_ENTRY and info.compress_size <= MAX_ENTRY and
                   total + info.file_size <= MAX_TOTAL, "ZIP size limit exceeded")
            total += info.file_size
        manifest_info = z.getinfo("manifest.sha256.json")
        demand(manifest_info.file_size <= 16 * 1024 * 1024, "oversized manifest")
        manifest = parse_json(z.read(manifest_info))
        common = {"version", "platform", "sourceCommit", "juceCommit", "kind", "files"}
        specific = ({"modulePath", "moduleSha256", "sourceArchive"} if kind == "binary"
                    else {"binaryArchive"})
        demand(isinstance(manifest, dict) and set(manifest) == common | specific,
               "invalid manifest fields")
        demand(manifest["version"] == VERSION and manifest["platform"] == platform and
               manifest["sourceCommit"] == commit and manifest["juceCommit"] == JUCE_COMMIT and
               manifest["kind"] == kind, "manifest version/platform/commit/kind mismatch")
        files = manifest["files"]
        demand(isinstance(files, dict) and set(files) == set(names) - {"manifest.sha256.json"},
               "ZIP inventory mismatch")
        for info in entries:
            if info.filename == "manifest.sha256.json":
                continue
            record = files[info.filename]
            demand(isinstance(record, dict) and set(record) == {"sha256", "bytes", "mode"} and
                   isinstance(record["sha256"], str) and SHA.fullmatch(record["sha256"]) and
                   type(record["bytes"]) is int and record["bytes"] == info.file_size and
                   record["mode"] == format((info.external_attr >> 16) & 0o777, "04o"),
                   "invalid file inventory record: " + info.filename)
            h = hashlib.sha256()
            length = 0
            with z.open(info) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    length += len(chunk)
                    demand(length <= info.file_size and length <= MAX_ENTRY, "expanded ZIP size exceeded")
                    h.update(chunk)
            demand(length == record["bytes"] and h.hexdigest() == record["sha256"],
                   "payload hash/size mismatch: " + info.filename)
        if kind == "binary":
            demand(manifest["sourceArchive"] == base + "-source.zip", "source archive cross-link mismatch")
            required = {"INSTALL.md", "LICENSE", "THIRD_PARTY_NOTICES.md"}
            required.update("third_party/" + name for name in (
                "JUCE-LICENSE.md", "vst3sdk-LICENSE.txt", "FLAC-LICENSE.txt",
                "Vorbis-LICENSE.txt", "JPEG-LICENSE.txt", "PNG-LICENSE.txt",
                "Zlib-LICENSE.txt", "HarfBuzz-LICENSE.txt", "SheenBidi-LICENSE.txt"))
            demand(required <= files.keys() and
                   len([n for n in files if re.fullmatch(r"TEST_REPORT\.(json|txt|md)", n)]) == 1 and
                   any(n.startswith("Garden Echo.vst3/") for n in files) and
                   all(n in required or n.startswith("Garden Echo.vst3/") or
                       re.fullmatch(r"TEST_REPORT\.(json|txt|md)", n) for n in files),
                   "binary bundle/support files missing or unexpected")
            folder, ext = {"linux-x86_64": ("Contents/x86_64-linux/", ".so"),
                           "windows-x64": ("Contents/x86_64-win/", ".vst3"),
                           "macos-universal": ("Contents/MacOS/", "")}[platform]
            prefix = "Garden Echo.vst3/" + folder
            modules = [n for n in files if n.startswith(prefix) and
                       "/" not in n[len(prefix):] and n.endswith(ext)]
            demand(len(modules) == 1 and manifest["modulePath"] == modules[0] and
                   manifest["moduleSha256"] == files[modules[0]]["sha256"],
                   "module path/hash mismatch")
            with z.open(modules[0]) as stream:
                header = stream.read(4096)
                architecture(header, platform, files[modules[0]]["bytes"], stream)
        else:
            demand(manifest["binaryArchive"] == base + ".zip", "binary archive cross-link mismatch")
            required = {"garden-echo/LICENSE", "garden-echo/THIRD_PARTY_NOTICES.md",
                        "garden-echo/CMakeLists.txt", "garden-echo/submission/REPRODUCE.md",
                        "JUCE/LICENSE.md", "JUCE/CMakeLists.txt", "PACKAGE_README.md"}
            demand(required <= files.keys() and
                   all(n == "PACKAGE_README.md" or n.startswith("garden-echo/") or
                       n.startswith("JUCE/") for n in files) and
                   any(n.startswith("garden-echo/src/") for n in files) and
                   any(n.startswith("JUCE/modules/") for n in files),
                   "source license/build/source files missing or unexpected")
        return manifest


def architecture(data, platform, module_size, stream=None):
    if platform == "linux-x86_64":
        demand(len(data) >= 20 and data[:6] == b"\x7fELF\x02\x01" and
               struct.unpack_from("<H", data, 18)[0] == 62, "incorrect ELF architecture")
    elif platform == "windows-x64":
        demand(len(data) >= 0x40 and data[:2] == b"MZ", "incorrect PE signature")
        offset = struct.unpack_from("<I", data, 0x3c)[0]
        demand(offset + 24 <= len(data) and data[offset:offset + 4] == b"PE\0\0" and
               struct.unpack_from("<H", data, offset + 4)[0] == 0x8664, "incorrect PE architecture")
    else:
        magic = data[:4]
        demand(magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
                         b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"), "incorrect Mach-O FAT signature")
        endian = ">" if magic[0] == 0xca else "<"
        width = 32 if magic in (b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca") else 20
        demand(len(data) >= 8, "truncated FAT header")
        count = struct.unpack_from(endian + "I", data, 4)[0]
        demand(2 <= count <= 64 and 8 + count * width <= len(data), "invalid FAT table")
        cpus = set()
        for i in range(count):
            cpu, _, start, size = struct.unpack_from(endian + ("IIQQ" if width == 32 else "IIII"),
                                                       data, 8 + i * width)
            demand(size >= 8 and start >= 8 + count * width and start + size <= module_size,
                   "invalid FAT slice")
            if stream is not None:
                stream.seek(start)
                slice_header = stream.read(8)
                demand(len(slice_header) == 8 and slice_header[:4] in
                       (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"), "invalid Mach-O slice magic")
                slice_endian = "<" if slice_header[0] == 0xcf else ">"
                demand(struct.unpack_from(slice_endian + "I", slice_header, 4)[0] == cpu,
                       "Mach-O slice CPU mismatch")
            cpus.add(cpu)
        demand({0x01000007, 0x0100000c} <= cpus, "universal module missing x86_64/arm64")


def git_tree(repo, commit):
    demand(repo.is_dir() and not repo.is_symlink(), "invalid Git root: " + str(repo))
    def run(*args):
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
        demand(p.returncode == 0, "Git verification failed: " + args[0])
        return p.stdout
    demand(run("rev-parse", "HEAD").strip().decode("ascii") == commit,
           "Git checkout HEAD does not match source commit")
    demand(Path(run("rev-parse", "--show-toplevel").strip().decode()).resolve() == repo.resolve(),
           "Git checkout is not root")
    rows = run("ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0")
    result = {}
    for row in rows:
        if not row:
            continue
        meta, raw_name = row.split(b"\t", 1)
        mode, kind, oid = meta.split()
        demand(kind == b"blob" and mode in (b"100644", b"100755"), "Git tree contains link/special entry")
        name = raw_name.decode("utf-8")
        safe_path(name)
        result[name] = (oid.decode("ascii"), "0755" if mode == b"100755" else "0644")
    demand(result, "empty Git source tree")
    return result


def verify_git(source_path, manifest, repo, juce_root):
    expected = {}
    for prefix, root, commit in (("garden-echo", repo, manifest["sourceCommit"]),
                                 ("JUCE", juce_root, manifest["juceCommit"])):
        for name, record in git_tree(root, commit).items():
            expected[prefix + "/" + name] = record
    files = manifest["files"]
    demand(set(files) - {"PACKAGE_README.md"} == set(expected),
           "source inventory differs from pinned Git trees")
    with zipfile.ZipFile(source_path) as z:
        for name, (oid, mode) in expected.items():
            demand(files[name]["mode"] == mode, "Git mode mismatch: " + name)
            h = hashlib.sha1()
            h.update(f"blob {files[name]['bytes']}\0".encode())
            with z.open(name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            demand(h.hexdigest() == oid, "Git blob mismatch: " + name)
    return {"gardenEcho": len([n for n in expected if n.startswith("garden-echo/")]),
            "JUCE": len([n for n in expected if n.startswith("JUCE/")])}


def verify(binary, source, repo=None, juce_root=None):
    demand(bool(repo) == bool(juce_root), "--repo and --juce-root must be used together")
    match = re.fullmatch(rf"Garden-Echo-{re.escape(VERSION)}-({'|'.join(PLATFORMS)})\.zip", binary.name)
    demand(match is not None, "unrecognized binary archive filename")
    platform = match[1]
    demand(source.name == binary.stem + "-source.zip" and source.resolve().parent == binary.resolve().parent,
           "binary and source archives must be matching siblings")
    # The SHA is declared by both archives; local Git verification can independently attest it.
    with zipfile.ZipFile(binary) as z:
        info = z.getinfo("manifest.sha256.json")
        demand(info.file_size <= 16 * 1024 * 1024, "oversized manifest")
        preliminary = parse_json(z.read(info))
    commit = preliminary.get("sourceCommit")
    demand(isinstance(commit, str) and COMMIT.fullmatch(commit), "invalid source commit SHA")
    b = archive(binary, "binary", platform, commit)
    s = archive(source, "corresponding-source", platform, commit)
    demand(all(b[k] == s[k] for k in ("version", "platform", "sourceCommit", "juceCommit")),
           "archive metadata mismatch")
    for bin_name, src_name in (("LICENSE", "garden-echo/LICENSE"),
                               ("THIRD_PARTY_NOTICES.md", "garden-echo/THIRD_PARTY_NOTICES.md")):
        demand(b["files"][bin_name]["sha256"] == s["files"][src_name]["sha256"],
               "binary/source notice mismatch: " + bin_name)
    counts = verify_git(source, s, repo, juce_root) if repo else None
    return {"status": "verified", "platform": platform, "binaryFiles": len(b["files"]),
            "sourceFiles": len(s["files"]), "sourceCommit": commit,
            "gitTreeCounts": counts}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--archive", type=Path, help="either archive; infer its sibling")
    parser.add_argument("--repo", type=Path, help="local garden-echo Git checkout at sourceCommit")
    parser.add_argument("--juce-root", type=Path, help="local JUCE Git checkout at juceCommit")
    args = parser.parse_args(argv)
    if args.archive:
        if args.binary or args.source:
            parser.error("--archive cannot be combined with --binary/--source")
        if args.archive.name.endswith("-source.zip"):
            args.source = args.archive
            args.binary = args.archive.with_name(args.archive.name.removesuffix("-source.zip") + ".zip")
        elif args.archive.name.endswith(".zip"):
            args.binary = args.archive
            args.source = args.archive.with_name(args.archive.name.removesuffix(".zip") + "-source.zip")
        else:
            parser.error("--archive must name a .zip")
    elif not args.binary or not args.source:
        parser.error("supply --binary and --source, or --archive")
    try:
        result = verify(args.binary, args.source, args.repo, args.juce_root)
    except (ValueError, OSError, KeyError, IndexError, UnicodeError, zipfile.BadZipFile,
            json.JSONDecodeError, struct.error) as error:
        parser.exit(2, "Rejected: " + str(error) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
