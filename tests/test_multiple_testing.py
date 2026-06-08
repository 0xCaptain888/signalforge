"""Unit tests for src/research/multiple_testing.py."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.multiple_testing import bh_fdr, deflated_sharpe


def test_bh_fdr_basic_behaviour() -> None:
    # Mix of "very small" and "large" p-values: the small ones should be
    # flagged significant at q=0.10, the large ones should not.
    p = [1e-6, 1e-5, 0.5, 0.6, 0.7]
    res = bh_fdr(p, q=0.10)
    assert res["significant"].iloc[0]
    assert res["significant"].iloc[1]
    assert not res["significant"].iloc[2:].any()
    assert res["p_adj"].iloc[0] <= res["p"].iloc[0] * len(p) + 1e-12


def test_bh_fdr_handles_nan() -> None:
    res = bh_fdr([np.nan, 0.001, np.nan, 0.9], q=0.05)
    # NaN rows: not significant, p_adj NaN, original p preserved.
    assert not res["significant"].iloc[0]
    assert not res["significant"].iloc[2]
    assert np.isnan(res["p_adj"].iloc[0])


def test_deflated_sharpe_punishes_more_trials() -> None:
    rng = np.random.default_rng(7)
    # 500 daily returns with mean = 0.001 and sd = 0.01 -> daily SR ~= 0.1.
    r = pd.Series(rng.normal(0.001, 0.01, 500))
    low_trials = deflated_sharpe(r, n_trials=1)
    high_trials = deflated_sharpe(r, n_trials=1000)
    # Both compute, daily Sharpe identical, DSR strictly smaller with more
    # trials (more deflation).
    assert np.isclose(
        low_trials["sharpe_daily"], high_trials["sharpe_daily"]
    )
    assert high_trials["deflated_sharpe_prob"] < low_trials[
        "deflated_sharpe_prob"
    ]


def test_deflated_sharpe_short_series() -> None:
    r = pd.Series([0.01] * 5)
    out = deflated_sharpe(r, n_trials=10)
    assert np.isnan(out["sharpe_daily"])
    assert np.isnan(out["deflated_sharpe_prob"])
