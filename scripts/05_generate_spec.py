"""Generate the StrategySpec.json — the machine-readable contract.

For every FDR-significant factor in `research_results.json`:
  1. ask `deepseek-reasoner` for an economic / behavioural rationale,
     grounded ONLY in the supplied stats;
  2. attach that rationale alongside the empirical numbers in a
     `FactorSpec` block.

Plus a short strategy-level description (`deepseek-chat`) for the spec
header. The spec is written to outputs/specs/<spec_id>.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from src.llm.deepseek_client import chat
from src.llm.research_synth import synthesize
from src.spec.builder import build_spec

# Plain-English definitions referenced by both the spec and the LLM prompt.
# Keep this map in sync with the columns produced by src/factors/timeseries.py
# and src/factors/cross_section.py.
DEFINITIONS: dict[str, str] = {
    "fg_level":      "CMC proprietary Fear & Greed raw value (0-100)",
    "fg_zscore_90":  "90-day rolling z-score of CMC F&G",
    "fg_momentum_7": "7-day change of CMC F&G",
    "fg_extreme_rev": (
        "+1 if CMC F&G < 20 (extreme fear), -1 if > 80 (extreme greed), "
        "else 0 — a contrarian flag"
    ),
    "fg_regime_dur": "consecutive days in current F&G classification bucket",
    "fg_cross_dom":  "interaction: (-fg_zscore_90) * dom_trend_30",
    "dom_trend_30":  "30-day BTC dominance slope (per-day)",
    "dom_zscore_90": "90-day z-score of BTC dominance",
    "mktcap_mom_30": "30-day total market-cap momentum",
    "xs_rank_mom_30": "cross-section change in CMC rank vs ~30 days ago",
    "xs_size":        "log market cap (size factor) within day",
    "xs_ret_mom_90":  "cross-section 90-day price return",
    "xs_vol_60":      "cross-section 60-day realised vol of daily returns",
}


def _need(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(
            f"required input missing: {path}\n"
            "Run scripts/03_run_research.py + scripts/04_backtest.py first."
        )
    return json.loads(path.read_text())


def main() -> None:
    out_dir = Path(settings.outputs_dir)
    research = _need(out_dir / "research_results.json")
    backtest = _need(out_dir / "backtest_results.json")

    # Per-factor rationales — only for the ones that survived FDR.
    explanations: dict[str, str] = {}
    for fid, fr in research.get("factors", {}).items():
        if fr.get("fdr_significant"):
            explanations[fid] = synthesize(
                fid, DEFINITIONS.get(fid, ""), fr
            )

    # Top-level strategy description (3 sentences).
    sig_factors = [
        k for k, v in research.get("factors", {}).items()
        if v.get("fdr_significant")
    ]
    oos_sharpe = (
        backtest.get("out_of_sample", {}).get("sharpe")
    )
    strategy_desc = chat(
        system=(
            "You write concise quantitative strategy descriptions. Use only "
            "the provided facts. Do not invent metrics."
        ),
        user=(
            "Describe this regime-aware multi-factor strategy in three "
            "sentences. Core edge: CMC PROPRIETARY Fear & Greed (distinct "
            f"from Alternative.me). FDR-significant factors: {sig_factors}. "
            f"Out-of-sample Sharpe: {oos_sharpe}."
        ),
        tag="strategy_desc",
    )

    descriptions = {**DEFINITIONS, "_strategy": strategy_desc}
    spec = build_spec(research, backtest, explanations, descriptions)

    out = out_dir / "specs" / f"{spec.spec_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(spec.model_dump_json(indent=2))
    print(
        f"spec written: {out} "
        f"({len(spec.factors)} FDR-significant factors)"
    )


if __name__ == "__main__":
    main()
