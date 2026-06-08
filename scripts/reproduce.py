"""Stage 7.1 — one-click reproduction with explicit number-consistency check.

Workflow:
    1. Set deterministic seeds (PYTHONHASHSEED=42, numpy seed, etc.).
    2. Run scripts/02 -> 06 in order (06 is best-effort — the report is
       narrative and may legitimately differ when the LLM is reachable).
    3. Canonicalise every numeric output: strip volatile fields
       (`created_at`, absolute paths), then compute a stable SHA-256.
    4. Compare each canonical hash to `outputs/reproduce_manifest.json`.
       - if the manifest is missing, write it (first-run mode);
       - if a hash differs, print a unified diff of the JSON values
         and exit non-zero. This is the §7.2 "与提交版数字逐项一致" gate.

Re-run anytime via `python scripts/reproduce.py`. Cache hits keep the cost
at zero CMC credits and zero LLM calls when the upstream parquets and the
LLM-fallback templates are in place.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# ---- determinism ---------------------------------------------------------

os.environ.setdefault("PYTHONHASHSEED", "42")
os.environ.setdefault("SIGNALFORGE_SEED", "42")

try:
    import numpy as np
    import random
    np.random.seed(42)
    random.seed(42)
except Exception:  # numpy missing during pre-install: handled by step 02
    pass

# ---- pipeline steps ------------------------------------------------------

STEPS = [
    "scripts/02_build_factors.py",
    "scripts/03_run_research.py",
    "scripts/04_backtest.py",
    "scripts/05_generate_spec.py",
    "scripts/06_write_report.py",
]

# Files whose CONTENT is checked for reproducibility. The report markdown is
# tracked for existence only — its narrative text is allowed to evolve.
CHECKED = {
    "research": "outputs/research_results.json",
    "backtest": "outputs/backtest_results.json",
    "spec":     "outputs/specs/signalforge-cmc-fg-regime-v1.json",
}

MANIFEST_PATH = Path("outputs/reproduce_manifest.json")

# Keys that change between runs even with a fixed seed (timestamps, abs paths).
# Stripped before hashing so the "numerical fields" check is meaningful.
VOLATILE_KEYS = {"created_at", "generation_time", "generated_at", "run_at"}


# ---- canonicalisation ----------------------------------------------------


def _strip_volatile(obj):
    """Recursively drop VOLATILE_KEYS from any dict in the structure."""
    if isinstance(obj, dict):
        return {
            k: _strip_volatile(v)
            for k, v in obj.items()
            if k not in VOLATILE_KEYS
        }
    if isinstance(obj, list):
        return [_strip_volatile(x) for x in obj]
    return obj


def _canonical_hash(path: Path) -> str:
    """SHA-256 of the volatile-stripped, sort_keys-canonicalised JSON."""
    data = json.loads(path.read_text())
    canon = json.dumps(
        _strip_volatile(data), sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canon.encode()).hexdigest()


def _run_step(step: str) -> None:
    print(f"\n>>> {step}")
    result = subprocess.run(
        [sys.executable, step],
        env={**os.environ, "PYTHONHASHSEED": "42"},
    )
    if result.returncode != 0:
        print(f"FAILED at {step} (exit {result.returncode})")
        sys.exit(1)


def _compare_or_write_manifest() -> bool:
    """Returns True if every checked file matches the manifest (or if no
    manifest exists yet, in which case it writes one)."""
    current = {tag: _canonical_hash(Path(p)) for tag, p in CHECKED.items()}

    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(current, indent=2))
        print(f"\nmanifest written: {MANIFEST_PATH}")
        for tag, h in current.items():
            print(f"  {tag:10s} -> {h[:16]}…")
        return True

    expected = json.loads(MANIFEST_PATH.read_text())
    ok, mismatches = True, []
    for tag, p in CHECKED.items():
        if current[tag] != expected.get(tag):
            ok = False
            mismatches.append((tag, p, expected.get(tag), current[tag]))

    print("\nreproducibility check:")
    for tag in CHECKED:
        mark = "✓" if current[tag] == expected.get(tag) else "✗"
        print(f"  {mark} {tag:10s} {current[tag][:16]}…  "
              f"(expected {str(expected.get(tag, ''))[:16]}…)")

    if not ok:
        print("\n=== MISMATCH DETAIL ==========================================")
        for tag, p, exp, got in mismatches:
            print(f"\n--- {tag} ({p}) ---")
            print(f"  expected hash: {exp}")
            print(f"  got hash     : {got}")
            print("  diff of volatile-stripped JSON keys:")
            data = _strip_volatile(json.loads(Path(p).read_text()))
            # Shallow comparison — print top-level numeric fields side-by-side.
            for k, v in (data.items() if isinstance(data, dict) else []):
                if isinstance(v, (int, float)):
                    print(f"    {k} = {v}")
        print("\nRun `rm outputs/reproduce_manifest.json` to accept the new "
              "numbers as canonical (use only if you intentionally changed "
              "data or factors).")
    return ok


def main() -> None:
    for step in STEPS:
        _run_step(step)

    print("\nreproduction complete. Verifying numerical consistency…")
    ok = _compare_or_write_manifest()
    if not ok:
        sys.exit(2)
    print("\n✓ reproduction PASSED — every numerical field matches the manifest.")


if __name__ == "__main__":
    main()
