#pragma once
#include "AtlasStudyData.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <vector>

namespace garden
{
// Authored classical DSP, not newly generated Atlas kernels. Future importers
// can supply measured tap coefficients via setPreset; provenance stays external.
// Wet-only stereo: mix, predelay, trim and bypass belong to the caller.
class EffectCore
{
public:
    static constexpr std::size_t effectCount = 12;
    struct Tap { float seconds, left, right; };
    struct Preset
    {
        const char* id;
        const char* name;
        const char* description;
        float delaySeconds, feedback, rateHz, depthSeconds;
        std::array<Tap, 4> taps;
    };
    // Normalized controls, default .5: time scales delays .5..1.5;
    // feedback scales the preset amount .4..1.2 (absolute maximum .864);
    // colour opens damping; motion sets modulation depth/rate where applicable.
    struct Parameters { float time = .5f, feedback = .5f, colour = .5f, motion = .5f; };
    // Append-only ordering: plugin study values 1..12 recall these indices.
    inline static constexpr std::array<Preset, effectCount> presets {{
        {"terrace", "Terrace Multitap", "Four weighted early reflections", .19f, .23f, .1f, 0,
            {{{.071f,.5f,.1f},{.137f,.2f,.45f},{.211f,.3f,.15f},{.317f,.12f,.3f}}}},
        {"crossing", "Crossing Ping-Pong", "Cross-coupled stereo repeats", .27f, .5f, .1f, 0, {}},
        {"amber", "Amber Dub", "Dark low-pass feedback echo", .36f, .57f, .17f, .0007f, {}},
        {"petal", "Petal Chorus", "Short quadrature modulated delay", .018f, .08f, .7f, .006f, {}},
        {"canopy", "Canopy Ensemble", "Three detuned delay voices", .029f, .1f, .43f, .009f, {}},
        {"ribbon", "Ribbon Flanger", "Short swept feedback comb", .003f, .55f, .21f, .0025f, {}},
        {"wire", "Wire Resonator", "Tuned damped comb resonance", .00682f, .72f, .1f, 0, {}},
        {"mist", "Mist Diffuser", "Cascaded stereo all-pass dispersion", .041f, .5f, .1f, 0, {}},
        {"lantern", "Lantern Tremolo Echo", "Opposed stereo amplitude pulses", .18f, .35f, 3.1f, 0, {}},
        {"brook", "Brook Filter Sweep", "LFO low-pass motion with short echo", .085f, .2f, .32f, 0, {}},
        {"prism", "Prism Stereo Doubler", "Asymmetric short stereo delays", .011f, 0, .13f, .001f, {}},
        {"steps", "Steps Rhythmic Taps", "Signed syncopated delay pattern", .24f, .38f, .1f, 0,
            {{{.12f,.55f,.15f},{.24f,-.2f,.5f},{.36f,.35f,-.2f},{.48f,.18f,.3f}}}}
    }};

    // Conservative authored-bank bound derived at compile time from presets
    // alone: the longest path under the maximum time scale, plus feedback decay
    // to -60 dB amplitude at the maximum bounded loop gain. It is not a
    // universal claim about arbitrary future setPreset banks. The plugin's host
    // tail must remain at or above this and must not shrink the proven value.
    struct BankTailEstimate { double longestPathSeconds, decaySeconds; };
    static constexpr BankTailEstimate estimateBankTail() noexcept
    {
        double longestPath = 0;
        double longestDelay = 0;
        for (const auto& preset : presets)
        {
            longestDelay = longestDelay > preset.delaySeconds ? longestDelay : preset.delaySeconds;
            for (const auto& tap : preset.taps)
                longestPath = longestPath > tap.seconds ? longestPath : tap.seconds;
        }
        constexpr double maximumTimeScale = 1.5;  // .5 + current.time maximum
        // Maximum bounded loop gain is .72 feedback * 1.2 control = .864, so
        // ceil(ln(1e-3 amplitude) / ln(.864)) = 48 feedback loops to -60 dB.
        constexpr double decayLoops = 48.0;
        return { longestPath * maximumTimeScale, decayLoops * longestDelay * maximumTimeScale };
    }

