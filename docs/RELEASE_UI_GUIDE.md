# Garden Echo 0.2.0 — sound and control guide

Garden Echo 0.2.0 is an open-source stereo Linux x86_64 VST3 release candidate. Put it on a track with audio, open
the native editor and select a sound with Previous/Next or Browse. The browser
supports search, Recorded Spaces / Effect Studies / Diagnostic, and family
filters. At compact sizes it replaces the detail panel; closing it restores
the detail view. The selected sound is preserved when searching or filtering.

## Sounds

The **three Recorded Spaces** derive from one measured `otoc-echo-v1` trajectory
(`backend:aer`, `mode:emu`) and one `retrocausal-echo-v1` explicit-unit-impulse
render; they are locally curated creative FIR
kernels, not three separate remote experiments or measured acoustic rooms.

| Sound | Character |
|---|---|
| Leaf Chamber | Original staggered, signed stereo echo timing. |
| Moss Arcade | Faster, progressively damped echoes. |
| Rain Canopy | Slower, damped, inverted, stereo-swapped echoes. |

The **twelve Effect Studies** are authored classical native DSP. Recorded
Atlas simulator outputs guide bounded tap/control mappings; a study does not
run Atlas on the incoming audio, and its diagram is illustrative, not a live
analyser or measured impulse response. The names below follow the fixed host
parameter order (1–12):

| Sound | Algorithm | Listen for |
|---|---|---|
| Terrace Multitap | Multitap | Sparse early reflections. |
| Crossing Ping-Pong | Ping-Pong | Alternating, cross-coupled repeats. |
| Amber Dub | Dub Delay | Dark low-pass feedback echo. |
| Petal Chorus | Chorus | Short quadrature-modulated delay. |
| Canopy Ensemble | Ensemble | Three detuned delay voices. |
| Ribbon Flanger | Flanger | Swept short feedback comb. |
| Wire Resonator | Resonator | Tuned damped comb resonance. |
| Mist Diffuser | Diffusion | Cascaded stereo all-pass spread. |
| Lantern Tremolo Echo | Tremolo Echo | Opposing stereo pulses. |
| Brook Filter Sweep | Filter Echo | Field-guided low-pass motion with short echo. |
| Prism Stereo Doubler | Doubler | Asymmetric short stereo delays. |
| Steps Rhythmic Taps | Rhythmic Delay | Signed syncopated repetitions. |

The **Unit impulse** is a separate diagnostic, not a musical sound. Its direct
unit taps help check alignment; the common mix, predelay and output settings
still apply. Previous/Next skips the diagnostic when cycling musical sounds.

There is no Atlas call within this plugin. Neither quantum hardware execution
nor quantum advantage is claimed.

## Controls and evidence

- **Wet/Dry** blends original and processed paths. **Predelay** adds 0–250 ms
  to the wet path. **Output** adjusts trim; **Effect active / Bypassed** toggles
  processing. These remain visible at the minimum editor size and are host
  automatable. Selecting a sound does not reset them.
- Studies additionally expose normalized **Time, Feedback, Colour, Motion**
  controls (0–1). The editor hides controls that are not applicable to the
  chosen study; their host parameters remain present for automation and state.
  Enter an exact value in a numeric box or double-click a dial to reset it.
- The recorded-space tap map is a static signed L/R visualization of bundled
  metadata. The study schematic is explicitly illustrative. Expand provenance
  to see the source role; original spaces disclose the full kernel SHA-256.
- Filter search with the keyboard; arrows/Home/End move the browser cursor,
  Enter selects, Escape closes. A recalled study excluded by an opt-in owner
  shortlist is marked **Recalled (outside shortlist)**; it is not silently
  substituted.

The included `effects-bank/manifest.json` maps all twelve studies to three
matched four-second dry cues (drum, pluck, chord) and 36 native rendered WAVs.
The bank's +4 dB wet audition trim and settings are recorded in the manifest;
dry cues are untrimmed and no per-file gain matching was performed. That bank
is a listening exhibit, not proof of physical hardware execution. For the
three original spaces, the archived shorter dry/wet pairs and provenance
appear in repository `evidence/audio/` and `evidence/PROVENANCE.json`.

Native UI capture and interaction details are in `docs/UI_DESIGN.md`; specific
test scope and release limitations are in `evidence/TEST_REPORT.md` and
`evidence/KNOWN_LIMITATIONS.md`. Screen-reader operation and real hardware
HiDPI remain unverified. The final pluginval strictness-5 pass and REAPER
reopen/offline render are recorded in `evidence/FINAL_RELEASE_REPORT.md`;
optional external Steinberg validation was skipped and a headless audio-device
modal obstructed a clean final REAPER editor screenshot. See
`docs/PUBLIC_RELEASE_STATUS.md` for current source approval and remaining binary
release and submission gates.
