"""Information Coefficient (IC) toolkit — the core scoring layer.

All metrics here are forward-looking by construction (factor at t is paired
with a STRICTLY FUTURE return), and pandas' default index alignment plus the
`shift(-horizon)` on returns guarantee that no realised return at or before t
is ever used to evaluate the factor at t.

Definitions used in this project:

- **IC**  Spearman rank correlation between factor and forward return.
  Robust to monotone transformations and outliers.
- **Rolling IC**  IC computed on a sliding window — gives the IC time series
  that powers IR and t-stat.
- **IR** (Information Ratio) = mean(IC) / std(IC) on the rolling series.
- **t-stat** = mean(IC) / std(IC) * sqrt(N) — significance of mean IC under
  the i.i.d. null.
- **IC decay** = same IC computed at multiple holding horizons — diagnoses
  how long the signal persists.

For cross-sectional factors, `cross_section_ic` computes the per-date
Rank-IC across the cross section and returns its time series so the same
IR / t-stat machinery applies.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Forward returns
# ---------------------------------------------------------------------------

def forward_returns(close: pd.Series, horizon: int) -> pd.Series:
    """Return the close-to-close % return over the next `horizon` days.

    `shift(-horizon)` aligns the FUTURE close at index t, so the result at
    index t is the return that would be realised by buying at t and selling
    at t+horizon. NaN at the last `horizon` positions because the future
    close is unknown.
    """
    return close.shift(-horizon) / close - 1.0


# ---------------------------------------------------------------------------
# Time-series IC primitives
# ---------------------------------------------------------------------------

def timeseries_ic(
    factor: pd.Series,
    fwd_ret: pd.Series,
    method: str = "spearman",
) -> dict:
    """Pooled IC over the entire overlapping sample.

    Returns dict {ic, p, n}. n is the number of non-NaN pairs used.
    """
    df = pd.concat([factor, fwd_ret], axis=1, keys=["f", "r"]).dropna()
    if len(df) < 30:
        return {"ic": np.nan, "n": len(df), "p": np.nan}
    if method == "spearman":
        ic, p = stats.spearmanr(df["f"], df["r"])
    else:
        ic, p = stats.pearsonr(df["f"], df["r"])
    return {"ic": float(ic), "p": float(p), "n": len(df)}


def rolling_ic_series(
    factor: pd.Series,
    fwd_ret: pd.Series,
    window: int = 60,
    method: str = "spearman",
) -> pd.Series:
    """IC computed in a sliding window. Returns a time series of ICs.

    Each value at index t uses the `window` observations strictly ending at
    (and including) t, so no future info leaks into the rolling estimate.
    """
    df = pd.concat([factor, fwd_ret], axis=1, keys=["f", "r"]).dropna()
    corr = stats.spearmanr if method == "spearman" else stats.pearsonr
    out: dict = {}
    for i in range(window, len(df) + 1):
        w = df.iloc[i - window:i]
        if w["f"].nunique() < 2 or w["r"].nunique() < 2:
            continue
        out[df.index[i - 1]] = corr(w["f"], w["r"])[0]
    return pd.Series(out, dtype=float)


def ir_and_tstat(ic_series: pd.Series) -> dict:
    """Compute mean IC, IR, t-stat from a rolling IC series."""
    ic = ic_series.dropna()
    if len(ic) < 10:
        return {
            "mean_ic": np.nan, "ir": np.nan, "t_stat": np.nan, "n": len(ic)
        }
    mean_ic = float(ic.mean())
    sd = float(ic.std())
    if sd == 0 or np.isnan(sd):
        return {
            "mean_ic": mean_ic, "ir": np.nan, "t_stat": np.nan, "n": len(ic)
        }
    ir = mean_ic / sd
    t_stat = ir * np.sqrt(len(ic))
    return {"mean_ic": mean_ic, "ir": ir, "t_stat": t_stat, "n": len(ic)}


# ---------------------------------------------------------------------------
# Cross-section Rank-IC
# ---------------------------------------------------------------------------

def cross_section_ic(
    factor_panel: pd.DataFrame,
    ret_panel: pd.DataFrame,
    horizon: int = 5,
) -> pd.Series:
    """Per-date cross-sectional Rank-IC.

    Parameters
    ----------
    factor_panel : pd.DataFrame
        index=date, columns=id, values=factor score at that date.
    ret_panel : pd.DataFrame
        index=date, columns=id, values=forward return for the same horizon.
    horizon : int
        Carried in only to make the caller's intent explicit; the actual
        alignment is by index.

    Returns
    -------
    pd.Series indexed by date with the Spearman Rank-IC of the cross section.
    """
    out: dict = {}
    for d in factor_panel.index:
        if d not in ret_panel.index:
            continue
        f = factor_panel.loc[d].dropna()
        r = ret_panel.loc[d].reindex(f.index).dropna()
        common = f.index.intersection(r.index)
        if len(common) < 10:
            continue
        out[d] = stats.spearmanr(f[common], r[common])[0]
    return pd.Series(out, dtype=float)


# ---------------------------------------------------------------------------
# IC decay
# ---------------------------------------------------------------------------

def ic_decay(
    factor: pd.Series,
    close: pd.Series,
    horizons: list[int],
) -> dict:
    """Compute pooled IC at each holding horizon — diagnoses signal half-life.

    Returns dict {horizon: ic}.
    """
    res: dict[int, float] = {}
    for h in horizons:
        fr = forward_returns(close, h)
        res[h] = timeseries_ic(factor, fr)["ic"]
    return res
