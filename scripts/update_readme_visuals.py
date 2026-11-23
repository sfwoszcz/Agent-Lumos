#!/usr/bin/env python3
"""Insert/replace the README demo section without disturbing other README content.

Runs from the repository root. Creates README.md.bak before editing.
"""
from pathlib import Path
import re
import sys

root = Path.cwd()
readme = root / "README.md"
snippet = root / "docs" / "README_VISUAL_SECTION.md"
if not readme.is_file() or not snippet.is_file():
    sys.exit("Run from project root after copying the visual-refresh kit there.")
original = readme.read_text(encoding="utf-8")
new_section = snippet.read_text(encoding="utf-8").rstrip() + "\n\n"
start, end = "<!-- lumos:visuals:start -->", "<!-- lumos:visuals:end -->"
block = start + "\n" + new_section.rstrip() + "\n" + end + "\n\n"
if start in original and end in original:
    beginning = original.index(start)
    ending = original.index(end, beginning) + len(end)
    result = original[:beginning] + block.rstrip() + original[ending:]
else:
    # Previous user-specific section begins at this exact heading.
    match = re.search(r"(?m)^## Agent Lumos in Action\s*$", original)
    if match:
        next_heading = re.search(r"(?m)^## (?!#)\S", original[match.end():])
        ending = match.end() + next_heading.start() if next_heading else len(original)
        result = original[:match.start()] + block + original[ending:]
    else:
        # Preserve existing CI badge and content by inserting before the intro heading.
        match = re.search(r"(?m)^## What is Agent Lumos\?\s*$", original)
        if match:
            result = original[:match.start()] + block + original[match.start():]
        else:
            result = original.rstrip() + "\n\n" + block
if result == original:
    print("README unchanged; visuals already up to date.")
else:
    (root / "README.md.bak").write_text(original, encoding="utf-8")
    readme.write_text(result, encoding="utf-8")
    print("README updated; original saved as README.md.bak (do not commit backup).")
