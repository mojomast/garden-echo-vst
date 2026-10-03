# Native UI verification — 2026-09-28

- [x] Configure native default and non-contiguous shortlist builds: exit 0.
- [x] Build Standalone + VST3 in `build/astra-ui`: exit 0, zero compiler warnings.
- [x] Build shortlist Standalone in `build/astra-ui/shortlist`: exit 0, zero compiler warnings.
- [x] `python3 evidence/ui/run_native_checks.py`: exit 0.
- [x] `GARDEN_UI_BUILD_DIR=build/astra-ui/shortlist python3 evidence/ui/run_native_checks.py`: exit 0.
- [x] Default browser exposes 3 recorded spaces, 12 musical studies and 1 diagnostic.
- [x] Shortlist canonical values 1/4/9/12 and recalled-hidden Prism map correctly.
- [x] View-only categories/search, empty Enter, and search persistence checked.
- [x] Recalled-row removal / subsequent mouse and double-click activation regression checked.
- [x] All canonical host selection writes update headings; mix parameters are unchanged.
- [x] StudyCatalog identities and applicable-control visibility checked for every study.
- [x] Native component bounds checked at 710×645, 900×730, 1280×1000 with browser open and closed.
- [x] Authentic standalone captures at all three sizes inspected, plus original/study/diagnostic, category popup, no-results, provenance, value entry/reset and bypass views.
- [x] Native keyboard search, Enter, End/Enter, Escape; native mouse next, disclosure and numeric entry/reset exercised.
- [x] `git diff --check`: exit 0.
- [ ] Screen-reader audit and physical high-DPI/OS scaling matrix.
- [ ] DAW automation OS-focus audit. Console native-peer focus attempt hit X11 BadAtom; no passing focus assertion is claimed.
- [ ] New pluginval / real DAW save-reopen cycle (outside this UI workstream).

No audio listening is claimed: standalone input is muted; ALSA sequencer access
is unavailable in this environment. The default screenshots include JUCE's
standalone title/mute strip. `component-*.png` are exact-size native editor
snapshots, not fabricated mockups. Capture uses ffmpeg without a cursor overlay.

Commands, implementation rationale, screenshot descriptions, known limitations
and reproduction instructions are in `docs/UI_DESIGN.md`. Native input actions
and measured X11 client dimensions are in `capture-dimensions.json`. Source and
PNG checksums are in `SHA256SUMS`.
