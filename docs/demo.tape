# Record from the Agent Lumos repository root, with dependencies already installed.
# The commands are real make targets; all STM32 observations are SIMULATED.
# Generate with: vhs docs/demo.tape

Output docs/assets/agent-lumos-demo.gif
Require make
Require python3
Set Shell "bash"
Set Theme "Dracula"
Set FontSize 18
Set Width 1200
Set Height 700
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35 ms

Type "make demo"
Enter
Wait+Screen /"sequence": 4/
Sleep 2 s

Type "make ml-demo"
Enter
Wait+Screen /Anomaly != attack/
Sleep 2 s

Type "make ml-frames"
Enter
Wait+Screen /"ml_anomaly": true/
Sleep 3 s
