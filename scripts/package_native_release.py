#!/usr/bin/env python3
"""Package an exact tested VST3 bundle and its corresponding Git source.

--out is an existing output directory. No compilation, download or test is run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile


VERSION = "0.2.0-rc.1"
JUCE_COMMIT = "91ad83ae34a81e0833b1a2b0866f54846370ae53"
PLATFORMS = ("linux-x86_64", "windows-x64", "macos-universal")
ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = {
    "private Tailnet hostname": rb"(?i)[a-z0-9.-]+\.ts\.net(?::[0-9]+)?",
    "Tailscale IPv4": rb"(?<![0-9])100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])(?:\.[0-9]{1,3}){2}(?![0-9])",
    "Tailscale IPv6": rb"(?i)fd7a:" rb"115c:" rb"a1e0(?::[0-9a-f]+)*",
    "personal home path": rb"(?<![A-Za-z0-9])(?:/" rb"home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|(?i:[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9._-]+))",
    "authorization header": rb"(?i)authorization\s*:\s*(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+",
    "signed URL": rb"(?i)(?:x-amz-signature|x-goog-signature|signature)=[A-Za-z0-9%._~+-]+",
    "email address": rb"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])",
}
SENSITIVE = {name: re.compile(pattern) for name, pattern in SENSITIVE.items()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    require(name and not name.startswith("/") and "\\" not in name and
            all(part not in ("", ".", "..") for part in name.split("/")) and
            not any(ord(c) < 32 for c in name) and not name.startswith("//") and
            not re.match(r"^[A-Za-z]:", name), "unsafe archive path: " + repr(name))
    return path


def scan(name, data):
    binary = b"\0" in data[:8192]
    try:
        if not binary:
            data.decode("utf-8")
    except UnicodeDecodeError:
        binary = True
    license_file = (name.startswith("JUCE/") or
                     PurePosixPath(name).name.lower().startswith(("license", "licence", "copying", "notice")) or
                     (name.startswith("third_party/") and "license" in PurePosixPath(name).name.lower()) or
                     "third_party_notices" in name.lower())
    vendor_index = name.endswith("/third_party/juce-8.0.15-source-tree.json")
    for label, pattern in SENSITIVE.items():
        if (label == "email address" and (license_file or vendor_index)) or (name.startswith("JUCE/") and label == "personal home path"):
            continue  # Preserve verbatim upstream source, including example paths and author contacts.
        if binary and label == "email address":
            continue  # Binary byte runs resembling emails are not actionable contact text.
        require(pattern.search(data) is None, f"sensitive text ({label}) in {name}")


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    require(result.returncode == 0, f"git {args[0]} failed for {repo}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout.strip().decode("utf-8")


def source_tree(repo, commit, prefix):
    require(repo.is_dir() and not repo.is_symlink(), f"missing or symlink Git checkout: {repo}")
    require(Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo.resolve(), f"not a Git root: {repo}")
    require(git(repo, "rev-parse", "HEAD") == commit, f"{repo}: HEAD differs from required commit {commit}")
    require(not git(repo, "status", "--porcelain", "--untracked-files=no"), "tracked source changes differ from declared commit")
    with tempfile.TemporaryFile() as archive:
        result = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit], stdout=archive, stderr=subprocess.PIPE)
        require(result.returncode == 0, f"git archive failed for {repo}: {result.stderr.decode(errors='replace').strip()}")
        archive.seek(0)
        files = {}
        with tarfile.open(fileobj=archive, mode="r:") as tar:
            for member in tar:
                if member.isdir():
                    continue
                require(member.isfile(), f"source contains link or special entry: {member.name}")
                safe_name(member.name)
                name = prefix + "/" + member.name
                require(name not in files, "duplicate Git source entry: " + name)
                payload = tar.extractfile(member).read()
                scan(name, payload)
                files[name] = (payload, 0o755 if member.mode & 0o111 else 0o644)
        require(files, f"empty Git source at {repo}")
        return files


def bundle_tree(bundle):
    require(bundle.is_dir() and not bundle.is_symlink() and bundle.name == "Garden Echo.vst3",
            "--bundle must be the Garden Echo.vst3 directory (no symlink)")
    files = {}
    for base, dirs, names in os.walk(bundle, followlinks=False):
        for entry in dirs + names:
            path = Path(base) / entry
            require(not path.is_symlink(), f"symlink in bundle: {path}")
            require(path.is_dir() or path.is_file(), f"special file in bundle: {path}")
        for filename in names:
            path = Path(base) / filename
            rel = path.relative_to(bundle).as_posix()
            safe_name(rel)
            name = bundle.name + "/" + rel
            require(name not in files, "duplicate bundle entry: " + name)
            data = path.read_bytes()
            scan(name, data)
            files[name] = (data, stat.S_IMODE(path.stat().st_mode) & 0o777)
    require(files, "empty VST3 bundle")
    return files


def architecture(data, platform):
    if platform == "linux-x86_64":
        require(len(data) >= 20 and data[:6] == b"\x7fELF\x02\x01" and
                struct.unpack_from("<H", data, 18)[0] == 62, "expected ELF64 little-endian x86_64 module")
    elif platform == "windows-x64":
        require(len(data) >= 0x40 and data[:2] == b"MZ", "expected PE executable (MZ header)")
        offset = struct.unpack_from("<I", data, 0x3c)[0]
        require(offset + 24 <= len(data) and data[offset:offset + 4] == b"PE\0\0" and
                struct.unpack_from("<H", data, offset + 4)[0] == 0x8664,
                "expected PE AMD64 module")
    else:
        require(len(data) >= 8, "expected Mach-O universal (FAT) binary")
        magic = data[:4]
        require(magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
                          b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"), "expected Mach-O FAT binary")
        endian = ">" if magic[0] == 0xca else "<"
        width = 32 if magic in (b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca") else 20
        count = struct.unpack_from(endian + "I", data, 4)[0]
        require(2 <= count <= 64 and 8 + count * width <= len(data), "invalid FAT architecture table")
        cpus = set()
        for index in range(count):
            pos = 8 + index * width
            cpu, _, start, size = struct.unpack_from(endian + ("IIQQ" if width == 32 else "IIII"), data, pos)
            require(size >= 8 and start >= 8 + count * width and start + size <= len(data),
                    "invalid Mach-O slice range")
            slice_magic = data[start:start + 4]
            require(slice_magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"),
                    "invalid Mach-O slice magic")
            slice_endian = "<" if slice_magic[0] == 0xcf else ">"
            require(struct.unpack_from(slice_endian + "I", data, start + 4)[0] == cpu,
                    "Mach-O slice CPU does not match FAT table")
            cpus.add(cpu)
        require({0x01000007, 0x0100000c} <= cpus, "Mach-O FAT must contain x86_64 and arm64")


def module_name(files, platform):
    directory, suffix = {
        "linux-x86_64": ("Contents/x86_64-linux/", ".so"),
        "windows-x64": ("Contents/x86_64-win/", ".vst3"),
        "macos-universal": ("Contents/MacOS/", ""),
    }[platform]
    matches = [name for name in files if name.startswith("Garden Echo.vst3/" + directory)
               and "/" not in name.removeprefix("Garden Echo.vst3/" + directory)
               and name.endswith(suffix)]
    require(len(matches) == 1, f"expected exactly one {platform} module in Contents/{directory}: got {matches}")
    architecture(files[matches[0]][0], platform)
    return matches[0]


def document(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def add(files, name, content):
    safe_name(name)
    require(name not in files, "archive entry collision: " + name)
    data = content.encode() if isinstance(content, str) else content
    scan(name, data)
    files[name] = (data, 0o644)


def install_text(platform):
    path = {"linux-x86_64": "~/.vst3/", "windows-x64":
            r"C:\Program Files\Common Files\VST3", "macos-universal": "~/Library/Audio/Plug-Ins/VST3/"}[platform]
    windows = ("The Windows system-wide location requires administrator permission; "
               "alternatively use a per-user VST3 folder supported/configured by your host.\n\n"
               if platform == "windows-x64" else "")
    mac = ("This package is unsigned/not notarized unless independently signed in the release pipeline. "
           "macOS Gatekeeper may block it; seek a trusted, approved signed build. "
           "No blanket quarantine-disabling command is recommended.\n\n"
           if platform == "macos-universal" else "")
    return (f"# Garden Echo {VERSION} — {platform}\n\n"
             "Extract the binary ZIP and copy the complete `Garden Echo.vst3` directory "
             f"to `{path}`. Restart/rescan your VST3 host. To uninstall, remove that "
             "directory and rescan. Keep the complete bundle intact.\n\n" + windows + mac +
             "The matching source ZIP includes exact project and JUCE source, licenses, "
             "build instructions in garden-echo/submission/REPRODUCE.md and PACKAGE_README.md, "
              "and a file hash inventory. The source ZIP includes an offline-verifiable JUCE "
              "tree and does not require Git history to configure. "
             "The bundled test report is a copy of supplied evidence, not a fresh validation. "
             "See garden-echo/evidence/KNOWN_LIMITATIONS.md in the source ZIP.\n")


def write_zip(target, files, meta):
    indexed = {name: {"sha256": digest(data), "bytes": len(data), "mode": format(mode, "04o")}
               for name, (data, mode) in sorted(files.items())}
    manifest = dict(meta, files=indexed)
    payloads = dict(files)
    payloads["manifest.sha256.json"] = (document(manifest), 0o644)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for name, (data, mode) in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((stat.S_IFREG | mode) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            info._compresslevel = 9
            archive.writestr(info, data)
    with zipfile.ZipFile(target) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), "duplicate ZIP entries")
        require(json.loads(archive.read("manifest.sha256.json")) == manifest, "manifest roundtrip failed")
        for name, record in indexed.items():
            data = archive.read(name)
            require(len(data) == record["bytes"] and digest(data) == record["sha256"],
                    "ZIP payload verification failed: " + name)
    return manifest


def package(args):
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_commit) is not None,
            "--source-commit must be a full lowercase 40-character Git SHA")
    out = args.out
    require(out.is_dir() and not out.is_symlink(), "--out must be an existing non-symlink directory")
    require(args.test_report.is_file() and not args.test_report.is_symlink(),
            "--test-report must be an existing non-symlink JSON or UTF-8 text file")
    require(args.test_report.suffix.lower() in (".json", ".txt", ".md"),
            "--test-report must have .json, .txt or .md extension")
    report = args.test_report.read_bytes()
    require(report and b"\0" not in report, "empty or binary test report")
    report.decode("utf-8")
    if args.test_report.suffix.lower() == ".json":
        json.loads(report)
    scan("test-report" + args.test_report.suffix.lower(), report)
    binary = bundle_tree(args.bundle)
    module = module_name(binary, args.platform)
    source = source_tree(ROOT, args.source_commit, "garden-echo")
    source.update(source_tree(args.juce_root, JUCE_COMMIT, "JUCE"))
    require("garden-echo/LICENSE" in source and "garden-echo/THIRD_PARTY_NOTICES.md" in source and
            "JUCE/LICENSE.md" in source and "garden-echo/submission/REPRODUCE.md" in source,
            "corresponding-source checkout missing required license/notices/build guide")
    base = f"Garden-Echo-{VERSION}-{args.platform}"
    add(binary, "INSTALL.md", install_text(args.platform))
    add(binary, "LICENSE", source["garden-echo/LICENSE"][0])
    add(binary, "THIRD_PARTY_NOTICES.md", source["garden-echo/THIRD_PARTY_NOTICES.md"][0])
    add(binary, "third_party/JUCE-LICENSE.md", source["JUCE/LICENSE.md"][0])
    notice_paths = {
        "vst3sdk-LICENSE.txt": "JUCE/modules/juce_audio_processors_headless/format_types/VST3_SDK/LICENSE.txt",
        "FLAC-LICENSE.txt": "JUCE/modules/juce_audio_formats/codecs/flac/Flac Licence.txt",
        "Vorbis-LICENSE.txt": "JUCE/modules/juce_audio_formats/codecs/oggvorbis/Ogg Vorbis Licence.txt",
        "JPEG-LICENSE.txt": "JUCE/modules/juce_graphics/image_formats/jpglib/README",
        "PNG-LICENSE.txt": "JUCE/modules/juce_graphics/image_formats/pnglib/LICENSE",
        "Zlib-LICENSE.txt": "JUCE/modules/juce_core/zip/zlib/README",
        "HarfBuzz-LICENSE.txt": "JUCE/modules/juce_graphics/fonts/harfbuzz/COPYING",
        "SheenBidi-LICENSE.txt": "JUCE/modules/juce_graphics/unicode/sheenbidi/LICENSE",
    }
    for destination, origin in notice_paths.items():
        require(origin in source, "missing dependency notice: " + origin)
        add(binary, "third_party/" + destination, source[origin][0])
    add(binary, "TEST_REPORT" + args.test_report.suffix.lower(), report)
    add(source, "PACKAGE_README.md", install_text(args.platform) +
        "\nThe garden-echo/ and JUCE/ trees are complete git-archive exports at the "
        "commits in manifest.sha256.json. Configure the extracted garden-echo/ source with "
        "-DJUCE_ROOT pointing at the extracted JUCE/ directory. CMake verifies every JUCE "
        "blob and the pinned source-tree identity without requiring .git metadata. Build "
        "garden-echo/ per submission/REPRODUCE.md; install the documented build prerequisites.\n")
    names = [base + ".zip", base + "-source.zip"]
    require(all(not (out / (name + suffix)).exists() for name in names for suffix in ("", ".sha256")),
            "output archive or checksum already exists; choose a clean --out directory")
    require(not out.resolve().is_relative_to(args.bundle.resolve()) and
            not out.resolve().is_relative_to(args.juce_root.resolve()), "--out overlaps input tree")
    common = {"version": VERSION, "platform": args.platform, "sourceCommit": args.source_commit,
              "juceCommit": JUCE_COMMIT}
    temps = []
    try:
        for name, files, meta in (
            (names[0], binary, {**common, "kind": "binary", "modulePath": module,
                                "moduleSha256": digest(binary[module][0]), "sourceArchive": names[1]}),
            (names[1], source, {**common, "kind": "corresponding-source", "binaryArchive": names[0]}),
        ):
            with tempfile.NamedTemporaryFile(dir=out, prefix=".package-", suffix=".zip", delete=False) as tmp:
                temporary = Path(tmp.name)
            temps.append(temporary)
            write_zip(temporary, files, meta)
            checksum = digest(temporary.read_bytes())
            with tempfile.NamedTemporaryFile(dir=out, prefix=".package-", suffix=".sha256", delete=False) as tmp:
                sidecar = Path(tmp.name)
                tmp.write(f"{checksum}  {name}\n".encode())
            temps.append(sidecar)
        for index, name in enumerate(names):
            os.replace(temps[index * 2], out / name)
            os.replace(temps[index * 2 + 1], out / (name + ".sha256"))
    finally:
        for path in temps:
            path.unlink(missing_ok=True)
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--juce-root", type=Path, required=True)
    parser.add_argument("--test-report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        names = package(args)
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(2, "Rejected: " + str(error) + "\n")
    print(document({"archives": [str(args.out / name) for name in names], "status": "verified"}).decode(), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
