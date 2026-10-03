#include "../src/PluginProcessor.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <GardenKernels.h>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <new>
#include <random>
#include <memory>

namespace
{
std::atomic<bool> tracking { false };
std::atomic<size_t> allocations { 0 };
}

// Measures ordinary C++ heap allocations *around steady-state processBlock*.
// JUCE may allocate during prepareToPlay; that is intentionally not counted.
void* operator new (std::size_t n)
{
    if (tracking.load (std::memory_order_relaxed)) allocations.fetch_add (1, std::memory_order_relaxed);
    if (auto* p = std::malloc (n == 0 ? 1 : n)) return p;
    throw std::bad_alloc();
}
void* operator new[] (std::size_t n)
{
    if (tracking.load (std::memory_order_relaxed)) allocations.fetch_add (1, std::memory_order_relaxed);
    if (auto* p = std::malloc (n == 0 ? 1 : n)) return p;
    throw std::bad_alloc();
}
void operator delete (void* p) noexcept { std::free (p); }
void operator delete[] (void* p) noexcept { std::free (p); }
void operator delete (void* p, std::size_t) noexcept { std::free (p); }
void operator delete[] (void* p, std::size_t) noexcept { std::free (p); }

namespace
{
void check (bool condition, const char* message)
{
    if (!condition)
    {
        std::fprintf (stderr, "FAIL: %s\n", message);
        std::exit (1);
    }
}

void set (garden::EchoProcessor& p, const char* id, float raw)
{
    auto* parameter = p.parameters.getParameter (id);
    check (parameter != nullptr, "parameter exists");
    parameter->setValueNotifyingHost (parameter->convertTo0to1 (raw));
}

float source (int sample, int rate, int channel)
{
    const float seconds = static_cast<float> (sample) / rate;
    const float pluck = std::exp (-7.0f * std::fmod (seconds, 0.42f));
    return (0.12f * std::sin (2.0f * juce::MathConstants<float>::pi * 220.0f * seconds)
          + 0.07f * std::sin (2.0f * juce::MathConstants<float>::pi * (channel ? 330.0f : 261.6f) * seconds))
          * pluck * (seconds < 1.25f ? 1.0f : 0.0f);
}

void writeAudio (const juce::File& file, juce::AudioBuffer<float>& audio, double rate)
{
    file.getParentDirectory().createDirectory();
    if (file.existsAsFile()) check (file.deleteFile(), "previous proof WAV removed before render");
    auto stream = std::make_unique<juce::FileOutputStream> (file);
    check (stream->openedOk(), "output WAV opened");
    juce::WavAudioFormat wav;
    auto writer = std::unique_ptr<juce::AudioFormatWriter> (wav.createWriterFor (stream.get(), rate, 2, 24, {}, 0));
    check (writer != nullptr, "WAV writer created");
    stream.release(); // writer owns the output stream
    check (writer->writeFromAudioSampleBuffer (audio, 0, audio.getNumSamples()), "WAV written");
}

void exerciseIdentity (int rate, int block)
{
    garden::EchoProcessor p;
    set (p, "space", 3);
    set (p, "wet", 1);
    set (p, "predelay", 0);
    p.prepareToPlay (rate, block);
    check (p.getLatencySamples() == 0, "zero-latency convolution reporting");
    juce::MidiBuffer midi;
    const int frames = block * 7 + 13;
    std::mt19937 generator (70);
    std::uniform_real_distribution<float> noise (-0.12f, 0.12f);
    int position = 0;
    size_t countBefore = allocations.load();
    while (position < frames)
    {
        const int length = juce::jmin (block, frames - position);
        juce::AudioBuffer<float> samples (2, length);
        juce::AudioBuffer<float> reference (2, length);
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < length; ++i)
            {
                const float x = position + i == 0 ? 0.9f : noise (generator);
                samples.setSample (c, i, x);
                reference.setSample (c, i, x);
            }
        // The first run may start JUCE's internal convolution worker. Exclude
        // it from steady-state allocation accounting, but check its samples.
        tracking.store (position > 0);
        p.processBlock (samples, midi);
        tracking.store (false);
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < length; ++i)
            {
                const float actual = samples.getSample (c, i), wanted = reference.getSample (c, i);
                if (!std::isfinite (actual) || std::abs (actual - wanted) >= 0.00006f)
                {
                    std::fprintf (stderr, "Identity %dHz/%d samples, index %d ch %d: %.8g vs %.8g\n",
                        rate, block, position + i, c, actual, wanted);
                    check (false, "wet identity equals undelayed input, tolerance 6e-5");
                }
            }
        position += length;
    }
    check (allocations.load() == countBefore, "no steady-state callback C++ heap allocations");
    p.releaseResources();
    std::printf ("PASS identity / finite / allocation: %d Hz, block %d\n", rate, block);
}

