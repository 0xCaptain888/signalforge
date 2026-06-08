"""Cross-sectional factors built from point-in-time listings snapshots.

The CMC `listings/historical` endpoint is what gives us a survivorship-bias-free
universe on each rebalance date: it returns the actual top-N coins by market
cap AS OF that date, including coins that later delisted.

NOTE: on the Basic plan this endpoint returns 403 (see README "M0 findings").
This module still ships and is unit-tested with synthetic data; it will start
producing real factors as soon as a paid CMC tier (or compatible fallback)
populates `listings_snapshots.parquet`.

Factors produced per §4.2 of the build doc:
    xs_rank_mom_30  — change in CMC rank vs ~30 days ago (positive = climbed)
    xs_size         — log market cap (a size factor)
    xs_ret_mom_90   — trailing 90-day price return
    xs_vol_60       — trailing 60-day realised vol of daily returns

All four are converted to within-day percentile ranks centred at zero, so each
day's cross section is in [-0.5, 0.5] and directly comparable across dates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_cross_section_factors(
    snapshots: pd.DataFrame,
    ohlcv: pd.DataFrame,
) -> pd.DataFrame:
    """Build a long-format cross-sectional factor panel.

    Parameters
    ----------
    snapshots : pd.DataFrame
        Point-in-time universe with columns [date, id, symbol, cmc_rank,
        price, market_cap]. One row per (date, id).
    ohlcv : pd.DataFrame
        Daily OHLCV history with columns [id, date, close, volume,
        market_cap]. Must cover enough history to compute 90-day returns and
        60-day vol for every (date, id) in `snapshots`.

    Returns
    -------
    pd.DataFrame with columns [date, id, xs_rank_mom_30, xs_size,
    xs_ret_mom_90, xs_vol_60]. Each metric is replaced by its within-day
    percentile rank minus 0.5 (range [-0.5, 0.5]).
    """
    px = ohlcv.sort_values(["id", "date"]).copy()
    # Per-coin 90-day return and 1-day return (the latter feeds 60-day vol).
    px["ret_90"] = px.groupby("id")["close"].pct_change(90)
    px["ret_1"] = px.groupby("id")["close"].pct_change()
    px["vol_60"] = px.groupby("id")["ret_1"].transform(
        lambda s: s.rolling(60, min_periods=60).std()
    )

    rows: list[dict] = []
    snaps = snapshots.sort_values("date")
    snap_dates = snaps["date"].unique()

    for d in snap_dates:
        uni = snaps[snaps["date"] == d]
        ids = uni["id"].tolist()

        # Look up the most recent rank in a 25–35-day-old window for each id.
        # This window matches CMC's rebalance cadence flex while staying
        # strictly in the past relative to d.
        prev = snaps[snaps["date"] <= d - pd.Timedelta(days=25)]
        prev = prev[prev["date"] >= d - pd.Timedelta(days=35)]
        prev_rank = prev.groupby("id")["cmc_rank"].last()

        px_d = px[(px["date"] == d) & (px["id"].isin(ids))].set_index("id")

        for cid in ids:
            cur_rank = uni[uni["id"] == cid]["cmc_rank"].iloc[0]
            mkt_cap = uni[uni["id"] == cid]["market_cap"].iloc[0]
            rows.append(
                {
                    "date": d,
                    "id": cid,
                    # Rank improvement: prev_rank - cur_rank > 0 means coin
                    # climbed (lower rank number = better).
                    "xs_rank_mom_30": (
                        prev_rank.get(cid, np.nan) - cur_rank
                    ),
                    "xs_size": np.log((mkt_cap or 0) + 1),
                    "xs_ret_mom_90": (
                        px_d["ret_90"].get(cid, np.nan)
                        if cid in px_d.index
                        else np.nan
                    ),
                    "xs_vol_60": (
                        px_d["vol_60"].get(cid, np.nan)
                        if cid in px_d.index
                        else np.nan
                    ),
                }
            )

    df = pd.DataFrame(rows)

    # Within-day percentile rank in [0, 1], shifted to [-0.5, 0.5].
    for col in ["xs_rank_mom_30", "xs_size", "xs_ret_mom_90", "xs_vol_60"]:
        df[col] = df.groupby("date")[col].rank(pct=True) - 0.5

    return df
