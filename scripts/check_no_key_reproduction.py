"""Stage 7.3 — verify a judge with NO API keys can reproduce core numbers.

Spec: a reviewer clones the repo, has neither CMC nor DeepSeek credentials,
and only relies on the committed `data/processed/` parquet cache plus the
sample dumps in `data/raw/_samples/`. They run `scripts/reproduce.py` and
expect every numerical field in the canonical JSONs to match the manifest.

This script enforces that:
  1. Snapshots current `outputs/` to a temp dir.
  2. Wipes the volatile outputs.
  3. Runs `scripts/reproduce.py` inside a subprocess whose environment has
     CMC_API_KEY="" and DEEPSEEK_API_KEY="" so any accidental network call
     fails loudly.
  4. Confirms the manifest comparison passes (reproduce.py exits 0).
  5. Restores the snapshot if anything went wrong.

Run: `python scripts/check_no_key_reproduction.py`
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VOLATILE_OUTPUTS = [
    "outputs/research_results.json",
    "outputs/backtest_results.json",
    "outputs/specs",
    "outputs/reports",
]


def _snapshot(dst: Path) -> None:
    for rel in VOLATILE_OUTPUTS:
        src = Path(rel)
        if not src.exists():
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, target, dirs_exist_ok=True)
        else:
            shutil.copy2(src, target)


def _restore(src: Path) -> None:
    for rel in VOLATILE_OUTPUTS:
        snap = src / rel
        if not snap.exists():
            continue
        live = Path(rel)
        if live.exists():
            if live.is_dir():
                shutil.rmtree(live)
            else:
                live.unlink()
        if snap.is_dir():
            shutil.copytree(snap, live)
        else:
            live.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snap, live)


def _wipe() -> None:
    for rel in VOLATILE_OUTPUTS:
        p = Path(rel)
        if not p.exists():
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


def main() -> None:
    required = ["data/processed/fear_greed.parquet",
                "data/processed/ohlcv.parquet",
                "outputs/reproduce_manifest.json"]
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        print(f"FAIL — required cached files missing: {missing}")
        sys.exit(2)

    snap_dir = Path(tempfile.mkdtemp(prefix="signalforge_snap_"))
    print(f"snapshotting current outputs/ -> {snap_dir}")
    _snapshot(snap_dir)

    try:
        _wipe()
        print("wiped volatile outputs; invoking reproduce.py with cleared "
              "CMC_API_KEY / DEEPSEEK_API_KEY (no-network mode)…\n")
        env = {
            **os.environ,
            "CMC_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "PYTHONHASHSEED": "42",
        }
        r = subprocess.run(
            [sys.executable, "scripts/reproduce.py"], env=env,
        )
        if r.returncode != 0:
            print(f"\nFAIL — reproduce.py exited {r.returncode} in no-key mode.")
            sys.exit(3)
    finally:
        # Restore snapshot ONLY if the run failed; on success, leave the
        # freshly reproduced outputs in place (they're proven identical).
        if not Path("outputs/specs").exists():
            print("restoring snapshot (run failed)…")
            _restore(snap_dir)
        shutil.rmtree(snap_dir, ignore_errors=True)

    print("\n✓ NO-KEY REPRODUCTION PASSED — judges can rerun without "
          "any API credentials.")


if __name__ == "__main__":
    main()
