# Garden Echo 0.2.0 — VST private-release verification

Date: 2026-09-29

Status: **tested Linux candidate; no public binary or completed event submission
claimed.** Public native-source and included-media redistribution were approved
by the owner on 2026-10-03; binary release remains separately gated.

## Exact candidate

- VST implementation baseline: `c610cd1`
- VST source comparison: `git diff c610cd1 -- src CMakeLists.txt tests` produced
  no differences before final packaging.
- Product: Garden Echo 0.2.0, Moth Garden, Linux x86_64 VST3
- Manufacturer/plugin codes: `Mgdn` / `Gdec`
- Inventory: 15 musical sounds plus separate Unit impulse diagnostic
- Tested module SHA-256:
  `94c7399516b21993bbcf6367d0f1e8577522e3701cf6e5e766f326ff97b21ce1`
- Tested module bytes: 14,320,800
- Maximum observed required GLIBC symbol: `GLIBC_2.38`

The release packager must consume this exact tested bundle. A different build
directory may produce a different module hash even from unchanged source.

## Toolchain

- CMake 3.31.6
- Ninja 1.12.1
- GCC/G++ 15.2.0
- Python 3.13.7
- JUCE 8.0.15 at commit `91ad83ae34a81e0833b1a2b0866f54846370ae53`
- Existing local sysroot; no dependency installation or network request

Paths in the attached logs are sanitized to `/workspace/...`; these receipts
are not byte-identical to the private local command output.

## Commands and results

The exact candidate in `build/release-audit-lead` was relinked before testing.
All commands exited 0:

```sh
cmake --build build/release-audit-lead \
  --target GardenEcho_VST3 GardenEcho_Standalone \
  EchoChecks EffectCoreChecks StateMigrationChecks -j 4
ctest --test-dir build/release-audit-lead --output-on-failure
xvfb-run -a -s '-screen 0 1280x800x24' \
  build/release-audit-lead/tools/pluginval --strictness-level 5 \
  --validate 'build/release-audit-lead/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3'
```

- CTest: 3/3 passed — EchoDSP 204.18 s, EffectCoreDSP 27.38 s,
  StateMigration 5.45 s; 237.01 s total.
- pluginval strictness 5: `SUCCESS`; scan, cold/warm open, editor while
  processing, 44.1/48/96 kHz processing and automation, state and bus tests
  completed.
- pluginval's optional external Steinberg validator remained unconfigured and
  was skipped; this is not represented as a pass.
- Full sanitized receipts: [`build.txt`](build.txt), [`ctest.txt`](ctest.txt),
  [`pluginval-strict5.txt`](pluginval-strict5.txt).

## Release boundaries

- Existing REAPER scan/load/save/reopen and offline-render evidence remains
  historical evidence from the same VST source. It was not rerun in this
  documentation pass.
- No physical playback or subjective listening was performed.
- No Windows, macOS, AU, older-Linux, screen-reader or real high-DPI validation.
- Public binary distribution remains blocked on exact-artifact owner approval,
  applicable AGPLv3 corresponding-source obligations, listening and event rules.
  The owner confirmed included-media redistribution permission on 2026-10-03.