struct EmbeddedWave { const char* bytes; int size; };
const EmbeddedWave embeddedWaves[] = {
    { GardenKernels::leafchamber_wav, GardenKernels::leafchamber_wavSize },
    { GardenKernels::mossarcade_wav, GardenKernels::mossarcade_wavSize },
    { GardenKernels::raincanopy_wav, GardenKernels::raincanopy_wavSize }
};

void exerciseRecordedConvolution (int rate, int block, int preset)
{
    const auto wave = embeddedWaves[preset];
    juce::WavAudioFormat wav;
    std::unique_ptr<juce::AudioFormatReader> reader (wav.createReaderFor (
        new juce::MemoryInputStream (wave.bytes, static_cast<size_t> (wave.size), false), true));
    check (reader != nullptr && reader->numChannels == 2 && reader->lengthInSamples > 1,
        "embedded space is a stereo multi-sample WAV");
    check (reader->sampleRate > 0 && reader->lengthInSamples < 500000,
        "embedded kernel has a bounded valid length and sample rate");
    juce::AudioBuffer<float> original (2, static_cast<int> (reader->lengthInSamples));
    check (reader->read (&original, 0, original.getNumSamples(), 0, true, true), "embedded WAV decoded");

    // Independent time-domain reference. Match JUCE's documented pinned
    // resampling path (MemoryAudioSource -> ResamplingAudioSource), including
    // its non-normalised sample-rate gain, then compare against FFT output.
    juce::AudioBuffer<float> kernel;
    if (reader->sampleRate == rate)
        kernel = original;
    else
    {
        juce::MemoryAudioSource source (original, false);
        juce::ResamplingAudioSource resampler (&source, false, 2);
        const double ratio = reader->sampleRate / rate;
        const int size = juce::roundToInt (juce::jmax (1.0, original.getNumSamples() / ratio));
        resampler.setResamplingRatio (ratio);
        resampler.prepareToPlay (size, reader->sampleRate);
        kernel.setSize (2, size);
        resampler.getNextAudioBlock ({ &kernel, 0, size });
        resampler.releaseResources();
    }
    kernel.applyGain (static_cast<float> (reader->sampleRate / rate));

    garden::EchoProcessor p;
    set (p, "space", static_cast<float> (preset));
    set (p, "wet", 1.0f);
    set (p, "predelay", 0.0f);
    p.prepareToPlay (rate, block);
    check (p.getLatencySamples() == 0, "recorded space has zero reported latency");
    check (p.getTailLengthSeconds() >= 2.25, "host tail covers bounded kernel and max predelay");
    juce::MidiBuffer midi;
    const int frames = kernel.getNumSamples() + block + 1;
    juce::AudioBuffer<float> chunk (2, block);
    double energy = 0.0, channelDifference = 0.0;
    float maximumError = 0.0f;
    for (int position = 0; position < frames; position += block)
    {
        const int count = juce::jmin (block, frames - position);
        chunk.clear();
        if (position == 0)
        {
            chunk.setSample (0, 0, 0.5f);
            chunk.setSample (1, 0, -0.375f);
        }
        // Last block can be shorter than the prepared block size.
        juce::AudioBuffer<float> view (chunk.getArrayOfWritePointers(), 2, count);
        p.processBlock (view, midi);
        for (int n = 0; n < count; ++n)
        {
            const int index = position + n;
            const float left = view.getSample (0, n), right = view.getSample (1, n);
            const float wantL = index < kernel.getNumSamples() ? 0.5f * kernel.getSample (0, index) : 0.0f;
            const float wantR = index < kernel.getNumSamples() ? -0.375f * kernel.getSample (1, index) : 0.0f;
            check (std::isfinite (left) && std::isfinite (right), "convolved WAV output finite");
            maximumError = juce::jmax (maximumError, std::abs (left - wantL), std::abs (right - wantR));
            energy += left * left + right * right;
            channelDifference += std::abs (left + right * (0.5f / 0.375f));
        }
    }
    if (maximumError >= 0.0004f)
    {
        std::fprintf (stderr, "Space %s, %dHz/%d: max direct-convolution error %.8g\n",
            garden::spaces[static_cast<size_t> (preset)].id, rate, block, maximumError);
        check (false, "embedded kernel FFT convolution matches time-domain impulse reference (4e-4)");
    }
    check (energy > 1.0e-9 && channelDifference > 1.0e-6,
        "kernel has audible energy and different left/right responses");
    // A seeded, non-impulse signal catches indexing and overlap mistakes that
    // an impulse-only check cannot. Render through the entire delayed echo,
    // including the 120ms of silence preceding the first recorded response.
    constexpr int probeLength = 512;
    const int outputLength = kernel.getNumSamples() + probeLength;
    std::mt19937 generator (static_cast<unsigned int> (preset + 304));
    std::uniform_real_distribution<float> noise (-0.08f, 0.08f);
    juce::AudioBuffer<float> input (2, probeLength), result (2, outputLength);
    result.clear();
    for (int c = 0; c < 2; ++c)
        for (int n = 0; n < probeLength; ++n)
            input.setSample (c, n, noise (generator));
    const int lengths[] { 7, block + 19, 1, block * 2 + 3, 37 };
    int callback = 0;
    for (int position = 0; position < outputLength; ++callback)
    {
        const int count = juce::jmin (lengths[callback % 5], outputLength - position);
        juce::AudioBuffer<float> batch (2, count);
        batch.clear();
        const int inputCount = juce::jlimit (0, count, probeLength - position);
        for (int c = 0; c < 2; ++c)
            if (inputCount > 0) batch.copyFrom (c, 0, input, c, position, inputCount);
        p.processBlock (batch, midi);
        for (int c = 0; c < 2; ++c) result.copyFrom (c, position, batch, c, 0, count);
        position += count;
    }
    juce::AudioBuffer<float> expected (2, outputLength);
    expected.clear();
    for (int c = 0; c < 2; ++c)
        for (int tap = 0; tap < kernel.getNumSamples(); ++tap)
        {
            const float coefficient = kernel.getSample (c, tap);
            if (coefficient == 0.0f) continue;
            for (int n = 0; n < probeLength; ++n)
                expected.addSample (c, tap + n, input.getSample (c, n) * coefficient);
        }
    float signalError = 0.0f, response = 0.0f;
    for (int c = 0; c < 2; ++c)
        for (int n = 0; n < outputLength; ++n)
        {
            signalError = juce::jmax (signalError, std::abs (result.getSample (c, n) - expected.getSample (c, n)));
            response = juce::jmax (response, std::abs (expected.getSample (c, n)));
        }
    check (response > 1.0e-6f, "seeded input produces a measurable recorded echo");
    check (signalError < 0.0004f, "seeded input matches independent direct FIR convolution (4e-4)");
    std::printf ("PASS embedded WAV convolution: %s, %d Hz, block %d, max error %.7g\n",
        garden::spaces[static_cast<size_t> (preset)].id, rate, block, juce::jmax (maximumError, signalError));
}

