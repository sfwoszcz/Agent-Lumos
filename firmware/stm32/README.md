# STM32 NUCLEO-F446RE firmware integration (Agent Lumos v1.1)

**Target:** STM32F446RE Nucleo-64; HAL F4 generated with STM32CubeIDE / STM32CubeMX.
**Status:** Portable protocol encoder is host-compiled and tested. The HAL board hook has *not yet been flashed or validated on a physical STM32 board*. This directory deliberately does not pretend to be a complete STM32CubeIDE project: board startup, linker script, CMSIS, HAL drivers and generated `main.c` come from CubeMX.

## How it connects

```text
STM32F446RE (C firmware)
   HAL_GetTick() -> C lumos_encode() -> UART2 / ST-LINK virtual COM port
                                        |
                                    USB serial
                                        |
                            Python Agent Lumos 1.1
                         strict parser + CRC + registry
                                        |
                             JWT-protected local API
                              GET /v1/stm32/devices
```

The NUCLEO-F446RE includes an on-board ST-LINK virtual COM port; the usual USART2 connection maps PA2 (TX) / PA3 (RX). Confirm routing on your exact board revision. Official references: [ST NUCLEO-F446RE board](https://www.st.com/en/evaluation-tools/nucleo-f446re.html), [ST Nucleo-64 manual UM1724](https://www.st.com/resource/en/user_manual/dm00105823-nucleo-f401re-user-manual-stmicroelectronics.pdf), [ST Getting Started with UART](https://wiki.st.com/stm32mcu/wiki/Getting_started_with_UART).

## Quick host-only test (no STM32 board needed)

From repository root on Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,stm32]'
./scripts/stm32_demo.sh
```

Requires `gcc`, `g++`, and a C++17 compiler. The script compiles `src/lumos_protocol.c` using C11, links it to the C++17 simulator/health policy, and passes four real encoded frames to the Python parser. The third simulated frame is an intentionally generated warning.

## Real hardware: setup with STM32CubeIDE

1. Create a **new STM32CubeIDE project** selecting NUCLEO-F446RE. Use the **STM32CubeF4 HAL** drivers, not HAL2 APIs.
2. Enable **USART2** in *Asynchronous* mode. Set **115200 baud, 8 data bits, no parity, 1 stop bit**, no hardware flow control. Verify PA2 (TX) / PA3 (RX) and ST-LINK VCP routing on the board schematic.
3. Generate the project. Copy `include/lumos_protocol.h` to the project include path, and `src/lumos_protocol.c` and `src/lumos_telemetry_hal.c` into the generated project `Core/Src`. Add the include path in project compiler settings.
4. Add this declaration to `main.c` inside a generated `/* USER CODE BEGIN 0 */` region:

   ```c
   void lumos_telemetry_tick(UART_HandleTypeDef *uart);
   ```

5. After generated `MX_USART2_UART_Init()` runs, call the function in the `while (1)` user-code section:

   ```c
   lumos_telemetry_tick(&huart2);
   HAL_Delay(10);
   ```

6. Build and flash using ST-LINK. On Linux, locate the serial port:

   ```bash
   python -m serial.tools.list_ports -v
   # Typical, but not guaranteed: /dev/ttyACM0
   agent-lumos stm32-read --port /dev/ttyACM0 --baud 115200 --max-frames 5
   ```

7. To expose observations inside the existing JWT-protected Agent Lumos API, initialize credentials (`agent-lumos init`, once), then edit your private `.env` and uncomment/add `LUMOS_STM32_PORT=/dev/ttyACM0`. Run `agent-lumos serve`, log in using `./scripts/demo.sh` or your own local JWT client, then `GET /v1/stm32/devices` with an authenticated bearer token. Note: don't run `stm32-read` and `agent-lumos serve` on the **same** serial port at once.

**Linux permissions:** your user may need membership in the device's serial-port group (commonly `dialout`). Log out and in after changing membership. Do not make the device world-writable or run the entire agent as root.

### What the actual firmware measures

The board example transmits **real HAL millisecond uptime only**, plus a sequence number and ID. Both the board's internal temperature and supply voltage are **`NA`** until calibrated ADC sampling is added. The state is **`unknown`** rather than claiming the hardware is healthy. The *native simulator* contains explicitly synthetic voltage/temperature samples to demonstrate our future monitoring pipeline. Never present these as physical measurements.

## Protocol v1

Line-oriented, ASCII-only, maximum **160 bytes** (including newline). Each line is:

```text
LUMOS1,<device_id>,<seq>,<uptime_ms>,<vdd_mv|NA>,<temp_centi|NA>,<state>,<CRC16>\n
```

- `device_id`: 1–24 ASCII letters, digits, hyphen or underscore.
- `seq`, `uptime_ms`: unsigned 32-bit decimal integers.
- `vdd_mv`: 1800–5500, or `NA` if not measured.
- `temp_centi`: -4000 through 12500 (hundredths °C), or `NA` if not measured.
- `state`: `ok`, `warn` or `unknown`.
- `CRC16`: upper-case four hexadecimal digits, CRC-16/CCITT-FALSE over all bytes before the final `,<CRC16>`, polynomial 0x1021, init 0xFFFF, no xor-out; reference vector `123456789 -> 29B1`.
- No user-defined commands and no input parsing on the MCU. The host never writes back to the serial port.

### Crucial security limitation

**CRC is not a cryptographic signature or message authentication code.** A user with access to the USB/serial channel can forge a valid frame with a matching CRC. Device IDs are unverified self-claims. The Python API uses JWT **to protect retrieval**, *not* to authenticate the STM32 device. This is only appropriate for a trusted, isolated learning lab. For untrusted networks, add protected device keys, authenticated channel encryption (such as a gateway using mTLS), provisioning, and an explicit device identity policy before relying on the data for security decisions. The device registry is in memory and will clear on restart; it is not a forensic audit store.

## C++ and assembly exercises

- `native/health_policy.hpp` and `.cpp`: a C++17 class that labels fully synthetic samples `ok`/`warn`/`unknown` according to configurable thresholds; used by `native/simulator.cpp` in host tests. It is **not yet compiled into STM32 firmware**.
- `asm/threshold_armv7m.S`: an optional Thumb-2 / Cortex-M4 assembly function implementing an unsigned comparison using AAPCS registers. It is **not linked or called** by firmware. You can compare its generated instructions to equivalent optimized C during an assembly-learning exercise. It assembles with `clang --target=armv7m-none-eabi -mcpu=cortex-m4 -mthumb -c ...`; using assembly in the production code is unnecessary here.

## Future milestones

Real ADC measurements with calibration and datasheet-conformant conversions; power management; watchdog; UART DMA/RX robustness; low-energy telemetry and BLE/LoRa gateway; signed firmware updates; device authentication and persistent audit logs. Security capabilities and boot support differ among STM32 series, so evaluate the exact MCU family before claiming secure boot, cryptographic acceleration, or hardware isolation.
