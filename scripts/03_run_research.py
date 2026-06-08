"""End-to-end research pass: IC / IR / t-stat / decay / regime / FDR.

Inputs (must exist under data/processed/):
    factors_timeseries.parquet  — produced by scripts/02_build_factors.py
    ohlcv.parquet               — needed for BTC forward returns
    regime.parquet              — needed for regime-layered attribution
    factors_cross_section.parquet (optional) — adds XS Rank-IC if present

Outputs:
    outputs/research_results.json
    outputs/figures/ic_decay.png
    outputs/figures/regime_ic_heatmap.png

If the Basic-plan blocker is still in effect (no ohlcv), the script exits
with a clear message rather than producing meaningless numbers — the
research layer needs forward returns to score factors.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import constants as C  # noqa: E402
from config.settings import settings  # noqa: E402
from src.research.ic import (  # noqa: E402
    forward_returns,
    ic_decay,
    ir_and_tstat,
    rolling_ic_series,
    timeseries_ic,
)
from src.research.multiple_testing import bh_fdr  # noqa: E402
from src.research.regime_attrib import (  # noqa: E402
    regime_ic_matrix,
    regime_layered_ic,
)

np.random.seed(C.SEED)

PROC = Path(settings.processed_dir)
OUT = Path(settings.outputs_dir)
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


def _need(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(
            f"required input missing: {path}\n"
            "Run scripts/01_pull_data.py + scripts/02_build_factors.py first."
        )
    return pd.read_parquet(path)


def main() -> None:
    ts = _need(PROC / "factors_timeseries.parquet").set_index("date")
    ohlcv = _need(PROC / "ohlcv.parquet")
    regime = _need(PROC / "regime.parquet").set_index("date")["regime"]
    btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"].sort_index()

    # 5-day forward return is the primary scoring horizon; IC decay sweeps
    # all of HOLDING_PERIODS for diagnostic plots.
    fwd5 = forward_returns(btc, 5)
    factor_cols = [c for c in ts.columns if c != "value_classification"]

    results: dict = {"factors": {}, "n_trials": 0, "horizon_primary": 5}
    pvals: list[float] = []
    pnames: list[str] = []

    for col in factor_cols:
        f = ts[col].reindex(btc.index)
        base = timeseries_ic(f, fwd5)
        ic_ser = rolling_ic_series(f, fwd5, window=60)
        stat = ir_and_tstat(ic_ser)
        decay = ic_decay(f, btc, C.HOLDING_PERIODS)
        lay = regime_layered_ic(f, fwd5, regime)

        results["factors"][col] = {
            "ic_overall": base["ic"],
            "p_overall": base["p"],
            "n": base["n"],
            "mean_ic_rolling": stat["mean_ic"],
            "ir": stat["ir"],
            "t_stat": stat["t_stat"],
            "ic_decay": {str(k): v for k, v in decay.items()},
            "regime_ic": lay.to_dict(orient="records"),
        }
        if not np.isnan(base["p"]):
            pvals.append(base["p"])
            pnames.append(col)
        # Trial budget: 1 pooled IC + one per non-empty regime bucket.
        results["n_trials"] += 1 + int((~lay["ic"].isna()).sum())

    # ------------------------------------------------------------ FDR
    fdr = bh_fdr(pvals, q=C.FDR_Q)
    for name, sig, padj in zip(pnames, fdr["significant"], fdr["p_adj"]):
        results["factors"][name]["fdr_significant"] = bool(sig)
        results["factors"][name]["p_adj"] = (
            None if np.isnan(padj) else float(padj)
        )

    # ------------------------------------------------------------ Figure 1: IC decay
    plt.figure(figsize=(8, 5))
    for col in factor_cols[:8]:
        d = results["factors"][col]["ic_decay"]
        xs = list(map(int, d.keys()))
        ys = list(d.values())
        plt.plot(xs, ys, marker="o", label=col)
    plt.axhline(0, color="gray", lw=0.5)
    plt.xlabel("Holding period (days)")
    plt.ylabel("Spearman IC")
    plt.title("Factor IC decay — CMC proprietary signals")
    plt.legend(fontsize=7, loc="best")
    plt.tight_layout()
    plt.savefig(FIG / "ic_decay.png", dpi=130)
    plt.close()

    # ------------------------------------------------------------ Figure 2: regime IC heatmap
    factors_dict = {c: ts[c].reindex(btc.index) for c in factor_cols}
    mat = regime_ic_matrix(factors_dict, fwd5, regime)
    plt.figure(figsize=(10, 6))
    plt.imshow(mat.values, aspect="auto", cmap="RdYlGn", vmin=-0.15, vmax=0.15)
    plt.colorbar(label="Rank-IC")
    plt.xticks(
        range(len(mat.columns)), mat.columns,
        rotation=45, ha="right", fontsize=7,
    )
    plt.yticks(range(len(mat.index)), mat.index, fontsize=7)
    plt.title("Factor × Regime IC heatmap — CMC proprietary signals")
    plt.tight_layout()
    plt.savefig(FIG / "regime_ic_heatmap.png", dpi=130)
    plt.close()

    # ------------------------------------------------------------ Persist
    (OUT / "research_results.json").write_text(
        json.dumps(results, indent=2, default=float)
    )
    sig = [
        k for k, v in results["factors"].items() if v.get("fdr_significant")
    ]
    print(f"research done — FDR-significant factors: {sig}")


if __name__ == "__main__":
    main()
