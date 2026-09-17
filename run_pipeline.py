"""One-command offline pipeline for the clean B→G rebuild."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(*args: str) -> None:
    print("\n>>>", " ".join(args))
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)

run("data_loader.py")
run("extractor.py")
run("resolver.py", "--as-of", "2026-09-25 17:00")
run("brief_generator.py", "--as-of", "2026-09-25 17:00")
run("test_resolver.py")
run("test_phase_f.py")
run("test_query_engine.py",
        "test_query_precision.py")
print("\nB→G pipeline completed successfully.")
print("Start the UI with: streamlit run app.py")
