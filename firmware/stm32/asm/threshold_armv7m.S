/* Optional learning example only: ARM Cortex-M4/Thumb-2/AAPCS.
 * uint32_t lumos_ge_u32_asm(uint32_t value, uint32_t threshold)
 * Returns 1 if value >= threshold, otherwise 0.
 * Not used in the C firmware or native host simulator.
 * Unnecessary for performance here: the C compiler can do this well.
 */
.syntax unified
.thumb
.text
.global lumos_ge_u32_asm
.type lumos_ge_u32_asm, %function
.thumb_func
lumos_ge_u32_asm:
    cmp r0, r1
    blo 1f
    movs r0, #1
    bx lr
1:
    movs r0, #0
    bx lr
.size lumos_ge_u32_asm, .-lumos_ge_u32_asm
