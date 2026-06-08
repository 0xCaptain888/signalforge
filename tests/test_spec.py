"""Unit tests for src/spec/{schema,builder}.py and the hallucination detector.

These verify the deterministic parts of the LLM + spec pipeline — no
network calls are required:
  - `build_spec` only includes FDR-significant factors and copies their
    numbers verbatim.
  - `StrategySpec.model_dump_json` round-trips through pydantic without
    losing fields.
  - `verify_numbers` flags decimals that don't appear in the source JSON
    and ignores ones that do (and is tolerant of sign flips and tiny
    universal constants).
"""
from __future__ import annotations

import json

from src.llm.report_writer import verify_numbers
from src.spec.builder import build_spec
from src.spec.schema import StrategySpec


def _research_fixture() -> dict:
    return {
        "factors": {
            "fg_extreme_rev": {
                "ic_overall": 0.082,
                "ir": 0.41,
                "t_stat": 3.12,
                "fdr_significant": True,
                "regime_ic": [
                    {"regime": "BEAR_FEAR", "ic": 0.14, "t_stat": 2.7,
                     "p": 0.01, "n": 120},
                ],
            },
            "fg_momentum_7": {
                "ic_overall": 0.012,
                "ir": 0.05,
                "t_stat": 0.4,
                "fdr_significant": False,
                "regime_ic": [],
            },
        },
        "n_trials": 18,
    }


def _backtest_fixture() -> dict:
    return {
        "in_sample": {"sharpe": 1.4, "ann_return": 0.32, "max_drawdown": -0.18},
        "out_of_sample": {"sharpe": 1.1, "ann_return": 0.21, "max_drawdown": -0.22},
        "deflated_sharpe": {"deflated_sharpe_prob": 0.82, "sharpe_daily": 0.07},
        "monte_carlo": {"random_sharpe_95pct": 0.6},
        "regime_weights_used": {"BEAR_FEAR": {"fg_extreme_rev": 0.14}},
        "is_oos_cut": "2024-06-01",
    }


def test_build_spec_only_significant_factors() -> None:
    spec = build_spec(
        _research_fixture(),
        _backtest_fixture(),
        explanations={"fg_extreme_rev": "Contrarian rebound at capitulation."},
        descriptions={
            "fg_extreme_rev": "+1 if F&G<20, -1 if >80",
            "_strategy": "Test strategy description.",
        },
    )
    ids = [f.id for f in spec.factors]
    assert ids == ["fg_extreme_rev"]
    f = spec.factors[0]
    assert f.rank_ic == 0.082
    assert f.t_stat == 3.12
    assert f.fdr_significant is True
    assert f.rationale.startswith("Contrarian")
    assert spec.regime["factor_weights_by_regime"] == {
        "BEAR_FEAR": {"fg_extreme_rev": 0.14}
    }


def test_strategy_spec_roundtrips_through_json() -> None:
    spec = build_spec(
        _research_fixture(),
        _backtest_fixture(),
        explanations={"fg_extreme_rev": "x"},
        descriptions={"fg_extreme_rev": "y", "_strategy": "z"},
    )
    blob = spec.model_dump_json()
    reloaded = StrategySpec.model_validate(json.loads(blob))
    assert reloaded.spec_id == spec.spec_id
    assert len(reloaded.factors) == 1
    assert reloaded.execution_assumptions["signal_to_trade_lag_days"] == 1


def test_verify_numbers_clean_when_all_present() -> None:
    research = {"ic": 0.08, "ir": 0.41}
    backtest = {"sharpe": 1.4, "drawdown": -0.18}
    md = (
        "The strategy posted a Sharpe of 1.4 with a drawdown of -0.18. "
        "The headline factor had an IC of 0.08 and IR of 0.41."
    )
    # 0.08, 0.41, 0.18 all <= 1.5 -> auto-skipped; 1.4 IS in source -> OK.
    warns = verify_numbers(md, research, backtest)
    assert warns == []


def test_verify_numbers_flags_invented() -> None:
    research = {"sharpe": 1.4}
    backtest = {"return": 0.32}
    md = "Our strategy achieved a Sharpe of 9.99 (clearly fabricated)."
    warns = verify_numbers(md, research, backtest)
    assert any("9.99" in w for w in warns)


def test_verify_numbers_accepts_sign_flip() -> None:
    research = {}
    backtest = {"max_drawdown": -22.5}
    md = "Worst drawdown was 22.5%."
    warns = verify_numbers(md, research, backtest)
    assert warns == []
