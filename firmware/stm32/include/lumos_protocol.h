#ifndef AGENT_LUMOS_PROTOCOL_H
#define AGENT_LUMOS_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

/* Maximum total line length including LF and terminating NUL (C buffer). */
#define LUMOS_FRAME_CAPACITY 160u
#define LUMOS_MISSING_TEMPERATURE INT32_MIN
#define LUMOS_MISSING_VDD (-1)

#ifdef __cplusplus
extern "C" {
#endif

/* CRC-16/CCITT-FALSE over the ASCII prefix through the last state character. */
uint16_t lumos_crc16_ccitt(const uint8_t *data, size_t length);

/*
 * Emit: LUMOS1,<id>,<seq>,<uptime_ms>,<vdd_mv|NA>,<temp_centi|NA>,<state>,<CRC4>\n
 * States: ok, warn, unknown. Missing values should be NA, never fabricated.
 * Returns bytes to transmit (without NUL), or -1 on invalid input/truncation.
 * Does no allocation and no I/O; appropriate for a cooperative main loop.
 */
int lumos_encode(const char *device_id, uint32_t seq, uint32_t uptime_ms,
                 int32_t vdd_mv, int32_t temp_centi,
                 const char *state, char *out, size_t out_capacity);

#ifdef __cplusplus
}
#endif
#endif
