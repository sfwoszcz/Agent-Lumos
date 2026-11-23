# Agent Lumos v1.2.0 — Embedded Security & ML Portfolio Release

Agent Lumos is an educational, security-conscious system-monitoring project that brings together **Python OOP, C11, C++17, assembly, Linux, CMake and machine-learning anomaly detection**.

## Highlights
- **Python agent:** metrics collection, JWT-protected read-only diagnostics, secure configuration, asynchronous encrypted telemetry and rotating logs.
- **Embedded foundations:** bounded, CRC-checked UART telemetry protocol in C11; C++17 health policy and STM32-compatible source examples.
- **Low-level exercises:** x86-64 System V ABI assembly with a native test and ARM/AArch64 learning examples.
- **Reproducible builds:** CMake presets, Makefile shortcuts, CTest, pytest and GitHub Actions.
- **Machine learning:** host-side IsolationForest demo using synthetic voltage/temperature data, a threshold baseline, evaluation metrics and simulator frame scoring.
- **Documentation:** Linux terminal demos, build instructions, architecture notes, ML methodology and security limitations.

## Local validation (2026-11-23)
- Python: **31 passed**
- Native CTest: **3 of 3 passed** (C/C++/x86-64 assembly)
- CMake native build: **passed**

## Quick start on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,stm32,ml]'
make test
make demo
make ml-demo
make ml-frames
```

See the main [README](README.md), [build guide](docs/BUILD.md) and [ML guide](docs/ML.md) for details.

## Scope / warnings
Agent Lumos is **not production-ready** and must only monitor systems you own or are authorized to manage. STM32 code has not been validated on a physical Nucleo board; the current ML results use synthetic data and do not demonstrate real-world cyberattack detection. No arbitrary remote shell endpoint is included.
