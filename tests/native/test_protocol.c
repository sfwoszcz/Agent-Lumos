#include "lumos_protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char buf[LUMOS_FRAME_CAPACITY];
    static const unsigned char reference[] = "123456789";
    assert(lumos_crc16_ccitt(reference, 9u) == 0x29B1u);
    int n = lumos_encode("board_1", 7u, 1000u, 3300, 2400, "ok", buf, sizeof(buf));
    assert(n > 0 && (size_t)n == strlen(buf));
    assert(strncmp(buf, "LUMOS1,board_1,7,1000,3300,2400,ok,", 34u) == 0);
    assert(lumos_encode("../oops", 1u, 1000u, 3300, 2400, "ok", buf, sizeof(buf)) == -1);
    assert(lumos_encode("board", 1u, 1000u, 3300, 2400, "ok", buf, 12u) == -1);
    assert(lumos_encode("board", 1u, 1000u, 3300, 2400, "bad", buf, sizeof(buf)) == -1);
    puts("protocol CRC and bounds: OK");
    return 0;
}
