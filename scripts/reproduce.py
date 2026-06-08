"""One-click reproduction (judge-facing).

Re-runs steps 02 -> 05 from the cached data (no fresh CMC pulls), with
SEED=42 fixed throughout. The expected outcome is bit-identical
intermediate JSONs and visually identical figures versus the committed
versions; the only thing that may legitimately vary is the LLM-written
text (which is logged for audit).

If any step fails the script exits with a non-zero code and the offending
step name so CI / a human can re-run from there.
"""
from __future__ import annotations

import subprocess
import sys

STEPS = [
    "scripts/02_build_factors.py",
    "scripts/03_run_research.py",
    "scripts/04_backtest.py",
    "scripts/05_generate_spec.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n>>> {step}")
        result = subprocess.run([sys.executable, step])
        if result.returncode != 0:
            print(f"FAILED at {step} (exit {result.returncode})")
            sys.exit(1)
    print(
        "\nreproduction complete. Compare outputs/ to the committed "
        "versions — numerical fields should match exactly (seed=42)."
    )


if __name__ == "__main__":
    main()
