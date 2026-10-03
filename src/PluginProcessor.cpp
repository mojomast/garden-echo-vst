#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "AtlasStudyPresets.h"
#include <GardenKernels.h>
#include <cmath>

namespace garden
{
namespace
{
constexpr const char* spaceId = "space";
constexpr const char* wetId = "wet";
constexpr const char* predelayId = "predelay";
constexpr const char* trimId = "trim";
constexpr const char* bypassId = "bypass";

struct EmbeddedKernel { const char* data; int size; };
const std::array<EmbeddedKernel, 4> kernels {{
    { GardenKernels::leafchamber_wav, GardenKernels::leafchamber_wavSize },
    { GardenKernels::mossarcade_wav, GardenKernels::mossarcade_wavSize },
    { GardenKernels::raincanopy_wav, GardenKernels::raincanopy_wavSize },
    { GardenKernels::identity_wav, GardenKernels::identity_wavSize },
}};
}

juce::AudioProcessorValueTreeState::ParameterLayout EchoProcessor::makeParameters()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;
    juce::StringArray spaceNames;
    for (const auto& space : spaces) spaceNames.add (juce::String::fromUTF8 (space.name));
    layout.add (std::make_unique<juce::AudioParameterChoice> (juce::ParameterID {spaceId, 1}, "Space",
        spaceNames, 0));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID {wetId, 1}, "Wet",
        juce::NormalisableRange<float> (0.0f, 1.0f, 0.001f), 0.42f));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID {predelayId, 1}, "Predelay",
        juce::NormalisableRange<float> (0.0f, 250.0f, 0.1f), 18.0f, juce::AudioParameterFloatAttributes().withLabel ("ms")));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID {trimId, 1}, "Output trim",
        juce::NormalisableRange<float> (-24.0f, 12.0f, 0.1f), 0.0f, juce::AudioParameterFloatAttributes().withLabel ("dB")));
    layout.add (std::make_unique<juce::AudioParameterBool> (juce::ParameterID {bypassId, 1}, "Bypass", false));
    juce::StringArray studyNames { "Original spaces" };
    for (const auto& preset : EffectCore::presets) studyNames.add (preset.name);
    layout.add (std::make_unique<juce::AudioParameterChoice> (juce::ParameterID {"study", 1}, "Study", studyNames, 0));
    const char* studyIds[] = { "studyTime", "studyFeedback", "studyColour", "studyMotion" };
    const char* studyNamesForHost[] = { "Study time", "Study feedback", "Study colour", "Study motion" };
    for (size_t i = 0; i < 4; ++i)
        layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID {studyIds[i], 1}, studyNamesForHost[i],
            juce::NormalisableRange<float> (0.0f, 1.0f, .001f), .5f));
    return layout;
}

