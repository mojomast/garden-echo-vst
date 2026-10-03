# Garden Echo synthetic baseline verification — 2026-09-24

Historical report copied verbatim from the synthetic baseline at commit
`0b453ff7fbaeb0d950833d0c41c478d0902e389b`, except this prefatory
note/title. Its media links and hashes refer to the artifacts at **that**
commit, not to the later recorded-kernel evidence files at the same paths.
Retrieve the baseline with `git show 0b453ff:<path>` if comparing audio or
images. This is not evidence that the recorded kernels ran in a native host.

**Status:** working Linux x86_64 VST3, tested with **synthetic** kernels only.
This is a pre-event development artifact; no Atlas processing POST or quantum
job was run for this repository. The VST3 bundle at
`build/release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3` contains a
14,335,800-byte `.so`, SHA-256
`c212e5c8f87adfed810e82053253726b1f88ece8c005a9e1e9da8b0537d9ac54`.

## Actual commands and exits

| Command (run from repo root unless noted) | Exit | Evidence |
| --- | ---: | --- |
| `python3 scripts/make_synthetic_spaces.py` | 0 | unit impulse + 3 distinct WAV kernels in `fixtures/synthetic-v1` |
| `python3 scripts/validate_contract.py fixtures/synthetic-v1/garden-pack.json` | 0 | v1 schema, path, checksums; **synthetic** provenance only |
| `python3 scripts/validate_contract.py` | 0 | 7 contract-negative and valid cases |
| `PKG_CONFIG_PATH="$PWD/build/sysroot/usr/lib/x86_64-linux-gnu/pkgconfig:$PWD/build/sysroot/usr/share/pkgconfig" PKG_CONFIG_SYSROOT_DIR="$PWD/build/sysroot" cmake -S . -B build/release -G Ninja -DCMAKE_BUILD_TYPE=Release -DJUCE_ROOT="$PWD/build/deps/JUCE" -DCMAKE_PREFIX_PATH="$PWD/build/sysroot/usr"` (local downloaded headers) | 0 | JUCE 8.0.15 pin verified at configuration |
| `cmake --build build/release --target GardenEcho_VST3 GardenEcho_Standalone EchoChecks -j 2` | 0 | actual `.vst3`, standalone and C++ checker binaries |
| `ctest --test-dir build/release --output-on-failure` | 0 | 1/1 native DSP suite passed |
| `build/release/EchoChecks_artefacts/Release/EchoChecks evidence/audio` | 0 | [full results](echochecks.log) and six 2.5s 24-bit dry/wet WAVs |
| `xvfb-run -a -s '-screen 0 1280x800x24' build/tools/pluginval/pluginval --strictness-level 5 'build/release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'` | 0 | [full sanitized log](pluginval-strict5.log); GUI tests enabled, one plugin found, success |
| `python3 scripts/import_impulse_kernel.py --pack fixtures/synthetic-v1/garden-pack.json --unit-asset unit-impulse --render-asset leaf-chamber --space leaf-chamber --out build/should-not-exist` | 2, expected | refused synthetic pack, destination absent |
| `python3 scripts/verify_artifacts.py` | 0 | exact unit impulse, WAV RIFF lengths/no trailing append, three distinct wet results, host output, and all 11 evidence hashes |
| `REAPER 7.80 -newinst -cfgfile <private>/reaper.ini -nosplash -new scripts/reaper_smoke.lua`, with private JACK 1.9.22 dummy server, `GARDEN_REAPER_STAGE=create` | 0 | [scan/load/parameter/save/play/stop](daw/create.txt); `playing=1`, JACK at 48k/256, dummy output (no speakers) |
| Same REAPER command loading `evidence/daw/garden-host-smoke.rpp` then `scripts/reaper_smoke.lua`, `GARDEN_REAPER_STAGE=reopen` | 0 | [plugin/state restored](daw/reopen.txt) at space 2/3, wet 0.56, predelay 12ms |
| `REAPER 7.80 -newinst -cfgfile <private>/reaper.ini -nosplash -renderproject evidence/daw/garden-host-smoke.rpp` | 0 | [REAPER's actual VST3 render](daw/garden-host-render.wav), 2.5s 44.1kHz stereo 24-bit |
| `ffmpeg -i evidence/audio/leaf-chamber-dry.wav -ar 44100 -c:a pcm_s24le build/dry-44100.wav`, followed by 24-bit PCM RMS comparison | 0 | dry RMS 0.028659, REAPER output RMS 0.020115, difference RMS **0.015446** (processed, not a copied dry file) |
| `git clone --local --branch work/build-2026-09-24-audio . build/clean-check` at commit `139fe46`, followed by `cmake -S build/clean-check -B build/clean-check-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DJUCE_ROOT="$PWD/build/deps/JUCE" -DCMAKE_PREFIX_PATH="$PWD/build/sysroot/usr"` with the same local `PKG_CONFIG_PATH`/`PKG_CONFIG_SYSROOT_DIR` | 0 | independent source checkout configured (local sysroot/JUCE toolchain shared, not vendored) |
| `cmake --build build/clean-check-build --target GardenEcho_VST3 EchoChecks -j 2` and `ctest --test-dir build/clean-check-build --output-on-failure` | 0, 0 | native VST3 rebuilt and 1/1 DSP suite passed; clean-build `.so` SHA-256 `ca215fb11aed2c1f1c4e3f08fd1f2afa23625b3adb5588494a6dac7a16b6a18f` |
| `xvfb-run -a -s '-screen 0 1280x800x24' build/tools/pluginval/pluginval --strictness-level 5 'build/clean-check-build/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'` | 0 | independent clean-checkout VST3 passed full pluginval including editor/automation checks |

Native tests cover 44.1/48/96 kHz and block sizes 32/64/256/1024;
impulse, silence, seeded noise, sine; stereo and mono; zero and oversized
variable blocks; 75ms predelay; bypass; save/restore with SHA mismatch
fallback; and sample-by-sample continuity/history across a preset change.
Identity kernel equals undelayed reference within **6e-5** at all 12 sample
rate/block combinations, reported latency is **0 samples**, and reported
maximum tail is **1.85s**. An overridden C++ `new`/`new[]` counter recorded
**0 allocations during steady-state processBlock** (not an exhaustive check
of all system allocators). Audio proof peaks were **0.07893**, **0.08022**,
**0.08279**, respectively; no non-finite output or clipping occurred.

Benchmark on **AMD Ryzen AI MAX+ 395 (32 logical CPUs), Ubuntu Linux x86_64**,
GCC 15.2.0 Release build: 1.0027 seconds of 48kHz stereo processed in **0.0426s
wall time** (ratio 0.042) on a shared machine, four active convolution engines.
This is an offline measurement, not a real-time deadline guarantee. REAPER's
host audio ran against a non-real-time JACK dummy device, rather than a
speaker-connected hardware interface.

## Visual/audio proof and provenance

- [Actual VST3 native editor in REAPER](daw/reaper-editor.png), screenshot
  obtained via Xvfb + X11 capture while the plugin was loaded and open.
- [Standalone diagnostic editor](standalone-ui.png), separate X11 capture.
- Three [matched dry/wet pairs](audio/) (same generated stereo cue); the wet
  file of each pair was **rendered by `EchoProcessor`**, not by post-processing
  the screenshot. [7.5s performance demo](audio/garden-echo-demo.flac) joins
  Leaf Chamber, Moss Arcade, and Rain Canopy in that order.
- [GardenPack v1 fixture](../fixtures/synthetic-v1/garden-pack.json), with
  `evidenceMode: synthetic`, null job IDs, and pinned mothbake commit.
  [PROVENANCE.json](PROVENANCE.json) has observed media/project hashes and an
  empty Atlas job list; contract schema is unchanged.

pluginval's optional external **Steinberg VST3 validator** was not supplied
and was explicitly skipped by pluginval. See
[known limitations](KNOWN_LIMITATIONS.md) for the genuine IR and release gates.
