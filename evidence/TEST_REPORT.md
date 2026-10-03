# Garden Echo recorded-kernel verification — 2026-09-24

## All-sounds 0.2.0 final-plugin addendum — 2026-09-28/29

This release candidate contains 15 musical choices (3 recorded variants +
12 native DSP studies), plus one diagnostic. Clean distinct
`build/ship-final` configure/build exited 0; six requested targets linked;
`ctest --test-dir build/ship-final --output-on-failure` exited 0 (3/3);
final-bundle pluginval strictness 5 under Xvfb exited 0 (`SUCCESS`). Final
VST3 `.so` SHA-256:
`17ac9ffa7b2a2a5c464dc897bd40e73b3d044193b2bfb71e0c69d8cebbe8965c`.
All 36 checked-in study WAV hashes rerendered exactly with `GardenBankRender`.
REAPER 7.80 scan/load, parameter selection and save succeeded, but editor-open
create timed out (exit 124) behind an audio-device modal; reopen/state
assertions and real offline host render exited 0. Its finite, non-silent
44.1-kHz stereo PCM24 WAV hash is
`c0a7484d51d6f7504a11830b95aed494f541bd7d977d8f3a5d6a3492202f779a`.
No physical playback or clean final REAPER editor capture is claimed. External
Steinberg validator unavailable. Python suite: 27 tests, 7 explicit skips
because this checkout omits original `effects-inputs` input assets; full
header/staging regeneration is an open gate. Exact commands, exits, platform,
logs and caveats: [final verification receipts](final-verification/RESULTS.md)
and [final integration report](FINAL_RELEASE_REPORT.md). `readelf`
maximum required GLIBC symbol on final module: **GLIBC_2.38**.

> **Historical three-space report.** This section documents the 2026-09-24
> VST3 build, not the all-sounds 0.2.0 binary. The final 2026-09-28/29
> all-sounds integration results and final-binary receipts are in
> [FINAL_RELEASE_REPORT.md](FINAL_RELEASE_REPORT.md). Do not apply the older
> `recorded-release` pluginval/REAPER/binary SHA to the final VST3.

**Status:** private, pre-event Linux x86_64 VST3 and standalone diagnostic built
with three locally curated kernels from **one** genuine Atlas simulator
`retrocausal-echo-v1` exact-unit-impulse render and **one** measured
`otoc-echo-v1` trajectory. This is neither three remote experiments nor a
measured room/reproducible remote nonlinear transfer function. No new Atlas
job, credit, hardware processing, global install or public submission occurred.
The original synthetic build/report remain at commit
`0b453ff7fbaeb0d950833d0c41c478d0902e389b` and
[SYNTHETIC_BASELINE.md](SYNTHETIC_BASELINE.md).

## Source and kernels

- Input: exact mono float32 22,050 Hz, 2 s first-sample unit impulse,
  SHA-256 `61f315bb803843cf4218267115ca09eb39c4cd34ee37e229e514b5c2243a637d`.
- Genuine remote stereo float32 22,050 Hz render, job
  `1c7f2c4b-e11f-4d06-92e6-88356c6c6777`, SHA-256
  `49e7bd3fb9504b2bb86c2f61cd6681ff9fd6a7a93afba6fa835192be7ebd2dfa`;
  source trajectory simulator job `5e4da3b1-32fc-4b67-96e7-cb4fbb422249`.
- Final PCM32 kernels: Leaf `2318c94161fc9260b527fd7699385b39f6e1ab2ceaeab7532a4033285a885a57`,
  Moss `c5cd94b2603c5601dae5208e17380ea75190e945d09b08e0d72e65a2f0d58ebb`,
  Rain `8a1d994184a11afe7cf6cbe16df5781a79d674db797f6152a3e995648bb68f70`.
  Delays, damping, inversion/stereo swap and downward peak/coefficient-sum gain
  are exact in [bundle.json](../fixtures/recorded-v1/bundle.json). The three
  displayed tap times/amplitudes are measured from final WAV bytes; complete
  four-event maps, remote sources and effective parameters are archived.
- See [source audit](recorded-source-audit.md) and [PROVENANCE.json](PROVENANCE.json)
  for cross-pack lineage, verified fresh remote-download attestation preserved
  from the shared hub, all hashes, source-vs-generated boundaries and limits.
  We did not repeat authenticated remote GETs in this audio workstream.

## Actual commands and exits

All commands ran in this checkout. `PKG_CONFIG_PATH` pointed to
`build/sysroot/usr/lib/x86_64-linux-gnu/pkgconfig` and
`build/sysroot/usr/share/pkgconfig`; `PKG_CONFIG_SYSROOT_DIR` was
`$PWD/build/sysroot`. Python `/usr/bin/python3` was selected explicitly
because a cached local 3.11 lacks `jsonschema`. JUCE was the already-pinned
8.0.15 checkout `91ad83ae34a81e0833b1a2b0866f54846370ae53`; no global
packages were installed.