EchoProcessor::EchoProcessor()
    : juce::AudioProcessor (BusesProperties().withInput ("Input", juce::AudioChannelSet::stereo(), true)
                                        .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      parameters (*this, nullptr, "GardenEchoParameters", makeParameters())
{
    spaceParam = parameters.getRawParameterValue (spaceId);
    wetParam = parameters.getRawParameterValue (wetId);
    predelayParam = parameters.getRawParameterValue (predelayId);
    trimParam = parameters.getRawParameterValue (trimId);
    bypassParam = parameters.getRawParameterValue (bypassId);
    studyParam = parameters.getRawParameterValue ("study");
    const char* ids[] = { "studyTime", "studyFeedback", "studyColour", "studyMotion" };
    for (size_t i = 0; i < studyControls.size(); ++i)
        studyControls[i] = parameters.getRawParameterValue (ids[i]);
}

int EchoProcessor::canonicalStudyIndex (float stored) noexcept
{
    return std::isfinite (stored)
        ? juce::jlimit (0, static_cast<int> (EffectCore::effectCount), static_cast<int> (std::lround (stored)))
        : 0;
}

int EchoProcessor::selectedStudy() const noexcept
{
    return canonicalStudyIndex (studyParam->load());
}

int EchoProcessor::selectedSpace() const noexcept
{
    return juce::jlimit (0, numberOfSpaces - 1, static_cast<int> (std::lround (spaceParam->load())));
}

bool EchoProcessor::isBusesLayoutSupported (const BusesLayout& layout) const
{
    const auto input = layout.getMainInputChannelSet();
    return (input == juce::AudioChannelSet::mono() || input == juce::AudioChannelSet::stereo())
        && layout.getMainOutputChannelSet() == input;
}

void EchoProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    prepared = false;
    // Same finite policy as EffectCore: non-finite or out-of-range hosts fall
    // back/clamp before any buffer sizing, so no allocation or cast can overflow.
    currentSampleRate = std::isfinite (sampleRate)
        ? juce::jlimit (8000.0, 384000.0, sampleRate) : 48000.0;
    maxBlock = juce::jlimit (1, 1024, samplesPerBlock);
    const int ringSize = juce::jmax (4, static_cast<int> (std::ceil (currentSampleRate * maximumPredelaySeconds)) + 4);
    delayLine.setSize (2, ringSize, false, true, false);
    predelayed.setSize (2, maxBlock, false, true, false);
    for (auto& buffer : wetBuffers)
        buffer.setSize (2, maxBlock, false, true, false);
    delayLine.clear();
    delayPosition = 0;

    const juce::dsp::ProcessSpec spec { currentSampleRate, static_cast<juce::uint32> (maxBlock), 2 };
    for (size_t i = 0; i < convolvers.size(); ++i)
    {
        // The WAV bytes have static lifetime. JUCE finishes the asynchronous
        // IR preparation inside prepare(), before the first audio callback.
        if (i == convolvers.size() - 1)
        {
            // An exact mathematical unit tap needs no sample-rate conversion:
            // JUCE's bandlimited resampler changes its amplitude at 44.1/96k.
            // This one-frame buffer is allocated before the audio callbacks.
            juce::AudioBuffer<float> identity (2, 1);
            identity.setSample (0, 0, 1.0f);
            identity.setSample (1, 0, 1.0f);
            convolvers[i].loadImpulseResponse (std::move (identity), currentSampleRate,
                juce::dsp::Convolution::Stereo::yes, juce::dsp::Convolution::Trim::no,
                juce::dsp::Convolution::Normalise::no);
        }
        else
            convolvers[i].loadImpulseResponse (kernels[i].data, static_cast<size_t> (kernels[i].size),
                juce::dsp::Convolution::Stereo::yes, juce::dsp::Convolution::Trim::no, 0,
                juce::dsp::Convolution::Normalise::no);
        convolvers[i].prepare (spec);
    }
    setLatencySamples (convolvers[0].getLatency()); // zero with the pinned uniform engine
    for (size_t i = 0; i < spaceWeights.size(); ++i)
    {
        spaceWeights[i].reset (currentSampleRate, 0.065);
        spaceWeights[i].setCurrentAndTargetValue (static_cast<int> (i) == selectedSpace() ? 1.0f : 0.0f);
    }
    wetSmooth.reset (currentSampleRate, 0.025);
    trimSmooth.reset (currentSampleRate, 0.025);
    predelaySmooth.reset (currentSampleRate, 0.045);
    bypassSmooth.reset (currentSampleRate, 0.012);
    wetSmooth.setCurrentAndTargetValue (wetParam->load());
    trimSmooth.setCurrentAndTargetValue (juce::Decibels::decibelsToGain (trimParam->load()));
    predelaySmooth.setCurrentAndTargetValue (predelayParam->load() * static_cast<float> (currentSampleRate / 1000.0));
    bypassSmooth.setCurrentAndTargetValue (bypassParam->load() >= 0.5f ? 1.0f : 0.0f);
    for (std::size_t i = 0; i < EffectCore::effectCount; ++i)
        effectCore.setPreset (i, atlasMappedPreset (i)); // immutable, before audio callback
    effectCore.setEffect (static_cast<size_t> (juce::jmax (0, selectedStudy() - 1)));
    effectCore.setParameters ({studyControls[0]->load(), studyControls[1]->load(), studyControls[2]->load(), studyControls[3]->load()});
    effectCore.prepare (currentSampleRate, static_cast<size_t> (maxBlock));
    studyBlend.reset (currentSampleRate, .065);
    studyBlend.setCurrentAndTargetValue (selectedStudy() == 0 ? 0.0f : 1.0f);
    prepared = true;
}

