"""Regime-layered IC attribution — the differentiated insight of this project.

Pooled IC tells you a factor "works on average". Regime-layered IC tells you
WHEN it works — for instance: is `fg_extreme_rev` driven entirely by the
BEAR_FEAR cell, while doing nothing or hurting in BULL_GREED?

`regime_layered_ic` slices the factor / forward-return pair by the regime
label at the same date, computes within-bucket Spearman IC, and reports a
table sortable by IC. The per-cell t-stat uses the standard
`r * sqrt((n-2)/(1-r^2))` approximation, which is sufficient for the
relative ranking that the LLM later narrates.

`regime_ic_matrix` runs that pipeline for many factors at once and reshapes
into a (factor x regime) matrix suitable for a heatmap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def regime_layered_ic(
    factor: pd.Series,
    fwd_ret: pd.Series,
    regime: pd.Series,
    method: str = "spearman",
) -> pd.DataFrame:
    """Compute IC within each regime bucket.

    Parameters
    ----------
    factor, fwd_ret, regime : pd.Series
        All indexed by date. They are inner-joined; missing-anywhere rows
        are dropped.

    Returns
    -------
    pd.DataFrame [regime, ic, t_stat, p, n] sorted by IC descending. NaN
    rows are kept (for buckets too thin to estimate) and pushed to the end.
    """
    df = pd.concat(
        [factor, fwd_ret, regime], axis=1, keys=["f", "r", "reg"]
    ).dropna()

    corr = stats.spearmanr if method == "spearman" else stats.pearsonr

    rows: list[dict] = []
    for reg, g in df.groupby("reg"):
        if len(g) < 20 or g["f"].nunique() < 2 or g["r"].nunique() < 2:
            rows.append(
                {"regime": reg, "ic": np.nan, "t_stat": np.nan,
                 "p": np.nan, "n": len(g)}
            )
            continue
        ic, p = corr(g["f"], g["r"])
        # Approximate t-stat for a Spearman correlation under the i.i.d. null.
        t = ic * np.sqrt((len(g) - 2) / max(1 - ic ** 2, 1e-9))
        rows.append(
            {"regime": reg, "ic": float(ic), "t_stat": float(t),
             "p": float(p), "n": len(g)}
        )

    return (
        pd.DataFrame(rows)
        .sort_values("ic", ascending=False, na_position="last")
        .reset_index(drop=True)
    )


def regime_ic_matrix(
    factors: dict[str, pd.Series],
    fwd_ret: pd.Series,
    regime: pd.Series,
) -> pd.DataFrame:
    """Stack `regime_layered_ic` for many factors into a (factor x regime) IC
    matrix, suitable for a heatmap (rows = factor, cols = regime)."""
    rows: dict[str, pd.Series] = {}
    for fname, fser in factors.items():
        lay = regime_layered_ic(fser, fwd_ret, regime).set_index("regime")["ic"]
        rows[fname] = lay
    mat = pd.DataFrame(rows).T  # rows = factor, cols = regime
    # Stable, readable column ordering: cycle through the canonical 3x3 grid.
    canonical = [
        f"{d}_{s}"
        for d in ("BULL", "CHOP", "BEAR")
        for s in ("FEAR", "NEUTRAL", "GREED")
    ]
    present = [c for c in canonical if c in mat.columns]
    extras = [c for c in mat.columns if c not in present]
    return mat[present + extras]