void behavior()
{
    garden::EchoProcessor p;
    juce::MidiBuffer midi;
    set (p, "space", 3);
    set (p, "wet", 1);
    set (p, "predelay", 75);
    p.prepareToPlay (48000, 64);
    juce::AudioBuffer<float> b (2, 64);
    for (int pos = 0; pos < 4800; pos += 64)
    {
        b.clear();
        if (pos == 0) b.setSample (0, 0, 0.7f);
        p.processBlock (b, midi);
        for (int i = 0; i < 64; ++i)
        {
            const auto index = pos + i;
            const auto expected = index == 3600 ? 0.7f : 0.0f;
            check (std::abs (b.getSample (0, i) - expected) < 0.00006f, "75ms predelay; impulse path exact");
            check (std::abs (b.getSample (1, i)) < 0.00006f, "stereo channel independence");
        }
    }
    set (p, "bypass", 1);
    for (int pass = 0; pass < 16; ++pass) // 12ms smooth bypass
    {
        b.clear();
        for (int i = 0; i < 64; ++i) b.setSample (0, i, 0.15f);
        p.processBlock (b, midi);
    }
    for (int i = 0; i < 64; ++i)
        check (std::abs (b.getSample (0, i) - 0.15f) < 0.00006f, "bypass dry unity after ramp");
    juce::MemoryBlock state;
    set (p, "space", 2);
    p.getStateInformation (state);
    garden::EchoProcessor restored;
    restored.setStateInformation (state.getData(), static_cast<int> (state.getSize()));
    check (restored.selectedSpace() == 2, "state roundtrip stores selected kernel hash");
    auto altered = juce::AudioProcessor::getXmlFromBinary (state.getData(), static_cast<int> (state.getSize()));
    check (altered != nullptr, "XML state decoded");
    altered->setAttribute ("kernelSha256", "bad-hash");
    juce::MemoryBlock invalid;
    juce::AudioProcessor::copyXmlToBinary (*altered, invalid);
    restored.setStateInformation (invalid.getData(), static_cast<int> (invalid.getSize()));
    check (restored.selectedSpace() == 3, "mismatched kernel hash falls back to unit identity");
    auto repaired = restored.parameters.copyState();
    check (static_cast<int> (repaired.getChildWithProperty ("id", "space").getProperty ("value")) == 3,
        "hash fallback persists in serialized parameter tree");
    altered->setAttribute ("kernelSha256", garden::spaces[2].sha256);
    auto* spaceXml = altered->getChildByAttribute ("id", "space");
    check (spaceXml != nullptr, "state contains space choice");
    spaceXml->setAttribute ("value", 1);
    juce::AudioProcessor::copyXmlToBinary (*altered, invalid);
    restored.setStateInformation (invalid.getData(), static_cast<int> (invalid.getSize()));
    check (restored.selectedSpace() == 3, "metadata must match the serialized space choice");
    restored.getStateInformation (invalid);
    auto normalized = juce::AudioProcessor::getXmlFromBinary (invalid.getData(), static_cast<int> (invalid.getSize()));
    check (normalized != nullptr && normalized->getStringAttribute ("kernelId") == garden::spaces[3].id,
        "saved metadata follows repaired detached choice");
    std::puts ("PASS 75ms impulse predelay, stereo, bypass, state restore/hash fallback");
}

