"""Look-ahead bias unit tests for src/factors/timeseries.py.

Two guarantees we must verify:

1. Tampering with a future observation can NOT change any historical factor.
   (Concretely: changing the last row's cmc_fg must leave fg_zscore_90,
   fg_momentum_7, fg_level for all earlier rows bit-for-bit identical.)

2. Rolling-window factors must return NaN until a full window of history
   exists, so a model never trains on a "warm-up" value that secretly
   leaked future information.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.factors.timeseries import build_fg_factors


def _make_fg(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    vals = rng.integers(10, 90, n).astype(float)
    return pd.DataFrame(
        {
            "date": dates,
            "cmc_fg": vals,
            "value_classification": ["Neutral"] * n,
        }
    )


def test_future_does_not_leak() -> None:
    base = _make_fg()
    f1 = build_fg_factors(base).set_index("date")

    tampered = base.copy()
    tampered.loc[tampered.index[-1], "cmc_fg"] = 999
    f2 = build_fg_factors(tampered).set_index("date")

    cols = ["fg_zscore_90", "fg_momentum_7", "fg_level"]
    a = f1[cols].iloc[:-1].fillna(-12345)
    b = f2[cols].iloc[:-1].fillna(-12345)
    assert np.allclose(a.values, b.values), (
        "look-ahead leak: changing the last cmc_fg altered historical factors"
    )


def test_rolling_uses_only_past() -> None:
    base = _make_fg()
    f = build_fg_factors(base).set_index("date")
    # First 89 rows have insufficient history for a 90-day window.
    assert f["fg_zscore_90"].iloc[:89].isna().all()


def test_momentum_uses_only_past() -> None:
    base = _make_fg()
    f = build_fg_factors(base).set_index("date")
    # First 7 rows can't have a 7-day backward diff.
    assert f["fg_momentum_7"].iloc[:7].isna().all()
    assert not f["fg_momentum_7"].iloc[7:].isna().all()
