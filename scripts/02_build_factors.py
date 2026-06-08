"""Assemble all factor panels into parquet files under data/processed/.

Reads the parquet outputs from `scripts/01_pull_data.py`:
    fear_greed.parquet         (required)
    global_metrics.parquet     (optional on Basic plan — gracefully skipped)
    ohlcv.parquet              (optional on Basic plan — gracefully skipped)
    listings_snapshots.parquet (optional, requires listings/historical access)

Outputs:
    factors_timeseries.parquet
    regime.parquet
    factors_cross_section.parquet  (if listings_snapshots present)

This script is intentionally tolerant of missing inputs: on the Basic CMC
plan only `fear_greed.parquet` is guaranteed, so we emit just F&G factors
and skip everything else with a clear message. Once a paid tier (or fallback
price source) supplies the rest, the same script produces the full set.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import constants as C
from config.settings import settings
from src.factors.cross_section import build_cross_section_factors
from src.factors.regime import label_regime
from src.factors.timeseries import (
    build_dominance_factors,
    build_fg_dominance_cross,
    build_fg_factors,
)

PROC = Path(settings.processed_dir)


def _safe_read(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_parquet(path)


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)

    fg = _safe_read(PROC / "fear_greed.parquet")
    gm = _safe_read(PROC / "global_metrics.parquet")
    ohlcv = _safe_read(PROC / "ohlcv.parquet")
    snaps = _safe_read(PROC / "listings_snapshots.parquet")

    if fg is None:
        raise SystemExit(
            "fear_greed.parquet missing. Run scripts/01_pull_data.py first "
            "(the F&G endpoint is the only data dependency that works on the "
            "Basic CMC plan; see README M0 findings)."
        )

    # ------------------------------------------------------------------ TS
    fg_f = build_fg_factors(fg)
    if gm is not None:
        dom_f = build_dominance_factors(gm)
        cross = build_fg_dominance_cross(fg_f, dom_f)
        ts = (
            fg_f.merge(dom_f, on="date", how="outer")
            .merge(cross, on="date", how="outer")
            .sort_values("date")
        )
    else:
        ts = fg_f.sort_values("date")
        print(
            "global_metrics.parquet missing — emitting F&G-only "
            "time-series factor panel (no dominance / cross factors)."
        )

    ts.to_parquet(PROC / "factors_timeseries.parquet", index=False)
    print(f"time-series factors: shape={ts.shape}")

    # ------------------------------------------------------------------ Regime
    if ohlcv is not None:
        btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"]
        fg_s = fg.set_index("date")["cmc_fg"]
        reg = label_regime(btc, fg_s)
        reg.to_parquet(PROC / "regime.parquet", index=False)
        print(f"regime label distribution:\n{reg['regime'].value_counts()}")
    else:
        print(
            "ohlcv.parquet missing — skipping regime labelling "
            "(needs BTC daily close)."
        )

    # ------------------------------------------------------------------ XS
    if (
        C.LISTINGS_HISTORICAL_AVAILABLE is not False
        and snaps is not None
        and ohlcv is not None
    ):
        xs = build_cross_section_factors(snaps, ohlcv)
        xs.to_parquet(PROC / "factors_cross_section.parquet", index=False)
        print(f"cross-section factors: shape={xs.shape}")
    else:
        print(
            "skipping cross-section factors "
            "(listings/historical or ohlcv not available)."
        )


if __name__ == "__main__":
    main()
