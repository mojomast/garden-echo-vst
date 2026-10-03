#include "../src/EffectCore.h"
#include "../src/AtlasStudyPresets.h"
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <new>

namespace { bool tracking = false; std::size_t allocations = 0; }
void* operator new (std::size_t n)
{
    if (tracking) ++allocations;
    if (auto* p = std::malloc (n == 0 ? 1 : n)) return p;
    throw std::bad_alloc();
}
void* operator new[] (std::size_t n) { return ::operator new (n); }
void operator delete (void* p) noexcept { std::free (p); }
void operator delete[] (void* p) noexcept { std::free (p); }
void operator delete (void* p, std::size_t) noexcept { std::free (p); }
void operator delete[] (void* p, std::size_t) noexcept { std::free (p); }

namespace
{
void check (bool ok, const char* message)
{
    if (!ok) { std::fprintf (stderr, "FAIL: %s\n", message); std::exit (1); }
}
using Core = garden::EffectCore;
void exercise (int rate)
{
    Core core;
    core.prepare (rate, 256);
    constexpr std::array<std::size_t, 7> blocks {0, 1, 32, 64, 256, 1024, 71};
    std::array<float, 1024> left {}, right {};
    std::array<std::vector<float>, Core::effectCount> fingerprints;
    for (std::size_t effect = 0; effect < Core::effectCount; ++effect)
    {
        core.setEffect (effect);
        core.setParameters ({});
        core.reset();
        auto& fingerprint = fingerprints[effect];
        fingerprint.resize (static_cast<std::size_t> (rate));
        std::size_t frame = 0, iteration = 0;
        double energy = 0, finalEnergy = 0;
        float peak = 0;
        while (frame < static_cast<std::size_t> (rate * 4))
        {
            const auto count = std::min (blocks[iteration++ % blocks.size()], static_cast<std::size_t> (rate * 4) - frame);
            left.fill (0); right.fill (0);
            if (frame == 0 && count > 0) left[0] = 1;
            tracking = true;
            core.process (left.data(), right.data(), count);
            tracking = false;
            for (std::size_t n = 0; n < count; ++n)
            {
                check (std::isfinite (left[n]) && std::isfinite (right[n]), "finite impulse tail");
                peak = std::max ({peak, std::abs (left[n]), std::abs (right[n])});
                energy += left[n] * left[n] + right[n] * right[n];
                if (frame + n >= static_cast<std::size_t> (rate * 3))
                    finalEnergy += left[n] * left[n] + right[n] * right[n];
                if (frame + n < fingerprint.size()) fingerprint[frame + n] = left[n] + .37f * right[n];
            }
            frame += count;
        }
        check (energy > 1.0e-6, "each study produces an audible impulse response");
        check (peak < 2, "default unit impulse peak bounded");
        check (finalEnergy < energy * .001, "default tail decays by four seconds");
        // Reset repeatability and sample/block equivalence against saved output.
        core.reset();
        for (std::size_t n = 0; n < fingerprint.size(); ++n)
        {
            const auto out = core.processSample (n == 0 ? 1.0f : 0.0f, 0);
            check (std::abs (out[0] + .37f * out[1] - fingerprint[n]) < 1.0e-6f,
                "reset deterministic; arbitrary blocks equal sample processing");
        }
    }
    for (std::size_t a = 0; a < Core::effectCount; ++a)
        for (std::size_t b = a + 1; b < Core::effectCount; ++b)
        {
            double difference = 0;
            for (std::size_t n = 0; n < fingerprints[a].size(); ++n)
            {
                const auto d = fingerprints[a][n] - fingerprints[b][n];
                difference += d * d;
            }
            check (difference > 1.0e-5, "pairwise distinct impulse responses");
        }
    // Maximum controls, changing selections, sine + deterministic noise and a
    // full conservative tail window. All voices keep running during this test.
    core.reset();
    unsigned random = 17;
    float finalPeak = 0;
    tracking = true;
    for (int n = 0; n < rate * 32; ++n)
    {
        if (n % 257 == 0)
        {
            core.setEffect (static_cast<std::size_t> (n / 257) % Core::effectCount);
            core.setParameters ({1, 1, n % 2 == 0 ? 0.0f : 1.0f, 1});
        }
        random = random * 1664525u + 1013904223u;
        const float x = n < rate ? .2f * static_cast<float> (std::sin (n * .07))
            + .1f * (static_cast<float> (random >> 8) / 8388608.0f - 1) : 0;
        const auto out = core.processSample (x, -.5f * x);
        check (std::isfinite (out[0]) && std::isfinite (out[1]), "finite automated stress output");
        check (std::max (std::abs (out[0]), std::abs (out[1])) <= 8.0f, "stress peak bounded");
        if (n > rate * 31) finalPeak = std::max ({finalPeak, std::abs (out[0]), std::abs (out[1])});
    }
    tracking = false;
    check (finalPeak < 1.0e-5f, "maximum feedback tail decays within advertised tail");
    core.setParameters ({std::numeric_limits<float>::quiet_NaN(), 100, -100, 100});
    const auto invalid = core.processSample (std::numeric_limits<float>::infinity(), std::numeric_limits<float>::quiet_NaN());
    check (std::isfinite (invalid[0]) && std::isfinite (invalid[1]), "invalid input containment");
    std::printf ("PASS %d Hz: 12 studies, distinct responses, variable blocks, reset, automation, tails\n", rate);
}

// Honest installed-bank proof: this exercises the *authored Atlas-mapped* bank
// that the plugin actually installs, not just the compile-time authored table.
// It asserts no universal EffectCore claim: a different future setPreset bank
// could exceed the bound.
void bankTail()
{
    const auto estimate = Core::estimateBankTail();
    check (estimate.decaySeconds + estimate.longestPathSeconds <= Core::tailSeconds,
        "advertised tail covers the authored bank estimate");
    std::printf ("MEASURED authored bank estimate: longest path %.6fs + decay %.6fs = %.6fs <= tail %.1fs\n",
        estimate.longestPathSeconds, estimate.decaySeconds,
        estimate.longestPathSeconds + estimate.decaySeconds, Core::tailSeconds);

    constexpr int rate = 48000;
    const auto total = static_cast<std::size_t> (rate * (Core::tailSeconds + 1.0));
    const auto tailStart = static_cast<std::size_t> (rate * Core::tailSeconds);
    double worstFinalPeak = 0;
    for (std::size_t effect = 0; effect < Core::effectCount; ++effect)
    {
        Core core;
        for (std::size_t i = 0; i < Core::effectCount; ++i)
            core.setPreset (i, garden::atlasMappedPreset (i)); // the installed bank
        core.prepare (rate, 256);
        core.setEffect (effect);
        core.setParameters ({1, 1, 1, 1}); // maximum time / feedback / colour / motion
        core.reset();
        unsigned random = 0x9e3779b9u ^ static_cast<unsigned> (effect * 2654435761u);
        float finalPeak = 0;
        bool finite = true;
        for (std::size_t n = 0; n < total; ++n)
        {
            random = random * 1664525u + 1013904223u;
            const float noise = static_cast<float> (random >> 8) / 8388608.0f - 1.0f;
            const float x = n < static_cast<std::size_t> (rate) ? 0.2f * noise : 0.0f;
            const auto out = core.processSample (x, 0.7f * x);
            finite = finite && std::isfinite (out[0]) && std::isfinite (out[1]);
            if (n >= tailStart)
                finalPeak = std::max ({finalPeak, std::abs (out[0]), std::abs (out[1])});
        }
        check (finite, "installed bank tail output stays finite under maximum controls");
        check (finalPeak < 1.0e-3f, "installed Atlas-mapped study decays inside the advertised tail");
        worstFinalPeak = std::max (worstFinalPeak, static_cast<double> (finalPeak));
        std::printf ("  study %2zu %-9s final-second peak %.3e\n", effect, Core::presets[effect].id, finalPeak);
    }
    check (worstFinalPeak < 1.0e-3, "every installed Atlas-mapped study decays inside the advertised tail");
    std::printf ("PASS authored Atlas-mapped bank tail: 12 studies, bound <%.3fs within tail %.1fs\n",
        estimate.longestPathSeconds + estimate.decaySeconds, Core::tailSeconds);
    std::printf ("MEASURED worst final-second peak across 12 Atlas-mapped studies: %.3e\n", worstFinalPeak);
}
}
int main()
{
    for (const auto rate : {44100, 48000, 96000}) exercise (rate);
    bankTail();
    check (allocations == 0, "no C++ allocations during processing or control changes");
    std::puts ("PASS zero processing allocations");
}
