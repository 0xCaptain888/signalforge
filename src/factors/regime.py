"""Regime labelling — direction (BTC trend) crossed with sentiment (CMC F&G).

Every label at time t depends only on data observed at or before t:
- The trend MA is `MA_WINDOW`-day rolling with `min_periods=MA_WINDOW`.
- The slope is a 20-day finite difference of that MA.
- The sentiment buckets come from the F&G value at time t.

The Cartesian product of {BULL, BEAR, CHOP} x {FEAR, NEUTRAL, GREED} gives
nine cells used by `src/research/regime_attrib.py` to compute regime-layered
IC tables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import constants as C


def label_regime(btc_close: pd.Series, fg: pd.Series) -> pd.DataFrame:
    """Tag every date with a (direction, sentiment, combined) regime label.

    Parameters
    ----------
    btc_close : pd.Series
        Daily BTC close indexed by date.
    fg : pd.Series
        Daily CMC proprietary F&G value indexed by date.

    Returns
    -------
    pd.DataFrame with columns [date, dir_regime, sent_regime, regime].
    """
    df = pd.DataFrame({"btc": btc_close}).join(
        pd.DataFrame({"fg": fg}), how="inner"
    )

    # Direction regime: price vs MA + 20-day slope sign of the MA.
    ma = df["btc"].rolling(C.MA_WINDOW, min_periods=C.MA_WINDOW).mean()
    slope = ma.diff(20)
    df["dir_regime"] = np.select(
        [(df["btc"] > ma) & (slope > 0), (df["btc"] < ma) & (slope < 0)],
        ["BULL", "BEAR"],
        default="CHOP",
    )

    # Sentiment regime: thresholds defined in config/constants.py.
    df["sent_regime"] = np.select(
        [df["fg"] < C.FG_FEAR, df["fg"] > C.FG_GREED],
        ["FEAR", "GREED"],
        default="NEUTRAL",
    )

    df["regime"] = df["dir_regime"] + "_" + df["sent_regime"]

    return (
        df.reset_index()
        .rename(columns={"index": "date"})[
            ["date", "dir_regime", "sent_regime", "regime"]
        ]
    )
