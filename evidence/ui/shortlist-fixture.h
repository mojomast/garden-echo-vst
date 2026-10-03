#pragma once
#include <array>
// UI regression fixture only. Non-contiguous canonical choices: 1, 4, 9, 12.
namespace garden::selection
{
inline constexpr bool enabled = true;
inline constexpr const char* bankSha256 = "ui-regression-fixture-not-a-release-bank";
inline constexpr std::array<bool, 12> allowed {{ true, false, false, true,
    false, false, false, false, true, false, false, true }};
}
