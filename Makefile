.PHONY: help native test demo ml-demo ml-frames firmware sanitize disassemble clean
PYTHON ?= python3

help:
	@printf '%s\n' 'Agent Lumos targets:' '  make native       configure/build host C/C++ simulator' '  make test         CTest + pytest' '  make demo         run host simulator through Python parser' '  make ml-demo      synthetic, labeled ML evaluation (requires .[ml])' '  make ml-frames    score C/C++ simulator frames with host ML' '  make firmware     Cortex-M4 objects, not flashable ELF (requires ARM toolchain)' '  make sanitize     host build under ASan/UBSan' '  make disassemble  inspect x86-64 learning binary (read-only)' '  make clean        delete build directory'

native:
	cmake --preset native
	cmake --build --preset native --parallel

test: native
	ctest --preset native
	$(PYTHON) -m pytest -q

demo: native
	./build/native/stm32-sim | PYTHONPATH=src $(PYTHON) -m agent_lumos stm32-read --stdin --max-frames 4

ml-demo:
	PYTHONPATH=src $(PYTHON) -m agent_lumos ml-demo

ml-frames: native
	./build/native/stm32-sim | PYTHONPATH=src $(PYTHON) -m agent_lumos ml-demo --stdin-frames

firmware:
	cmake --preset stm32-objects
	cmake --build --preset stm32-objects --parallel

sanitize:
	cmake --preset native-sanitized
	cmake --build --preset native-sanitized --parallel
	ctest --preset native-sanitized

disassemble: native
	objdump -d ./build/native/test_x86_64_asm | grep -A 14 -E '<lumos_ge_u32_x86_64>:'

clean:
	rm -rf build