void resetAndLargeHints (int rate, int hint)
{
    garden::EchoProcessor p;
    juce::MidiBuffer midi;
    set (p, "space", 3);
    set (p, "wet", 1);
    set (p, "predelay", 250);
    p.prepareToPlay (rate, hint);
    juce::AudioBuffer<float> impulse (2, 1);
    impulse.clear();
    impulse.setSample (0, 0, 0.7f);
    p.processBlock (impulse, midi);
    p.reset();
    const int delaySamples = rate / 4;
    int position = 0;
    for (int callback = 0; position < delaySamples + 79; ++callback)
    {
        const int length = juce::jmin (callback % 3 == 0 ? hint + 101 : (callback % 3 == 1 ? 13 : 513),
                                      delaySamples + 79 - position);
        juce::AudioBuffer<float> block (2, length);
        block.clear();
        if (position == 0) block.setSample (0, 0, 0.4f);
        p.processBlock (block, midi);
        for (int i = 0; i < length; ++i)
        {
            const float expected = position + i == delaySamples ? 0.4f : 0.0f;
            check (std::abs (block.getSample (0, i) - expected) < 0.00006f,
                "reset removes prior 250ms predelay impulse while preserving fresh timing");
            check (std::abs (block.getSample (1, i)) < 0.00006f, "reset keeps stereo channels independent");
        }
        position += length;
    }
    // The recorded IR first responds long after the initiating callback.
    // Reset must discard that pending convolution history too.
    set (p, "space", 0);
    set (p, "predelay", 0);
    p.prepareToPlay (rate, hint);
    impulse.clear();
    impulse.setSample (0, 0, 0.8f);
    p.processBlock (impulse, midi);
    p.reset();
    juce::AudioBuffer<float> silent (2, hint + 101);
    const size_t countBefore = allocations.load();
    for (int pass = 0; pass < 2; ++pass)
    {
        silent.clear();
        tracking.store (pass != 0);
        p.processBlock (silent, midi);
        tracking.store (false);
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < silent.getNumSamples(); ++i)
                check (std::abs (silent.getSample (c, i)) < 0.00006f, "reset removes convolution tail");
    }
    check (allocations.load() == countBefore, "oversized callbacks avoid steady-state C++ allocations");
    std::printf ("PASS reset / large prepare hint: %d Hz, hint %d\n", rate, hint);
}

