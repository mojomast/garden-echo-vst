#!/usr/bin/env python3
"""Fail closed when the shipped canonical choice mapping or recorded bytes drift."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    ("terrace", "Terrace Multitap", "Repeats & rhythm"),
    ("crossing", "Crossing Ping-Pong", "Repeats & rhythm"),
    ("amber", "Amber Dub", "Repeats & rhythm"),
    ("petal", "Petal Chorus", "Moving & widening"),
    ("canopy", "Canopy Ensemble", "Moving & widening"),
    ("ribbon", "Ribbon Flanger", "Moving & widening"),
    ("wire", "Wire Resonator", "Tone & resonance"),
    ("mist", "Mist Diffuser", "Texture & pulse"),
    ("lantern", "Lantern Tremolo Echo", "Texture & pulse"),
    ("brook", "Brook Filter Sweep", "Tone & resonance"),
    ("prism", "Prism Stereo Doubler", "Moving & widening"),
    ("steps", "Steps Rhythmic Taps", "Repeats & rhythm"),
]
KERNELS = {
    "leaf-chamber": "2318c94161fc9260b527fd7699385b39f6e1ab2ceaeab7532a4033285a885a57",
    "moss-arcade": "c5cd94b2603c5601dae5208e17380ea75190e945d09b08e0d72e65a2f0d58ebb",
    "rain-canopy": "8a1d994184a11afe7cf6cbe16df5781a79d674db797f6152a3e995648bb68f70",
}
BANK_SHA = "7f8bcf2ee968ede7445ac5ae205fb94ab3ba374b1f7e0556ab97668d83c6be27"


def check():
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def text(path):
        return (ROOT / path).read_text()

    def sha(path):
        return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

    inventory = json.loads(text("submission/INVENTORY.json"))
    require(inventory["version"] == "0.2.0", "inventory version")
    require(inventory["musicalCount"] == 15 and inventory["selectableCount"] == 16, "inventory count")
    require(inventory["bankManifestSha256"] == sha("effects-bank/manifest.json") == BANK_SHA, "bank manifest drift")
    spaces = json.loads(text("fixtures/recorded-v1/spaces.json"))["spaces"]
    require([(s["id"], s["name"]) for s in spaces] ==
            [("leaf-chamber", "Leaf Chamber"), ("moss-arcade", "Moss Arcade"),
             ("rain-canopy", "Rain Canopy")], "recorded order/name drift")
    for space in spaces:
        path = "fixtures/recorded-v1/" + space["file"]
        require(space["kernelSha256"] == sha(path) == KERNELS[space["id"]], "kernel drift: " + path)
    bank = json.loads(text("effects-bank/manifest.json"))
    require([(e["id"], e["name"], e["parameters"]["studyIndex"]) for e in bank["effects"]] ==
            [(i, n, j) for j, (i, n, _) in enumerate(EXPECTED, 1)], "bank ID/name/index drift")
    core = text("src/EffectCore.h")
    presets = re.findall(r'^\s*\{"([a-z]+)", "([^"]+)", "[^"]+",', core, re.M)
    require(presets == [(i, n) for i, n, _ in EXPECTED], "EffectCore order/name drift")
    catalog = text("src/StudyCatalog.h")
    entries = re.findall(r'^\s*\{"([a-z]+)", "([^"]+)",', catalog, re.M)
    require(entries == [(i, family) for i, _, family in EXPECTED], "browser family/identity drift")
    processor = text("src/PluginProcessor.cpp")
    require('for (const auto& space : spaces) spaceNames.add (juce::String::fromUTF8 (space.name))' in processor,
            "space host choice no longer follows recorded order")
    require('for (const auto& preset : EffectCore::presets) studyNames.add (preset.name)' in processor,
            "study host choice no longer follows EffectCore order")
    require('juce::StringArray studyNames { "Original spaces" }' in processor, "study zero changed")
    require('static_cast<size_t> (study - 1)' in processor, "study DSP index changed")
    require('canonicalStudyIndex (studyParam->load())' in processor, "canonical study mapping changed")
    parameters = re.findall(r'juce::ParameterID \{(?:([a-zA-Z]+)|"([a-zA-Z]+)"), 1\}', processor)
    ids = [a or b for a, b in parameters]
    require(ids == ["spaceId", "wetId", "predelayId", "trimId", "bypassId", "study"], "host parameter order/version drift")
    require(re.findall(r'constexpr const char\* ([a-zA-Z]+) = "([a-zA-Z]+)";', processor)[:5] ==
            [("spaceId", "space"), ("wetId", "wet"), ("predelayId", "predelay"),
             ("trimId", "trim"), ("bypassId", "bypass")], "host parameter ID drift")
    require('"studyTime", "studyFeedback", "studyColour", "studyMotion"' in processor,
            "host study macro order drift")
    require('juce::ParameterID {studyIds[i], 1}' in processor and
            'juce::NormalisableRange<float> (0.0f, 1.0f, .001f), .5f' in processor,
            "host study macro version/range/default drift")
    require('spaceNames, 0)' in processor and 'studyNames, 0)' in processor and
            '0.42f' in processor and '18.0f' in processor and 'false));' in processor and
            '0.0f' in processor and '1.0f, .001f), .5f' in processor,
            "host defaults/ranges drift; inspect manually")
    require('"GardenEchoParameters"' in processor and '"kernelSha256"' in processor,
            "state schema/recorded hash marker drift")
    cmake = text("CMakeLists.txt")
    require('project(GardenEcho VERSION 0.2.0' in cmake and
            'PLUGIN_MANUFACTURER_CODE Mgdn' in cmake and 'PLUGIN_CODE Gdec' in cmake and
            'BUNDLE_ID "garden.moth.echo"' in cmake, "version or plugin identity drift")
    require('set(GARDEN_SELECTION_HEADER ""' in cmake and
            'true,true,true,true,true,true,true,true,true,true,true,true' in cmake,
            "ship-default all-studies setting drift")
    require(inventory["parameters"] == {
        "space": {"version": 1, "values": [0, 1, 2, 3], "default": 0},
        "study": {"version": 1, "values": list(range(13)), "default": 0},
        "orderedHostIds": ["space", "wet", "predelay", "trim", "bypass", "study",
                           "studyTime", "studyFeedback", "studyColour", "studyMotion"],
        "defaults": {"wet": 0.42, "predelayMs": 18, "trimDb": 0, "bypass": False,
                     "studyTime": .5, "studyFeedback": .5, "studyColour": .5, "studyMotion": .5}},
            "inventory host parameter contract drift")
    expected_choices = ([{"id": s["id"], "name": s["name"], "category": "Recorded spaces",
                          "space": j, "study": 0, "kernelSha256": KERNELS[s["id"]]}
                         for j, s in enumerate(spaces[:3])] +
                        [{"id": i, "name": n, "category": family, "space": None, "study": j}
                         for j, (i, n, family) in enumerate(EXPECTED, 1)] +
                        [{"id": "unit-impulse", "name": "Unit impulse / diagnostic",
                          "category": "Diagnostic", "space": 3, "study": 0}])
    require(inventory["choices"] == expected_choices, "inventory choice omission/reorder/mapping drift")
    require('for (int space = 0; space < 3; ++space)' in text("src/PluginEditor.cpp") and
            'const BrowserRow row { false, 3, false }' in text("src/PluginEditor.cpp"),
            "browser original/diagnostic traversal drift")
    print("PASS: 15 musical + 1 diagnostic; canonical host mappings, full ship default, recorded kernel and bank hashes")


if __name__ == "__main__":
    try:
        check()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        sys.exit("FAIL inventory: " + str(exc))
