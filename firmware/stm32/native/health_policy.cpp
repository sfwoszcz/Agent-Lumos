#include "health_policy.hpp"

namespace lumos {
const char* HealthPolicy::classify(const Sample& sample) const noexcept {
    if (!sample.vdd_mv.has_value() && !sample.temperature_centi.has_value()) return "unknown";
    if ((sample.vdd_mv && *sample.vdd_mv < minimum_vdd_mv_) ||
        (sample.temperature_centi && *sample.temperature_centi > maximum_temp_centi_)) return "warn";
    return "ok";
}
}  // namespace lumos
