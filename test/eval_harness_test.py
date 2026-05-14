#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cmd = [
    sys.executable,
    str(root / "src" / "eval_harness.py"),
    "--cases",
    str(root / "examples" / "cases.jsonl"),
    "--outputs",
    str(root / "examples" / "outputs.jsonl"),
    "--json",
]

result = subprocess.run(cmd, check=True, text=True, capture_output=True)
report = json.loads(result.stdout)

assert report["total"] == 3
assert report["failed"] == 0
assert report["score"] == 1
assert report["total_cost_usd"] > 0

print("eval_harness_test.py passed")
