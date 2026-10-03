#include "../src/PluginProcessor.h"
#include "../src/AtlasStudyPresets.h"
#include <SelectedStudies.h>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <utility>
#include <vector>

namespace
{
void check (bool condition, const char* message)
{
    if (! condition)
    {
        std::fprintf (stderr, "FAIL: %s\n", message);
        std::exit (1);
    }
}

constexpr std::array<const char*, 10> ids {
    "space", "wet", "predelay", "trim", "bypass", "study",
    "studyTime", "studyFeedback", "studyColour", "studyMotion"
};

float raw (garden::EchoProcessor& processor, const char* id)
{
    auto* value = processor.parameters.getRawParameterValue (id);
    check (value != nullptr, "raw parameter exists");
    return value->load();
}

void set (garden::EchoProcessor& processor, const char* id, float value)
{
    auto* parameter = processor.parameters.getParameter (id);
    check (parameter != nullptr, "parameter exists for setting");
    parameter->setValueNotifyingHost (parameter->convertTo0to1 (value));
}

juce::MemoryBlock save (garden::EchoProcessor& processor)
{
    juce::MemoryBlock data;
    processor.getStateInformation (data);
    check (data.getSize() > 0, "state serialized");
    return data;
}

void load (garden::EchoProcessor& processor, const juce::MemoryBlock& data)
{
    processor.setStateInformation (data.getData(), static_cast<int> (data.getSize()));
}

juce::MemoryBlock encode (const juce::ValueTree& tree)
{
    auto xml = tree.createXml();
    check (xml != nullptr, "ValueTree XML created");
    juce::MemoryBlock data;
    juce::AudioProcessor::copyXmlToBinary (*xml, data);
    return data;
}

juce::ValueTree stateTree (const juce::MemoryBlock& data)
{
    auto xml = juce::AudioProcessor::getXmlFromBinary (data.getData(), static_cast<int> (data.getSize()));
    check (xml != nullptr, "saved XML decodes");
    return juce::ValueTree::fromXml (*xml);
}

void addParameter (juce::ValueTree& tree, const char* id, float value)
{
    juce::ValueTree child ("PARAM");
    child.setProperty ("id", id, nullptr);
    child.setProperty ("value", value, nullptr);
    tree.appendChild (child, nullptr);
}

void checkFloat (garden::EchoProcessor& processor, const char* id,
                 float start, float end, float defaultValue)
{
    const auto* parameter = dynamic_cast<juce::AudioParameterFloat*> (processor.parameters.getParameter (id));
    check (parameter != nullptr, "float parameter type");
    const auto range = parameter->getNormalisableRange();
    check (range.start == start && range.end == end, "float parameter range");
    check (std::abs (parameter->get() - defaultValue) < 1.0e-6f, "float parameter default");
}
}

