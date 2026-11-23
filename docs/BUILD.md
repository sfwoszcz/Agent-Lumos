# CMake, Make, C/C++, ARM, and Linux development

Agent Lumos v1.2 uses **CMake as the source of truth** for native C11 and C++17 builds; the top-level `Makefile` is only an ergonomic interface. Python is packaged separately using `pyproject.toml` and tested with `pytest`.

## Native Linux prerequisite tools

- Python >=3.11 and `pip`, GCC and G++, `make`, CMake >=3.23, Ninja, and `objdump`
- For Debian/Ubuntu: `sudo apt install build-essential cmake ninja-build binutils python3-venv`

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,stm32,ml]'
make native
make test
make demo
make ml-demo
make ml-frames
```

Equivalent CMake commands:

```bash
cmake --preset native
cmake --build --preset native --parallel
ctest --preset native --output-on-failure
```

The native build produces a simulator, portable protocol library, health-policy library, and tests. `test_x86_64_asm` is included on x86-64 Linux; other architectures skip this specific ABI test.

## Sanitizers and analysis

```bash
make sanitize         # Linux: ASan/UBSan host test build
make disassemble      # x86-64 Linux only: inspect a learning function
```

Sanitizers are **host-side development checks**, not a substitute for code review, fuzzing, or target hardware testing. `make disassemble` requires `objdump` and an x86-64 Linux host. Source examples for AArch64 and ARM Thumb are included, but not all are assembled in native CI.

## STM32 Cortex-M4 cross compilation

Install a compatible `arm-none-eabi-gcc` toolchain, then:

```bash
make firmware
```

This compiles **object files only** (`lumos_protocol.c` and Cortex-M4 assembly). It does **not** produce a flashable ELF or BIN. A real NUCLEO-F446RE project requires device-specific HAL/CMSIS startup code, a linker script, a board clock/interrupt configuration, serial initialization, an image entry point, physical wiring, and testing on the board. Follow [STM32 firmware integration](../firmware/stm32/README.md).

## Build contracts

| Target | Output | Confirmed |
| --- | --- | --- |
| `make native` | C/C++ Linux simulator | Yes, on x86-64 Linux |
| `make test` | 3 native CTest suites + Python tests | Yes, on x86-64 Linux |
| `make ml-demo` | ML evaluation of synthetic data | Yes, on Linux |
| `make ml-frames` | Python ML scores simulator frames | Yes, on Linux |
| `make firmware` | STM32 Cortex-M4 *objects* | Toolchain-dependent; not a physical device build |
| AArch64 assembly source | ABI study exercise | Not integrated into x86-64 CI |
