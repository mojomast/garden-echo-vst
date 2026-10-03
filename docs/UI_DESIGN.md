# Garden Echo — native UI design and verification

## Status and scope

Implemented in the native JUCE editor, not a web mockup. The default catalog is
**15 musical sounds + 1 separate diagnostic**: Leaf Chamber, Moss Arcade, Rain
Canopy; all twelve canonical EffectCore studies; and Unit impulse. This work
does not change DSP, host parameter IDs, ranges, ordering, processor state, or
the immutable recorded assets. First run remains Leaf; selecting sounds never
changes Wet/Dry, Predelay, Output or Bypass.

This is bounded UI verification, not release approval or a new DAW/audio test.
Native standalone and VST3 builds, UI regression checks and authentic Xvfb
screenshots are available below. Screen-reader and hardware high-DPI testing
remain open gates. No network, Atlas jobs, credentials, installs, public release,
commits or pushes were used for this UI work.

## Visual system and information architecture

- Charcoal `#0B191B`, evergreen panels `#17292A`, raised panels `#1E3534`,
  pale leaf text `#E7EAD5`, sage `#9CAE9A`, pollen `#E6BB78`.
  Main text/panel contrast is about 12.35:1; secondary sage/panel about 6.44:1.
  These are palette calculations, not a certification of every rendered state.
- Native system sans-serif fonts and vector drawing only. No external fonts,
  imagery, raster UI assets or animated pseudo-analysis.
- Header: product mark, current sound/family, previous/next, Browse. Previous
  and next wrap through musical sounds and skip the diagnostic. From Diagnostic,
  next returns to Leaf and previous to the last available musical study.
- Persistent bottom strip: Wet/Dry, Predelay (ms), Output (dB), and a toggle
  explicitly reading **Effect active** / **Bypassed**. Numeric boxes are editable;
  double-clicking a dial resets its parameter default.
- Browser: search, top-level Recorded Spaces / Effect Studies / Diagnostic,
  four family facets, count, Clear, no-results message, native scrolling list.
  Facets are Repeats & rhythm, Moving & widening, Tone & resonance, Texture &
  pulse. Search covers names, descriptions, family, IDs, listening guidance and
  aliases. Filters never change the selected sound.
- Current-sound marker `>` and bold/highlighted cursor distinguish selection
  without hue alone. Hover has an outline; keyboard focus has an additional
  gold outline. Normal interactive targets are at least 32 logical pixels high;
  browser rows are 56 high. TooltipWindow is editor-scoped.
- Detail: canonical name, description, listening guidance, honest visualization,
  and a compact expandable provenance disclosure. Recalled studies outside a
  custom shortlist are explicitly labeled in both header and browser metadata.

### Responsive layout

At **900×730**, the browser opens as a bounded 260px rail next to detail. At
**1280×1000**, its width stays bounded while the explanatory map expands. At
**710×645**, an open browser replaces detail, not the persistent controls.
Closing it returns to detail; query/category state survives within the editor.
Study controls occupy their own band and retain their stable positions. Inert
controls are hidden using named catalog applicability, not magic DSP indices.
At minimum size, an open provenance disclosure may replace the illustrative
map; names, listening guidance, provenance and controls remain readable.

The four shared study controls remain **Time / Feedback / Colour / Motion**,
normalized 0–1. Prism omits Feedback; Mist omits Colour; Motion is shown for
Amber, Petal, Canopy, Ribbon, Lantern, Brook and Prism. Hiding a control never
changes its host value or removes the parameter from the processor.

## Canonical mapping and interaction correctness

There is **no study ComboBoxAttachment**. A browser row carries a canonical
`study` value 1–12 or `space` value 0–3. ParameterAttachment writes that exact
denormalized value with `setValueAsCompleteGesture`; view position/count are
never used to normalize a sound selection. `study = 0` selects original-space
mode. The facet ComboBox is view-only and has no host attachment.

Canonical study order: terrace, crossing, amber, petal, canopy, ribbon, wire,
mist, lantern, brook, prism, steps. StudyCatalog metadata follows this order.
Allowed entries plus the currently recalled hidden entry are rebuilt from
these identities, independently of search and filtering.

ParameterAttachment callbacks provide the authoritative value because the
APVTS raw value may lag during the same listener notification. A low-rate timer
only checks for subsequent changes and repaints hover/focus; it never grabs
focus or opens/closes the browser. Automation preserves the search text.

List cursor movement is deliberately separate from activation: arrows and
Home/End navigate; **Enter or click selects**, double-click also closes, Escape
closes without clearing search. Structural refresh suppresses list callbacks.
Mouse activation copies its canonical row before notifying the parameter.
This avoids a reviewed JUCE re-entrancy bug where selecting a later row while
leaving a recalled-only item could otherwise shift that row's numeric index
between selection and click callbacks. Double-click never reapplies that stale
index. A regression exercises JUCE's selection/click/double-click callback order.

## Truthful visuals and provenance

Recorded spaces show a **static signed L/R tap map**, with separate zero
baselines, proportional signed coefficients, timing annotations and a time
axis. This is the bundled early-tap metadata, not a live waveform, FFT, full
kernel trace or proof of a physical room. The listening label's accessible
description/tooltip includes every displayed tap's time and signed L/R gain.
Diagnostic shows equal positive unit taps at 0ms and explains that shared mix,
predelay and output still apply.

Studies use family-specific static explanatory schematics explicitly marked
**ILLUSTRATIVE / NOT A LIVE ANALYSER**. They are not measured study impulse
responses. Provenance distinguishes authored classical DSP with bounded Atlas
simulator-derived control mapping from recorded creative kernels and synthetic
diagnostics. Original-space disclosure includes the full kernel SHA-256 and
explains the local variation of one render / no measured-room claim. ASCII
separators replace the previously misdecoded UTF-8 separator.

