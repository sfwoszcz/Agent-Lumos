#pragma once

#include <cstdint>
#include <optional>

namespace lumos {
struct Sample {
    std::optional<int32_t> vdd_mv;
    std::optional<int32_t> temperature_centi;
};

class HealthPolicy final {
public:
    HealthPolicy(int32_t minimum_vdd_mv = 3200, int32_t maximum_temp_centi = 7000)
        : minimum_vdd_mv_(minimum_vdd_mv), maximum_temp_centi_(maximum_temp_centi) {}

    const char* classify(const Sample& sample) const noexcept;

private:
    const int32_t minimum_vdd_mv_;
    const int32_t maximum_temp_centi_;
};
}  // namespace lumos
