"""Compose and verify the markdown research report.

Pipeline:
  1. Load research + backtest JSONs and the previously-written StrategySpec.
  2. Extract per-factor rationales from the spec (no new LLM calls needed).
  3. Ask DeepSeek to write the full markdown report.
  4. Run `verify_numbers` over the draft: every decimal not traceable to
     the source JSONs is flagged as a possible hallucination. The report
     is still written either way so the human reviewer can decide.
"""
from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from src.llm.report_writer import verify_numbers, write_report


def _need(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(
            f"required input missing: {path}\n"
            "Run the upstream scripts in order: 03 -> 04 -> 05."
        )
    return json.loads(path.read_text())


def main() -> None:
    out_dir = Path(settings.outputs_dir)
    research = _need(out_dir / "research_results.json")
    backtest = _need(out_dir / "backtest_results.json")

    spec_dir = out_dir / "specs"
    spec_files = sorted(spec_dir.glob("*.json"))
    if not spec_files:
        raise SystemExit(
            f"no spec found in {spec_dir}. Run scripts/05_generate_spec.py first."
        )
    spec = json.loads(spec_files[0].read_text())
    explanations = {
        f["id"]: f.get("rationale", "") for f in spec.get("factors", [])
    }

    md = write_report(research, backtest, explanations)
    warnings = verify_numbers(md, research, backtest)

    rpt = out_dir / "reports" / "research_report.md"
    rpt.parent.mkdir(parents=True, exist_ok=True)
    rpt.write_text(md)

    if warnings:
        print("number-verification warnings (manual review required):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("number-verification: clean")
    print(f"report: {rpt}")


if __name__ == "__main__":
    main()
