# Build and verify Garden Echo 0.2.0

This documents the native Linux x86_64 VST3. There is no Atlas request inside
the plugin; the bundled kernels and mapping data were authored offline.
The 0.2.0 selection contract in [`INVENTORY.json`](INVENTORY.json) contains
15 musical sounds (three curated recorded-space kernels and twelve classical
EffectCore studies) plus the separate Unit impulse diagnostic. Ordered host IDs
are `space, wet, predelay, trim, bypass, study, studyTime, studyFeedback,
studyColour, studyMotion`; `space` is 0–3, `study` is 0–12; defaults are Wet
0.42, Predelay 18 ms, Trim 0 dB, Bypass false and all study macros 0.5.
The source OTOC measurement reports `backend:aer`, `mode:emu` and the kernel
source is one explicit-unit-impulse Retrocausal render. Neither quantum
hardware execution nor quantum advantage is claimed.

The VST implementation baseline is `c610cd1`. The public source export has
fresh history and unchanged native DSP/state code. The owner approved source
and included-media redistribution on 2026-10-03; no binary release or completed
submission is claimed. See [release status](../docs/PUBLIC_RELEASE_STATUS.md).

The final 0.2.0 build/host receipts are in
[`evidence/final-verification/RESULTS.md`](../evidence/final-verification/RESULTS.md).
The complete Linux VST3 bundle is
`build/ship-final/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3`;
copy the whole bundle for a local host scan, never the bare `.so`.
Use pinned JUCE 8.0.15 and the packages/sysroot described below:

```sh
cmake -S . -B build/ship-final -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/path/to/local/sysroot/usr \
  -DJUCE_ROOT=/path/to/pinned/JUCE -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build build/ship-final --target GardenEcho_VST3 GardenEcho_Standalone EchoChecks EffectCoreChecks StateMigrationChecks GardenBankRender --parallel 2
ctest --test-dir build/ship-final --output-on-failure
python3 scripts/verify_ship_inventory.py
python3 -m unittest discover -s scripts -p 'test_*.py' -q
timeout 600s xvfb-run -a -s '-screen 0 1280x800x24' /path/to/pluginval \
  --strictness-level 5 --validate 'build/ship-final/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'
```

For the private REAPER cycle, set `GARDEN_ECHO_WORKSPACE` to the checkout,
`GARDEN_REAPER_STAGE=create` then `reopen`, configure a private REAPER
`vstpath` to the final bundle's parent, and invoke
`scripts/reaper_final_smoke.lua` with the isolated REAPER executable under
Xvfb. The exact three host commands, private paths and exits are in the final
verification receipt. Never point these steps at the older `recorded-release`
bundle or mistake an offline render for physical listening.

On this checkout the Python suite has **seven explicit skips** because the
original `effects-inputs/` authoring delivery and four referenced original
input assets are absent; do not count those as passing checks. The
`effects-bank` itself and 36 exact local renders were independently verified.
The final `.so` requires at most **GLIBC_2.38** among measured GLIBC symbols;
older distro compatibility is untested. pluginval strictness 5 passed but its
optional external Steinberg validator was unavailable. REAPER reopen/offline
render passed; headless GUI create timed out behind an audio-device modal.
There is no physical listening, clean final REAPER editor screenshot or
Windows/macOS/AU claim.

The commands and host observations below describe the earlier three-space
recorded baseline; do not confuse its hashes with the later 0.2.0 receipts.
Reproduction requires this source tree and the pinned JUCE checkout. Build
output is not a complete distribution: include corresponding source, JUCE and
SDK notices, documentation and an exact-artifact checksum before distributing
a binary. See [release status](../docs/PUBLIC_RELEASE_STATUS.md).

## Toolchain and source

Linux x86_64 was verified using GCC 15.2.0, CMake 3.31.6, Ninja 1.12.1,
Python 3.11/3.13 with `jsonschema`, JUCE **8.0.15** pinned to
`91ad83ae34a81e0833b1a2b0866f54846370ae53`. CMake requires >=3.22.
On Ubuntu install a compiler, CMake, Ninja, pkg-config, Python with
`jsonschema`, and development headers for X11/Xext/Xrender/Xinerama/Xrandr/
Xcursor/Xcomposite, FreeType2, fontconfig, OpenGL and ALSA. Our isolated
machine lacked these headers, so Ubuntu `-dev` Debian packages were unpacked
only in `build/sysroot` (no global install); normal machines can instead use
their package manager. `xvfb-run` is used for automated GUI validation.

```sh
git clone --depth 1 --branch 8.0.15 https://github.com/juce-framework/JUCE.git build/deps/JUCE
git -C build/deps/JUCE rev-parse HEAD  # must be 91ad83ae34a81e0833b1a2b0866f54846370ae53
# Default build: checksum-verified, tracked fixtures/recorded-v1 snapshot.
# To build the separately labelled old synthetic edition, configure with
# -DGARDEN_SPACES_DIR="$PWD/fixtures/synthetic-v1" instead.
cmake -S . -B build/recorded-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DJUCE_ROOT="$PWD/build/deps/JUCE"
cmake --build build/recorded-release --target GardenEcho_VST3 GardenEcho_Standalone EchoChecks -j 2
ctest --test-dir build/recorded-release --output-on-failure
build/recorded-release/EchoChecks_artefacts/Release/EchoChecks evidence/audio
```