| Command / action | Exit | Result |
|---|---:|---|
| `python3 scripts/test_recorded_import.py` | 0 | 11 positive/negative source, input, tamper, WAV and byte-identical regeneration tests |
| `python3 scripts/validate_contract.py fixtures/recorded-v1/sources/releases/echo-explicit-impulse/pack.json` and same for `echo-measure/pack.json` | 0, 0 | both recorded GardenPacks schema/hash/path valid |
| `python3 scripts/import_impulse_kernel.py --source-root fixtures/recorded-v1/sources --out build/recorded-regeneration` followed by `cmp` for five generated files | 0, 0 | source-only offline regeneration byte-identical; no remote call |
| `cmake -S . -B build/recorded-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3 -DJUCE_ROOT="$PWD/build/deps/JUCE" -DCMAKE_PREFIX_PATH="$PWD/build/sysroot/usr"` | 0 | generated recorded, hash-validated `SpaceData.h` |
| `cmake --build build/recorded-release --target GardenEcho_VST3 GardenEcho_Standalone EchoChecks -j 2` | 0 | actual native VST3, standalone, and C++ checker; an earlier 120 s tool timeout interrupted an incomplete build, then resumed successfully |
| `ctest --test-dir build/recorded-release --output-on-failure` | 0 | 1/1 EchoDSP passed, 153.61 s; an earlier 120 s tool timeout was too short, not a test failure |
| `build/recorded-release/EchoChecks_artefacts/Release/EchoChecks evidence/audio` | 0 | [full DSP/CPU log](echochecks.log), 3 dry/wet pairs |
| `xvfb-run -a -s '-screen 0 1280x800x24' build/tools/pluginval/pluginval --strictness-level 5 'build/recorded-release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'` | 0 | [full GUI-enabled strictness-5 log](pluginval-strict5.log), one plugin, `SUCCESS` |
| REAPER 7.80 `-newinst -cfgfile build/reaper-recorded/reaper.ini -nosplash -new scripts/reaper_smoke.lua`, `GARDEN_REAPER_STAGE=create`, named private JACK dummy at 48 kHz/256 | 0 | [scan/load/save/play/stop](daw/create.txt); `playing=1` |
| REAPER 7.80 loading `evidence/daw/garden-host-smoke.rpp` then `scripts/reaper_smoke.lua`, `GARDEN_REAPER_STAGE=reopen` | 0 | [state restored](daw/reopen.txt): Rain 2/3, Wet .56, Predelay 12 ms |
| REAPER 7.80 `-renderproject evidence/daw/garden-host-smoke.rpp` with the same private config | 0 | [actual host WAV](daw/garden-host-render.wav), 44.1 kHz / stereo PCM24 / 154,350 frames |
| `python3 scripts/write_provenance.py` and `python3 scripts/verify_artifacts.py` | 0, 0 | refreshed observed media hashes; source lineage, WAV framing and distinct wet renders validated |
| Explicit synthetic configure/build/`ctest --test-dir build/release --output-on-failure` | 0, 0, 0 | retained alternate diagnostic build; 1/1 test passed (46.06 s) |

The host used a private configuration pointing to the **recorded-release**
VST3 and a named JACK dummy server; only that job's JACK PID was stopped.
REAPER ran in Xvfb with no physical speakers. Real screenshots:
[recorded VST3 editor in REAPER](daw/reaper-editor.png) (visible Rain tap map,
source/job label and kernel SHA prefix) and
[standalone diagnostic editor](standalone-ui.png). The standalone is not the
primary deliverable. The actual VST3 `.so` SHA-256 is
`94b9b5036b61ff5f5a792783ca7720eecb32e2a9ddba3be11974891b7ab1cadf`.
Decoding the saved REAPER project state confirms its `kernelSha256` begins
`8a1d994184a11afe...`, matching the complete Rain Canopy snapshot hash;
the saved project also contains the stable component CID.
The JUCE-generated VST3 component/controller CID manifest is byte-identical
to the original synthetic baseline; pluginval's display identifier changed,
not the plugin CIDs.
`ldd` on the recorded `.so` reported no unresolved dependencies on this host;
it links host libraries including fontconfig, FreeType, libstdc++, glibc and
their dependencies rather than bundling a cross-distribution runtime.

## DSP and audio observations