void EchoProcessor::releaseResources()
{
    prepared = false;
    reset();
}

void EchoProcessor::reset()
{
    for (auto& conv : convolvers) conv.reset();
    effectCore.reset();
    delayLine.clear();
    delayPosition = 0;
}

void EchoProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&)
{
    render (buffer, false);
}

void EchoProcessor::processBlockBypassed (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&)
{
    render (buffer, true);
}

void EchoProcessor::render (juce::AudioBuffer<float>& buffer, bool hostBypassed)
{
    juce::ScopedNoDenormals noDenormals;
    const int channels = std::min ({2, buffer.getNumChannels(), getTotalNumInputChannels(), getTotalNumOutputChannels()});
    if (!prepared || channels == 0 || buffer.getNumSamples() == 0)
        return;
    const auto target = selectedSpace();
    const auto study = selectedStudy();
    if (study > 0) effectCore.setEffect (static_cast<size_t> (study - 1));
    effectCore.setParameters ({studyControls[0]->load(), studyControls[1]->load(), studyControls[2]->load(), studyControls[3]->load()});
    studyBlend.setTargetValue (study == 0 ? 0.0f : 1.0f);
    for (size_t i = 0; i < spaceWeights.size(); ++i)
        spaceWeights[i].setTargetValue (static_cast<int> (i) == target ? 1.0f : 0.0f);
    wetSmooth.setTargetValue (wetParam->load());
    predelaySmooth.setTargetValue (predelayParam->load() * static_cast<float> (currentSampleRate / 1000.0));
    trimSmooth.setTargetValue (juce::Decibels::decibelsToGain (trimParam->load()));
    bypassSmooth.setTargetValue ((hostBypassed || bypassParam->load() >= 0.5f) ? 1.0f : 0.0f);
    for (int offset = 0; offset < buffer.getNumSamples(); offset += maxBlock)
        processSlice (buffer, offset, juce::jmin (maxBlock, buffer.getNumSamples() - offset), channels);
}

void EchoProcessor::processSlice (juce::AudioBuffer<float>& buffer, int offset, int length, int channels)
{
    const int ringSize = delayLine.getNumSamples();
    // Predelay feeds both the convolved space path and the native study path
    // (predelayed is the study input below), so the study tail must budget for
    // it too. Fractional read and smoothing avoid steps/clicks when the host
    // automates the time parameter.
    for (int n = 0; n < length; ++n)
    {
        const float delay = juce::jlimit (0.0f, static_cast<float> (ringSize - 2), predelaySmooth.getNextValue());
        const int whole = static_cast<int> (delay);
        const float fraction = delay - static_cast<float> (whole);
        int a = delayPosition - whole;
        if (a < 0) a += ringSize;
        int b = a - 1;
        if (b < 0) b += ringSize;
        for (int c = 0; c < 2; ++c)
        {
            const float input = buffer.getSample (juce::jmin (c, channels - 1), offset + n);
            delayLine.setSample (c, delayPosition, input);
            const float delayed = delayLine.getSample (c, a) * (1.0f - fraction)
                                + delayLine.getSample (c, b) * fraction;
            predelayed.setSample (c, n, delayed);
        }
        if (++delayPosition == ringSize) delayPosition = 0;
    }
    for (size_t i = 0; i < convolvers.size(); ++i)
    {
        wetBuffers[i].copyFrom (0, 0, predelayed, 0, 0, length);
        wetBuffers[i].copyFrom (1, 0, predelayed, 1, 0, length);
        auto block = juce::dsp::AudioBlock<float> (wetBuffers[i]).getSubBlock (0, static_cast<size_t> (length));
        convolvers[i].process (juce::dsp::ProcessContextReplacing<float> (block));
    }
    for (int n = 0; n < length; ++n)
    {
        std::array<float, spaces.size()> weights;
        for (size_t i = 0; i < weights.size(); ++i) weights[i] = spaceWeights[i].getNextValue();
        const float wet = wetSmooth.getNextValue();
        const float trim = trimSmooth.getNextValue();
        const float bypass = bypassSmooth.getNextValue();
        const auto studyWet = effectCore.processSample (predelayed.getSample (0, n), predelayed.getSample (1, n));
        const float blend = studyBlend.getNextValue();
        for (int c = 0; c < channels; ++c)
        {
            float spatial = 0.0f;
            for (size_t i = 0; i < weights.size(); ++i)
                spatial += weights[i] * wetBuffers[i].getSample (c, n);
            spatial += blend * (studyWet[static_cast<size_t> (c)] - spatial);
            const float dry = buffer.getSample (c, offset + n);
            const float effected = ((1.0f - wet) * dry + wet * spatial) * trim;
            buffer.setSample (c, offset + n, effected + bypass * (dry - effected));
        }
    }
}

