#!/usr/bin/env bash
# Native end-to-end demo: compile original C/C++ sources and parse with Python.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
printf '%s\n' '=== Agent Lumos STM32 host simulation ==='
printf '%s\n' '[1/3] Compile portable C protocol (GCC)'
gcc -std=c11 -Wall -Wextra -Werror -pedantic -I"$ROOT/firmware/stm32/include" \
  -c "$ROOT/firmware/stm32/src/lumos_protocol.c" -o "$BUILD/lumos_protocol.o"
printf '%s\n' '[2/3] Compile C++17 device simulator (G++)'
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -I"$ROOT/firmware/stm32/include" \
  "$ROOT/firmware/stm32/native/health_policy.cpp" \
  "$ROOT/firmware/stm32/native/simulator.cpp" \
  "$BUILD/lumos_protocol.o" -o "$BUILD/stm32-sim"
printf '%s\n' '[3/3] MCU-like frames => Python bridge => validated JSON'
"$BUILD/stm32-sim" | python -m agent_lumos stm32-read --stdin --max-frames 4