## Verification and actual artifacts

Tools: GCC 15.2.0, CMake 3.31.6, Ninja 1.12.1 and repository-pinned JUCE 8.0.15
(`91ad83ae34a81e0833b1a2b0866f54846370ae53`). Existing dependency tree and
sysroot were read-only. Missing optional curl/WebKit pkg-config modules do not
affect this native configuration, which disables them.

```sh
PKG_CONFIG_PATH="$PWD/build/sysroot/usr/lib/x86_64-linux-gnu/pkgconfig:$PWD/build/sysroot/usr/share/pkgconfig" \
PKG_CONFIG_SYSROOT_DIR="$PWD/build/sysroot" \
cmake -S . -B build/astra-ui -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DJUCE_ROOT="$PWD/build/deps/JUCE" \
  -DCMAKE_PREFIX_PATH="$PWD/build/sysroot/usr" \
  -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build build/astra-ui --target GardenEcho_Standalone GardenEcho_VST3 -j 2
python3 evidence/ui/run_native_checks.py
xvfb-run -a -s '-screen 0 1400x1200x24' python3 evidence/ui/capture_native.py
git diff --check
```

All commands above completed with exit 0 for the implemented UI. Native build
logs contain no compiler warnings under the existing project flags. Configure,
build, UI regression and capture logs are under `evidence/ui/`. Native artifacts:

`evidence/ui/verification-results.txt` also preserves the final actual logs in
a trackable text file (the repository ignores `*.log`).

- `build/astra-ui/GardenEcho_artefacts/Release/Standalone/Garden Echo`
- `build/astra-ui/GardenEcho_artefacts/Release/VST3/Garden Echo.vst3`

The additional non-contiguous shortlist build uses the same configure arguments
with `-B build/astra-ui/shortlist` and
`-DGARDEN_SELECTION_HEADER="$PWD/evidence/ui/shortlist-fixture.h"`:

```sh
cmake --build build/astra-ui/shortlist --target GardenEcho_Standalone -j 2
GARDEN_UI_BUILD_DIR=build/astra-ui/shortlist python3 evidence/ui/run_native_checks.py
```

The fixture allows canonical studies **1, 4, 9, 12**, not consecutive indices.
Both catalog builds pass the native UI harness. It checks every allowed choice,
filtered canonical Prism (including recalled-hidden Prism), empty search/Enter,
view-only top-level categories, recalled-row mouse/double-click regression,
search persistence/no automatic browser opening, host writes 0–12 and 0–3 with
matching headings, canonical metadata and per-study control applicability,
visible component bounds in browser-open and browser-closed
states at all three sizes, and unchanged persistent mix parameters. These are
UI tests linked to the real shared-code archive, not a substitute DSP.

### Screenshots inspected

Actual standalone/Xvfb captures (1400×1200 screen including host chrome):

- `default-900x730.png`, `compact-710x645.png`, `expanded-1280x1000.png`
- `study-default-900x730.png` — filtered Prism; Feedback absent; visible focus
- `diagnostic-default-900x730.png`, `diagnostic-provenance-900x730.png`
- `compact-leaf-detail-710x645.png` — browser closed, returning from Diagnostic
- `study-compact-710x645.png`, `study-expanded-1280x1000.png`
- `no-results-900x730.png`, `categories-native.png` — actual empty-state message
  and all top-level/family filters
- `exact-value-entry.png`, `double-click-reset.png`, `bypass-state.png` — native
  numeric entry to 0.500 Wet, reset to 0.420, and explicit bypass state

All are in `evidence/ui/`. Native mouse/key actions and X11 window geometries
are retained in `capture-dimensions.json`; replay its `nativeInputActions` as
`GARDEN_UI_ACTIONS` to reproduce the additional views. The main window has no
WM_NAME on this machine, so capture correctly identifies its Garden Echo
WM_CLASS. Its measured chrome adds 8×64 logical pixels (including JUCE's muted
audio warning). The inferred editor dimensions are independently supplemented
by exact-size native JUCE `component-710x645.png`, `component-900x730.png` and
`component-1280x1000.png` snapshots produced by the harness; shortlist snapshots
are separately named. Rerunning intentionally replaces named captures/logs.

Inspection found no control/heading overlap or mojibake at the three sizes.
Scrolling may intentionally show a partial boundary row; native scrolling keeps
every row reachable. Expanded/static maps are deliberately not animated. Native
XTest search/Enter, list End/Enter, Escape, next navigation and provenance
disclosure were exercised. All screenshots are actual rendered UI, not generated
placeholder images.

## Remaining limits and gates

- No screen-reader audit, real hardware high-DPI/OS scaling matrix, or exhaustive
  host keyboard-interception test. Native JUCE roles, titles, descriptions,
  toggle state and slider values are exposed where supported. Focus outlines
  are visible in captures. Source review verifies automation contains no
  focus-grab path; retained automated checks verify search/browser state, not
  actual OS focus during DAW automation.
- A console-harness attempt to create a focus-testing native peer failed with
  X11 `BadAtom` under bare Xvfb; that OS-focus assertion was removed rather than
  reported as passing. The real standalone opens and captures successfully.
- Standalone reports unavailable ALSA sequencer access and keeps input muted.
  This task claims UI interaction only, not listening or audio-device operation.
- This UI pass did not run a new pluginval session or real DAW save/reopen cycle;
  those are separate integration/release gates. VST3 compilation is not a host
  compatibility claim.
- No favorites, user presets, sample player, cloud, FFT, A/B snapshots or new DSP.
  Owner licensing/event/public-release approval remains required.
