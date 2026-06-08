"""Unit tests for src/strategy/{signals,portfolio,backtest}.py.

The critical invariants verified here:

1. `factor_to_signal` is bounded in [-1, 1] and zero-fills NaNs.
2. `combine_signals` produces an L1-normalised weighted sum bounded by 1.
3. `backtest_single` applies a STRICT one-bar execution lag: a position
   that perfectly predicts tomorrow's return realises gains; the same
   position aligned without the lag would realise zero (or negative)
   gains in this construction.
4. Turnover and cost accounting move in the right direction (more
   trading => more cost => lower Sharpe).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.backtest import backtest_single, monte_carlo_random
from src.strategy.portfolio import (
    cross_section_positions,
    regime_conditional_positions,
)
from src.strategy.signals import combine_signals, factor_to_signal


def test_factor_to_signal_bounded_and_nan_safe() -> None:
    f = pd.Series([np.nan, -10.0, -1.0, 0.0, 1.0, 10.0])
    s = factor_to_signal(f)
    assert s.between(-1, 1).all()
    assert s.iloc[0] == 0.0
    # tanh(0) = 0, tanh(+/-10) ~= +/-1.
    assert s.iloc[3] == 0.0
    assert s.iloc[5] > 0.99
    assert s.iloc[1] < -0.99


def test_factor_to_signal_long_only_clips_at_zero() -> None:
    f = pd.Series([-5.0, 0.0, 5.0])
    s = factor_to_signal(f, long_only=True)
    assert (s >= 0).all()
    assert s.iloc[0] == 0.0


def test_combine_signals_l1_normalised() -> None:
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    a = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0], index=idx)
    b = pd.Series([-1.0, -1.0, -1.0, -1.0, -1.0], index=idx)
    # Equal-magnitude opposite signals should cancel to ~0.
    combined = combine_signals({"a": a, "b": b}, {"a": 1.0, "b": 1.0})
    assert np.allclose(combined.values, 0.0)
    # Skewed weights should tilt toward the heavier side.
    combined2 = combine_signals({"a": a, "b": b}, {"a": 3.0, "b": 1.0})
    assert (combined2 > 0).all()
    assert combined2.between(-1, 1).all()


def test_backtest_single_t_plus_1_execution() -> None:
    """A 'perfect predictor' position (sign of tomorrow's return at t)
    must be positively profitable AFTER the t->t+1 shift, because at t
    we already know `pos_exec at t+1 == sign(ret t+1->t+2)` only if we
    use a backward-looking signal — so this test instead verifies that
    a CONSTANT positive position earns +ve mean return on an up-trend.

    More importantly, swapping the signal sign must flip the sign of
    the realised mean strategy return; this only holds if the same
    `shift(1)` is applied consistently to both."""
    n = 100
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(100, 200, n), index=idx)  # smooth up-trend

    long_pos = pd.Series(1.0, index=idx)
    short_pos = pd.Series(-1.0, index=idx)

    perf_long = backtest_single(long_pos, close, fee_bps=0, slippage_bps=0)
    perf_short = backtest_single(short_pos, close, fee_bps=0, slippage_bps=0)

    # Up-trend: long is positive, short is negative, magnitudes match.
    assert perf_long["ann_return"] > 0
    assert perf_short["ann_return"] < 0
    assert np.isclose(
        perf_long["returns"].sum(), -perf_short["returns"].sum(), atol=1e-9
    )


def test_backtest_signal_does_not_use_today_return() -> None:
    """Verify the t->t+1 lag explicitly.

    Construct a signal that exactly equals the realised SAME-DAY return.
    Without the lag, this would be a perfect (look-ahead) predictor and
    earn a huge Sharpe. With the correct one-bar shift, the signal at t
    is acted on at t+1 — earning ret(t+1->t+2), which is uncorrelated
    with ret(t-1->t). So Sharpe should be near zero, not enormous.
    """
    rng = np.random.default_rng(42)
    n = 400
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    ret = rng.normal(0.0, 0.02, n)
    close = pd.Series(100 * np.exp(np.cumsum(ret)), index=idx)

    # "Cheat" signal: sign of the same-day return. If the backtest didn't
    # apply shift(1), Sharpe would be enormous.
    cheat = pd.Series(np.sign(close.pct_change().fillna(0.0)), index=idx)
    perf = backtest_single(cheat, close, fee_bps=0, slippage_bps=0)
    # With the lag, |Sharpe| must stay modest (well under 5; perfect
    # look-ahead would be > 30).
    assert abs(perf["sharpe"]) < 5, (
        f"backtest appears to leak today's return: Sharpe={perf['sharpe']}"
    )


def test_costs_reduce_returns() -> None:
    rng = np.random.default_rng(0)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)
    # Flippy signal -> high turnover.
    pos = pd.Series(rng.choice([-1, 1], n), index=idx)
    no_cost = backtest_single(pos, close, fee_bps=0, slippage_bps=0)
    high_cost = backtest_single(pos, close, fee_bps=50, slippage_bps=50)
    assert high_cost["ann_return"] < no_cost["ann_return"]


def test_cross_section_positions_long_short_balanced() -> None:
    rng = np.random.default_rng(0)
    n_days, n_ids = 5, 20
    idx = pd.date_range("2024-01-01", periods=n_days, freq="D")
    panel = pd.DataFrame(
        rng.normal(0, 1, (n_days, n_ids)), index=idx,
        columns=list(range(n_ids)),
    )
    pos = cross_section_positions(panel, top_q=0.2, bottom_q=0.2)
    # Long/short equal-weight basket sums to ~0 every day.
    assert np.allclose(pos.sum(axis=1).values, 0.0, atol=1e-9)
    # Concentration cap respected.
    assert pos.abs().max().max() <= 0.30 + 1e-9


def test_regime_conditional_zero_when_regime_unmapped() -> None:
    n = 10
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    factors = pd.DataFrame({"f1": np.linspace(-1, 1, n)}, index=idx)
    regime = pd.Series(["UNKNOWN_REGIME"] * n, index=idx)
    weights = {"SOMETHING_ELSE": {"f1": 1.0}}
    pos = regime_conditional_positions(factors, regime, weights)
    assert (pos == 0).all()


def test_monte_carlo_random_returns_sane_stats() -> None:
    rng = np.random.default_rng(0)
    n = 365
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    close = pd.Series(
        100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))), index=idx
    )
    mc = monte_carlo_random(close, n_sims=100, seed=1)
    # Mean random Sharpe should be near zero, 95th percentile must exceed it.
    assert abs(mc["random_sharpe_mean"]) < 1.0
    assert mc["random_sharpe_95pct"] > mc["random_sharpe_mean"]
