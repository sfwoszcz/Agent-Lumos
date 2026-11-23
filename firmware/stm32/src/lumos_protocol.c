#include "lumos_protocol.h"

#include <stdio.h>
#include <string.h>

uint16_t lumos_crc16_ccitt(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xFFFFu;
    size_t i;
    if (data == NULL && length != 0u) return 0u;
    for (i = 0; i < length; i++) {
        unsigned int bit;
        crc ^= (uint16_t)((uint16_t)data[i] << 8);
        for (bit = 0; bit < 8u; bit++) {
            if ((crc & 0x8000u) != 0u) {
                crc = (uint16_t)(((unsigned int)crc << 1u) ^ 0x1021u);
            } else {
                crc = (uint16_t)((unsigned int)crc << 1u);
            }
        }
    }
    return crc;
}

static int valid_id(const char *id)
{
    size_t i;
    if (!id) return 0;
    for (i = 0; i < 25u && id[i] != '\0'; i++) {
        const char c = id[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '_' || c == '-')) return 0;
    }
    return i > 0u && i <= 24u && id[i] == '\0';
}

int lumos_encode(const char *device_id, uint32_t seq, uint32_t uptime_ms,
                 int32_t vdd_mv, int32_t temp_centi,
                 const char *state, char *out, size_t capacity)
{
    char vdd_str[12];
    char temp_str[16];
    int written;
    uint16_t crc;
    if (!out || capacity == 0 || capacity > LUMOS_FRAME_CAPACITY || !valid_id(device_id)) return -1;
    if (!state || (strcmp(state, "ok") && strcmp(state, "warn") && strcmp(state, "unknown"))) return -1;
    if (vdd_mv != LUMOS_MISSING_VDD && (vdd_mv < 1800 || vdd_mv > 5500)) return -1;
    if (temp_centi != LUMOS_MISSING_TEMPERATURE && (temp_centi < -4000 || temp_centi > 12500)) return -1;
    if (vdd_mv == LUMOS_MISSING_VDD) {
        (void)snprintf(vdd_str, sizeof(vdd_str), "NA");
    } else {
        (void)snprintf(vdd_str, sizeof(vdd_str), "%ld", (long)vdd_mv);
    }
    if (temp_centi == LUMOS_MISSING_TEMPERATURE) {
        (void)snprintf(temp_str, sizeof(temp_str), "NA");
    } else {
        (void)snprintf(temp_str, sizeof(temp_str), "%ld", (long)temp_centi);
    }
    written = snprintf(out, capacity, "LUMOS1,%s,%lu,%lu,%s,%s,%s",
                       device_id, (unsigned long)seq, (unsigned long)uptime_ms,
                       vdd_str, temp_str, state);
    if (written < 0 || (size_t)written + 7u > capacity) return -1;
    crc = lumos_crc16_ccitt((const uint8_t *)out, (size_t)written);
    {
        int tail = snprintf(out + written, capacity - (size_t)written, ",%04X\n", (unsigned int)crc);
        if (tail != 6) return -1;
        return written + tail;
    }
}
