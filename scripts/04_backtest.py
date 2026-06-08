"""End-to-end backtest: IS/OOS split + walk-forward + plateau scan + cost
sensitivity + Monte-Carlo + Deflated Sharpe.

Inputs:
    data/processed/factors_timeseries.parquet
    data/processed/regime.parquet
    data/processed/ohlcv.parquet            (needs BTC close at id=1)
    outputs/research_results.json           (used only for n_trials → DSR)

Outputs:
    outputs/backtest_results.json
    outputs/figures/walkforward_oos.png

Rigor notes (per dev-doc §8.5 checklist and §9 trap list):

* **IS-only weight calibration.** `build_weights_is_only` recomputes the
  regime-layered IC using ONLY dates strictly before the IS/OOS cut, so
  the regime_weights that feed the OOS backtest never see OOS data.
  This closes the leak that earlier versions had when reading
  full-sample weights from `research_results.json`.
* **Walk-forward.** `walk_forward_windows(train=365, test=90, step=90)`
  produces non-overlapping evaluation windows. For each window, weights
  are refit on the training slice only and applied to the test slice.
  The per-window Sharpes are persisted so the report can show stability.
* **Parameter plateau.** A simple grid scan over the rolling-IC window
  is run with weights frozen at the primary IS-only fit. A flat plateau
  of OOS Sharpes near-by indicates the strategy is not over-fit to one
  knob value.
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
from src.research.ic import forward_returns  # noqa: E402
from src.research.multiple_testing import deflated_sharpe  # noqa: E402
from src.research.regime_attrib import regime_layered_ic  # noqa: E402
from src.research.robustness import (  # noqa: E402
    cost_sensitivity,
    parameter_plateau,
    time_split,
    walk_forward_windows,
)
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

# Plateau scan grid for the rolling-IC window. Held small on purpose so
# the scan is cheap; widen here if the report ever needs more cells.
PLATEAU_WINDOW_GRID = [30, 45, 60, 90, 120]


# --------------------------------------------------------------------------- #
# Weight calibration helpers
# --------------------------------------------------------------------------- #
def build_weights_is_only(
    ts: pd.DataFrame,
    btc: pd.Series,
    regime: pd.Series,
    is_dates: pd.DatetimeIndex,
    horizon: int = 5,
) -> dict[str, dict[str, float]]:
    """Refit ``regime → factor → weight`` using ONLY ``is_dates``.

    For every (factor, regime) cell with ``|IC| > RANK_IC_THRESHOLD`` and
    at least 30 IS observations, the weight is ``sign(IC) * |IC|``. This
    is the function whose output is actually fed to the OOS backtest —
    no OOS data ever enters the calibration set.
    """
    fwd = forward_returns(btc, horizon)
    is_mask = ts.index.isin(is_dates)
    ts_is = ts.loc[is_mask]
    fwd_is = fwd.reindex(ts_is.index)
    regime_is = regime.reindex(ts_is.index)

    weights: dict[str, dict[str, float]] = {}
    for fname in ts_is.columns:
        if fname == "value_classification":
            continue
        lay = regime_layered_ic(ts_is[fname], fwd_is, regime_is)
        for _, rec in lay.iterrows():
            reg, ic, n = rec["regime"], rec["ic"], rec["n"]
            if pd.isna(ic) or n < 30:
                continue
            if abs(ic) > C.RANK_IC_THRESHOLD:
                weights.setdefault(reg, {})[fname] = float(
                    np.sign(ic) * abs(ic)
                )
    return weights


# --------------------------------------------------------------------------- #
# Walk-forward helper
# --------------------------------------------------------------------------- #
def run_walk_forward(
    ts: pd.DataFrame,
    btc: pd.Series,
    regime: pd.Series,
    fee_bps: int = C.FEE_BPS,
) -> list[dict]:
    """For each window, refit weights on train and backtest on test.

    Returns a list of records: ``{train_start, train_end, test_start,
    test_end, sharpe, ann_return, n_trades}`` per window. An empty list
    is returned if the panel is too short for the default window sizes.
    """
    dates = btc.dropna().index.sort_values()
    windows = walk_forward_windows(dates, train=365, test=90, step=90)
    records: list[dict] = []
    for train_idx, test_idx in windows:
        weights = build_weights_is_only(ts, btc, regime, train_idx)
        if not weights:
            continue
        factor_cols = sorted(
            {f for w in weights.values() for f in w.keys() if f in ts.columns}
        )
        if not factor_cols:
            continue
        factors_test = ts[factor_cols].reindex(test_idx)
        pos_test = regime_conditional_positions(
            factors_test, regime.reindex(test_idx), weights, max_pos=1.0
        )
        perf = backtest_single(pos_test, btc.reindex(test_idx), fee_bps=fee_bps)
        records.append(
            {
                "train_start": str(train_idx[0].date()),
                "train_end": str(train_idx[-1].date()),
                "test_start": str(test_idx[0].date()),
                "test_end": str(test_idx[-1].date()),
                "sharpe": float(perf.get("sharpe", float("nan"))),
                "ann_return": float(perf.get("ann_return", float("nan"))),
                "n_obs": int(len(test_idx)),
            }
        )
    return records


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    ts = _need(PROC / "factors_timeseries.parquet").set_index("date")
    regime = _need(PROC / "regime.parquet").set_index("date")["regime"]
    ohlcv = _need(PROC / "ohlcv.parquet")
    btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"].sort_index()

    # IS / OOS split — 70 / 30 chronological. This cut governs BOTH the
    # primary backtest and the IS-only weight calibration below.
    cut, _ = time_split(btc.index, is_frac=0.7)
    is_dates = btc.index[btc.index < cut]

    # Primary calibration: IS-only. Fallback to hand-set defaults so the
    # pipeline still produces a meaningful number when IS is too thin.
    weights = build_weights_is_only(ts, btc, regime, is_dates)
    used_default = not weights
    if used_default:
        weights = default_regime_weights()

    factor_cols = sorted(
        {f for w in weights.values() for f in w.keys() if f in ts.columns}
    )
    if not factor_cols:
        raise SystemExit(
            "no overlap between calibrated factors and factors_timeseries; "
            "check the IS slice or default_regime_weights()."
        )
    factors = ts[factor_cols].reindex(btc.index)

    pos = regime_conditional_positions(factors, regime, weights, max_pos=1.0)

    perf_is = backtest_single(
        pos[pos.index < cut], btc[btc.index < cut]
    )
    perf_oos = backtest_single(
        pos[pos.index >= cut], btc[btc.index >= cut]
    )

    # DSR uses the OOS leg with the research trial budget when available.
    research_path = OUT / "research_results.json"
    research = (
        json.loads(research_path.read_text()) if research_path.exists() else {}
    )
    n_trials = int(research.get("n_trials", 20))
    dsr = deflated_sharpe(perf_oos["returns"], n_trials=n_trials)

    # Cost grid — re-run backtest at each fee level.
    cost_df = cost_sensitivity(
        lambda fee: _clean(backtest_single(pos, btc, fee_bps=fee)),
        cost_grid_bps=[0, 5, 10, 20, 40],
    )

    # Walk-forward — refit weights on each window's training slice.
    wf_records = run_walk_forward(ts, btc, regime)

    # Parameter plateau — fix weights at the primary IS-only fit and sweep
    # the rolling-IC window. Cheap proxy: re-evaluate OOS Sharpe at each
    # plateau cell by re-fitting weights on IS with a different IC window.
    def _plateau_metric(params: dict) -> float:
        # Recompute IS-only weights with the requested rolling window.
        # We piggy-back on regime_layered_ic which uses pooled within-bucket
        # Spearman; the "window" knob effectively rescales factor inputs
        # via factor.rolling(window).mean() before fitting.
        w_grid: dict[str, dict[str, float]] = {}
        win = int(params["window"])
        fwd = forward_returns(btc, 5)
        ts_is = ts.loc[is_dates]
        fwd_is = fwd.reindex(ts_is.index)
        reg_is = regime.reindex(ts_is.index)
        for fname in ts_is.columns:
            if fname == "value_classification":
                continue
            smoothed = ts_is[fname].rolling(win, min_periods=win).mean()
            lay = regime_layered_ic(smoothed, fwd_is, reg_is)
            for _, rec in lay.iterrows():
                if pd.isna(rec["ic"]) or rec["n"] < 30:
                    continue
                if abs(rec["ic"]) > C.RANK_IC_THRESHOLD:
                    w_grid.setdefault(rec["regime"], {})[fname] = float(
                        np.sign(rec["ic"]) * abs(rec["ic"])
                    )
        if not w_grid:
            return float("nan")
        cols = sorted({f for w in w_grid.values() for f in w.keys()
                       if f in ts.columns})
        if not cols:
            return float("nan")
        pos_g = regime_conditional_positions(
            ts[cols].reindex(btc.index), regime, w_grid, max_pos=1.0
        )
        p_oos = backtest_single(
            pos_g[pos_g.index >= cut], btc[btc.index >= cut]
        )
        return float(p_oos.get("sharpe", float("nan")))

    plateau_df = parameter_plateau(
        _plateau_metric, {"window": PLATEAU_WINDOW_GRID}
    )

    mc = monte_carlo_random(btc)

    # ----- OOS equity figure -----
    plt.figure(figsize=(9, 5))
    perf_oos["equity_curve"].plot(label="SignalForge (OOS, IS-only fit)")
    btc_oos = btc[btc.index >= cut]
    if len(btc_oos) > 0:
        (btc_oos / btc_oos.iloc[0]).plot(label="BTC HODL", alpha=0.7)
    plt.legend()
    plt.title("Out-of-sample equity curve (regime weights fit on IS only)")
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
        "regime_weights_source": (
            "default_regime_weights (IS-only fit empty)"
            if used_default
            else "build_weights_is_only (no OOS leak)"
        ),
        "is_oos_cut": str(cut),
        "factors_used": factor_cols,
        "walk_forward": wf_records,
        "parameter_plateau": plateau_df.to_dict("records"),
    }
    (OUT / "backtest_results.json").write_text(
        json.dumps(out, indent=2, default=float)
    )
    print(
        f"OOS Sharpe (IS-only fit): {perf_oos['sharpe']:.2f} | "
        f"DSR p: {dsr.get('deflated_sharpe_prob')} | "
        f"random 95pct Sharpe: {mc['random_sharpe_95pct']:.2f} | "
        f"walk-forward windows: {len(wf_records)} | "
        f"plateau cells: {len(plateau_df)}"
    )


if __name__ == "__main__":
    main()
