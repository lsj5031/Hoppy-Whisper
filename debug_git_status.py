#!/usr/bin/env python3
import subprocess
import sys

# Debug git status
result = subprocess.run(["git", "status", "--short", "--", "src", "tests"], 
                       capture_output=True, text=True)
print("Git status output:")
print(repr(result.stdout))
print("Lines:")
for i, line in enumerate(result.stdout.splitlines()):
    print(f"  {i}: {line!r}")

# Parse paths
paths = []
for line in result.stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    entry = line[3:]
    if " -> " in entry:
        entry = entry.split(" -> ", 1)[1]
    entry = entry.strip()
    if entry.endswith((".py", ".pyi")):
        paths.append(entry)
        print(f"Added path: {entry!r}")

print(f"Final paths: {paths}")