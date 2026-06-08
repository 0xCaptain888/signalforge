"""End-to-end backtest: IS/OOS split + cost sensitivity + monte-carlo + DSR.

Inputs:
    data/processed/factors_timeseries.parquet
    data/processed/regime.parquet
    data/processed/ohlcv.parquet            (needs BTC close at id=1)
    outputs/research_results.json           (for regime-weight calibration)

Outputs:
    outputs/backtest_results.json
    outputs/figures/walkforward_oos.png

If `research_results.json` is absent or yields no regime weights above
the IC threshold, the script falls back to `default_regime_weights()` so
the pipeline still produces a backtest a human can sanity-check.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import constants as C  # noqa: E402
from config.settings import settings  # noqa: E402
from src.research.multiple_testing import deflated_sharpe  # noqa: E402
from src.research.robustness import cost_sensitivity, time_split  # noqa: E402
from src.strategy.backtest import (  # noqa: E402
    backtest_single,
    monte_carlo_random,
)
from src.strategy.portfolio import (  # noqa: E402
    default_regime_weights,
    regime_conditional_positions,
)

np.random.seed(C.SEED)

PROC = Path(settings.processed_dir)
OUT = Path(settings.outputs_dir)
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def build_weights_from_research(
    research: dict,
) -> dict[str, dict[str, float]] | None:
    """Convert the research scorecard into regime->factor->weight.

    For every (factor, regime) cell with |IC| > RANK_IC_THRESHOLD and at
    least 30 obs, take sign(IC) * |IC| as the weight. Weights are L1-
    normalised inside `combine_signals` at evaluation time.
    """
    weights: dict[str, dict[str, float]] = {}
    for fname, fr in research.get("factors", {}).items():
        for rec in fr.get("regime_ic", []):
            reg, ic, n = rec.get("regime"), rec.get("ic"), rec.get("n", 0)
            if ic is None or np.isnan(ic) or n < 30:
                continue
            if abs(ic) > C.RANK_IC_THRESHOLD:
                weights.setdefault(reg, {})[fname] = float(
                    np.sign(ic) * abs(ic)
                )
    return weights or None


def _clean(perf: dict) -> dict:
    """Strip the un-JSON-serialisable bits (equity_curve / returns Series)."""
    return {k: v for k, v in perf.items() if k not in ("equity_curve", "returns")}


def _need(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(
            f"required input missing: {path}\n"
            "Run scripts/01_pull_data.py + scripts/02_build_factors.py first."
        )
    return pd.read_parquet(path)


def main() -> None:
    ts = _need(PROC / "factors_timeseries.parquet").set_index("date")
    regime = _need(PROC / "regime.parquet").set_index("date")["regime"]
    ohlcv = _need(PROC / "ohlcv.parquet")
    btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"].sort_index()

    # Calibrated weights if the research pass produced any; else defaults.
    research_path = OUT / "research_results.json"
    research = (
        json.loads(research_path.read_text()) if research_path.exists() else {}
    )
    weights = build_weights_from_research(research) or default_regime_weights()

    # Pull only the factor columns referenced by ANY regime's weight dict.
    factor_cols = sorted(
        {f for w in weights.values() for f in w.keys() if f in ts.columns}
    )
    if not factor_cols:
        raise SystemExit(
            "no overlap between calibrated factors and factors_timeseries; "
            "re-check research_results.json factor names."
        )
    factors = ts[factor_cols].reindex(btc.index)

    # IS / OOS split — 70 / 30 chronological.
    cut, _ = time_split(btc.index, is_frac=0.7)
    pos = regime_conditional_positions(factors, regime, weights, max_pos=1.0)

    perf_is = backtest_single(
        pos[pos.index < cut], btc[btc.index < cut]
    )
    perf_oos = backtest_single(
        pos[pos.index >= cut], btc[btc.index >= cut]
    )

    # DSR uses the OOS leg with the research trial budget.
    n_trials = int(research.get("n_trials", 20))
    dsr = deflated_sharpe(perf_oos["returns"], n_trials=n_trials)

    # Cost grid — re-run backtest at each fee level.
    cost_df = cost_sensitivity(
        lambda fee: _clean(backtest_single(pos, btc, fee_bps=fee)),
        cost_grid_bps=[0, 5, 10, 20, 40],
    )

    mc = monte_carlo_random(btc)

    # ----- OOS equity figure -----
    plt.figure(figsize=(9, 5))
    perf_oos["equity_curve"].plot(label="SignalForge (OOS)")
    btc_oos = btc[btc.index >= cut]
    if len(btc_oos) > 0:
        (btc_oos / btc_oos.iloc[0]).plot(label="BTC HODL", alpha=0.7)
    plt.legend()
    plt.title("Out-of-sample equity curve")
    plt.ylabel("Cumulative growth")
    plt.tight_layout()
    plt.savefig(FIG / "walkforward_oos.png", dpi=130)
    plt.close()

    out = {
        "in_sample": _clean(perf_is),
        "out_of_sample": _clean(perf_oos),
        "deflated_sharpe": dsr,
        "monte_carlo": mc,
        "cost_sensitivity": cost_df.to_dict("records"),
        "regime_weights_used": weights,
        "is_oos_cut": str(cut),
        "factors_used": factor_cols,
    }
    (OUT / "backtest_results.json").write_text(
        json.dumps(out, indent=2, default=float)
    )
    print(
        f"OOS Sharpe: {perf_oos['sharpe']:.2f} | "
        f"DSR p: {dsr.get('deflated_sharpe_prob')} | "
        f"random 95pct Sharpe: {mc['random_sharpe_95pct']:.2f}"
    )


if __name__ == "__main__":
    main()
