cmake_minimum_required(VERSION 3.23)
project(AgentLumosNative VERSION 1.2.0 LANGUAGES C CXX ASM)

option(LUMOS_STM32_OBJECTS "Compile STM32 Cortex-M4 protocol/assembly objects (not a firmware image)" OFF)
option(LUMOS_SANITIZERS "Enable AddressSanitizer and UBSan for native tests" OFF)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(lumos_warnings target)
  if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
endfunction()

if(LUMOS_STM32_OBJECTS)
  # Not a flashable image. CubeMX HAL, startup, linker script, clocks and MCU
  # configuration must be provided by a board-specific application.
  if(NOT CMAKE_CROSSCOMPILING)
    message(FATAL_ERROR "Use cmake/toolchains/arm-none-eabi.cmake for STM32 objects")
  endif()
  add_library(lumos_stm32_objects OBJECT
    firmware/stm32/src/lumos_protocol.c
    firmware/stm32/asm/threshold_armv7m.S)
  target_include_directories(lumos_stm32_objects PUBLIC firmware/stm32/include)
  target_compile_options(lumos_stm32_objects PRIVATE -mcpu=cortex-m4 -mthumb
    -ffunction-sections -fdata-sections)
  lumos_warnings(lumos_stm32_objects)
  return()
endif()

if(LUMOS_SANITIZERS)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang" AND UNIX)
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
  else()
    message(FATAL_ERROR "Sanitizer preset requires GCC/Clang on a supported UNIX host")
  endif()
endif()

add_library(lumos_protocol STATIC firmware/stm32/src/lumos_protocol.c)
target_include_directories(lumos_protocol PUBLIC firmware/stm32/include)
lumos_warnings(lumos_protocol)

add_library(lumos_health STATIC firmware/stm32/native/health_policy.cpp)
target_include_directories(lumos_health PUBLIC firmware/stm32/native)
lumos_warnings(lumos_health)

add_executable(stm32-sim firmware/stm32/native/simulator.cpp)
target_link_libraries(stm32-sim PRIVATE lumos_protocol lumos_health)
lumos_warnings(stm32-sim)

enable_testing()
add_executable(test_protocol_native tests/native/test_protocol.c)
target_link_libraries(test_protocol_native PRIVATE lumos_protocol)
lumos_warnings(test_protocol_native)
add_test(NAME protocol_crc_bounds COMMAND test_protocol_native)

add_executable(test_health_native tests/native/test_health.cpp)
target_link_libraries(test_health_native PRIVATE lumos_health)
lumos_warnings(test_health_native)
add_test(NAME health_thresholds COMMAND test_health_native)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$" AND UNIX)
  add_executable(test_x86_64_asm tests/native/test_x86_64_asm.c
    firmware/native/asm/x86_64/unsigned_ge.S)
  lumos_warnings(test_x86_64_asm)
  add_test(NAME asm_x86_64_abi COMMAND test_x86_64_asm)
endif()
