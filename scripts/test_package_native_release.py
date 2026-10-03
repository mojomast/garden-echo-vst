#!/usr/bin/env python3
"""Synthetic security and integration fixtures for native release packaging.

All binaries and project metadata in this module are synthetic test inputs; they
are not release artifacts or submission evidence.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_native_release as packager
import verify_native_package as verifier


def fake_elf(machine=62):
    data = bytearray(64)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", data, 18, machine)
    return bytes(data)


def fake_pe(machine=0x8664):
    data = bytearray(0x80)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 0x40)
    data[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<H", data, 0x44, machine)
    return bytes(data)


def fake_fat(cpus=(0x01000007, 0x0100000c)):
    # FAT_MAGIC and two FAT_ARCH records; slice offsets/sizes are in-range.
    data = bytearray(160)
    struct.pack_into(">II", data, 0, 0xcafebabe, len(cpus))
    for index, cpu in enumerate(cpus):
        offset = 64 + index * 48
        struct.pack_into(">IIIII", data, 8 + index * 20, cpu, 3, offset, 32, 0)
        struct.pack_into("<II", data, offset, 0xfeedfacf, cpu)
    return bytes(data)


class NativeReleasePackageTests(unittest.TestCase):
    def test_platform_architecture_headers_and_mismatches(self):
        packager.architecture(fake_elf(), "linux-x86_64")
        packager.architecture(fake_pe(), "windows-x64")
        packager.architecture(fake_fat(), "macos-universal")
        for data, platform, message in (
            (fake_elf(183), "linux-x86_64", "ELF64"),
            (fake_pe(0x14c), "windows-x64", "AMD64"),
            (fake_fat((0x01000007, 0x01000007)), "macos-universal", "must contain"),
        ):
            with self.subTest(platform=platform), self.assertRaisesRegex(ValueError, message):
                packager.architecture(data, platform)

    def test_archive_paths_reject_traversal_and_absolute_names(self):
        for name in ("../escape", "a/../../escape", "/absolute", "C:/drive", "a\\b"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe archive path"):
                packager.safe_name(name)
        self.assertEqual(str(packager.safe_name("src/module.cpp")), "src/module.cpp")

    def test_bundle_tree_rejects_symlink_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "Garden Echo.vst3"
            bundle.mkdir()
            (bundle / "module.so").write_bytes(b"fixture")
            try:
                (bundle / "linked").symlink_to(bundle / "module.so")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable on this runner")
            with self.assertRaisesRegex(ValueError, "symlink in bundle"):
                packager.bundle_tree(bundle)

    def test_license_contact_email_exception_and_other_privacy_scans(self):
        contact = b"author" + b"@" + b"example.org"
        packager.scan("project/LICENSE", b"Copyright contact: " + contact)
        packager.scan("project/THIRD_PARTY_NOTICES.md", b"Copyright " + contact)
        with self.assertRaisesRegex(ValueError, "email address"):
            packager.scan("project/README.md", b"Contact " + contact)
        with self.assertRaisesRegex(ValueError, "private Tailnet hostname"):
            packager.scan("project/README.md", b"host.example" + b".ts" + b".net")
        with self.assertRaisesRegex(ValueError, "personal home path"):
            packager.scan("Garden Echo.vst3/Contents/x86_64-linux/Garden Echo.so",
                          b"\x7fELF\x00/tmp\x00/" + b"home/privateuser/project\x00")
        packager.scan("JUCE/modules/example.cpp", b"Example /" + b"home/generic and " + contact)
        packager.scan("project/README.md", b"Use Arrow/Home/End navigation")
        for path in (b"/" + b"Users/privateuser/project", b"C:" + b"\\" + b"Users" + b"\\" + b"privateuser\\project"):
            with self.assertRaisesRegex(ValueError, "personal home path"):
                packager.scan("module", b"\0" + path)

    def test_write_zip_is_deterministic_and_detects_payload_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "one.zip", Path(temp) / "two.zip"
            files = {"project/LICENSE": (b"MIT fixture", 0o644), "bin/module": (b"fixture", 0o755)}
            metadata = {"kind": "synthetic-test"}
            packager.write_zip(first, files, metadata)
            packager.write_zip(second, files, metadata)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                manifest = json.loads(archive.read("manifest.sha256.json"))
                self.assertEqual(manifest["files"]["bin/module"]["sha256"], hashlib.sha256(b"fixture").hexdigest())
            # Model an archive-byte edit, then assert the recorded digest detects it.
            tampered = dict(files)
            tampered["bin/module"] = (b"tampered", 0o755)
            with zipfile.ZipFile(second) as archive:
                record = json.loads(archive.read("manifest.sha256.json"))["files"]["bin/module"]
            self.assertNotEqual(hashlib.sha256(tampered["bin/module"][0]).hexdigest(), record["sha256"])

    def test_package_records_requested_source_identity_and_requires_licenses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "Garden Echo.vst3"
            module = bundle / "Contents/x86_64-linux/Garden Echo.so"
            module.parent.mkdir(parents=True)
            module.write_bytes(fake_elf())
            out = root / "out"
            out.mkdir()
            report = root / "report.txt"
            report.write_text("Synthetic fixture test report.\n", encoding="utf-8")
            source_sha = "a" * 40
            juce_sha = packager.JUCE_COMMIT
            source_files = {
                "garden-echo/LICENSE": (b"MIT License fixture\n", 0o644),
                "garden-echo/THIRD_PARTY_NOTICES.md": (b"Fixture notices\n", 0o644),
                "garden-echo/submission/REPRODUCE.md": (b"Fixture build guide\n", 0o644),
                "garden-echo/src/main.cpp": (b"fixture source\n", 0o644),
            }
            juce_files = {"JUCE/LICENSE.md": (b"JUCE license fixture\n", 0o644)}
            for path in (
                "modules/juce_audio_processors_headless/format_types/VST3_SDK/LICENSE.txt",
                "modules/juce_audio_formats/codecs/flac/Flac Licence.txt",
                "modules/juce_audio_formats/codecs/oggvorbis/Ogg Vorbis Licence.txt",
                "modules/juce_graphics/image_formats/jpglib/README",
                "modules/juce_graphics/image_formats/pnglib/LICENSE",
                "modules/juce_core/zip/zlib/README",
                "modules/juce_graphics/fonts/harfbuzz/COPYING",
                "modules/juce_graphics/unicode/sheenbidi/LICENSE",
            ):
                juce_files["JUCE/" + path] = (b"Dependency license fixture\n", 0o644)
            def source_tree(_repo, commit, prefix):
                self.assertIn(commit, (source_sha, juce_sha))
                return dict(source_files if prefix == "garden-echo" else juce_files)

            args = type("Args", (), {"source_commit": source_sha, "out": out, "test_report": report,
                "bundle": bundle, "platform": "linux-x86_64", "juce_root": root / "JUCE"})()
            with mock.patch.object(packager, "source_tree", side_effect=source_tree):
                names = packager.package(args)
            with zipfile.ZipFile(out / names[1]) as archive:
                manifest = json.loads(archive.read("manifest.sha256.json"))
                self.assertEqual(manifest["sourceCommit"], source_sha)
                self.assertEqual(manifest["juceCommit"], juce_sha)
                self.assertIn("garden-echo/src/main.cpp", manifest["files"])
                self.assertIn("JUCE/LICENSE.md", archive.namelist())

            del source_files["garden-echo/LICENSE"]
            out2 = root / "out-missing-license"
            out2.mkdir()
            args.out = out2
            with mock.patch.object(packager, "source_tree", side_effect=source_tree):
                with self.assertRaisesRegex(ValueError, "missing required license"):
                    packager.package(args)

    def test_verifier_rejects_rewritten_payload_even_with_new_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "Garden-Echo-0.2.0-rc.1-linux-x86_64"
            binary, source = root / (name + ".zip"), root / (name + "-source.zip")
            commit = "a" * 40
            common = {"version": packager.VERSION, "platform": "linux-x86_64",
                      "sourceCommit": commit, "juceCommit": packager.JUCE_COMMIT}
            module = "Garden Echo.vst3/Contents/x86_64-linux/Garden Echo.so"
            license_data = b"GNU AGPLv3 synthetic fixture\n"
            binary_files = {module: (fake_elf(), 0o755), "INSTALL.md": (b"fixture\n", 0o644),
                            "LICENSE": (license_data, 0o644),
                            "THIRD_PARTY_NOTICES.md": (b"fixture notices\n", 0o644),
                             "TEST_REPORT.txt": (b"SYNTHETIC FIXTURE\n", 0o644)}
            for notice in ("JUCE-LICENSE.md", "vst3sdk-LICENSE.txt", "FLAC-LICENSE.txt",
                           "Vorbis-LICENSE.txt", "JPEG-LICENSE.txt", "PNG-LICENSE.txt",
                           "Zlib-LICENSE.txt", "HarfBuzz-LICENSE.txt", "SheenBidi-LICENSE.txt"):
                binary_files["third_party/" + notice] = (b"Dependency license fixture\n", 0o644)
            source_files = {"garden-echo/LICENSE": (license_data, 0o644),
                            "garden-echo/THIRD_PARTY_NOTICES.md": (b"fixture notices\n", 0o644),
                            "garden-echo/CMakeLists.txt": (b"fixture\n", 0o644),
                            "garden-echo/submission/REPRODUCE.md": (b"fixture\n", 0o644),
                            "garden-echo/src/main.cpp": (b"fixture\n", 0o644),
                            "JUCE/LICENSE.md": (b"fixture\n", 0o644),
                            "JUCE/CMakeLists.txt": (b"fixture\n", 0o644),
                            "JUCE/modules/example.cpp": (b"fixture\n", 0o644),
                            "PACKAGE_README.md": (b"fixture\n", 0o644)}
            packager.write_zip(binary, binary_files, {**common, "kind": "binary",
                "modulePath": module, "moduleSha256": packager.digest(fake_elf()),
                "sourceArchive": source.name})
            packager.write_zip(source, source_files, {**common, "kind": "corresponding-source",
                "binaryArchive": binary.name})
            for path in (binary, source):
                (root / (path.name + ".sha256")).write_text(
                    f"{packager.digest(path.read_bytes())}  {path.name}\n")
            self.assertEqual(verifier.verify(binary, source)["status"], "verified")
            with zipfile.ZipFile(binary) as archive:
                entries = [(info, archive.read(info)) for info in archive.infolist()]
            # A rewritten payload and sidecar cannot pass the manifest's hash inventory.
            with zipfile.ZipFile(binary, "w") as archive:
                for info, payload in entries:
                    archive.writestr(info, fake_elf(183) if info.filename == module else payload)
            (root / (binary.name + ".sha256")).write_text(
                f"{packager.digest(binary.read_bytes())}  {binary.name}\n")
            with self.assertRaisesRegex(ValueError, "payload hash/size mismatch"):
                verifier.verify(binary, source)


if __name__ == "__main__":
    unittest.main()
