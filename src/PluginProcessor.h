#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_dsp/juce_dsp.h>
#include <SpaceData.h>
#include <array>
#include "EffectCore.h"

namespace garden
{
class EchoProcessor final : public juce::AudioProcessor
{
public:
    EchoProcessor();

    const juce::String getName() const override { return "Garden Echo"; }
    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void reset() override;
    void releaseResources() override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    void processBlockBypassed (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    bool isBusesLayoutSupported (const BusesLayout&) const override;
    // One safe maximum for every installed study, not a claim that any arbitrary
    // future setPreset bank fits. EffectCoreChecks measure the
    // installed Atlas-mapped bank decaying within EffectCore::tailSeconds under
    // maximum controls, and EffectCore.h statically checks its own authored
    // preset table against that bound. The shared wet predelay then adds its
    // full window. Space-only recall keeps the original shorter bound. Hosts may
    // cache this value per instance, so it deliberately does not vary with the
    // current study or control settings.
    static constexpr double maximumPredelaySeconds = 0.25;
    static constexpr double studyTailSeconds = EffectCore::tailSeconds + maximumPredelaySeconds;
    double getTailLengthSeconds() const override { return selectedStudy() == 0 ? 2.25 : studyTailSeconds; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return "Garden"; }
    void changeProgramName (int, const juce::String&) override {}
    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    juce::AudioProcessorValueTreeState parameters;
    static juce::AudioProcessorValueTreeState::ParameterLayout makeParameters();
    static constexpr int numberOfSpaces = static_cast<int> (spaces.size());
    int selectedSpace() const noexcept;
    int selectedStudy() const noexcept;
    // Canonical 0..12 study index. Non-finite and out-of-range stored values
    // collapse to Original spaces (0) for both live recall and state validation,
    // so the two paths can never disagree. Values 1..12 map to EffectCore
    // indices 0..11 (append-only).
    static int canonicalStudyIndex (float stored) noexcept;

private:
    void render (juce::AudioBuffer<float>&, bool hostBypassed);
    void processSlice (juce::AudioBuffer<float>&, int offset, int length, int channels);

    // All four immutable FIR engines are constructed and warmed outside
    // processBlock. Streaming *every* engine maintains history across a
    // mid-stream preset change. The output weights crossfade without loading
    // or freeing any kernel on the realtime thread.
    std::array<juce::dsp::Convolution, spaces.size()> convolvers;
    std::array<juce::AudioBuffer<float>, spaces.size()> wetBuffers;
    juce::AudioBuffer<float> predelayed, delayLine;
    std::array<juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear>, spaces.size()> spaceWeights;
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> wetSmooth, trimSmooth, predelaySmooth, bypassSmooth;
    std::atomic<float>* spaceParam = nullptr;
    std::atomic<float>* wetParam = nullptr;
    std::atomic<float>* trimParam = nullptr;
    std::atomic<float>* predelayParam = nullptr;
    std::atomic<float>* bypassParam = nullptr;
    int delayPosition = 0;
    int maxBlock = 0;
    double currentSampleRate = 48000.0;
    bool prepared = false;
    EffectCore effectCore;
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> studyBlend;
    std::atomic<float>* studyParam = nullptr;
    std::array<std::atomic<float>*, 4> studyControls {};

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (EchoProcessor)
};
} // namespace garden
