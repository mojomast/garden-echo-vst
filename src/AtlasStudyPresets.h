#pragma once
#include "AtlasStudyData.h"
#include "EffectCore.h"

namespace garden
{
// Local, reproducible interpretation of the verified simulator results. The
// phase-mode Prism source is DENSE; its six signed 128-frame onset integrals
// are intentionally a sparse approximation, not full dense FIR convolution.
inline EffectCore::Preset atlasMappedPreset (std::size_t index) noexcept
{
    auto result = EffectCore::presets[index];
    const auto source = index % 3; // Bloom, Prism, Fracture; stable append-only mapping
    const auto fieldFilter = atlasStudy::fields[0][(index * 3) % 16];
    const auto fieldRhythm = atlasStudy::fields[1][(index * 5) % 16];
    const auto central = atlasStudy::measuredCenterComplex[source][index % 6];
    const auto onset = atlasStudy::remoteOnsetSums[source][index % 6];
    const auto step = source == 0 ? .16f : (source == 1 ? .21f : .26f);
    // Original short chorus/flanger/resonator/doubler character is retained;
    // Bloom/Prism/Fracture time and complex trajectory alter bounded controls.
    const bool longDelay = index == 0 || index == 1 || index == 2 || index == 8 || index == 11;
    result.delaySeconds = longDelay
        ? step * (1.0f + .18f * std::abs (central[0]) + .04f * std::abs (onset[1]))
        : result.delaySeconds * (.8f + .4f * fieldFilter + .08f * std::abs (onset[0]));
    result.feedback = std::min (.65f, result.feedback * (.8f + .25f * fieldRhythm + .1f * std::abs (onset[0])));
    result.rateHz = std::min (9.0f, result.rateHz * (.75f + .65f * std::abs (central[0]) + .3f * fieldRhythm));
    result.depthSeconds *= .65f + .65f * fieldFilter;
    if (index == 0 || index == 11)
    {
        float maximum = .01f;
        for (std::size_t tap = 0; tap < 4; ++tap)
            for (int c = 0; c < 2; ++c)
                maximum = std::max (maximum, std::abs (atlasStudy::remoteOnsetSums[source][tap][c]));
        for (std::size_t tap = 0; tap < 4; ++tap)
        {
            auto& t = result.taps[tap];
            const auto rhythm = atlasStudy::fields[1][(index + tap * 4) % 16];
            t.seconds = index == 0 ? step * (tap + 1)
                                     : step * (.5f + tap * .43f) + .025f * rhythm;
            t.left = .58f * atlasStudy::remoteOnsetSums[source][tap][0] / maximum * (.7f + .3f * rhythm);
            t.right = .58f * atlasStudy::remoteOnsetSums[source][tap][1] / maximum * (.7f + .3f * rhythm);
        }
    }
    return result;
}
} // namespace garden
