# Garden Echo effects bank: offline native handoff

The bank packager **does not render wet effects** or call Atlas. The separate experimental native plugin renderer must deliver 10 or more distinct effects, each rendered against all three authored dry cues. This is a proposed interchange for new studies, not a claim that the previously recorded 22.05 kHz impulse response is a fresh job. The historical snapshot in `fixtures/recorded-v1/` contains one remote impulse render and classical local variations; see `evidence/recorded-source-audit.md`.

## Produce dry inputs and stage native outputs

```sh
python3 scripts/build_effects_bank.py cues --out build/effects-cues
```

The deterministic `drum-dry.wav`, `pluck-dry.wav`, `chord-dry.wav` are independently authored 4-second 48,000 Hz stereo PCM16 inputs, with room for tails. The renderer uses those exact bytes and exports 4-second aligned stereo PCM16 with a canonical 44-byte header at 48 kHz (accepted by the independent hub verifier). It expects the singular `chord` filename. No automatic gain normalization is performed by this packager; all measured peaks/RMS describe the delivered bytes. Any global audition gain must be disclosed by the renderer in its `localProcessing` or `parameters` rather than hidden per-file normalization.

Create a staging directory (e.g. `build/native-stage/`) containing `renders.json` and the **actual** rendered WAVs. The expected native renderer filenames are `<effect-id>-drum.wav`, `<effect-id>-pluck.wav`, `<effect-id>-chord.wav` at the staging root; JSON `path` entries are relative to staging and must name the exact delivered files. Choose stable kebab effect IDs. For example:

```json
{
  "schemaVersion": 1,
  "renderOrigin": "experimental-native-plugin",
  "renderImplementation": "experimental native renderer build executable sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; DSP source commit <actual commit>",
  "effects": [{
    "id": "tape-garden", "name": "Tape Garden", "family": "Delay",
    "description": "Listen for softened repetitions", "atlasRole": "Actual supplied Atlas trajectory and precise local mapping",
    "localProcessing": "Exact native DSP description; wet/dry gain and tail behavior",
    "parameters": {"feedback": 0.35}, "sourceRunIds": ["ACTUAL-DELIVERED-RUN-ID"],
    "renders": [
      {"sourceId":"drum", "path":"tape-garden-drum.wav", "sha256":"<64 lowercase hex from file>"},
      {"sourceId":"pluck", "path":"tape-garden-pluck.wav", "sha256":"<64 lowercase hex from file>"},
      {"sourceId":"chord", "path":"tape-garden-chord.wav", "sha256":"<64 lowercase hex from file>"}
    ]
  }]
}
```

That example is illustrative; deliver at least ten complete effects. `renderImplementation` **must cite the actual renderer binary/source hash**, not the example digest. `sourceRunIds` must reference jobs genuinely delivered by the lead, describing exactly which Atlas output influenced that effect; a local interpretation should say so in `atlasRole`. Source lineage cannot be synthesized from a historical pack or an absent job.

The lead separately places `atlas-inputs.json` under a chosen inputs directory, plus every file it references. Format: `{ "schemaVersion":1, "runs":[{"id":"...","engineId":"...","jobId":"...","params":{},"execution":"simulator","assets":[{"role":"trajectory","path":"trajectory.json","sha256":"..."}]}] }`. Every asset is copied byte-for-byte to `provenance/atlas-assets/<original path>` after hash validation; the original `atlas-inputs.json` is also copied byte-for-byte. This packager only checks local supplied bytes and attribution, not whether the remote service truly ran the job. The lead controls actual jobs and verification.

```sh
python3 scripts/build_effects_bank.py bank \
  --stage build/native-stage --atlas effects-inputs --cues build/effects-cues \
  --out build/effects-bank
sha256sum build/effects-bank/manifest.json
```

The new/empty destination contains `manifest.json`, `audio/*-dry.wav`, `audio/<effect-id>-<source-id>.wav`, `provenance/render-metadata.json`, `provenance/atlas-inputs.json`, and hashed original assets. Every output path is relative, with no `..`, URLs or symlink input paths. Builder checks every SHA256, exact RIFF framing, 48 kHz stereo PCM16/24, four-second duration, finite decoded samples, silence, clipping, DC and RMS/peak bounds before writing. Integer PCM intrinsically contains no NaNs; other formats are rejected. Build output is only created after all inputs pass validation; output should be distributed as a byte-for-byte snapshot. The renderer's original metadata and Atlas files remain untouched. Bank `manifest.json` follows the shared `EFFECTS_LAB_CONTRACT.md` schema; its **exact byte SHA256** is the browser selection identity. Fixture tests use slightly modified dry cues as simulated wet bytes and do not establish a real native bank.

## Owner selection interchange and offline install

Export the selection JSON from the audition UI, then run:

```sh
python3 scripts/install_effects_selection.py \
  --bank build/effects-bank --selection /path/to/owner-export.json \
  --out build/owner-subset.json
python3 scripts/test_effects_bank.py
```

Selection schema: `{ "schemaVersion":1, "bankId":"garden-echo-effects-v1", "bankSha256":"<exact manifest bytes SHA256>", "selectedEffectIds":[], "decisions":{"each-effect-id":"include|exclude|undecided"}, "notes":{}, "updatedAt":"2026-09-25T12:00:00Z" }`. Decisions cover every bank effect, with exactly the `include` IDs also present in `selectedEffectIds`; an empty selection is valid. Notes are limited to 1,000 characters each and 10,000 total; export file to 100 KB. Installer rechecks bank assets and audio metrics, provenance attribution, selection identity and decisions before writing a **new, read-only** config. It never overwrites an earlier export. A selection export is not silent owner approval.

To produce a **separate candidate VST3 whose menu lists only the owner-exported choices**, explicitly run the following after inspecting and exporting a real owner selection. This does not replace the original installed plugin:

```sh
python3 /path/to/shared/scripts/validate_effect_selection.py \
  effects-bank/manifest.json /path/to/owner-selection.json
python3 scripts/build_selected_plugin.py --bank effects-bank \
  --selection /path/to/owner-selection.json \
  --out build/owner-candidate/SelectedStudies.h
cmake -S . -B build/owner-candidate-vst -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE=/usr/bin/python3 \
  -DJUCE_ROOT="$PWD/build/deps/JUCE" \
  -DGARDEN_SELECTION_HEADER="$PWD/build/owner-candidate/SelectedStudies.h"
cmake --build build/owner-candidate-vst --target GardenEcho_VST3 -j 2
# Review/test the private candidate; only owner controls any eventual install.
```

On this machine the configure also needs `PKG_CONFIG_PATH`, `PKG_CONFIG_SYSROOT_DIR`, and `CMAKE_PREFIX_PATH` from `submission/REPRODUCE.md`. The header embeds exact manifest SHA256 and a fixed 12-position allowlist; CMake selection is **opt-in**. Zero includes leaves only Original spaces in the menu. Original spaces, all parameter IDs/order and saved host states remain stable. A saved unlisted study is displayed as `Recalled (outside shortlist)`, not silently remapped; DAW automation can still address it. This is a **menu/curation filter**, not a security lock or removal of DSP code. No export automatically installs/activates a binary. These tools handle no credentials or processing requests.

Limits: Four-second windows may be too short for very long delay/reverb tails; renderer must select parameters accordingly. Peak/DC limits reject clipped or biased deliverables; they are not a subjective loudness match. The manifest records sample metrics and hashes, not live renderer execution proof, perceptual distinctness, remote authenticity, or hardware claims.
