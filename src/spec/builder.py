"""Assemble a `StrategySpec` from the research + backtest + LLM outputs.

Only factors that pass the FDR filter in the research pass end up in the
final spec. Their per-factor numbers are copied verbatim from the research
JSON, and the LLM-authored rationale is attached as `rationale`.

The data sources, universe, regime definition, execution assumptions, and
reproducibility fields are filled in from `config/constants.py` and the
backtest summary, so the spec is a single self-contained artifact.
"""
from __future__ import annotations

from datetime import datetime, timezone

from config import constants as C
from src.spec.schema import DataSource, FactorSpec, StrategySpec


def _classify(fid: str) -> str:
    """Heuristic: ids starting with fg_/dom_/mkt_ are time-series; xs_ is
    cross-section. New factor families should be added here if introduced."""
    if fid.startswith(("fg_", "dom_", "mkt")):
        return "timeseries"
    if fid.startswith("xs_"):
        return "cross_section"
    return "timeseries"


def build_spec(
    research: dict,
    backtest: dict,
    explanations: dict[str, str],
    descriptions: dict[str, str],
) -> StrategySpec:
    """Build the spec from already-validated component outputs.

    Parameters
    ----------
    research : dict
        Parsed `outputs/research_results.json`.
    backtest : dict
        Parsed `outputs/backtest_results.json`.
    explanations : dict[str, str]
        Factor id -> LLM-authored rationale string.
    descriptions : dict[str, str]
        Factor id -> short human-readable definition. May also contain a
        special "_strategy" key for the top-level strategy description.
    """
    factors: list[FactorSpec] = []
    for fid, fr in research.get("factors", {}).items():
        if not fr.get("fdr_significant"):
            continue
        factors.append(
            FactorSpec(
                id=fid,
                definition=descriptions.get(fid, ""),
                type=_classify(fid),
                rank_ic=fr.get("ic_overall"),
                ir=fr.get("ir"),
                t_stat=fr.get("t_stat"),
                fdr_significant=True,
                rationale=explanations.get(fid, ""),
            )
        )

    return StrategySpec(
        spec_id="signalforge-cmc-fg-regime-v1",
        name="CMC Proprietary F&G Regime-Aware Multi-Factor Strategy",
        created_at=datetime.now(timezone.utc).isoformat(),
        description=descriptions.get("_strategy", ""),
        data_sources=[
            DataSource(
                provider="CoinMarketCap",
                endpoint="/v3/fear-and-greed/historical",
                field="value",
                is_proprietary=True,
                note=(
                    "CMC proprietary Fear & Greed — distinct algorithm from "
                    "Alternative.me; under-researched alpha source."
                ),
            ),
            DataSource(
                provider="CoinMarketCap",
                endpoint="/v1/global-metrics/quotes/historical",
                field="btc_dominance",
            ),
            DataSource(
                provider="CoinMarketCap",
                endpoint="/v1/cryptocurrency/listings/historical",
                note=(
                    "Point-in-time universe; survivorship-bias-free when "
                    "available (Standard+ plan)."
                ),
            ),
            DataSource(
                provider="CoinMarketCap",
                endpoint="/v2/cryptocurrency/ohlcv/historical",
            ),
        ],
        universe={
            "selection": "top_N_by_market_cap",
            "N": C.UNIVERSE_TOP_N,
            "source": "listings/historical (point-in-time)",
            "survivorship_handling": (
                "delisted coins included within their active window via "
                "first/last_historical_data from /cryptocurrency/map"
            ),
        },
        factors=factors,
        regime={
            "definition": {
                "direction": (
                    f"BTC vs MA{C.MA_WINDOW} + dominance 20d slope"
                ),
                "sentiment": (
                    f"CMC F&G with thresholds FEAR<{C.FG_FEAR}, "
                    f"GREED>{C.FG_GREED}"
                ),
            },
            "factor_weights_by_regime": backtest.get(
                "regime_weights_used", {}
            ),
        },
        signal_to_position={
            "method": "IR-weighted, regime-conditional",
            "max_asset_weight": 0.30,
            "max_gross_leverage": 1.0,
            "rebalance_frequency": "daily",
        },
        execution_assumptions={
            "signal_to_trade_lag_days": 1,
            "fee_bps": C.FEE_BPS,
            "slippage_bps_by_size": C.SLIPPAGE_BPS,
        },
        backtest_window={
            "in_sample_to_oos_cut": backtest.get("is_oos_cut"),
        },
        reported_performance={
            "in_sample": backtest.get("in_sample"),
            "out_of_sample": backtest.get("out_of_sample"),
            "deflated_sharpe": backtest.get("deflated_sharpe"),
            "monte_carlo_baseline": backtest.get("monte_carlo"),
        },
        reproducibility={
            "seed": C.SEED,
            "engine_version": "signalforge-0.1.0",
            "reproduce_command": "python scripts/reproduce.py",
        },
    )
