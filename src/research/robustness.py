"""Robustness scaffolding: walk-forward windows, time splits, parameter
plateau scans, cost sensitivity.

These helpers are deliberately functional — they take in callables and
return tidy DataFrames — so the backtest layer (§6) can plug in any
backtest function without import cycles.
"""
from __future__ import annotations

import itertools
from typing import Callable, Iterable

import numpy as np
import pandas as pd


def time_split(
    dates: pd.DatetimeIndex,
    is_frac: float = 0.7,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Single in-sample / out-of-sample chronological split.

    Returns (is_end_date, oos_start_date) — both equal to the boundary date
    so callers can use `< cut` for IS and `>= cut` for OOS without ambiguity.
    """
    if len(dates) == 0:
        raise ValueError("time_split needs a non-empty DatetimeIndex")
    cut = dates[int(len(dates) * is_frac)]
    return cut, cut


def walk_forward_windows(
    dates: pd.DatetimeIndex,
    train: int = 365,
    test: int = 90,
    step: int = 90,
) -> list[tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """Generate non-overlapping rolling (train, test) date windows.

    Yields windows of length `train` for fitting and the next `test` days
    for evaluation, sliding by `step`. The last window is dropped if the
    test slice would run off the end.
    """
    windows: list[tuple[pd.DatetimeIndex, pd.DatetimeIndex]] = []
    i = train
    while i + test <= len(dates):
        windows.append((dates[i - train:i], dates[i:i + test]))
        i += step
    return windows


def parameter_plateau(
    metric_fn: Callable[[dict], float],
    param_grid: dict[str, Iterable],
) -> pd.DataFrame:
    """Grid-scan parameters; record metric per combination.

    A flat (plateau) region of high metric across nearby parameter values is
    evidence of robustness; a single sharp peak suggests over-fitting.
    """
    keys = list(param_grid.keys())
    rows = []
    for combo in itertools.product(*param_grid.values()):
        params = dict(zip(keys, combo))
        try:
            m = float(metric_fn(params))
        except Exception as e:  # noqa: BLE001 — diagnostic only
            m = float("nan")
            params["_error"] = str(e)[:80]
        rows.append({**params, "metric": m})
    return pd.DataFrame(rows)


def cost_sensitivity(
    backtest_fn: Callable[[int], dict],
    cost_grid_bps: list[int],
) -> pd.DataFrame:
    """Re-run a backtest at multiple per-trade cost levels.

    `backtest_fn(fee_bps)` must return a dict of perf metrics. The function
    flattens them into one DataFrame indexed by `fee_bps`.
    """
    rows = []
    for c in cost_grid_bps:
        perf = backtest_fn(c)
        rows.append({"fee_bps": c, **perf})
    return pd.DataFrame(rows)


def stationary_block_bootstrap(
    series: pd.Series,
    block_len: int,
    n_paths: int,
    seed: int = 42,
) -> np.ndarray:
    """Stationary-block bootstrap (Politis & Romano, 1994).

    Returns an array of shape (n_paths, len(series)) where each row is a
    resampled path drawn by concatenating random blocks. Useful for
    constructing distribution-free confidence bands on Sharpe / drawdown /
    other statistics computed by the backtest.
    """
    rng = np.random.default_rng(seed)
    x = series.dropna().to_numpy()
    n = len(x)
    if n == 0:
        return np.zeros((n_paths, 0))
    out = np.empty((n_paths, n), dtype=x.dtype)
    p = 1.0 / max(block_len, 1)
    for k in range(n_paths):
        i = 0
        start = rng.integers(0, n)
        while i < n:
            length = rng.geometric(p)
            for j in range(length):
                if i >= n:
                    break
                out[k, i] = x[(start + j) % n]
                i += 1
            start = rng.integers(0, n)
    return out
