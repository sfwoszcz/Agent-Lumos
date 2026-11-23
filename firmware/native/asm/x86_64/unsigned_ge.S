/* Linux x86-64 System V ABI: uint32_t ge(uint32_t value, uint32_t threshold).
 * Arguments: edi, esi; return: eax. No syscalls, I/O, or memory access.
 * Educational ABI/disassembly lab, not a security boundary.
 */
.text
.globl lumos_ge_u32_x86_64
.type lumos_ge_u32_x86_64, @function
lumos_ge_u32_x86_64:
    cmpl %esi, %edi
    setae %al
    movzbl %al, %eax
    ret
.size lumos_ge_u32_x86_64, .-lumos_ge_u32_x86_64
.section .note.GNU-stack,"",@progbits
