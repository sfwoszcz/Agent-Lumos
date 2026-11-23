# Run `vhs docs/demo.tape` from the Agent Lumos repository root.
# The real command builds and executes the native C11/C++17 simulator,
# validates UART frames, and evaluates synthetic data on the Linux host.
# Needs: VHS (ttyd + ffmpeg), CMake/Ninja/GCC/G++ and the .[ml] Python extra.

Output docs/assets/agent-lumos-demo.gif
Require bash
Require cmake
Require python3

Set Shell "bash"
Set Theme "Dracula"
Set Width 1180
Set Height 670
Set FontSize 19
Set Padding 24
Set WindowBar Colorful
Set TypingSpeed 35 ms
Set CursorBlink false

Type "./scripts/portfolio_demo.sh"
Enter
Wait+Screen@120s /Simulation complete/
Sleep 4s
