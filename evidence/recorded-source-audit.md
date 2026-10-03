# Recorded-source truth review — 2026-09-24

## Scope and result

Authoring work was performed in `/workspace/moth-garden-echo`
against starting commit `0b453ff7fbaeb0d950833d0c41c478d0902e389b`.
**Three distinct local creative kernels now derive from one genuine remote
explicit-unit-impulse render and one upstream simulator trajectory.** They are
not three independent Atlas experiments or measurements of physical rooms.
The space names are creative preset labels. The authoring script makes no
network requests; this work used no new Atlas jobs or credits.

The source release index, remote-download attestation, both GardenPacks, their
assets, the exact uploaded impulse and trajectory, and both input lineage
sidecars are copied byte-for-byte into `fixtures/recorded-v1/sources/`. Copies
were verified and made mode `0444`; Git does not preserve a read-only permission
bit, so content hashes and validation remain authoritative after checkout.
Shared releases were only read. The snapshot is 1,652,810 bytes across 17 files
(including three stereo PCM32 kernels); no redundant alternate render is bundled.

`bundle.json` is explicitly a **build snapshot, not a GardenPack**. Original
GardenPacks retain their actual `atlas-live` evidence labels and exact bytes;
the offline consumer snapshot is labelled `atlas-recorded`.

## Verified remote lineage

| Object | SHA256 / job |
|---|---|
| Explicit-render pack | `be5314372045ac92d7b5d3c2ecd6d7566de2913a0546d81e80a74973fec12c3a` |
| `retrocausal-echo-v1` render job | `1c7f2c4b-e11f-4d06-92e6-88356c6c6777` |
| Unmodified remote `result.wav` | `49e7bd3fb9504b2bb86c2f61cd6681ff9fd6a7a93afba6fa835192be7ebd2dfa` |
| Original uploaded mono float32 impulse | `61f315bb803843cf4218267115ca09eb39c4cd34ee37e229e514b5c2243a637d` |
| Upstream `echo-measure` pack | `a1e7fcc86ef043ed7129d6c83841ff34826d914a21be3d230a81e7ce5e02cbda` |
| `otoc-echo-v1` trajectory job | `5e4da3b1-32fc-4b67-96e7-cb4fbb422249` |
| Measurement's original result envelope | `ce0ef77feeb02fd4832613f4e3f6c67ad9f8c3006e8b67a3fdc3c474b4a3e226` |
| Exact uploaded extracted trajectory | `ae7549afcd890bef2274361c8b0aef888777729c5b97e07db8bffc5b85526d11` |
| Renderer-returned trajectory | `8e1ef3e5c81a5ca14c158dd8e2a2cc907fa3bb8fd7488b5708a1ae5a99f9f3d3` |

The importer pins the reviewed pack/input hashes, validates GardenPack schema,
asset hashes, paths, run references and output hashes, and cross-checks the
matching release-index and completed-job attestation entries. That archived
hub attestation reports independent GET status/result and fresh-download
comparison at `2026-09-24T19:02:44.280Z`. This task did not repeat remote GETs.

The two renderer input hashes are exactly the archived impulse and extracted
trajectory. Decoded JSON equality establishes that uploaded trajectory equals
the measurement envelope's entire `.output`, and the renderer-returned IR's
entire `.data` equals that trajectory's `.data`. It has four sites, four steps,
six finite 4×4 series and seed 607. Actual provenance says `aer`, `emu`,
`shots:null`, no QPU job. This is simulator execution; no hardware or quantum
advantage is claimed. Both input lineage sidecars are also hash-pinned.

The hub's source producer strings identify its checked-out base revisions;
the runner/input additions were uncommitted at the time of the jobs. The
archived attestation records that limitation. This review does not claim those
scripts existed in those earlier revisions.

## Actual WAV samples, not assumed engine tap amplitudes

The original input is RIFF IEEE-float32, mono, 22,050 Hz, 44,100 frames / 2 s.
Decoded sample zero is **exactly 1.0**; the remaining 44,099 samples are zero.
The importer checks the actual samples in addition to the input hash.

The remote result is RIFF IEEE-float32, stereo, 22,050 Hz, 44,100 frames / 2 s.
Only these four frames are nonzero (eight channel samples):

| Frame | Seconds | Left | Right |
|---:|---:|---:|---:|
| 3969 | 0.18 | -0.26344120502471924 | -0.5594968795776367 |
| 7938 | 0.36 | -0.21178780496120453 | -0.7557339668273926 |
| 11907 | 0.54 | -0.4049910604953766 | 0.251852422952652 |
| 15876 | 0.72 | 0.0028815437108278275 | 0.24186263978481293 |

All values are finite and bounded; clipped sample count is zero. Peak is
0.7557339668273926, RMS 0.003816034869661791, channel means approximately
−0.0000198943 / −0.0000186285. Absolute coefficient sums are
0.8831016141921282 / 1.8089459091424942. These are sparse signed echo kernels,
not dense room reverberation. The engine reports 14 site/depth taps, which
overlap into four occupied stereo frames; those 14 entries are not 14 separate
audible time positions. Its nested `tap_map.peak` is zero despite the nonzero
waveform, so actual decoded samples are the curation and display authority.

