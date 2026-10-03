# Garden Echo 0.2.0 — private integration review (2026-09-28/29)

This is a local review candidate, **not** authorization to distribute or submit.
The final host/build/package receipts are recorded below after verification; the
dated 2026-09-24 three-space report remains historical evidence in
[`TEST_REPORT.md`](TEST_REPORT.md).

**2026-09-29 update:** the package hashes later in this report are retained as
historical receipts. The later exact-module rebuild is recorded in
[`release-readiness/VST_RELEASE_VERIFICATION.md`](release-readiness/VST_RELEASE_VERIFICATION.md).
Current publication boundaries are documented in
[`../docs/PUBLIC_RELEASE_STATUS.md`](../docs/PUBLIC_RELEASE_STATUS.md).

## Canonical product inventory

The default, unshortlisted VST3 exposes **15 musical sounds** (three locally
curated recorded kernels and twelve local classical DSP studies) and a separate
Unit impulse **Diagnostic** (16 selectable behaviors). The machine-readable
[`submission/INVENTORY.json`](../submission/INVENTORY.json) pins the host-facing
`space` choices 0–3, `study` choices 0–12, names, IDs, category, defaults,
parameter order/version, bank manifest digest and three immutable kernel
digests. `python3 scripts/verify_ship_inventory.py` exited 0; mutation tests
`python3 scripts/test_ship_inventory.py` exited 0 and rejected missing,
reordered or changed mappings. Bank manifest SHA-256:
`7f8bcf2ee968ede7445ac5ae205fb94ab3ba374b1f7e0556ab97668d83c6be27`.
The explicit shortlist header mechanism remains a **non-ship** developer tool;
the default CMake setting includes all twelve. Its previously skipped test
now uses the tracked bank: `python3 scripts/test_build_selected_plugin.py`
exited 0 and checked exact non-contiguous canonical allowlist positions.
`python3 scripts/test_effects_bank.py` exited 0 (6 fixture/negative tests);
fixture tests alone do not establish Atlas execution or final plugin behavior.
`python3 scripts/test_recorded_import.py` exited 0 (11 offline importer
positive/negative tests); no remote request was made.
`python3 scripts/test_atlas_study_data.py` initially exited 1 because this
checkout has no `effects-inputs/` original delivery. The tracked bank archives
render/measurement assets but omits **four referenced original input assets**.
After adjusting this test to use only the actual archived source bytes and to
skip the two full-regeneration/tamper checks that require absent inputs, it
exited 0 (one dense-Prism observation passed, two explicit skips). Neither
missing input bytes nor equivalent evidence was invented. Regenerating the
study header from original delivery remains a reproducibility gate.
`python3 -m unittest discover -s scripts -p 'test_*.py' -q` initially
exited 1 (five staging-test `FileNotFoundError`s for absent `effects-inputs`).
After making the staging suite explicitly skip when that original delivery
is absent, it exited 0: **27 tests, 7 skips** (the five staging tests plus
two header-regeneration checks). These skips are not verified passes.
`python3 scripts/verify_artifacts.py` exited 0 for the historical recorded
source/media exhibit; it does not verify the new VST3 or prove a host cycle.
The available read-only hub verifier
`python3 /workspace/hub/scripts/verify_effects_bank.py effects-bank`
exited 0: 12 effects, 3 sources, 36 renders and 8 indexed simulator runs,
with bank SHA `7f8bcf2e...c6be27`. It checks archive lineage/hashes,
not rights to redistribute or physical listening.

## Native UI review

Actual native-component PNGs in [`evidence/ui/`](ui/) were inspected at
710×645, 900×730 and 1280×1000 (PNG headers confirm exact component sizes).
No visible outer-control clipping was observed at those sizes; narrow mode
replaces detail with a browser while leaving mix controls available. Separate
captured states show a study with applicable macros, family-category menu,
no-results search, Unit impulse and its provenance, exact-entry/reset and
bypass. The standalone captures include standalone chrome/muted-input warning,
not a REAPER host claim. `python3 evidence/ui/run_native_checks.py` exited 0
and exercised canonical 0–12/0–3 values and native bounds. This is a visual
and automation check, **not** a screen-reader, physical HiDPI, or DAW focus
audit. Source details and SHA-256 screenshot index:
[`docs/UI_DESIGN.md`](../docs/UI_DESIGN.md), [`ui/SHA256SUMS`](ui/SHA256SUMS).
The separate non-ship shortlist UI regression also exited 0 with
`GARDEN_UI_BUILD_DIR=build/astra-ui/shortlist python3 evidence/ui/run_native_checks.py`;
this does not redefine the all-sounds shipping build.

