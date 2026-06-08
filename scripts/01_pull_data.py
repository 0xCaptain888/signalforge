"""Stage 2.9 / 2.10 — full data pull with degraded-path tolerance.

Pulls ALL historical data the configured CMC plan exposes and stores it as
parquet under data/processed/. Cache-hits on data/raw/*.json never re-hit the
API, so re-running this script costs 0 credits when nothing changed.

M0 reality (Basic plan, key 4466eccb…):
    [A] key/info               OK
    [B] crypto/map             OK
    [C] listings/historical    403  -> skipped
    [D] ohlcv/historical       403  -> falls back to Binance public klines
    [E] fear-and-greed/hist    OK   *** the proprietary alpha source ***
    [F] global-metrics/hist    403  -> falls back to "latest" snapshot only
    [G] global-metrics/latest  OK

Binance fallback (D only): public REST /api/v3/klines, no API key required.
We only use BTCUSDT / ETHUSDT etc. to power BTC-trend regime + forward
returns for IC testing of the CMC F&G factors. Honestly disclosed in the
report — CMC F&G is still the unique alpha source, prices are infrastructure.
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

from src.cmc.endpoints import Endpoints
from config.settings import settings
from config import constants as C

PROC = Path(settings.processed_dir)
PROC.mkdir(parents=True, exist_ok=True)


# ---------- CMC-native pulls ----------


def pull_fear_greed(ep: Endpoints) -> pd.DataFrame:
    """Paginate /v3/fear-and-greed/historical (500 rows / page)."""
    rows, start = [], 1
    while True:
        resp = ep.fear_greed_historical(start=start, limit=500)
        data = resp.get("data", []) or []
        if not data:
            break
        rows.extend(data)
        if len(data) < 500:
            break
        start += 500
    df = pd.DataFrame(rows)
    # CMC returns timestamp as UNIX-seconds-as-string. Coerce.
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(None).dt.normalize()
    df = df.rename(columns={"value": "cmc_fg"}).sort_values("date")
    df = df[["date", "cmc_fg", "value_classification"]].drop_duplicates("date")
    df.to_parquet(PROC / "fear_greed.parquet", index=False)
    print(f"F&G: {len(df)} rows, {df['date'].min().date()} ~ {df['date'].max().date()}")
    return df


def pull_global_metrics_latest_only(ep: Endpoints) -> pd.DataFrame:
    """Basic plan cannot serve historical global metrics. Fall back to a
    one-row snapshot of /v1/global-metrics/quotes/latest so downstream code
    has a deterministic placeholder. This is enough for build_dominance_factors
    to skip gracefully (it needs history) and for live-mode reporting."""
    resp = ep.global_metrics_latest()
    d = resp.get("data", {}) or {}
    usd = d.get("quote", {}).get("USD", {})
    row = {
        "date": pd.Timestamp(d.get("last_updated") or datetime.now(timezone.utc)).tz_localize(None).normalize(),
        "btc_dominance": d.get("btc_dominance"),
        "eth_dominance": d.get("eth_dominance"),
        "total_market_cap": usd.get("total_market_cap"),
        "total_volume_24h": usd.get("total_volume_24h"),
    }
    df = pd.DataFrame([row])
    df.to_parquet(PROC / "global_metrics_latest.parquet", index=False)
    print(f"global_metrics_latest: 1 snapshot row (historical 403 on Basic)")
    return df


def pull_map(ep: Endpoints) -> pd.DataFrame:
    resp = ep.crypto_map()
    df = pd.DataFrame(resp.get("data", []))
    keep = [c for c in ["id", "name", "symbol", "slug", "first_historical_data",
                        "last_historical_data", "is_active", "rank"] if c in df.columns]
    df = df[keep]
    df.to_parquet(PROC / "crypto_map.parquet", index=False)
    print(f"map: {len(df)} coins")
    return df


# ---------- Binance public-API fallback for OHLCV ----------

_BINANCE = "https://api.binance.com/api/v3/klines"

# CMC id -> Binance symbol (kept small; expand as needed for cross-section work).
_BINANCE_SYMBOLS = {
    1: "BTCUSDT", 1027: "ETHUSDT", 1839: "BNBUSDT", 5426: "SOLUSDT",
    52: "XRPUSDT", 2010: "ADAUSDT", 74: "DOGEUSDT", 5805: "AVAXUSDT",
    1958: "TRXUSDT", 6636: "DOTUSDT", 1975: "LINKUSDT",
    1831: "BCHUSDT", 1376: "NEOUSDT", 512: "STXUSDT",
    7083: "UNIUSDT", 11419: "TONUSDT", 3794: "ATOMUSDT",
    2: "LTCUSDT",
}


def _binance_klines(symbol: str, start_ms: int, end_ms: int) -> list[list]:
    """Pull 1d klines in batches of 1000."""
    out, cur = [], start_ms
    with httpx.Client(timeout=30.0) as cli:
        while cur < end_ms:
            r = cli.get(_BINANCE, params={
                "symbol": symbol, "interval": "1d",
                "startTime": cur, "endTime": end_ms, "limit": 1000,
            })
            if r.status_code != 200:
                # symbol may not exist on Binance; bubble up empty
                return out
            batch = r.json()
            if not batch:
                break
            out.extend(batch)
            # Advance by last close+1ms
            last_close = batch[-1][6]
            if last_close <= cur:
                break
            cur = last_close + 1
            time.sleep(0.10)  # be polite to public endpoint
    return out


def pull_ohlcv_via_binance(ids: list[int], start_date: str, end_date: str) -> pd.DataFrame:
    """Fallback OHLCV when CMC ohlcv/historical is 403."""
    start_ms = int(pd.Timestamp(start_date).timestamp() * 1000)
    end_ms = int(pd.Timestamp(end_date).timestamp() * 1000) + 86_400_000
    rows = []
    for cid in ids:
        sym = _BINANCE_SYMBOLS.get(cid)
        if not sym:
            continue
        klines = _binance_klines(sym, start_ms, end_ms)
        for k in klines:
            rows.append({
                "id": cid,
                "date": pd.to_datetime(k[0], unit="ms").normalize(),
                "open": float(k[1]),
                "high": float(k[2]),
                "low":  float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "market_cap": None,   # unknown without CMC; fine for IC tests
            })
        print(f"  binance {sym}: {len(klines)} bars")
    df = pd.DataFrame(rows).sort_values(["id", "date"])
    df.to_parquet(PROC / "ohlcv.parquet", index=False)
    print(f"ohlcv (binance fallback): {len(df)} rows, {df['id'].nunique()} coins")
    return df


# ---------- CMC-native OHLCV (paid plan; not used on Basic) ----------


def pull_ohlcv_via_cmc(ep: Endpoints, ids: list[int],
                       start_date: str, end_date: str) -> pd.DataFrame:
    """Batched OHLCV via CMC. Only runs on Standard+ plans."""
    all_rows = []
    for i in range(0, len(ids), 5):
        batch = ",".join(str(x) for x in ids[i:i + 5])
        resp = ep.ohlcv_historical(ids=batch, time_start=start_date, time_end=end_date)
        data = resp.get("data", {}) or {}
        items = data.values() if isinstance(data, dict) and "quotes" not in data else [data]
        for item in items:
            cid = item.get("id")
            for q in item.get("quotes", []) or []:
                usd = q.get("quote", {}).get("USD", {})
                all_rows.append({
                    "id": cid,
                    "date": pd.to_datetime(q.get("timestamp")).tz_localize(None).normalize(),
                    "open": usd.get("open"),
                    "high": usd.get("high"),
                    "low":  usd.get("low"),
                    "close": usd.get("close"),
                    "volume": usd.get("volume"),
                    "market_cap": usd.get("market_cap"),
                })
    df = pd.DataFrame(all_rows).sort_values(["id", "date"])
    df.to_parquet(PROC / "ohlcv.parquet", index=False)
    print(f"ohlcv (cmc native): {len(df)} rows, {df['id'].nunique()} coins")
    return df


# ---------- Driver ----------


def main():
    ep = Endpoints()
    today = datetime.utcnow().date()
    end = (today - timedelta(days=1)).isoformat()
    start = "2018-01-01"

    print("=" * 60)
    print(f"SignalForge data pull — plan={C.CMC_PLAN}")
    print("=" * 60)

    # 1) F&G — the proprietary alpha source. ALWAYS pull (Basic plan grants).
    fg = pull_fear_greed(ep)

    # 2) crypto/map. ALWAYS pull (Basic plan grants).
    cmap = pull_map(ep)

    # 3) Global metrics. Historical 403 on Basic; degrade to latest snapshot.
    if C.GLOBAL_METRICS_HISTORICAL_AVAILABLE:
        # Standard+ path — not exercised on Basic.
        resp = ep.global_metrics_historical(time_start=start, time_end=end, interval="1d")
        quotes = resp.get("data", {}).get("quotes", []) or []
        rows = []
        for q in quotes:
            usd = q.get("quote", {}).get("USD", {})
            rows.append({
                "date": pd.to_datetime(q.get("timestamp")).tz_localize(None).normalize(),
                "btc_dominance": q.get("btc_dominance"),
                "eth_dominance": q.get("eth_dominance"),
                "total_market_cap": usd.get("total_market_cap"),
                "total_volume_24h": usd.get("total_volume_24h"),
            })
        gm = pd.DataFrame(rows).sort_values("date")
        gm.to_parquet(PROC / "global_metrics.parquet", index=False)
        print(f"global_metrics (historical): {len(gm)} rows")
    else:
        pull_global_metrics_latest_only(ep)

    # 4) OHLCV. Universe = small curated set with Binance liquidity coverage.
    universe_ids = sorted(_BINANCE_SYMBOLS.keys())[: C.UNIVERSE_TOP_N]
    common_start = str(fg["date"].min().date()) if not fg.empty else start

    if C.OHLCV_EARLIEST:
        pull_ohlcv_via_cmc(ep, universe_ids, common_start, end)
    else:
        print(f"\n[fallback] CMC ohlcv/historical is 403 on Basic. "
              f"Pulling Binance public klines for {len(universe_ids)} symbols "
              f"({common_start} → {end})…")
        pull_ohlcv_via_binance(universe_ids, common_start, end)

    # 5) listings/historical snapshots — 403 on Basic; skip.
    if C.LISTINGS_HISTORICAL_AVAILABLE:
        month_dates = pd.date_range(common_start, end, freq="MS").strftime("%Y-%m-%d").tolist()
        rows = []
        for d in month_dates:
            try:
                resp = ep.listings_historical(date=d, limit=C.UNIVERSE_TOP_N)
                for r in resp.get("data", []) or []:
                    usd = r.get("quote", {}).get("USD", {})
                    rows.append({
                        "date": pd.to_datetime(d).normalize(),
                        "id": r.get("id"), "symbol": r.get("symbol"),
                        "cmc_rank": r.get("cmc_rank"),
                        "price": usd.get("price"), "market_cap": usd.get("market_cap"),
                    })
            except Exception as e:
                print(f"  listings {d} skip: {e}")
        df = pd.DataFrame(rows)
        df.to_parquet(PROC / "listings_snapshots.parquet", index=False)
        print(f"listings snapshots: {len(df)} rows over {len(month_dates)} dates")
    else:
        print("listings/historical skipped (403 on Basic).")

    print("=" * 60)
    print(f"Cumulative CMC credit consumption: {ep.c.total_credits}")
    print(f"Outputs in: {PROC}")
    print("=" * 60)
    ep.c.close()


if __name__ == "__main__":
    main()