void switchingAndVariableBlocks()
{
    garden::EchoProcessor changing, old, next;
    for (auto* p : { &changing, &old, &next })
    {
        set (*p, "wet", 1);
        set (*p, "predelay", 0);
        p->prepareToPlay (48000, 32);
    }
    set (next, "space", 1);
    // The first render of next is at preset 0, so fill the 65ms ramp before
    // comparing against its fully settled target.
    juce::MidiBuffer midi;
    int position = 0;
    for (int pass = 0; pass < 220; ++pass)
    {
        const int frames = pass % 2 ? 13 : 513; // exceeds 32-sample prepare hint
        juce::AudioBuffer<float> a (1, frames), b (1, frames), c (1, frames);
        for (int i = 0; i < frames; ++i)
        {
            const float input = 0.08f * std::sin (2 * juce::MathConstants<float>::pi
                                                 * 330.0f * (position + i) / 48000.0f);
            a.setSample (0, i, input);
            b.setSample (0, i, input);
            c.setSample (0, i, input);
        }
        if (pass == 70) set (changing, "space", 1);
        changing.processBlock (a, midi);
        old.processBlock (b, midi);
        next.processBlock (c, midi);
        for (int i = 0; i < frames; ++i)
        {
            const float actual = a.getSample (0, i);
            check (std::isfinite (actual) && std::abs (actual) < 0.8f, "mono switching finite and bounded");
            if (pass == 69)
                check (std::abs (actual - b.getSample (0, i)) < 0.0001f, "old preset matches before switch");
            if (pass == 70 && i == 0)
                check (std::abs (actual - b.getSample (0, i)) < 0.0004f, "first switching sample continuous");
            if (pass > 100)
                check (std::abs (actual - c.getSample (0, i)) < 0.0002f, "settled new preset retains pre-switch history");
        }
        position += frames;
    }
    juce::AudioBuffer<float> zero (1, 0);
    changing.processBlock (zero, midi);
    std::puts ("PASS mono layout, zero/oversized variable blocks, smooth preset change/history");
}

// Production clamps non-finite and out-of-range host rates before it sizes any
// buffer. Exercise the documented policy boundary set and confirm the callback
// stays finite and safe, including a zero samples-per-block prepare hint.
void sampleRatePolicy()
{
    const double rates[] {
        std::numeric_limits<double>::quiet_NaN(),
        std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
        0.0, -1000.0, 5.0, 7999.0, 8000.0, 384000.0, 384001.0, 1.0e9
    };
    juce::MidiBuffer midi;
    unsigned random = 0x1234abcdu;
    auto fill = [&random] (juce::AudioBuffer<float>& block)
    {
        for (int i = 0; i < block.getNumSamples(); ++i)
        {
            random = random * 1664525u + 1013904223u;
            const float x = 0.1f * (static_cast<float> (random >> 8) / 8388608.0f - 1.0f);
            block.setSample (0, i, x);
            block.setSample (1, i, -x);
        }
    };
    for (double rate : rates)
    {
        garden::EchoProcessor p;
        set (p, "space", 0);
        set (p, "wet", 1);
        set (p, "predelay", 250);
        p.prepareToPlay (rate, 64);
        juce::AudioBuffer<float> block (2, 64);
        fill (block);
        p.processBlock (block, midi); // warm the convolution engine outside accounting
        fill (block);
        const size_t before = allocations.load();
        tracking.store (true);
        p.processBlock (block, midi);
        tracking.store (false);
        bool finite = true;
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < 64; ++i)
                finite = finite && std::isfinite (block.getSample (c, i));
        check (finite, "non-finite or out-of-range sample rate produces finite output");
        check (allocations.load() == before, "out-of-range rate callback avoids steady-state allocation");
        p.releaseResources();
    }
    {
        garden::EchoProcessor p;
        set (p, "wet", 1);
        set (p, "predelay", 250);
        p.prepareToPlay (48000, 0); // maxBlock clamps to 1
        juce::AudioBuffer<float> one (2, 1);
        one.clear();
        one.setSample (0, 0, 0.3f);
        p.processBlock (one, midi);
        check (std::isfinite (one.getSample (0, 0)) && std::isfinite (one.getSample (1, 0)),
            "zero samples-per-block prepare is safe and finite");
        p.releaseResources();
    }
    std::puts ("PASS sample-rate policy: 11 clamped/non-finite rates finite, zero block hint safe");
}

