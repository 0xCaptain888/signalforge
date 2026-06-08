"""Factor -> signal transforms.

All signals are emitted at time t and CONSUMED at t+1 by the backtest
(`backtest_single` and `backtest_panel` apply a `shift(1)` to positions
before realising returns). Keeping the t/t+1 alignment in the backtest —
not here — means signal generators stay simple and reusable.

The default `factor_to_signal` uses tanh to squash the factor into [-1, 1]
without truncating the tails as aggressively as a hard clip would. Long-only
clipping at zero is supported as a flag.

`combine_signals` does an L1-normalised weighted sum so the weights can come
from IR / regime-IC calibration without the caller having to renormalise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def factor_to_signal(
    factor: pd.Series,
    long_only: bool = False,
) -> pd.Series:
    """Compress a factor series into a [-1, 1] signal.

    NaN factor values become 0 (neutral). `tanh` is smooth and bounded; a
    factor with z-score ~1 maps to ~0.76, ~2 to ~0.96, so it preserves rank
    while taming outliers.
    """
    s = np.tanh(factor.fillna(0.0))
    if long_only:
        s = s.clip(lower=0.0)
    return s


def combine_signals(
    signals: dict[str, pd.Series],
    weights: dict[str, float],
) -> pd.Series:
    """L1-normalised weighted sum of named signals.

    Parameters
    ----------
    signals : dict[str, pd.Series]
        name -> signal in [-1, 1].
    weights : dict[str, float]
        name -> weight (can be positive or negative for inverted signals).
        The combined output is divided by sum(|weight|) so the result stays
        bounded in [-1, 1].

    Returns
    -------
    pd.Series indexed by the union of all input indices, clipped to [-1, 1].
    """
    idx: pd.Index | None = None
    for s in signals.values():
        idx = s.index if idx is None else idx.union(s.index)
    if idx is None:
        return pd.Series(dtype=float)

    out = pd.Series(0.0, index=idx)
    wsum = sum(abs(w) for w in weights.values()) or 1.0
    for name, w in weights.items():
        if name in signals:
            out = out.add(
                (w / wsum) * signals[name].reindex(idx).fillna(0.0),
                fill_value=0.0,
            )
    return out.clip(-1, 1)
