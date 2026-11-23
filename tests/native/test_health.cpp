#include "health_policy.hpp"
#include <cassert>
#include <string_view>
#include <iostream>
int main() {
    lumos::HealthPolicy policy;
    assert(std::string_view(policy.classify({3300, 2500})) == "ok");
    assert(std::string_view(policy.classify({3199, 2500})) == "warn");
    assert(std::string_view(policy.classify({3200, 7001})) == "warn");
    assert(std::string_view(policy.classify({3200, 7000})) == "ok");
    assert(std::string_view(policy.classify({std::nullopt, std::nullopt})) == "unknown");
    std::cout << "health-policy boundary tests: OK\n";
}
