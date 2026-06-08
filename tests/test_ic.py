"""Unit tests for src/research/ic.py.

These tests verify the contracts the research layer depends on:

1. `forward_returns` uses STRICTLY FUTURE prices — the value at index t
   reflects close[t+h]/close[t]-1, and the last h positions are NaN.
2. `timeseries_ic` recovers a strong, positive IC when factor and forward
   return are constructed to be monotonically related.
3. `ir_and_tstat` returns positive IR for a series with positive mean.
4. `cross_section_ic` produces one IC per date and returns NaN/skip when
   the cross section is too thin.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.ic import (
    cross_section_ic,
    forward_returns,
    ir_and_tstat,
    rolling_ic_series,
    timeseries_ic,
)


def test_forward_returns_uses_future() -> None:
    close = pd.Series(
        [100.0, 110.0, 121.0, 133.1, 146.41],
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )
    fr1 = forward_returns(close, 1)
    # First four are ~10% returns; last is NaN (no future close).
    assert np.allclose(fr1.iloc[:4].values, 0.10, atol=1e-9)
    assert np.isnan(fr1.iloc[-1])


def test_timeseries_ic_detects_monotone_signal() -> None:
    n = 200
    rng = np.random.default_rng(0)
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    factor = pd.Series(np.linspace(-1, 1, n), index=idx)
    # Returns = factor * 0.01 + noise — Spearman IC should be very high.
    fwd = pd.Series(factor.values * 0.01 + rng.normal(0, 0.001, n), index=idx)
    res = timeseries_ic(factor, fwd)
    assert res["ic"] > 0.9
    assert res["p"] < 1e-10
    assert res["n"] == n


def test_ir_positive_when_mean_ic_positive() -> None:
    rng = np.random.default_rng(1)
    ic = pd.Series(rng.normal(0.05, 0.10, 200))
    stat = ir_and_tstat(ic)
    assert stat["mean_ic"] > 0
    assert stat["ir"] > 0
    assert stat["t_stat"] > 0


def test_rolling_ic_series_no_lookahead() -> None:
    n = 120
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    f = pd.Series(np.linspace(0, 1, n), index=idx)
    r = pd.Series(np.linspace(0, 1, n) * 0.01, index=idx)
    s = rolling_ic_series(f, r, window=60)
    # All emitted indices are >= the 60th observation.
    assert (s.index >= idx[59]).all()
    # Perfect monotone relationship -> rolling IC is 1.0 (or extremely close).
    assert (s >= 0.999).all()


def test_cross_section_ic_skips_thin_dates() -> None:
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    factor = pd.DataFrame(
        {1: [0.1, np.nan, 0.3], 2: [0.2, np.nan, 0.1]}, index=dates
    )
    ret = pd.DataFrame(
        {1: [0.01, 0.02, 0.03], 2: [0.02, 0.01, 0.01]}, index=dates
    )
    s = cross_section_ic(factor, ret)
    # With only 2 ids per cross section, the function should skip all dates
    # (the implementation requires >= 10 common ids).
    assert len(s) == 0
