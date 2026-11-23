# Architecture

```text
                             localhost / trusted TLS
  Administrator ── POST /v1/login ──────┐
         │                              │ JWTAuthenticator + LoginLimiter
         │ Bearer JWT                   ▼
         ├── GET  /v1/metrics ────> AgentAPI ──> SystemMonitor ──> psutil
         └── POST /v1/diagnostics ───────┘           │
               (fixed read-only action IDs)         │ periodic snapshot
                                                   ▼
                                        TelemetryReporter (async)
                                            │ HTTPS + bearer auth
                                            │ optional Fernet
                                            ▼
                                        Collector you control
                                (DemoReceiver on localhost for testing)
```

The server and sender share `SystemMonitor`. The sender runs in the same event loop as the API; `aiohttp` manages asynchronous outbound HTTP. The agent is not a command-and-control server: it does not run user-supplied code. Configuration is isolated in `AgentConfig`, and the demo receiver lives in a separate module.

For production-grade remote management, add explicit approval, least-privilege policy, audit trails, device enrollment and cryptographically authenticated task definitions before any privileged operations.


## STM32 extension (v1.1)

```text
NUCLEO-F446RE (STM32 HAL C: real millisecond uptime, sensors unknown)
       |  UART2 -> ST-LINK VCP -> USB serial (untrusted local input)
       v
collect_serial() -> STM32Registry -> GET /v1/stm32/devices
                     ^                  (scoped JWT required)
                     |
 C11 protocol encoder + C++17 native simulator -> Python stdin demo

[optional] ARM Thumb Cortex-M4 assembly learning snippet, not linked
```

The serial transport uses CRC-16 for accidental error detection; no device identity or encryption claims. The real-board firmware integration is a CubeIDE HAL snippet, not a pre-generated board binary. See [STM32 demo](STM32.md) and [board instructions](../firmware/stm32/README.md).


## Build system and host ML (v1.2)

```text
CMake native preset -> C11 protocol + C++17 policy + Linux simulator
                  -> CTest: protocol / policy / x86-64 assembly ABI
                              | simulator UART-style frames
                              v
              Python STM32 parser (CRC + size/range checks)
                              |
                   Python host-side ML score
                      (synthetic baseline)
                              |
                 Rules / anomaly indicator
                 NOT a verified security alert
```

The Makefile wraps CMake + pytest tasks. The ARM toolchain preset compiles objects only, not a flashable firmware image. AArch64 and Thumb assembly examples are educational and platform-specific. See [BUILD.md](BUILD.md) and [ML.md](ML.md).
