/* AArch64 AAPCS64: uint32_t lumos_ge_u32_aarch64(uint32_t value, uint32_t threshold).
 * Arguments: w0, w1; return: w0. Educational example; not executed in CI
 * until an AArch64 toolchain/emulator is configured.
 */
.text
.global lumos_ge_u32_aarch64
.type lumos_ge_u32_aarch64, %function
lumos_ge_u32_aarch64:
    cmp w0, w1
    cset w0, hs
    ret
.size lumos_ge_u32_aarch64, .-lumos_ge_u32_aarch64
