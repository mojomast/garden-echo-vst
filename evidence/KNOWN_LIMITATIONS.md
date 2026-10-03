# Limitations / release gates

## 0.2.0 all-sounds review addendum (2026-09-28)

The numbered items below describe the historical three-space verification
build. The new default adds twelve local classical DSP studies (fifteen
musical choices plus Unit impulse as a separate diagnostic); the effects bank
contains authored dry cues and local native renders informed by separately
archived Atlas **simulator** assets, not a hardware or quantum-advantage test.
The optional owner shortlist is not the shipping default. See
[`FINAL_RELEASE_REPORT.md`](FINAL_RELEASE_REPORT.md) for final-build checks and
specific open gates. No public distribution or submission is approved: JUCE
AGPLv3/commercial choice, Atlas output/media redistribution permissions,
event eligibility/rules, owner signoff, cross-distro glibc compatibility,
screen-reader/physical HiDPI and listening on physical audio hardware remain
unresolved unless explicitly superseded by later evidence. Linux x86_64 VST3
is the only packaged plugin format; a native standalone is supplementary.
The final VST3's measured maximum required GLIBC symbol is **GLIBC_2.38**;
there was no older-distro runtime matrix. Final pluginval strictness 5 passed,
but optional external Steinberg validation remained unavailable. REAPER
reopen/state and offline render passed; its GUI create run timed out behind a
headless audio-device modal, and the screenshot is obscured. Do not represent
that as a clean final DAW editor or successful physical playback.
The original `effects-inputs/` study authoring delivery is absent in this
checkout: the tracked effects bank retains rendered/measurement assets but
not four referenced original input assets. Full regeneration of
`AtlasStudyData.h` and five native-stage fixture tests cannot run here;
the Python suite marks seven checks skipped rather than inventing inputs.


1. The default three curated kernels share genuine remote lineage: a measured
   `otoc-echo-v1` trajectory and a `retrocausal-echo-v1` rendering of an exact
   unit-impulse input. Local transformations do not constitute independent
   remote jobs or additional measured rooms. The old synthetic fixture remains
   selectable only explicitly. Remote job authenticity is backed by the
   shared verified GardenPack releases and hashes, not by a claim that this
   plugin owner independently ran those jobs.
2. No claim of a measured physical room IR or generally linear,
   time-invariant renderer is made. Even a genuine rendered unit impulse may
   be a creative kernel rather than an exact transferable room model. The
   source has four occupied stereo frames; the UI plots the three strongest
   final-kernel frames, while all four samples and transform metadata are
   archived in `fixtures/recorded-v1/bundle.json`.
3. Pinned JUCE 8.0.15 is AGPLv3/commercial. Source is offered under AGPLv3;
   public binary distribution, owner license selection, event rules, and
   submission are pending owner approval. The VST3 SDK being MIT does not
   remove JUCE obligations.
4. Linux x86_64 was tested on this glibc 2.42 host; compatibility with older
   Linux distributions is unverified. No Windows/macOS/AU artifact, judge OS decision,
   real audio hardware latency test, or formal live-system deadline test.
   REAPER playback used an isolated JACK dummy device. pluginval strictness 5
   passed with GUI checks; its **external Steinberg VST3 validator was not
   configured**, as shown in the log. JUCE's generated `moduleinfo.json`
   contains trailing commas and is rejected by Python's strict JSON parser;
   both pluginval and REAPER accepted the bundle, but stricter host behavior
   remains untested. Component/controller CIDs match the synthetic baseline.
5. Four always-warm convolution engines trade CPU/memory for gapless,
   allocation-free preset transitions. The imported kernels are bounded to
   two seconds before compilation; CPU and memory results are host-dependent.
   Prepared engines resample garden kernels for other sample rates; only the
   mathematical diagnostic identity avoids resampling. The test allocator
   counter intercepts C++ `new`/`new[]`, not every libc or driver allocator;
   internal convolution slices are capped at 1024 samples to avoid the pinned
   JUCE FFT's known large-block `malloc` scratch path.
6. The saved REAPER smoke project has absolute **media and render** paths from
   the verification checkout. Regenerate it with `scripts/reaper_smoke.lua`
   from another checkout rather than treating that `.rpp` as portable. Its
   plugin must also be scanned/installed by the local host.
7. Keyboard-accessible standard controls and editor resizing have been
   visually inspected under Xvfb/pluginval, but assistive-technology
   screen-reader usability and HiDPI matrix were not independently tested.
   The native one-channel-buffer test does not independently negotiate an
   actual mono host bus layout; the checker log's "mono layout" label is
   imprecise.

Pre-event contribution date: **2026-09-24**. The in-person jam opens Sep 26;
deadline timezone, pre-existing-work rules, AI/team rules and judge platforms
remain subject to organizer/owner confirmation.