Native tests at 44.1/48/96 kHz and 32/64/256/1024-frame blocks covered
identity impulse/noise/sine/silence, bypass, state save/restore/hash mismatch,
44.1/48/96 kHz real embedded stereo-WAV convolution vs direct time-domain FIR
with JUCE-matched resampling, seeded noise through the full measured echo,
one-channel buffers under the default stereo bus, stereo/zero/oversized
variable callbacks, 250 ms predelay, reset of FIR
and predelay history, and 8193/16384-sample host preparation hints. The
convolution comparison threshold is 4e-4; actual displayed errors in the
[log](echochecks.log) were on the order of 1e-8. Steady-state C++ `new`/`new[]`
allocation counter recorded zero; this does not intercept every `malloc` or
host allocator. Internal callback slices cap at 1024 samples. Reported latency
is 0 samples; conservative maximum reported tail is 2.25 s.
True host-negotiated mono bus layout was not independently exercised, despite
the checker log's historical shorthand `mono layout` for a one-channel buffer.

On **AMD Ryzen AI MAX+ 395 (32 logical CPUs), Ubuntu Linux x86_64,
GCC 15.2.0 Release**, 1.0027 s of 48 kHz stereo audio was processed in
**0.0735 s wall time** on this shared VM (offline ratio .073, not a real-time
hardware guarantee). Three [matched dry/wet pairs](audio/) use identical
48 kHz, stereo PCM24, 168,000-frame / 3.5 s generated pluck phrases. Native
processor wet peaks were .05845/.05976/.06247 and finite/unclipped.
Pairwise wet-file difference RMS values (Leaf/Moss, Leaf/Rain, Moss/Rain)
were .004554/.004628/.004442; this measures distinct signals but is not a
subjective listening-quality claim.
The [lossless 10.5 s demo](audio/garden-echo-demo.flac) concatenates those
three wet files in Leaf/Moss/Rain order; SHA-256
`84171d46dfcf4de91d0a5df401fc4a51d989d2cb2a373001f521a2e6213af816`.
The REAPER host render SHA-256 is
`2574a2dd53fa53b35f0d305b62fe58cfc3ef28b7e8ca931ec35bad7ea576ccf0`,
peak .13276 and RMS .01674. Resampling the matched dry source to 44.1 kHz
with ffmpeg produced dry RMS .024221 and host-vs-dry difference RMS .008429;
the rendered host file is not a copied dry source.

pluginval skipped its optional **external Steinberg validator** because no
validator path was supplied. No Windows/macOS/AU build or speaker-connected
hardware test was performed. See [known limitations](KNOWN_LIMITATIONS.md) for
remaining licensing, portability, platform and event gates.

## Independent committed clean-checkout rebuild

The committed integration source `e19b36006e06d25b2831c6453c8e45b65c030ffc`
was cloned into `build/clean-recorded-checkout`; its
`git status --porcelain=v1` was empty before and after all checks. This is an
independent checkout and binary, but deliberately shares the already-pinned
local JUCE/sysroot/pluginval toolchain rather than pretending those dependencies
are bundled in Git. This report's subsequent documentation-only updates do
not alter the code/kernel commit tested in that checkout.

| Command | Exit / result |
|---|---|
| `git clone --local --branch work/build-2026-09-24-audio . build/clean-recorded-checkout` | 0, exact source SHA above |
| `env PKG_CONFIG_LIBDIR="$PWD/build/sysroot/usr/lib/x86_64-linux-gnu/pkgconfig:$PWD/build/sysroot/usr/share/pkgconfig" PKG_CONFIG_SYSROOT_DIR="$PWD/build/sysroot" cmake -S build/clean-recorded-checkout -B build/clean-recorded-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PWD/build/sysroot/usr" -DJUCE_ROOT="$PWD/build/deps/JUCE" -DPython3_EXECUTABLE=/usr/bin/python3` | 0, recorded snapshot re-verified |
| `cmake --build build/clean-recorded-build --target GardenEcho_VST3 GardenEcho_Standalone EchoChecks --parallel 2` | 0, native plugin/diagnostic/checker independently rebuilt |
| `ctest --test-dir build/clean-recorded-build --output-on-failure` | 0, 1/1 EchoDSP passed in 159.65 s |
| `timeout 600s xvfb-run -a build/tools/pluginval/pluginval --strictness-level 5 --validate 'build/clean-recorded-build/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'` | 0, `SUCCESS`, editor-while-processing included |
| `python3 scripts/test_recorded_import.py` and `python3 scripts/verify_artifacts.py` from the clean checkout | 0 and 0, 11 importer tests and recorded artifact validation |

The clean checkout `.so` SHA-256 was
`cdd96d59b2eb3162e3793823314ecb0d42484fa9c7b942747262c4e0b15c517a`;
it is distinct from the original build's binary hash due to independent source
and build paths. Sanitized tool logs remain privately at
`build/clean-recorded-{configure,build,ctest,import,artifacts,pluginval}.log`
(ignored build artifacts). The clean pluginval run likewise skipped the
optional external Steinberg validator. No separate clean-checkout REAPER pass
was run; the original recorded build has the full host cycle above.