When using the locally unpacked `-dev` package sysroot instead, configure
with `PKG_CONFIG_PATH="$PWD/build/sysroot/usr/lib/x86_64-linux-gnu/pkgconfig:$PWD/build/sysroot/usr/share/pkgconfig"`,
`PKG_CONFIG_SYSROOT_DIR="$PWD/build/sysroot"`, and
`-DCMAKE_PREFIX_PATH="$PWD/build/sysroot/usr"`. On this verification machine
also pass `-DPython3_EXECUTABLE=/usr/bin/python3` (Python 3.13 with
`jsonschema`); an older cached local Python 3.11 lacks `jsonschema` and cannot
validate recorded GardenPacks. The JUCE tag/commit check is
mandatory and fails configuration on other versions. Artifact paths:

- **VST3:** `build/recorded-release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3`.
- **Standalone diagnostic only:** `build/recorded-release/GardenEcho_artefacts/Release/Standalone/Garden Echo`.

## Install, listen, remove

For a local host test copy the **whole bundle**, not just its internal `.so`:

```sh
mkdir -p "$HOME/.vst3"
cp -a 'build/recorded-release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3' "$HOME/.vst3/"
# Re-scan VST3 paths in the host, insert Garden Echo on an audio track.
# When done, remove only this plugin's installed bundle:
rm -rf "$HOME/.vst3/Garden Echo.vst3"
```

The three default garden options are **curated genuine-impulse-derived creative kernels**
sharing one `retrocausal-echo-v1` render and a measured `otoc-echo-v1` trajectory;
they are not independent experiments or physical rooms. Try Leaf Chamber at wet 0.42,
predelay 18ms, trim 0dB; switch to Moss Arcade or Rain Canopy while playing.
Select the fourth *Unit impulse / diagnostic* option for direct-path
alignment. The UI shows the selected kernel's hash and evidence label.

## Host and audio evidence

Download the official
[pluginval 1.0.4 Linux build](https://github.com/Tracktion/pluginval/releases/tag/v1.0.4)
(ZIP SHA-256 `c01c49d8063965c4c2dea8324468336768f5c9139e0b1caebde14c2400b55352`),
unzip into `build/tools/pluginval/`, then:

```sh
xvfb-run -a -s '-screen 0 1280x800x24' build/tools/pluginval/pluginval \
  --strictness-level 5 'build/recorded-release/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'
```

For the DAW cycle, download official
[REAPER 7.80 Linux x86_64](https://www.reaper.fm/download.php)
(tarball SHA-256 `95f9e0093359741430fe152b695538fb08a106df052333ecec2056239c8d5c67`)
and extract it as `build/tools/reaper_linux_x86_64`. Use a private
`build/reaper-recorded/reaper.ini` with:

```ini
[reaper]
vstpath=/absolute/path/to/this/repo/build/recorded-release/GardenEcho_artefacts/Release/VST3
```

Start a *named, local* JACK dummy server (JACK 1.9.22; optional only for
playback) with `jackd --no-realtime -n garden_echo_recorded -d dummy -r 48000 -p 256`.
Set `JACK_DEFAULT_SERVER=garden_echo_recorded` for the following commands. The host
script's only output is a test project and small text receipts in `evidence/daw`:

```sh
export GARDEN_ECHO_WORKSPACE="$PWD"
export HOME="$PWD/build/reaper-home" XDG_CONFIG_HOME="$PWD/build/reaper-recorded"
export GARDEN_REAPER_STAGE=create JACK_DEFAULT_SERVER=garden_echo_recorded
xvfb-run -a build/tools/reaper_linux_x86_64/REAPER/reaper -newinst \
  -cfgfile "$PWD/build/reaper-recorded/reaper.ini" -nosplash -new "$PWD/scripts/reaper_smoke.lua"
export GARDEN_REAPER_STAGE=reopen
xvfb-run -a build/tools/reaper_linux_x86_64/REAPER/reaper -newinst \
  -cfgfile "$PWD/build/reaper-recorded/reaper.ini" -nosplash \
  "$PWD/evidence/daw/garden-host-smoke.rpp" "$PWD/scripts/reaper_smoke.lua"
xvfb-run -a build/tools/reaper_linux_x86_64/REAPER/reaper -newinst \
  -cfgfile "$PWD/build/reaper-recorded/reaper.ini" -nosplash \
  -renderproject "$PWD/evidence/daw/garden-host-smoke.rpp"
```

The saved test project on this machine has **absolute source-media and render
paths**. Regenerate it using the `create` stage in another checkout rather than
assuming the checked-in `.rpp` is portable. Only stop the named JACK process
that you started; do not alter the system's audio device configuration.
See [test report](../evidence/TEST_REPORT.md) and
[recorded artifacts](../evidence/PROVENANCE.json).

## Recorded exact-unit-impulse provenance (no remote calls in these scripts)

The archived `fixtures/recorded-v1` default is derived offline from a shared
recorded GardenPack v1; its source hashes, job IDs, exact input verification,
local curation, gain and output hashes are in the build bundle and
`evidence/PROVENANCE.json`. No remote processing or credit use occurs during
rebuilding. The remote result is processed impulse audio, not an established
transferable linear room model. The source pack remains immutable.

The checked-in snapshot is the reproducible **default**, not three repeated
engine executions. To re-author from the unmodified shared source packs, use
the deterministic offline importer (choose a fresh empty destination):

```sh
python3 scripts/import_impulse_kernel.py \
  --source-root fixtures/recorded-v1/sources --out build/recorded-rebuild
sha256sum build/recorded-rebuild/{leaf-chamber,moss-arcade,rain-canopy}.wav
```

Compare the resulting WAVs and metadata hashes to
`fixtures/recorded-v1/bundle.json`. The
build snapshot is not a new GardenPack and does not establish engine linearity.
Public distribution still needs licensing and event-rule approval.