    // Only prepare allocates. All methods are single-audio-thread operations;
    // callers own control handoff. Processing accepts arbitrary block lengths.
    void prepare (double sampleRate, std::size_t /*maxBlock*/)
    {
        rate = std::isfinite (sampleRate) ? std::clamp (sampleRate, 8000.0, 384000.0) : 48000.0;
        for (auto& voice : voices)
            for (auto& line : voice.lines) line.assign (static_cast<std::size_t> (rate * 2.1) + 8, 0.0f);
        smoothing = static_cast<float> (1.0 - std::exp (-1.0 / (rate * .025)));
        fieldSmoothing = static_cast<float> (1.0 - std::exp (-1.0 / (rate * .018)));
        ready = true;
        reset();
    }
    void reset() noexcept
    {
        for (auto& voice : voices)
        {
            for (auto& line : voice.lines) std::fill (line.begin(), line.end(), 0.0f);
            voice.position = 0; voice.phase = 0; voice.low = {}; voice.second = {}; voice.fieldEnvelope = 0;
        }
        current = target;
        weights.fill (0); weights[selected] = 1;
    }
    void setEffect (std::size_t index) noexcept { selected = std::min (index, effectCount - 1); }
    void setParameters (Parameters p) noexcept
    { target = {unit (p.time), unit (p.feedback), unit (p.colour), unit (p.motion)}; }
    void setPreset (std::size_t index, const Preset& preset) noexcept
    {
        // Install mappings before prepare or while silent (no coefficient
        // crossfade here). Names require caller-owned lifetime. Numeric fields
        // are bounded at use. tailSeconds covers the authored bank only.
        if (index < effectCount) bank[index] = preset;
    }
    std::array<float, 2> processSample (float left, float right) noexcept
    {
        if (!ready) return {};
        current.time += smoothing * (target.time - current.time);
        current.feedback += smoothing * (target.feedback - current.feedback);
        current.colour += smoothing * (target.colour - current.colour);
        current.motion += smoothing * (target.motion - current.motion);
        const std::array<float, 2> input {safe (left), safe (right)};
        std::array<float, 2> output {};
        for (std::size_t i = 0; i < effectCount; ++i)
        {
            weights[i] += smoothing * ((i == selected ? 1.0f : 0.0f) - weights[i]);
            if (weights[i] < 1.0e-20f) weights[i] = 0;
            // Live histories allow smooth switches without clearing in callbacks.
            const auto wet = tick (i, input);
            for (int c = 0; c < 2; ++c) output[c] += weights[i] * wet[c];
        }
        return {safe (output[0]), safe (output[1])};
    }
    void process (float* left, float* right, std::size_t frames) noexcept
    {
        if (left == nullptr || right == nullptr) return;
        for (std::size_t n = 0; n < frames; ++n)
        {
            const auto out = processSample (left[n], right[n]);
            left[n] = out[0]; right[n] = out[1];
        }
    }
    static constexpr double tailSeconds = 30.0;

private:
    static float bounded (float v, float lo, float hi) noexcept
    { return std::isfinite (v) ? std::clamp (v, lo, hi) : lo; }
    static float unit (float v) noexcept { return bounded (v, 0, 1); }
    static float safe (float v) noexcept
    { return std::abs (v) < 1.0e-20f ? 0.0f : (std::isfinite (v) ? std::clamp (v, -8.0f, 8.0f) : 0.0f); }
    struct Voice
    {
        std::array<std::vector<float>, 2> lines;
        std::array<float, 2> low {}, second {};
        std::size_t position = 0;
        double phase = 0;
        float fieldEnvelope = 0;
    };
    float read (const Voice& v, int channel, float seconds) const noexcept
    {
        const auto& line = v.lines[channel];
        const float delay = bounded (seconds * static_cast<float> (rate), 1, static_cast<float> (line.size() - 2));
        const auto whole = static_cast<std::size_t> (delay);
        const auto a = (v.position + line.size() - whole) % line.size();
        const auto b = (a + line.size() - 1) % line.size();
        return line[a] + (delay - static_cast<float> (whole)) * (line[b] - line[a]);
    }
    std::array<float, 2> tick (std::size_t index, const std::array<float, 2>& input) noexcept
    {
        auto& v = voices[index];
        const auto& p = bank[index];
        const float scale = .5f + current.time;
        const float base = bounded (p.delaySeconds, .001f, 1) * scale;
        const float feedback = bounded (p.feedback, 0, .72f) * (.4f + current.feedback * .8f);
        const float depth = bounded (p.depthSeconds, 0, .02f) * (current.motion * 2);
        const float frequency = bounded (p.rateHz, .01f, 10) * (.3f + current.motion * 1.4f);
        v.phase += frequency / rate;
        if (v.phase >= 1) v.phase -= 1;
        // The 16 genuine Blur Core values form a cyclic control trajectory;
        // one-pole smoothing avoids an audible discontinuity at cell edges.
        if (index == 8 || index == 9)
        {
            const auto step = std::min (15, static_cast<int> (v.phase * 16));
            const auto field = atlasStudy::fields[index == 8 ? 1 : 0][static_cast<std::size_t> (step)];
            v.fieldEnvelope += fieldSmoothing * (field - v.fieldEnvelope);
        }
        constexpr double tau = 6.283185307179586;
        std::array<float, 2> delayed {}, result {};
        for (int c = 0; c < 2; ++c)
        {
            const float wave = static_cast<float> (std::sin (tau * (v.phase + c * .25)));
            delayed[c] = read (v, c, base + depth * wave + (index == 10 ? c * .009f : 0));
            float cutoff = 400 + current.colour * 15000;
            if (index == 2) cutoff = 250 + current.colour * 3000;
            if (index == 9) cutoff = 250 + v.fieldEnvelope * (850 + current.colour * 5700);
            const float coefficient = static_cast<float> (1 - std::exp (-tau * cutoff / rate));
            v.low[c] = safe (v.low[c] + coefficient * (delayed[c] - v.low[c]));
        }
        for (int c = 0; c < 2; ++c)
        {
            float write = input[c] + feedback * v.low[index == 1 ? 1 - c : c];
            float wet = v.low[c];
            if (index == 0 || index == 11)
            {
                wet = 0;
                float norm = 0;
                for (const auto& tap : p.taps)
                {
                    const float gain = bounded (c == 0 ? tap.left : tap.right, -1, 1);
                    wet += gain * read (v, c, bounded (tap.seconds, 0, 1.3f) * scale);
                    norm += std::abs (gain);
                }
                wet /= std::max (1.0f, norm);
            }
            if (index == 4)
            {
                wet = 0;
                for (int j = 0; j < 3; ++j)
                    wet += read (v, c, base + depth * static_cast<float> (std::sin (tau * (v.phase + j / 3.0 + c * .17)))) / 3;
            }
            if (index == 5) wet = .5f * (input[c] + wet);
            if (index == 7)
            {
                const float first = delayed[c] - feedback * input[c];
                write = input[c] + feedback * first;
                wet = v.second[c] - .55f * first;
                v.second[c] = safe (first + .55f * wet);
            }
            if (index == 8)
                wet *= (1 - current.motion * .7f) + current.motion * .7f *
                    (c == 0 ? v.fieldEnvelope : .5f * (v.fieldEnvelope + .4f));
            v.lines[c][v.position] = safe (write);
            result[c] = safe (wet);
        }
        if (++v.position == v.lines[0].size()) v.position = 0;
        return result;
    }
    std::array<Voice, effectCount> voices;
    std::array<Preset, effectCount> bank = presets;
    std::array<float, effectCount> weights {};
    Parameters current, target;
    std::size_t selected = 0;
    double rate = 48000;
    float smoothing = .001f;
    float fieldSmoothing = .001f;
    bool ready = false;
};

// Outside the class body so the constexpr member definition is complete.
static_assert (EffectCore::tailSeconds
        >= EffectCore::estimateBankTail().decaySeconds + EffectCore::estimateBankTail().longestPathSeconds,
    "EffectCore tailSeconds must cover the authored preset bank under maximum controls");
} // namespace garden
