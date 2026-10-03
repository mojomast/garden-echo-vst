#include "../src/PluginProcessor.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <cmath>
#include <memory>
#include <array>

namespace
{
void require (bool ok, const juce::String& why)
{
    if (! ok) throw std::runtime_error (why.toStdString());
}

void set (garden::EchoProcessor& processor, const char* id, float value)
{
    auto* parameter = processor.parameters.getParameter (id);
    require (parameter != nullptr, "Missing plugin parameter: " + juce::String (id));
    parameter->setValueNotifyingHost (parameter->convertTo0to1 (value));
}

void render (const juce::File& source, const juce::File& dest, int study, float wet, float trim)
{
    juce::WavAudioFormat format;
    auto input = std::unique_ptr<juce::AudioFormatReader> (format.createReaderFor (source.createInputStream().release(), true));
    require (input != nullptr && input->numChannels == 2 && input->sampleRate == 48000.0
             && input->lengthInSamples > 0 && input->lengthInSamples <= 48000 * 16,
             "Expected <=16s stereo 48k WAV: " + source.getFullPathName());
    garden::EchoProcessor processor;
    set (processor, "study", static_cast<float> (study));
    set (processor, "wet", wet);
    set (processor, "predelay", 0.0f);
    set (processor, "trim", trim);
    processor.prepareToPlay (48000.0, 256);
    auto output = std::make_unique<juce::FileOutputStream> (dest);
    require (output->openedOk(), "Cannot open " + dest.getFullPathName());
    // A canonical RIFF PCM16 header avoids JUCE's otherwise harmless JUNK
    // reservation chunk; strict portable bank consumers require fmt+data only.
    const auto bytes = static_cast<juce::uint32> (input->lengthInSamples * 4);
    std::array<unsigned char, 44> header {};
    auto put16 = [&] (int offset, juce::uint16 value)
    { for (int i = 0; i < 2; ++i) header[static_cast<size_t> (offset + i)] = static_cast<unsigned char> (value >> (8 * i)); };
    auto put32 = [&] (int offset, juce::uint32 value)
    { for (int i = 0; i < 4; ++i) header[static_cast<size_t> (offset + i)] = static_cast<unsigned char> (value >> (8 * i)); };
    for (auto [offset, text] : { std::pair {0, "RIFF"}, {8, "WAVE"}, {12, "fmt "}, {36, "data"} })
        for (int i = 0; i < 4; ++i) header[static_cast<size_t> (offset + i)] = static_cast<unsigned char> (text[i]);
    put32 (4, 36 + bytes); put32 (16, 16); put16 (20, 1); put16 (22, 2);
    put32 (24, 48000); put32 (28, 48000 * 4); put16 (32, 4); put16 (34, 16); put32 (40, bytes);
    require (output->write (header.data(), header.size()), "Cannot write WAV header");
    juce::AudioBuffer<float> block (2, 256);
    std::array<unsigned char, 256 * 4> encoded {};
    juce::MidiBuffer midi;
    double peak = 0.0;
    for (juce::int64 start = 0; start < input->lengthInSamples; start += 256)
    {
        const int length = static_cast<int> (std::min<juce::int64> (256, input->lengthInSamples - start));
        block.clear();
        require (input->read (&block, 0, length, start, true, true), "Cannot read input WAV");
        // A fixed-length source already contains its tail silence. No hidden
        // per-render normalization, limiter, or callback allocations.
        processor.processBlock (block, midi);
        for (int c = 0; c < 2; ++c)
            for (int n = 0; n < length; ++n)
            {
                const auto sample = block.getSample (c, n);
                require (std::isfinite (sample), "Nonfinite DSP output");
                peak = std::max (peak, std::abs (static_cast<double> (sample)));
            }
        for (int n = 0; n < length; ++n)
            for (int c = 0; c < 2; ++c)
            {
                const auto scaled = static_cast<juce::int32> (std::lrint (block.getSample (c, n) * 32767.0f));
                const auto bits = static_cast<juce::uint32> (scaled);
                for (int byte = 0; byte < 2; ++byte)
                    encoded[static_cast<size_t> (n * 4 + c * 2 + byte)] = static_cast<unsigned char> (bits >> (8 * byte));
            }
        require (output->write (encoded.data(), static_cast<size_t> (length * 4)), "Cannot write WAV");
    }
    require (peak < 0.98, "Clipped/high-peak rendering: " + dest.getFileName());
    juce::Logger::writeToLog (dest.getFileName() + " peak=" + juce::String (peak, 6));
}
}

int main (int argc, char** argv)
{
    try
    {
        require (argc == 4, "Usage: GardenBankRender DRY_DIR OUTPUT_DIR EFFECTS_JSON");
        const juce::File dry (juce::String::fromUTF8 (argv[1]));
        const juce::File output (juce::String::fromUTF8 (argv[2]));
        const juce::File description (juce::String::fromUTF8 (argv[3]));
        auto data = juce::JSON::parse (description);
        auto effectsValue = data.getProperty ("effects", juce::var());
        auto* effects = effectsValue.getArray();
        require (effects != nullptr && effects->size() >= 10 && effects->size() <= 12, "Need 10–12 effects");
        require (output.createDirectory().wasOk(), "Cannot create output directory");
        for (const auto& effect : *effects)
        {
            auto id = effect.getProperty ("id", "").toString();
            require (id.isNotEmpty() && id.length() < 64 && id.containsOnly ("abcdefghijklmnopqrstuvwxyz0123456789-"), "Invalid effect ID");
            auto index = static_cast<int> (effect.getProperty ("studyIndex", -1));
            require (index >= 1 && index <= 12, "Invalid study index");
            const auto wet = static_cast<float> (effect.getProperty ("wet", 0.55));
            const auto trim = static_cast<float> (effect.getProperty ("trim", 4.0));
            require (wet >= 0.0f && wet <= 1.0f && trim >= -24.0f && trim <= 6.0f, "Unsafe effect gains");
            for (const auto* cue : { "drum", "pluck", "chord" })
                render (dry.getChildFile (juce::String (cue) + "-dry.wav"),
                        output.getChildFile (id + "-" + cue + ".wav"), index, wet, trim);
        }
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf (stderr, "GardenBankRender: %s\n", error.what());
        return 1;
    }
}
