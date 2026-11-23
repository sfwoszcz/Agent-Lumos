#include <assert.h>
#include <stdint.h>
#include <stdio.h>
extern uint32_t lumos_ge_u32_x86_64(uint32_t value, uint32_t threshold);
int main(void) {
    assert(lumos_ge_u32_x86_64(0u, 0u) == 1u);
    assert(lumos_ge_u32_x86_64(1u, 2u) == 0u);
    assert(lumos_ge_u32_x86_64(4000000000u, 7u) == 1u);
    assert(lumos_ge_u32_x86_64(0u, UINT32_MAX) == 0u);
    puts("x86-64 ABI tests: OK");
    return 0;
}
