"""Run the project's core verification tests."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for test in ("test_resolver.py", "test_phase_f.py", "test_query_engine.py"):
    subprocess.run([sys.executable, test], cwd=ROOT, check=True)
print("All B→G verification tests passed.")
