## Agent Lumos in Action

<p align="center">
  <img src="docs/assets/agent-lumos-demo.gif" alt="Animated Linux terminal showing the native STM32 simulator and host-side ML anomaly detection" width="1000">
</p>

*Animated terminal visualization of verified **host-simulator** output. Data is synthetic; the STM32 firmware has not yet been demonstrated on physical hardware. An ML anomaly is not proof of a cyberattack.*

### Reproduce the terminal demo

From the repository root, on Linux with CMake, Ninja, GCC/G++, Python 3.11+ and the ML dependencies installed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,stm32,ml]'
./scripts/portfolio_demo.sh
```

Optionally, regenerate a **real terminal recording** using [VHS](https://github.com/charmbracelet/vhs) and its prerequisites:

```bash
vhs docs/demo.tape
```

### Architecture overview

```mermaid
flowchart TD
    subgraph Simulator["Embedded protocol / native Linux simulator"]
        C["C11 telemetry encoder"]
        P["C++17 simulator health policy"]
        P --> C
    end
    C -->|"UART-style frames + CRC-16 error check"| V["Python bounded frame parser"]
    V --> R["STM32 device registry"]
    R --> A["Authenticated read-only API"]
    V --> M["Host-side ML demo: IsolationForest"]
    M --> S["Anomaly scoring and threshold comparison"]
    T["CMake / CTest / pytest / GitHub Actions"] -.-> Simulator
    T -.-> V
```

> **Security boundary:** CRC-16 detects accidental corruption; it does not authenticate the device. The STM32 HAL example and optional ARM/AArch64 assembly samples are not represented here as verified physical-device functionality.