void busesLayoutPolicy()
{
    garden::EchoProcessor p;
    juce::AudioProcessor::BusesLayout mono;
    mono.inputBuses.add (juce::AudioChannelSet::mono());
    mono.outputBuses.add (juce::AudioChannelSet::mono());
    check (p.isBusesLayoutSupported (mono), "mono in / mono out supported");
    juce::AudioProcessor::BusesLayout stereo;
    stereo.inputBuses.add (juce::AudioChannelSet::stereo());
    stereo.outputBuses.add (juce::AudioChannelSet::stereo());
    check (p.isBusesLayoutSupported (stereo), "stereo in / stereo out supported");
    juce::AudioProcessor::BusesLayout mismatch;
    mismatch.inputBuses.add (juce::AudioChannelSet::mono());
    mismatch.outputBuses.add (juce::AudioChannelSet::stereo());
    check (! p.isBusesLayoutSupported (mismatch), "mono in / stereo out rejected");
    std::puts ("PASS bus layouts: mono, stereo, mismatched mono->stereo rejected");
}

void allStudiesNative()
{
    juce::MidiBuffer midi;
    for (int study = 0; study <= 12; ++study)
    {
        garden::EchoProcessor p;
        set (p, "wet", 0.6f);
        set (p, "trim", -3.0f);
        set (p, "predelay", 37.0f);
        set (p, "study", static_cast<float> (study));
        p.prepareToPlay (48000, 64);
        check (p.selectedStudy() == study, "requested study is recalled exactly");
        const double expectedTail = study == 0 ? 2.25 : garden::EchoProcessor::studyTailSeconds;
        check (std::abs (p.getTailLengthSeconds() - expectedTail) < 1.0e-9,
            "tail length equals the single safe installed-bank maximum");
        juce::AudioBuffer<float> block (2, 64);
        unsigned random = static_cast<unsigned> (study * 7919 + 13);
        bool finite = true;
        for (int pass = 0; pass < 40; ++pass)
        {
            for (int i = 0; i < 64; ++i)
            {
                random = random * 1664525u + 1013904223u;
                const float x = 0.12f * (static_cast<float> (random >> 8) / 8388608.0f - 1.0f);
                block.setSample (0, i, x);
                block.setSample (1, i, -0.6f * x);
            }
            p.processBlock (block, midi);
            for (int c = 0; c < 2; ++c)
                for (int i = 0; i < 64; ++i)
                    finite = finite && std::isfinite (block.getSample (c, i));
        }
        check (finite, "every native study output is finite");
        p.releaseResources();
    }
    std::puts ("PASS all 13 study settings native: selection, tail, 40x64 finite blocks");
}

void benchmark()
{
    garden::EchoProcessor p;
    p.prepareToPlay (48000, 256);
    juce::AudioBuffer<float> b (2, 256);
    juce::MidiBuffer midi;
    const auto start = std::chrono::steady_clock::now();
    for (int block = 0; block < 188; ++block)
    {
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < 256; ++i) b.setSample (c, i, source (block * 256 + i, 48000, c));
        p.processBlock (b, midi);
    }
    const auto elapsed = std::chrono::duration<double> (std::chrono::steady_clock::now() - start).count();
    std::printf ("MEASURED wall %.4fs for %.4fs stereo 48k audio (4 warm FIR engines); ratio %.3f; shared VM\n",
        elapsed, 188 * 256.0 / 48000.0, elapsed / (188 * 256.0 / 48000.0));
}

