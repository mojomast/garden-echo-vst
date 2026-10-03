# Garden Echo — native VST3 project description

Garden Echo 0.2.0 offers fifteen musical sounds: Leaf Chamber, Moss Arcade and
Rain Canopy recorded-space variations, plus twelve native classical studies
(multitap, ping-pong, dub delay, chorus, ensemble, flanger, resonator,
diffusion, tremolo echo, filter echo, stereo doubler and rhythmic taps). A
separate unit impulse is diagnostic. Browse/search by family; shape a study
with Time, Feedback, Colour and Motion where applicable. Blend wet/dry, offset the wet path up to
250 ms, trim the result, or glide into bypass. A static stereo early-tap map
helps musicians understand the time and side-to-side character of each recorded
space. Study diagrams are labelled illustrations, not live analysis.
The host can automate every control; space changes crossfade between live,
prewarmed convolution engines without interrupting prior audio. The plugin
remembers the selected kernel ID and SHA-256 in its saved state.

The Linux x86_64 VST3 embeds three curated kernels derived from one recorded
`retrocausal-echo-v1` explicit-unit-impulse render and one measured
`otoc-echo-v1` simulator trajectory (`backend:aer`, `mode:emu`). Leaf retains its original sparse timing;
Moss compresses and damps the delay pattern; Rain stretches, inverts and swaps
the stereo response. Local transformations and gain are recorded per
kernel; these are neither three independent engine experiments nor acoustic
room measurements. The earlier synthetic fixture remains an explicitly
selectable development build. The twelve classical studies use bounded mappings
from separately recorded Atlas simulator outputs; no Atlas call happens inside
the plugin. Neither quantum hardware execution nor quantum advantage is claimed.
The [sound guide](../docs/RELEASE_UI_GUIDE.md) and [matched study bank](../effects-bank/manifest.json)
describe all 0.2.0 choices and 36 native study renders. Earlier evidence links
below cover the recorded-space baseline; the [final all-sounds test report](../evidence/FINAL_RELEASE_REPORT.md)
records pluginval strictness 5 (optional external Steinberg validator skipped),
qualified REAPER reopen/offline render and the GUI create run obstructed by a
headless audio-device modal; there is no clean final REAPER editor screenshot.
No physical listening/playback was verified. The measured maximum required
GLIBC symbol is GLIBC_2.38, not an older-distro compatibility test; Windows,
macOS and AU are untested. The owner approved public source and included-media
redistribution on 2026-10-03, using JUCE's AGPLv3 source-licensing path. Exact
binary release, corresponding-source compliance, physical listening and event
eligibility remain separate gates. No completed submission is claimed; see
[release status](../docs/PUBLIC_RELEASE_STATUS.md).

Earlier recorded-baseline evidence: [REAPER plugin screenshot](../evidence/daw/reaper-editor.png),
[native VST3 validation/DAW report](../evidence/TEST_REPORT.md),
[dry/wet pairs and short demo](../evidence/audio/).