void EchoProcessor::getStateInformation (juce::MemoryBlock& dest)
{
    auto state = parameters.copyState();
    const auto choice = state.getChildWithProperty ("id", spaceId);
    const int index = choice.isValid()
        ? juce::jlimit (0, numberOfSpaces - 1, static_cast<int> (std::lround (static_cast<float> (choice.getProperty ("value")))))
        : numberOfSpaces - 1;
    const auto& selected = spaces[static_cast<size_t> (index)];
    state.setProperty ("gardenEchoVersion", 1, nullptr);
    state.setProperty ("kernelId", selected.id, nullptr);
    state.setProperty ("kernelSha256", selected.sha256, nullptr);
    if (auto xml = state.createXml()) copyXmlToBinary (*xml, dest);
}

void EchoProcessor::setStateInformation (const void* data, int size)
{
    if (size <= 0 || size > 1024 * 1024) return;
    auto xml = getXmlFromBinary (data, size);
    if (xml == nullptr || !xml->hasTagName (parameters.state.getType().toString())) return;
    const auto id = xml->getStringAttribute ("kernelId");
    const auto hash = xml->getStringAttribute ("kernelSha256");
    if (xml->getIntAttribute ("gardenEchoVersion", -1) != 1) return;
    auto state = juce::ValueTree::fromXml (*xml);
    auto choice = state.getChildWithProperty ("id", spaceId);
    const int storedIndex = choice.isValid()
        ? juce::jlimit (0, numberOfSpaces - 1, static_cast<int> (std::lround (static_cast<float> (choice.getProperty ("value")))))
        : numberOfSpaces - 1;
    int validIndex = numberOfSpaces - 1; // explicit unit kernel if asset identity has changed
    for (int i = 0; i < numberOfSpaces; ++i)
        if (i == storedIndex && id == spaces[static_cast<size_t> (i)].id
            && hash == spaces[static_cast<size_t> (i)].sha256)
            validIndex = i;
    if (!choice.isValid())
    {
        choice = juce::ValueTree ("PARAM");
        choice.setProperty ("id", spaceId, nullptr);
        state.appendChild (choice, nullptr);
    }
    choice.setProperty ("value", validIndex, nullptr);
    // Missing fields in v1 projects must restore original spaces, even if a
    // study was selected before loading. Keep the existing schema and IDs.
    for (const auto* parameterId : { "study", "studyTime", "studyFeedback", "studyColour", "studyMotion" })
    {
        if (!state.getChildWithProperty ("id", parameterId).isValid())
        {
            juce::ValueTree value ("PARAM");
            value.setProperty ("id", parameterId, nullptr);
            value.setProperty ("value", juce::String (parameterId) == "study" ? 0.0f : .5f, nullptr);
            state.appendChild (value, nullptr);
        }
    }
    parameters.replaceState (state);
}

juce::AudioProcessorEditor* EchoProcessor::createEditor() { return new EchoEditor (*this); }
} // namespace garden

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new garden::EchoProcessor(); }
