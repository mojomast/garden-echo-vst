#pragma once

#include <array>

namespace garden::studyCatalog
{
enum class Family { repeats, moving, tone, texture };

struct Entry
{
    const char* id;
    const char* familyName;
    const char* listenFor;
    const char* terms;
    std::array<bool, 4> applicable;
};

// Search and accessible-description metadata for the canonical EffectCore bank.
// Applicability order is [Time, Feedback, Colour, Motion].
inline constexpr std::array<Entry, 12> entries {{
    {"terrace", "Repeats & rhythm", "Four early echoes step across the stereo field; listen for the spaced reflections after each attack.", "multitap taps reflections early room delay garden echoes", {true, true, true, false}},
    {"crossing", "Repeats & rhythm", "Repeats cross between left and right; listen for each side answering from the other.", "ping pong cross coupled stereo bounce delay echo", {true, true, true, false}},
    {"amber", "Repeats & rhythm", "A dark dub repeat hangs behind the note; listen for the low-pass tone to soften each return.", "dub dark filtered low pass feedback delay warm repeat", {true, true, true, true}},
    {"petal", "Moving & widening", "A short, gently moving chorus thickens the source; listen for a widening shimmer around sustained notes.", "chorus modulation modulated short quadrature width shimmer", {true, true, true, true}},
    {"canopy", "Moving & widening", "Three detuned voices spread around the source; listen for a broad ensemble-like sway.", "ensemble detuned voices triple widen modulation", {true, true, true, true}},
    {"ribbon", "Moving & widening", "A swept comb adds a bright moving edge; listen for the flange-like dip and rise around the dry tone.", "flanger flange swept comb jet motion feedback", {true, true, true, true}},
    {"wire", "Tone & resonance", "A tuned, damped comb rings close to the note; listen for a focused resonant tail.", "resonator resonance tuned comb damped ring tone", {true, true, true, false}},
    {"mist", "Texture & pulse", "Cascaded all-pass stages smear transients without a distinct echo; listen for a diffuse, softened edge.", "diffuser diffusion all pass allpass smear texture", {true, true, false, false}},
    {"lantern", "Texture & pulse", "Stereo amplitude pulses animate the echoes; listen for differing left-right swells.", "tremolo pulse amplitude panning stereo rhythm", {true, true, true, true}},
    {"brook", "Tone & resonance", "A moving low-pass sweep colors a short echo; listen for the returning tone opening and darkening.", "filter sweep lfo low pass moving echo stream", {true, true, true, true}},
    {"prism", "Moving & widening", "Unequal short delays create a wider image without a repeat loop; listen for a subtle stereo split.", "doubler double widening asymmetric stereo delay", {true, false, true, true}},
    {"steps", "Repeats & rhythm", "Signed taps form a syncopated pattern; listen for the off-beat accents and stereo answer.", "rhythmic taps syncopation signed pattern groove delay", {true, true, true, false}}
}};
} // namespace garden::studyCatalog