int main()
{
    static_assert (garden::selection::allowed.size() == 12, "12 allowlist entries required");
    static_assert (garden::EchoProcessor::studyTailSeconds == 30.25, "study tail must include predelay");

    {
        garden::EchoProcessor processor;
        check (processor.parameters.state.getType().toString() == "GardenEchoParameters", "APVTS root type");
        const auto& parameters = processor.getParameters();
        check (parameters.size() == static_cast<int> (ids.size()), "exactly ten parameters");
        for (std::size_t i = 0; i < ids.size(); ++i)
            check (parameters[static_cast<int> (i)] == processor.parameters.getParameter (ids[i]),
                   "parameter ID and insertion order");
        check (garden::EchoProcessor::numberOfSpaces == 4, "four spaces");
        check (garden::EffectCore::effectCount == 12, "twelve effects");

        const auto* space = dynamic_cast<juce::AudioParameterChoice*> (processor.parameters.getParameter ("space"));
        const auto* study = dynamic_cast<juce::AudioParameterChoice*> (processor.parameters.getParameter ("study"));
        check (space != nullptr && space->choices.size() == 4 && space->getIndex() == 0, "space choice shape/default");
        check (study != nullptr && study->choices.size() == 13 && study->getIndex() == 0, "study choice shape/default");
        checkFloat (processor, "wet", 0, 1, .42f);
        checkFloat (processor, "predelay", 0, 250, 18);
        checkFloat (processor, "trim", -24, 12, 0);
        for (const auto* id : {"studyTime", "studyFeedback", "studyColour", "studyMotion"})
            checkFloat (processor, id, 0, 1, .5f);
        const auto* bypass = dynamic_cast<juce::AudioParameterBool*> (processor.parameters.getParameter ("bypass"));
        check (bypass != nullptr && ! bypass->get(), "bypass bool shape/default");
        check (processor.getNumPrograms() == 1 && processor.getCurrentProgram() == 0
               && processor.getProgramName (0) == "Garden", "program compatibility");
        std::puts ("PASS: schema, parameter shapes/defaults, programs");
    }

    {
        constexpr std::array<const char*, 12> presetIds {
            "terrace", "crossing", "amber", "petal", "canopy", "ribbon",
            "wire", "mist", "lantern", "brook", "prism", "steps"
        };
        constexpr std::array<const char*, 12> presetNames {
            "Terrace Multitap", "Crossing Ping-Pong", "Amber Dub", "Petal Chorus",
            "Canopy Ensemble", "Ribbon Flanger", "Wire Resonator", "Mist Diffuser",
            "Lantern Tremolo Echo", "Brook Filter Sweep", "Prism Stereo Doubler", "Steps Rhythmic Taps"
        };
        for (std::size_t i = 0; i < garden::EffectCore::effectCount; ++i)
        {
            const auto& original = garden::EffectCore::presets[i];
            const auto mapped = garden::atlasMappedPreset (i);
            check (std::strcmp (original.id, presetIds[i]) == 0 && std::strcmp (original.name, presetNames[i]) == 0,
                   "append-only preset ID/name catalog");
            check (std::strcmp (mapped.id, original.id) == 0 && std::strcmp (mapped.name, original.name) == 0
                   && std::strcmp (mapped.description, original.description) == 0, "mapped preset identity");
            check (std::isfinite (mapped.delaySeconds) && mapped.delaySeconds > 0 && mapped.delaySeconds <= 1
                   && std::isfinite (mapped.feedback) && mapped.feedback >= 0 && mapped.feedback <= .65f
                   && std::isfinite (mapped.rateHz) && mapped.rateHz >= 0 && mapped.rateHz <= 9
                   && std::isfinite (mapped.depthSeconds) && mapped.depthSeconds >= 0 && mapped.depthSeconds <= .02f,
                   "mapped numeric bounds");
            for (const auto& tap : mapped.taps)
                check (std::isfinite (tap.seconds) && tap.seconds >= 0 && tap.seconds <= 1.3f
                       && std::isfinite (tap.left) && std::abs (tap.left) <= 1
                       && std::isfinite (tap.right) && std::abs (tap.right) <= 1, "mapped tap bounds");
        }
        if (! garden::selection::enabled)
            for (bool allowed : garden::selection::allowed)
                check (allowed, "default disabled selection allows all 12 studies");
        std::puts ("PASS: 12 preset identities, mapped bounds, selection allowlist");
    }

    {
        constexpr float nan = std::numeric_limits<float>::quiet_NaN();
        constexpr float inf = std::numeric_limits<float>::infinity();
        for (const auto [value, expected] : std::array<std::pair<float, int>, 11> {{
            {-1, 0}, {0, 0}, {.49f, 0}, {.5f, 1}, {12, 12}, {12.4f, 12},
            {12.5f, 12}, {100, 12}, {nan, 0}, {inf, 0}, {-inf, 0}
        }})
            check (garden::EchoProcessor::canonicalStudyIndex (value) == expected, "canonical study index");
        std::puts ("PASS: 11 canonical study inputs");
    }

    for (int space = 0; space < 4; ++space)
        for (int study = 0; study <= 12; ++study)
        {
            garden::EchoProcessor processor;
            set (processor, "space", static_cast<float> (space));
            set (processor, "study", static_cast<float> (study));
            check (processor.selectedSpace() == space && processor.selectedStudy() == study, "all 52 selections available");
            processor.prepareToPlay (48000, 64);
            juce::AudioBuffer<float> audio (2, 32);
            juce::MidiBuffer midi;
            unsigned seed = 0x754327u + static_cast<unsigned> (space * 13 + study);
            for (int block = 0; block < 3; ++block)
            {
                for (int channel = 0; channel < 2; ++channel)
                    for (int sample = 0; sample < audio.getNumSamples(); ++sample)
                    {
                        seed = seed * 1664525u + 1013904223u;
                        audio.setSample (channel, sample, (static_cast<float> ((seed >> 16) & 65535u) / 65535.0f - .5f) * .2f);
                    }
                processor.processBlock (audio, midi);
                for (int channel = 0; channel < 2; ++channel)
                    for (int sample = 0; sample < audio.getNumSamples(); ++sample)
                        check (std::isfinite (audio.getSample (channel, sample)), "finite rendered audio in 52 selections");
            }
            check (processor.getTailLengthSeconds() == (study == 0 ? 2.25 : garden::EchoProcessor::studyTailSeconds),
                   "selection tail length");
            const auto data = save (processor);
            const auto tree = stateTree (data);
            check (static_cast<int> (tree.getProperty ("gardenEchoVersion")) == 1, "serialized v1 version");
            check (tree.getProperty ("kernelId").toString() == garden::spaces[static_cast<std::size_t> (space)].id
                   && tree.getProperty ("kernelSha256").toString() == garden::spaces[static_cast<std::size_t> (space)].sha256,
                   "serialized kernel ID and hash for each space");
            garden::EchoProcessor restored;
            load (restored, data);
            check (restored.selectedSpace() == space && restored.selectedStudy() == study,
                   "all 52 space/study states recall");
        }
    std::puts ("PASS: 52 space/study combinations rendered finite audio, tails, metadata and recall");

    {
        juce::ValueTree legacy ("GardenEchoParameters");
        legacy.setProperty ("gardenEchoVersion", 1, nullptr);
        legacy.setProperty ("kernelId", garden::spaces[2].id, nullptr);
        legacy.setProperty ("kernelSha256", garden::spaces[2].sha256, nullptr);
        addParameter (legacy, "space", 2);
        garden::EchoProcessor processor;
        set (processor, "study", 9);
        for (const auto* id : {"studyTime", "studyFeedback", "studyColour", "studyMotion"}) set (processor, id, .8f);
        load (processor, encode (legacy));
        check (processor.selectedSpace() == 2 && processor.selectedStudy() == 0 && raw (processor, "study") == 0,
               "v1 missing study migrates to original spaces");
        for (const auto* id : {"studyTime", "studyFeedback", "studyColour", "studyMotion"})
            check (std::abs (raw (processor, id) - .5f) < 1.0e-6f, "v1 missing study control migrates to .5");
        legacy.removeProperty ("kernelId", nullptr);
        legacy.setProperty ("kernelSha256", "", nullptr);
        load (processor, encode (legacy));
        check (processor.selectedSpace() == 3, "v1 missing/empty identity falls back to unit kernel");
        std::puts ("PASS: stable v1 missing-field migration and absent identity fallback");
    }

    {
        garden::EchoProcessor processor;
        for (const auto& [id, value] : std::array<std::pair<const char*, float>, 10> {{
            {"space", 1}, {"wet", .3f}, {"predelay", 123}, {"trim", -6}, {"bypass", 1},
            {"study", 7}, {"studyTime", .25f}, {"studyFeedback", .75f}, {"studyColour", 0}, {"studyMotion", 1}
        }}) set (processor, id, value);
        const auto data = save (processor);
        garden::EchoProcessor restored;
        load (restored, data);
        check (restored.selectedSpace() == 1 && restored.selectedStudy() == 7, "native distinctive selection recalled");
        for (const auto* id : ids)
            check (std::abs (raw (processor, id) - raw (restored, id)) < 1.0e-6f, "native raw parameter exact roundtrip");

        const auto baseline = stateTree (data);
        auto altered = baseline.createCopy();
        altered.setProperty ("kernelSha256", "wrong-hash", nullptr);
        load (restored, encode (altered));
        check (restored.selectedSpace() == 3, "corrupted kernel hash falls back");
        altered = baseline.createCopy();
        altered.setProperty ("kernelId", "wrong-id", nullptr);
        load (restored, encode (altered));
        check (restored.selectedSpace() == 3, "mismatched kernel ID falls back");
        altered = baseline.createCopy();
        altered.getChildWithProperty ("id", "space").setProperty ("value", 2, nullptr);
        load (restored, encode (altered));
        check (restored.selectedSpace() == 3, "choice and kernel metadata mismatch falls back");
        std::puts ("PASS: ten raw parameters roundtrip and three kernel identity mismatch fallbacks");

        load (restored, data);
        const auto verifyUnchanged = [&] (const void* bytes, int length)
        {
            restored.setStateInformation (bytes, length);
            check (restored.selectedSpace() == 1 && restored.selectedStudy() == 7,
                   "rejected state leaves prior selection intact");
        };
        verifyUnchanged (nullptr, 0);
        verifyUnchanged (data.getData(), -1);
        std::vector<char> oversized (1024 * 1024 + 1, 'x');
        verifyUnchanged (oversized.data(), static_cast<int> (oversized.size()));
        const char garbage[] = "random non-XML bytes";
        verifyUnchanged (garbage, static_cast<int> (sizeof garbage));
        altered = juce::ValueTree ("WrongRoot");
        altered.setProperty ("gardenEchoVersion", 1, nullptr);
        const auto wrongRoot = encode (altered);
        verifyUnchanged (wrongRoot.getData(), static_cast<int> (wrongRoot.getSize()));
        for (int version : {0, 2})
        {
            altered = baseline.createCopy();
            altered.setProperty ("gardenEchoVersion", version, nullptr);
            const auto invalid = encode (altered);
            verifyUnchanged (invalid.getData(), static_cast<int> (invalid.getSize()));
        }
        altered = baseline.createCopy();
        altered.removeProperty ("gardenEchoVersion", nullptr);
        const auto missingVersion = encode (altered);
        verifyUnchanged (missingVersion.getData(), static_cast<int> (missingVersion.getSize()));
        std::puts ("PASS: 8 malformed/unsupported state rejection cases preserve selection");
    }

    std::puts ("ALL StateMigrationChecks PASSED");
    return 0;
}
