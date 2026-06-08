"""Vectorised backtest engine.

Execution rule (strictly enforced): a signal observed at the close of day t
is acted on at the close of day t+1, and earns the t+1 -> t+2 return. This
removes the trivial look-ahead of "trading on the day you see the signal".

Cost model: round-trip turnover * (fee_bps + slippage_bps) / 1e4 per change
in position. Slippage default is conservative for single-asset (5 bps) and
larger for cross-section baskets (10 bps), reflecting typical impact on
smaller alts.

Performance metrics: annualised return / vol / Sharpe / Sortino / Calmar,
max drawdown, win rate, average turnover, alpha & beta vs a benchmark
(equal-weight basket for the panel backtest; HODL for single-asset),
plus `equity_curve` and `returns` so the caller can plot or feed DSR.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import constants as C


def backtest_single(
    positions: pd.Series,
    close: pd.Series,
    fee_bps: float = C.FEE_BPS,
    slippage_bps: float = 5,
) -> dict:
    """Single-asset timing backtest.

    Parameters
    ----------
    positions : pd.Series
        Position in [-1, 1] indexed by date. The position at t is what is
        EXECUTED on t+1's close.
    close : pd.Series
        Daily close indexed by date.

    Returns
    -------
    dict from `_perf` — see that function for keys.
    """
    df = pd.DataFrame({"pos": positions, "close": close}).dropna().sort_index()
    # `ret` at row t is the close-to-close return from t to t+1.
    df["ret"] = df["close"].pct_change().shift(-1)
    # Signal at t actually executed at t+1 — implement as one-bar shift.
    df["pos_exec"] = df["pos"].shift(1).fillna(0.0)
    df["turnover"] = df["pos_exec"].diff().abs().fillna(0.0)
    cost = df["turnover"] * (fee_bps + slippage_bps) / 1e4
    df["strat_ret"] = df["pos_exec"] * df["ret"] - cost

    bench = df["ret"].dropna()  # HODL benchmark
    return _perf(df["strat_ret"].dropna(), bench, float(df["turnover"].mean()))


def backtest_panel(
    positions: pd.DataFrame,
    close_panel: pd.DataFrame,
    fee_bps: float = C.FEE_BPS,
    slippage_bps: float = 10,
) -> dict:
    """Cross-sectional backtest of a (date x id) weight panel.

    Benchmark is the equal-weight basket of all ids on each day.
    """
    ret = close_panel.pct_change().shift(-1)
    pos_exec = positions.shift(1).fillna(0.0)
    turnover = pos_exec.diff().abs().sum(axis=1).fillna(0.0)
    gross = (pos_exec * ret).sum(axis=1)
    cost = turnover * (fee_bps + slippage_bps) / 1e4
    strat_ret = (gross - cost).dropna()
    bench = ret.mean(axis=1).dropna()
    return _perf(strat_ret, bench, float(turnover.mean()))


def _perf(
    strat: pd.Series,
    bench: pd.Series,
    avg_turnover: float,
) -> dict:
    """Compute the performance dict consumed by callers / spec / report."""
    strat = strat.dropna()
    if len(strat) == 0:
        return {
            "ann_return": float("nan"), "ann_vol": float("nan"),
            "sharpe": float("nan"), "sortino": float("nan"),
            "calmar": float("nan"), "max_drawdown": float("nan"),
            "win_rate": float("nan"), "avg_turnover": avg_turnover,
            "alpha_vs_bench": float("nan"), "beta_vs_bench": float("nan"),
            "n_days": 0,
            "equity_curve": pd.Series(dtype=float),
            "returns": strat,
        }

    ann = 365
    mean = float(strat.mean())
    sd = float(strat.std())
    downside = float(strat[strat < 0].std()) if (strat < 0).any() else 0.0
    cum = (1 + strat).cumprod()
    dd = float((cum / cum.cummax() - 1).min())

    sharpe = mean / sd * np.sqrt(ann) if sd > 0 else np.nan
    sortino = (
        mean / downside * np.sqrt(ann) if downside and downside > 0 else np.nan
    )
    ann_ret = (1 + mean) ** ann - 1
    calmar = ann_ret / abs(dd) if dd < 0 else np.nan

    # Alpha / beta vs benchmark — needs overlapping >=10 obs to be meaningful.
    common = strat.index.intersection(bench.index)
    if len(common) > 10:
        s_aligned = strat.reindex(common).values
        b_aligned = bench.reindex(common).values
        cov = np.cov(s_aligned, b_aligned)
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else np.nan
        alpha = (mean - beta * float(np.mean(b_aligned))) * ann
    else:
        beta = alpha = np.nan

    return {
        "ann_return": float(ann_ret),
        "ann_vol": float(sd * np.sqrt(ann)),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "max_drawdown": float(dd),
        "win_rate": float((strat > 0).mean()),
        "avg_turnover": float(avg_turnover),
        "alpha_vs_bench": float(alpha) if alpha == alpha else float("nan"),
        "beta_vs_bench": float(beta) if beta == beta else float("nan"),
        "n_days": int(len(strat)),
        "equity_curve": cum,
        "returns": strat,
    }


def monte_carlo_random(
    close: pd.Series,
    n_sims: int = 1000,
    seed: int = C.SEED,
) -> dict:
    """Random-signal Sharpe distribution — a sanity baseline.

    Generates `n_sims` random {-1, 0, +1} position series and computes their
    annualised Sharpe. A strategy is only convincing if its Sharpe lies in
    the top tail of this distribution.
    """
    rng = np.random.default_rng(seed)
    ret = close.pct_change().shift(-1).dropna()
    sharpes = []
    for _ in range(n_sims):
        rand_pos = pd.Series(rng.choice([-1, 0, 1], len(ret)), index=ret.index)
        sr = (rand_pos * ret).dropna()
        s = sr.mean() / sr.std() * np.sqrt(365) if sr.std() > 0 else 0.0
        sharpes.append(float(s))
    return {
        "random_sharpe_mean": float(np.mean(sharpes)),
        "random_sharpe_95pct": float(np.percentile(sharpes, 95)),
        "random_sharpe_std": float(np.std(sharpes)),
        "n_sims": int(n_sims),
    }
