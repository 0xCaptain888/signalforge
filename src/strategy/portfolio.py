"""Position-sizing: signals -> portfolio weights.

Two flavours:

- `regime_conditional_positions` — single-asset (e.g. BTC) timing. On each
  date, look up the regime label, pick that regime's factor-weight dict,
  combine the per-factor signals into a position in [-max_pos, +max_pos].
- `cross_section_positions` — top-q / bottom-q long-short with a per-asset
  weight cap, fed by a (date x id) composite-factor panel.

Both functions operate purely on data that is already point-in-time; the
t -> t+1 execution lag is applied later by the backtest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.signals import combine_signals, factor_to_signal


def regime_conditional_positions(
    factors: pd.DataFrame,
    regime: pd.Series,
    weights_by_regime: dict[str, dict[str, float]],
    max_pos: float = 1.0,
) -> pd.Series:
    """Combine factor signals using regime-specific weights.

    Parameters
    ----------
    factors : pd.DataFrame
        index=date, columns=factor name. Raw factor values (pre-tanh).
    regime : pd.Series
        index=date, values=string regime label (e.g. "BEAR_FEAR").
    weights_by_regime : dict[str, dict[str, float]]
        regime label -> {factor name: weight}. Missing regime => 0 position.
    max_pos : float
        Cap on absolute position size, default 1.0 (fully long or short).

    Returns
    -------
    pd.Series indexed by `factors.index`, values in [-max_pos, +max_pos].
    """
    # Pre-compute per-factor signals once, then index per date.
    sigs = {c: factor_to_signal(factors[c]) for c in factors.columns}
    dates = factors.index
    pos = pd.Series(0.0, index=dates)

    for d in dates:
        reg = regime.get(d, None)
        w = weights_by_regime.get(reg, {})
        if not w:
            continue
        # Slice each factor's signal at date d into a one-element series so
        # combine_signals can return a single combined scalar.
        day_sig = {
            k: pd.Series([v.get(d, 0.0)], index=[d]) for k, v in sigs.items()
        }
        combined = combine_signals(day_sig, w)
        pos.loc[d] = float(combined.iloc[0])

    return (pos * max_pos).clip(-max_pos, max_pos)


def cross_section_positions(
    factor_panel: pd.DataFrame,
    top_q: float = 0.2,
    bottom_q: float = 0.2,
    long_only: bool = False,
    max_asset: float = 0.30,
) -> pd.DataFrame:
    """Top-q long / bottom-q short equal-weight portfolio.

    Per date, take the top `top_q` fraction of ids by composite factor score
    and long them equal-weight (capped at `max_asset`); optionally short
    the bottom `bottom_q` fraction symmetrically.

    Parameters
    ----------
    factor_panel : pd.DataFrame
        index=date, columns=id. Composite factor score.
    top_q, bottom_q : float
        Quantile thresholds (e.g. 0.2 = top/bottom 20%).
    long_only : bool
        If True, skip the short leg.
    max_asset : float
        Cap on absolute weight per asset (concentration limit).

    Returns
    -------
    pd.DataFrame with the same shape as `factor_panel`, weights in
    [-max_asset, +max_asset]; missing factor values default to 0 weight.
    """
    pos = pd.DataFrame(
        0.0, index=factor_panel.index, columns=factor_panel.columns
    )
    for d in factor_panel.index:
        row = factor_panel.loc[d].dropna()
        if len(row) < 5:
            continue
        n_top = max(int(len(row) * top_q), 1)
        longs = row.nlargest(n_top).index
        pos.loc[d, longs] = min(1.0 / n_top, max_asset)
        if not long_only:
            n_bot = max(int(len(row) * bottom_q), 1)
            shorts = row.nsmallest(n_bot).index
            pos.loc[d, shorts] = -min(1.0 / n_bot, max_asset)
    return pos


def default_regime_weights() -> dict[str, dict[str, float]]:
    """Hand-set starting weights — overwritten by `build_weights_from_research`
    in `scripts/04_backtest.py` once the research scorecard exists.

    Intent (rough heuristics):
    - BEAR_FEAR: capitulation regime — extreme-reversal long, fade negative z.
    - BULL_GREED: trend regime — dominance and momentum confirm direction.
    - CHOP_NEUTRAL: mean-reversion — fade extremes in both F&G and dominance.
    """
    return {
        "BEAR_FEAR":    {"fg_extreme_rev": 0.6, "fg_zscore_90": -0.4},
        "BULL_GREED":   {"dom_trend_30": 0.5, "fg_momentum_7": 0.5},
        "CHOP_NEUTRAL": {"fg_zscore_90": -0.5, "dom_zscore_90": -0.5},
    }
