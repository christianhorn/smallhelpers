#!/usr/bin/env pmpython

import subprocess

result = subprocess.run(['ls', '-la'], capture_output=True, text=True)

print("Return code:", result.returncode)
print("Errors:", result.stderr)

for line in result.stdout.splitlines():
	print(line)