Requested settings and the engine's full returned effective settings are both
preserved in `bundle.json`, with their original evidence in `sources/`.
Relevant returned settings: wet `mix:1`, `feedback:0`, `negative_mode:invert`,
`diffusion_ms:0`, `tail_ms:0`, `master_ms:720`, `decay:0.9`, `bus_norm:power`,
`output_gain:headroom`, `min_level:0.025`. Supplied IR provenance says
`ir_source:supplied` and `rendered:processed_input`. The returned generic
parameter defaults include 8 sites/depth, while the supplied trajectory's
actual spec has 4 sites/depth; no new eight-site measurement is inferred.

One impulse render alone does **not** establish linearity/time invariance of
the remote renderer. In particular headroom/bus normalization may depend on
input. The final static local FIR convolution is an impulse-based creative
effect, not proof of a transferable room or a faithful model of the remote
engine on arbitrary audio.

### Reviewed alternate, not used

`echo-impulse` is a genuine separate renderer job
`05dd2ff4-2848-4c03-984f-c4a079c3c3e0`, but uses the engine's built-in own-IR
mode without an uploaded audio impulse. Pack hash
`0b5f85c88a5ebf3f04806c4e79e179ac6d35118f42bf55714cf695daaffc7717` and result
hash `6e0f6f562b66ad95f435fb4acbb43191e2881348fac7a966670fa556ca2def3b`
were verified. Actual output is stereo PCM16 / 22,050 Hz / 44,100 frames,
eight nonzero channel samples at frames 2646, 5292, 7938, 10584
(0.12/0.24/0.36/**0.48 exactly** seconds), peak 0.755706787109375 and no
clipped samples. The handoff's approximate last time 0.480023 is not the
actual last occupied frame in these bytes. The explicit-upload render was
selected to preserve an auditable true unit-impulse input. The alternate job
is excluded from this snapshot's contributing-job count and hashes.

## Local DSP curation and gain

All outputs retain 22,050 Hz / 44,100 frames, stereo PCM32. There is **no
offline waveform sample-rate conversion**. Sparse delay events are intentionally
retimed to the nearest integer destination frame, ties to even. The original
coefficients are used; zero fill retains the two-second duration. No events
are truncated. Native plugin sample-rate conversion is a separate operation
that must be verified by native tests.

For occupied event rank `r = 0..3`, curation applies the following transformations
in order: delay remap, optional stereo swap, polarity × damping^r, then one
common stereo gain. Encoding rounds to nearest/ties-even `sample * 2^31`;
it does not clamp samples. Gain is
`min(1, 0.8/preGainPeak, 0.85/maxChannelAbsoluteCoefficientSum)`.
The coefficient-sum bound protects arbitrary bounded-input convolution at the
native kernel rate more meaningfully than peak-only normalization. PCM32
rounding may move the 0.85 bound by less than 2e-9. This does not certify
arbitrary host trim, sample-rate conversion or external processing.

| Preset | Delay scale | Damping^r | Polarity / stereo | Applied gain | Gain dB | Final peak |
|---|---:|---:|---|---:|---:|---:|
| Leaf Chamber | 1 | 1 | +1 / original | 0.4698869080076202 | -6.560133102488636 | 0.35510949697345495 |
| Moss Arcade | 2/3 | 0.875 | +1 / original | 0.5394709694399139 | -5.360638420966288 | 0.35673446860164404 |
| Rain Canopy | 5/4 | 0.75 | -1 / swapped | 0.6204378910954162 | -4.146033740342445 | 0.3516644914634526 |

Final frame positions are respectively `[3969,7938,11907,15876]`,
`[2646,5292,7938,10584]`, `[4961,9922,14884,19845]`. Rain's actual times are
0.2249886621, 0.4499773243, 0.6750113379, 0.9 seconds; metadata does not
pretend rounding was exact at every nominal quarter-frame position.
All final WAVs have eight finite nonzero samples, no clipped samples and a
maximum channel coefficient sum below 0.850000002.

| Final filename | SHA256 |
|---|---|
| `leaf-chamber.wav` | `2318c94161fc9260b527fd7699385b39f6e1ab2ceaeab7532a4033285a885a57` |
| `moss-arcade.wav` | `c5cd94b2603c5601dae5208e17380ea75190e945d09b08e0d72e65a2f0d58ebb` |
| `rain-canopy.wav` | `8a1d994184a11afe7cf6cbe16df5781a79d674db797f6152a3e995648bb68f70` |

`spaces.json` uses exactly those filenames and hashes. Its three displayed
taps are the three strongest occupied frames in the **final decoded PCM WAV**,
sorted chronologically; the weakest fourth frame is omitted from the display.
All four final frames and exact channel samples are in `bundle.json`, along
with the original remote hash and every DSP transform/gain. There is no claim
that the display is a complete engine trajectory or all 14 engine taps.

## Verification performed

Environment: Linux x86_64, kernel `6.17.0-41-generic`, glibc 2.42,
Python **3.13.7**, jsonschema **4.19.2**. Commands ran from this checkout.

| Command / check | Exit | Result |
|---|---:|---|
| `git rev-parse HEAD` | 0 | Exact requested baseline above |
| `python3 scripts/import_impulse_kernel.py --source-root /workspace/moth --out fixtures/recorded-v1` | 0 | Created verified snapshot |
| `python3 scripts/test_recorded_import.py` | 0 | 11 tests passed in 0.543 s |
| `python3 scripts/validate_contract.py fixtures/recorded-v1/sources/releases/echo-explicit-impulse/pack.json` | 0 | GardenPack schema/references/paths/hashes valid |
| `python3 scripts/validate_contract.py fixtures/recorded-v1/sources/releases/echo-measure/pack.json` | 0 | GardenPack schema/references/paths/hashes valid |
| `python3 scripts/write_provenance.py` | 0 | Recorded source/kernel lineage and 11 observed artifact hashes |
| `python3 scripts/verify_artifacts.py` | 0 | Snapshot lineage, diagnostic impulse, RIFF lengths, existing evidence hashes valid |
| `python3 scripts/make_space_header.py fixtures/recorded-v1 scripts/<temporary>/recorded-v1.h` | 0 | Recorded mode generated; temporary output removed |
| `python3 scripts/make_space_header.py fixtures/synthetic-v1 scripts/<temporary>/synthetic-v1.h` | 0 | Explicit synthetic mode generated; temporary output removed |

The importer suite rebuilds the **entire snapshot** from its archived sources
in a temporary directory under `scripts/` and compares every file byte hash
with the first import; outputs and metadata are identical. It independently
checks real source samples, final transform amplitudes within half a PCM32
LSB, exact retimed positions, final tap maps and L1 gain bounds. Negative
checks cover tampered input/render/trajectory/pack, failed-job attestation,
extra nonzero impulse samples, a nonunit first sample, NaN/Inf/out-of-range
floats, bad RIFF size/byte rate/fact count, path traversal/symlink escape,
altered final tap maps and refusing to overwrite a snapshot. The subprocess
with a tampered input explicitly returned **exit 2** before creating output.

Offline regeneration, requiring an empty new destination:

```sh
python3 scripts/import_impulse_kernel.py \
  --source-root fixtures/recorded-v1/sources \
  --out build/recorded-rebuild
```

`assemble_spaces.py` now invokes the same cross-pack verified pipeline rather
than trusting three unrelated sidecar claims. The explicit synthetic fixture
remains in `fixtures/synthetic-v1`; select that path for synthetic diagnostics.

## Existing host output and evidence attribution

**Historical audit snapshot:** this section describes the files as they were
before the subsequent recorded-mode native/REAPER rerun. The recorded-mode
replacement artifacts and their new hashes are documented in
`evidence/TEST_REPORT.md` and `evidence/PROVENANCE.json`.

Read-only inspection of the existing `evidence/daw/garden-host-render.wav`
found SHA256
`38513bf686c4f0e474b2241c81134f7256cc0d706b0b364bfa864bc5258e6707`,
stereo PCM24, 44,100 Hz, 110,250 frames / 2.5 s, exact RIFF length,
220,484 nonzero channel samples, peak 0.12924861907958984 and zero clipped
samples. This is the **pre-existing synthetic baseline host render**. It
does not prove the new recorded kernels were loaded by REAPER.

The read-only inspection used Python `wave`, signed little-endian PCM sample
decoding, SHA256, and the RIFF size field. The alternate source was separately
passed through `validate_contract.validate`, `read_wav`, `signal_stats` and
`events`, all successfully (exit 0). No DAW process or pluginval was launched.

`PROVENANCE.json` preserves historical synthetic artifact hashes separately
from the recorded source/kernel lineage and labels current evidence-file
hashes as observations, not automatic proof of a recorded-mode host run.
If the parent later rerenders artifacts, rerun `write_provenance.py`; use the
native/host reports to establish how those new bytes were produced.

## Remaining limitations

- One simulator trajectory, one explicit render, three classical local
  variations. No independent acoustic experiments, hardware result or quantum
  advantage claim; no subjective listening preference is asserted here.
- This audit verifies archived source authenticity by pinned hashes and the
  hub's archived remote verification; it is not a new live API attestation.
- Host scan/load/play/save/reopen, recorded-kernel render attribution,
  pluginval, resampling/alignment and realtime behavior belong to separate
  native verification. Existing synthetic evidence must not be relabelled.
- Original renderer LTI/linearity has not been established. Source JSON and
  effective defaults have been preserved rather than silently rationalized.
- Public release/submission permission and event/asset-license review remain
  governed by the project-level evidence and owner decision.
