# Native VST3 packaging (candidate only)

`scripts/package_native_release.py` packages a **complete, already built and tested**
`Garden Echo.vst3` bundle. It does not compile, test, sign, notarize, publish or
install anything. The experimental version is `0.2.0-rc.1`; platform identifiers
are `linux-x86_64`, `windows-x64`, and `macos-universal` (Intel x86_64 and Apple
arm64 in one Mach-O FAT module). Each platform must be built and tested on an
appropriate native runner before packaging. A local Linux smoke test is not a
Windows/macOS compatibility claim, and CTest alone is not a DAW/host cycle.

After native validation, from the exact checked-out public source commit:

```sh
mkdir -p dist
python3 scripts/package_native_release.py \
  --bundle 'build/ci-release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3' \
  --platform linux-x86_64 --out dist --source-commit "$(git rev-parse HEAD)" \
  --juce-root build/deps/JUCE --test-report build/test-results.txt
python3 scripts/verify_native_package.py \
  --archive dist/Garden-Echo-0.2.0-rc.1-linux-x86_64.zip \
  --repo . --juce-root build/deps/JUCE
```

Substitute the platform and native bundle path on Windows/macOS; the workflow
uses the same arguments. The test report is copied verbatim, never interpreted
as proof that unrun tests passed. Inspect it and retain host/pluginval results
separately before any release claim. The packager requires HEAD to equal the
full lowercase `--source-commit`, and the JUCE Git checkout HEAD to equal
`91ad83ae34a81e0833b1a2b0866f54846370ae53` (JUCE 8.0.15).

It writes four files, refusing to overwrite existing outputs:

* `Garden-Echo-0.2.0-rc.1-<platform>.zip` — untouched module bytes in the whole
  bundle, `INSTALL.md`, GNU AGPLv3 `LICENSE`, project/JUCE/embedded-dependency
  notices and the supplied test report.
* `Garden-Echo-0.2.0-rc.1-<platform>-source.zip` — every Git-tracked public
  project file at the declared commit plus **all Git-tracked JUCE source** at
  the pinned commit, including tagged `JUCE/LICENSE.md`, SDK notices and the
  project `third_party/` notices. Build and source-checkout instructions are in
  `PACKAGE_README.md`; each source payload has a SHA-256 and size in the archive
  manifest. This is corresponding source, not a link to a mutable upstream ZIP.
* A `<zip>.sha256` sidecar for each ZIP. Both ZIPs have `manifest.sha256.json`
  listing all other archive payloads, their byte counts, SHA-256 and Unix modes,
  along with commit IDs, platform and the binary module path/hash.

Both ZIPs are deterministic for identical inputs (sorted entries, fixed ZIP
timestamps/modes) and include no build tree, `.git` history, generated CI
credentials, or private runner directory. A source export contains no Git
metadata: CMake verifies all 4,425 pinned JUCE source blobs and their Git tree
identity, so the included `JUCE/` tree is a directly configurable JUCE_ROOT.
Pass its extracted absolute path to `-DJUCE_ROOT` and follow
`submission/REPRODUCE.md`. This works without fetching Git metadata and does
not weaken the dependency pin.

The packager checks bundle/module layout and magic/architecture, rejects links
and unsafe paths, screens packaged material (including binary byte strings) for
private endpoints, signed URLs, authorization headers and home paths, and preserves legitimate
upstream JUCE source/license author contact addresses verbatim. Upstream JUCE
source also contains generic home-path examples; these are preserved rather
than rewritten. A module embedding local build paths must be rebuilt with
appropriate compile-time path remapping and **retested**; stripping/replacing
bytes after validation is not an acceptable packaging workaround. Review
included material for context as well. It does **not**
prove that a supplied test report is genuine, that the module came from the
declared source, or that legal/host approval is complete. No module bytes are
rewritten, stripped, signed or post-processed. macOS bundles containing
symlinks (even in-bundle links) are currently refused: copying links safely
requires a separately tested archive/link policy; do not flatten or silently
drop them. The verifier independently checks both ZIP inventories, digests,
source notices and module architecture; `--repo` and `--juce-root` additionally
compare every source ZIP file against Git blobs at the pinned commits.

## Manual installation and removal

Extract the binary ZIP, verify its checksum and copy the **entire**
`Garden Echo.vst3` folder; do not copy only the `.so`/PE/Mach-O file. Restart or
rescan your host after installing/removing it.

| System | Destination | Removal |
| --- | --- | --- |
| Linux x86_64 | `~/.vst3/Garden Echo.vst3` | Remove that bundle. |
| Windows x64 | `C:\Program Files\Common Files\VST3\Garden Echo.vst3` (system-wide, administrator permission); a host-supported configured per-user folder may be an alternative | Remove the installed bundle from the same location. |
| macOS universal | `~/Library/Audio/Plug-Ins/VST3/Garden Echo.vst3` | Remove that bundle. |

macOS candidate archives are **unsigned and unnotarized unless an explicitly
verified signing stage is added**. Gatekeeper may reject them; obtain an
approved signed build rather than blindly disabling quarantine/security. An
ad-hoc signature, if used, is not Apple notarization. Installation does not
assert host support or signing status.

These are release **candidate** outputs only: owner signoff, license/security
review, exact-artifact native host validation and distribution authority remain
independent gates. Synthetic tests (`python3 -m unittest
scripts/test_package_native_release.py`) only exercise the packaging code and
cannot establish actual platform compatibility.