void renderProof (const juce::File& folder)
{
    // The cue ends at 1.25s; retain a full 2s kernel plus 12ms predelay and
    // a small margin rather than truncating its terminal measured echo.
    constexpr int rate = 48000, block = 256, frames = 168000;
    juce::MidiBuffer midi;
    juce::AudioBuffer<float> dry (2, frames);
    for (int c = 0; c < 2; ++c)
        for (int i = 0; i < frames; ++i) dry.setSample (c, i, source (i, rate, c));
    for (int preset = 0; preset < 3; ++preset)
    {
        garden::EchoProcessor p;
        set (p, "space", static_cast<float> (preset));
        set (p, "predelay", 12.0f);
        set (p, "wet", 0.56f);
        set (p, "trim", -3.0f);
        p.prepareToPlay (rate, block);
        juce::AudioBuffer<float> wet (2, frames);
        float peak = 0;
        for (int start = 0; start < frames; start += block)
        {
            const int size = juce::jmin (block, frames - start);
            juce::AudioBuffer<float> chunk (2, size);
            for (int c = 0; c < 2; ++c) chunk.copyFrom (c, 0, dry, c, start, size);
            p.processBlock (chunk, midi);
            for (int c = 0; c < 2; ++c)
            {
                wet.copyFrom (c, start, chunk, c, 0, size);
                for (int i = 0; i < size; ++i)
                {
                    const float x = chunk.getSample (c, i);
                    check (std::isfinite (x), "proof audio finite");
                    peak = juce::jmax (peak, std::abs (x));
                }
            }
        }
        check (peak < 1.0f, "proof audio peak below clipping");
        const auto name = garden::spaces[static_cast<size_t> (preset)].id;
        writeAudio (folder.getChildFile (juce::String (name) + "-dry.wav"), dry, rate);
        writeAudio (folder.getChildFile (juce::String (name) + "-wet.wav"), wet, rate);
        std::printf ("PASS actual processor render: %s, peak %.5f\n", name, peak);
    }
}

void benchmarkStudies()
{
    garden::EchoProcessor p;
    set (p, "wet", .55f);
    set (p, "trim", -3.0f);
    set (p, "study", 1.0f);
    p.prepareToPlay (48000, 256);
    juce::AudioBuffer<float> samples (2, 256);
    juce::MidiBuffer midi;
    const auto before = allocations.load();
    const auto start = std::chrono::steady_clock::now();
    constexpr int blocks = 12 * 38; // 2.432 s at 48kHz, 256-frame callbacks
    float peak = 0;
    for (int block = 0; block < blocks; ++block)
    {
        if (block % 38 == 0) set (p, "study", static_cast<float> (block / 38 + 1));
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < 256; ++i)
                samples.setSample (c, i, source (block * 256 + i, 48000, c));
        tracking.store (block > 0);
        p.processBlock (samples, midi);
        tracking.store (false);
        for (int c = 0; c < 2; ++c)
            for (int i = 0; i < 256; ++i)
            {
                const float x = samples.getSample (c, i);
                check (std::isfinite (x), "all studies finite on native plugin");
                peak = juce::jmax (peak, std::abs (x));
            }
    }
    const auto elapsed = std::chrono::duration<double> (std::chrono::steady_clock::now() - start).count();
    check (peak < 1.0f, "all studies unclipped at matched levels");
    check (allocations.load() == before, "all studies no steady-state C++ allocation");
    std::printf ("MEASURED study switching wall %.4fs / audio %.4fs = %.3f; peak %.5f; new allocations 0 (12 warm DSP voices + original 4 FIRs)\n",
        elapsed, blocks * 256.0 / 48000.0, elapsed / (blocks * 256.0 / 48000.0), peak);
}
}

int main (int argc, char** argv)
{
    for (int rate : { 44100, 48000, 96000 })
        for (int block : { 32, 64, 256, 1024 })
        {
            exerciseIdentity (rate, block);
            for (int preset = 0; preset < 3; ++preset)
                exerciseRecordedConvolution (rate, block, preset);
        }
    behavior();
    for (int rate : { 44100, 48000, 96000 })
        for (int hint : { 8193, 16384 }) resetAndLargeHints (rate, hint);
    switchingAndVariableBlocks();
    sampleRatePolicy();
    busesLayoutPolicy();
    allStudiesNative();
    benchmark();
    benchmarkStudies();
    if (argc == 2) renderProof (juce::File (argv[1]));
    std::puts ("ALL EchoChecks PASSED");
    return 0;
}
