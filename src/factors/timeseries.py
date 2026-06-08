"""Time-series factors (point-in-time).

All rolling windows are right-anchored at t with `min_periods=window` so that
no observation strictly after t can influence the factor value at t. This is
enforced by tests in tests/test_no_lookahead.py.

Factor families implemented here, per §4.1 of the build doc:

- F&G (CMC proprietary) — level / 90-day z-score / 7-day momentum /
  extreme-reversal flag / regime-duration counter
- BTC-dominance — 30-day slope / 90-day z-score / total-mkt-cap 30-day return
- Interaction — (-fg_zscore_90) * dom_trend_30  (fear + rising dominance =
  flight-to-quality rotation signal)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _roll_z(s: pd.Series, window: int) -> pd.Series:
    """Rolling z-score using ONLY past data within the window.

    `min_periods=window` guarantees that NaN is returned until a full window of
    history is available, which prevents the early-sample bias of partially
    populated windows.
    """
    m = s.rolling(window, min_periods=window).mean()
    sd = s.rolling(window, min_periods=window).std()
    return (s - m) / sd.replace(0, np.nan)


# ---------------------------------------------------------------------------
# CMC proprietary Fear & Greed factors
# ---------------------------------------------------------------------------

def build_fg_factors(fg: pd.DataFrame) -> pd.DataFrame:
    """Build F&G-derived time-series factors.

    Parameters
    ----------
    fg : pd.DataFrame
        Must contain columns [date, cmc_fg, value_classification].

    Returns
    -------
    pd.DataFrame with columns [date, fg_level, fg_zscore_90, fg_momentum_7,
    fg_extreme_rev, fg_regime_dur].
    """
    df = fg.sort_values("date").copy().set_index("date")
    out = pd.DataFrame(index=df.index)

    out["fg_level"] = df["cmc_fg"]
    out["fg_zscore_90"] = _roll_z(df["cmc_fg"], 90)
    out["fg_momentum_7"] = df["cmc_fg"] - df["cmc_fg"].shift(7)

    # Mean-reversion flag at sentiment extremes (no future info; pure pointwise).
    out["fg_extreme_rev"] = np.select(
        [df["cmc_fg"] < 20, df["cmc_fg"] > 80],
        [1.0, -1.0],
        default=0.0,
    )

    # Number of consecutive days the F&G classification has stayed in its
    # current bucket. Implemented with a group-id cumcount so the value at t
    # depends only on labels at times <= t.
    cls = df["value_classification"].fillna("NA")
    grp = (cls != cls.shift()).cumsum()
    out["fg_regime_dur"] = cls.groupby(grp).cumcount() + 1

    return out.reset_index()


# ---------------------------------------------------------------------------
# Global / dominance factors
# ---------------------------------------------------------------------------

def build_dominance_factors(gm: pd.DataFrame) -> pd.DataFrame:
    """Build BTC-dominance and total-market-cap factors.

    Parameters
    ----------
    gm : pd.DataFrame
        Must contain columns [date, btc_dominance, eth_dominance,
        total_market_cap, total_volume_24h].

    Returns
    -------
    pd.DataFrame with columns [date, dom_trend_30, dom_zscore_90,
    mktcap_mom_30].
    """
    df = gm.sort_values("date").copy().set_index("date")
    out = pd.DataFrame(index=df.index)

    # 30-day per-day slope of BTC dominance (simple finite difference / N).
    out["dom_trend_30"] = df["btc_dominance"].diff(30) / 30.0
    out["dom_zscore_90"] = _roll_z(df["btc_dominance"], 90)
    out["mktcap_mom_30"] = df["total_market_cap"].pct_change(30)

    return out.reset_index()


# ---------------------------------------------------------------------------
# Interaction factor (sentiment * structure)
# ---------------------------------------------------------------------------

def build_fg_dominance_cross(
    fg_f: pd.DataFrame,
    dom_f: pd.DataFrame,
) -> pd.DataFrame:
    """Interaction factor: low F&G (fear) combined with rising BTC dominance.

    Intuition: in regimes of panic where capital rotates into BTC as a
    "quality" hedge, the negative z-score of F&G times positive dominance
    trend is large and positive — a flight-to-quality proxy.

    Parameters
    ----------
    fg_f : pd.DataFrame
        Output of `build_fg_factors`, must contain [date, fg_zscore_90].
    dom_f : pd.DataFrame
        Output of `build_dominance_factors`, must contain [date, dom_trend_30].

    Returns
    -------
    pd.DataFrame with columns [date, fg_cross_dom].
    """
    m = fg_f.merge(dom_f, on="date", how="inner")
    m["fg_cross_dom"] = (-m["fg_zscore_90"]) * m["dom_trend_30"]
    return m[["date", "fg_cross_dom"]]
