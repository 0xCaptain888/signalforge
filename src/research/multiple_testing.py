"""Multiple-testing corrections and selection-bias-aware Sharpe.

When N factors are screened simultaneously, the chance that at least one
appears "significant" by luck grows quickly with N. Two complementary
defences are implemented here:

- `bh_fdr` — Benjamini–Hochberg False Discovery Rate at level q. Controls
  the expected fraction of false positives among rejected nulls.
- `deflated_sharpe` — López de Prado's Deflated Sharpe Ratio. Shrinks the
  realised Sharpe given the number of strategy trials, the sample length,
  and the higher moments of the return distribution. Returns the
  PROBABILITY that the true Sharpe exceeds the benchmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def bh_fdr(pvalues: list[float], q: float = 0.10) -> pd.DataFrame:
    """Benjamini–Hochberg FDR adjustment.

    Parameters
    ----------
    pvalues : list[float]
        Per-factor p-values (NaNs allowed; they are excluded from the
        adjustment and reported as not significant).
    q : float
        Target FDR level.

    Returns
    -------
    pd.DataFrame columns [p, p_adj, significant]. One row per input p-value,
    preserving order.
    """
    p = np.array(pvalues, dtype=float)
    mask = ~np.isnan(p)
    reject = np.full(len(p), False)
    p_adj = np.full(len(p), np.nan)
    if mask.sum() > 0:
        rej, padj, _, _ = multipletests(p[mask], alpha=q, method="fdr_bh")
        reject[mask] = rej
        p_adj[mask] = padj
    return pd.DataFrame({"p": p, "p_adj": p_adj, "significant": reject})


def deflated_sharpe(
    returns: pd.Series,
    n_trials: int,
    sr_benchmark: float = 0.0,
) -> dict:
    """Deflated Sharpe Ratio (López de Prado, 2014).

    The DSR is the probability that the realised Sharpe is statistically
    distinguishable from the EXPECTED MAXIMUM Sharpe under N independent
    trials of a noise process — i.e., it accounts for data-snooping bias.

    Parameters
    ----------
    returns : pd.Series
        Strategy daily returns.
    n_trials : int
        Total number of strategy configurations attempted (including the
        winning one). The wider the search, the heavier the deflation.
    sr_benchmark : float
        Benchmark Sharpe to test against (default 0).

    Returns
    -------
    dict with keys
        sharpe_daily, sharpe_annual, deflated_sharpe_prob, n_trials, n_obs
    """
    r = returns.dropna()
    n = len(r)
    if n < 30:
        return {
            "sharpe_daily": np.nan, "sharpe_annual": np.nan,
            "deflated_sharpe_prob": np.nan, "n_trials": n_trials, "n_obs": n,
        }

    sr = r.mean() / r.std() if r.std() > 0 else 0.0
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))  # non-excess

    # Expected max Sharpe over n_trials i.i.d. trials (Bailey & López de
    # Prado closed-form). emc = Euler–Mascheroni constant.
    emc = 0.5772156649
    n_eff = max(n_trials, 2)
    z = stats.norm.ppf(1 - 1.0 / n_eff)
    z2 = stats.norm.ppf(1 - 1.0 / n_eff * np.e ** -1)
    sr_expected_max = z * (1 - emc) + z2 * emc

    # Standard error of the (non-Gaussian) Sharpe.
    sr_std = np.sqrt(
        max((1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / (n - 1), 1e-12)
    )

    dsr = (
        float(stats.norm.cdf(
            (sr - sr_benchmark - sr_expected_max * sr_std) / sr_std
        ))
        if sr_std > 0
        else np.nan
    )

    return {
        "sharpe_daily": float(sr),
        "sharpe_annual": float(sr * np.sqrt(365)),
        "deflated_sharpe_prob": dsr,
        "n_trials": int(n_trials),
        "n_obs": int(n),
    }
