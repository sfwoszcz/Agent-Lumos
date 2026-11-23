/* Native STM32 wire-format simulator: C frame encoder + C++ health policy. */
#include "health_policy.hpp"
#include "lumos_protocol.h"

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

int main() {
    constexpr std::array<lumos::Sample, 4> samples{{
        {3300, 2430}, {3260, 2525}, {3100, 7480}, {3300, 2600},
    }};
    const lumos::HealthPolicy policy;
    for (std::size_t i = 0; i < samples.size(); ++i) {
        char frame[LUMOS_FRAME_CAPACITY];
        const int count = lumos_encode("stm32-sim", static_cast<uint32_t>(i + 1),
             static_cast<uint32_t>((i + 1) * 1000),
             *samples[i].vdd_mv, *samples[i].temperature_centi,
             policy.classify(samples[i]), frame, sizeof(frame));
        if (count < 0 || std::fwrite(frame, 1u, static_cast<std::size_t>(count), stdout)
                               != static_cast<std::size_t>(count)) return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
