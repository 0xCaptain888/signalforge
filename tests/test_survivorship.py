"""Survivorship-bias unit tests for src/factors/cross_section.py.

Guarantee: the universe on each rebalance date is exactly the set of ids
present in the listings snapshot for THAT date — never the union of past
and future, never the latest snapshot back-projected.

The test simulates a delisting (coin B disappears between t1 and t2) and a
new listing (coin C appears at t2) and asserts the per-date universes match
the snapshots exactly.
"""
from __future__ import annotations

import pandas as pd

from src.factors.cross_section import build_cross_section_factors


def test_universe_is_point_in_time() -> None:
    # t1 universe = {1, 2}; t2 universe = {1, 3}.
    snaps = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2023-01-01"),
                "id": 1,
                "symbol": "A",
                "cmc_rank": 1,
                "price": 10,
                "market_cap": 1e9,
            },
            {
                "date": pd.Timestamp("2023-01-01"),
                "id": 2,
                "symbol": "B",
                "cmc_rank": 2,
                "price": 5,
                "market_cap": 5e8,
            },
            {
                "date": pd.Timestamp("2023-02-01"),
                "id": 1,
                "symbol": "A",
                "cmc_rank": 1,
                "price": 12,
                "market_cap": 1.2e9,
            },
            {
                "date": pd.Timestamp("2023-02-01"),
                "id": 3,
                "symbol": "C",
                "cmc_rank": 2,
                "price": 8,
                "market_cap": 6e8,
            },
        ]
    )

    # Enough OHLCV history so 90-day return / 60-day vol can be computed.
    ohlcv = pd.DataFrame(
        [
            {"id": i, "date": d, "close": 10.0, "volume": 1, "market_cap": 1e9}
            for i in [1, 2, 3]
            for d in pd.date_range("2022-09-01", "2023-02-01", freq="D")
        ]
    )

    xs = build_cross_section_factors(snaps, ohlcv)

    t1 = set(xs[xs["date"] == "2023-01-01"]["id"])
    t2 = set(xs[xs["date"] == "2023-02-01"]["id"])

    assert t1 == {1, 2}, f"t1 universe leaked future coin: {t1}"
    assert t2 == {1, 3}, f"t2 universe kept delisted coin: {t2}"


def test_no_lookahead_in_xs_returns() -> None:
    """A coin with no OHLCV history before the snapshot date must yield NaN
    for return / vol factors (not be silently zero-filled)."""
    snaps = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2023-01-01"),
                "id": 1,
                "symbol": "A",
                "cmc_rank": 1,
                "price": 10,
                "market_cap": 1e9,
            },
        ]
    )
    # Only ONE day of OHLCV history -> 90d return must be NaN.
    ohlcv = pd.DataFrame(
        [{"id": 1, "date": pd.Timestamp("2023-01-01"), "close": 10.0,
          "volume": 1, "market_cap": 1e9}]
    )

    xs = build_cross_section_factors(snaps, ohlcv)
    # After pct-rank within day, a single-row cross-section ranks to 0.5 -
    # 0.5 = 0.0 for non-NaN inputs, and NaN stays NaN. We assert NaN here.
    assert xs["xs_ret_mom_90"].isna().all()
    assert xs["xs_vol_60"].isna().all()