## Final build, host and distribution receipts

The exact command/exit/log matrix is in
[`final-verification/RESULTS.md`](final-verification/RESULTS.md). Pinned JUCE
8.0.15 / `91ad83ae34a81e0833b1a2b0866f54846370ae53` and the existing
local sysroot configured `build/ship-final` (exit 0); all six requested
targets built (exit 0, JUCE standalone macro-redefinition warnings); CTest
passed **3/3** in 214.42 s (exit 0). Default CMake cache has an empty
`GARDEN_SELECTION_HEADER`; generated VST3 `moduleinfo.json` says **0.2.0**.
The final `.so` SHA-256 is
`17ac9ffa7b2a2a5c464dc897bd40e73b3d044193b2bfb71e0c69d8cebbe8965c`.
Sanitized `.txt` copies of final configure/build/CTest/pluginval/REAPER
stderr and bank comparison logs are under `final-verification/`, alongside
the original `.log` receipts; the host Lua `reaper-create.txt` and
`reaper-reopen.txt` remain the separate parameter/state receipts.
`readelf --version-info` on this exact module (extract `GLIBC_*`,
`sort -Vu`) shows maximum required **GLIBC_2.38**. That is a symbol ceiling,
not a compatibility test on older Linux distributions. No AU, Windows or
macOS binary was built.

The final VST3 passed pluginval strictness 5 under Xvfb (exit 0, `SUCCESS`;
[`pluginval-strict5.txt`](final-verification/pluginval-strict5.txt)). An
external Steinberg validator executable was unavailable and its optional
check was skipped, not passed. `GardenBankRender` returned 0 and reproduced
**36/36** study wet WAV hashes, verified against the checked-in bank manifest
([comparison log](final-verification/bank-rerender-compare.txt)). An initial
renderer invocation with the wrong manifest shape exited 1 (`Invalid study
index`); the correct flattened spec derived from the checked-in parameters
then passed. The bank hash and original three kernel hashes remained unchanged.

REAPER 7.80 in private Xvfb scanned/loaded this **final** VST3 and its host
parameter receipt covered original choices, representatives in all four
study families and Unit impulse. The create run saved
[`final-host.rpp`](final-verification/final-host.rpp) but timed out after
120 s (**exit 124**) because a headless audio-device modal obstructed clean
GUI quit. Reopen separately exited **0** and confirmed exact normalized
Space 1/3, Study 4/12, Wet .56, Predelay .048 (=12 ms); the offline host
render exited **0**. Its actual WAV is stereo PCM24 44.1 kHz, 154350 frames,
finite with peak .16392994, RMS .01959093, 117084 nonzero channel-samples;
SHA-256 `c0a7484d51d6f7504a11830b95aed494f541bd7d977d8f3a5d6a3492202f779a`.
The captured [`REAPER screen`](final-verification/reaper-final-editor.png)
shows an obstructed editor and modal; it is **not** accepted as a clean
editor/category-dropdown proof. Native UI category evidence remains separate
from this host run. No physical listening or playback is claimed.

The private package command exited **0** after those checks; the archive is
`build/release-review-0.2.0/Garden-Echo-0.2.0-linux-x86_64.zip` (ignored,
local, **28 MiB**), SHA-256
`36843c1c5fd5139e3b75edd4fed962d877149bce71dd0f3616d95b92c7d36139`.
The independent archive checker exited **0**, verifying **123** payload
SHA-256/length entries, module, bundle-tree and sidecar archive digest.
The final bundle-tree SHA-256 is
`15c8501018e4e95f3bcfffd5970c408ceae59d416c523afdcdaf2cba1adb08b7`;
its module SHA matches the tested `.so` above. Historical package receipts were
stored as `release-package/README.md`, `package-command.txt` and
`verify-command.txt` in the private review workspace. This is a
**private review archive**, not an approved publication. The archive embeds
the final test report and provenance as frozen pre-package evidence; this
release report/receipt remains outside the ZIP to avoid self-hashing.

No new Atlas job, hardware execution, license entitlement, dependency
installation, commit, push, public hosting or prior deployment replacement
is implied. Public release/submission remain blocked on owner legal/media
permission, event rules and platform judgment; the missing original study
inputs, optional Steinberg validator and clean final REAPER editor capture
are explicitly unresolved test/evidence limitations.
