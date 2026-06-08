"""Smoke test: probe 7 CMC endpoints, dump samples, report plan & data availability.

This is the go/no-go checkpoint. After running, back-fill:
- config/constants.py  (CMC_PLAN, FG_HISTORY_MAX_DAYS, OHLCV_EARLIEST,
                        LISTINGS_HISTORICAL_AVAILABLE)
- src/cmc/schemas.py   (correct field names against data/raw/_samples/*.json)
"""
import json
from datetime import datetime, timedelta, timezone

from src.cmc.endpoints import Endpoints


def main() -> None:
    ep = Endpoints()
    today = datetime.now(timezone.utc).date()
    d30 = (today - timedelta(days=30)).isoformat()
    d1 = (today - timedelta(days=1)).isoformat()

    print("=" * 60)
    print("SignalForge smoke test (Stage 2 / M0)")
    print("=" * 60)

    # ---------- A. key/info (plan + credits) ----------
    try:
        info = ep.key_info(save_sample="key_info")
        plan = (info.get("data") or {}).get("plan") or {}
        usage = (info.get("data") or {}).get("usage") or {}
        print("[A] key/info OK")
        print(f"    plan name        : {plan.get('name')}")
        print(f"    credits/month    : {plan.get('credit_limit_monthly')}")
        print(f"    credits/min      : {plan.get('rate_limit_minute')}")
        print(f"    usage (snapshot) : {json.dumps(usage)[:300]}")
    except Exception as e:
        print(f"[A] key/info FAIL: {e}")

    # ---------- B. map ----------
    try:
        m = ep.crypto_map(limit=10, save_sample="crypto_map")
        sample = (m.get("data") or [])[:1]
        keys = list(sample[0].keys()) if sample else []
        print(f"[B] crypto/map OK, sample fields: {keys}")
    except Exception as e:
        print(f"[B] crypto/map FAIL: {e}")

    # ---------- C. listings/historical ----------
    try:
        lh = ep.listings_historical(
            date=d30, limit=10, save_sample="listings_historical"
        )
        n = len(lh.get("data") or [])
        print(f"[C] listings/historical OK, rows: {n}")
        print(f"    => LISTINGS_HISTORICAL_AVAILABLE = True")
    except Exception as e:
        print(f"[C] listings/historical FAIL (plan may not support): {e}")
        print(f"    => LISTINGS_HISTORICAL_AVAILABLE = False "
              f"(fall back to pure time-series factors)")

    # ---------- D. ohlcv (BTC id=1) ----------
    try:
        o = ep.ohlcv_historical(
            ids="1", time_start=d30, time_end=d1,
            save_sample="ohlcv_historical",
        )
        data = o.get("data") or {}
        # API may shape as {quotes:[...]} or {id:{quotes:[...]}}
        if isinstance(data, dict) and "quotes" in data:
            quotes = data.get("quotes") or []
        elif isinstance(data, dict):
            first = next(iter(data.values()), {})
            if isinstance(first, list):
                first = first[0] if first else {}
            quotes = (first or {}).get("quotes") or []
        else:
            quotes = []
        print(f"[D] ohlcv/historical OK, points: {len(quotes)}")
    except Exception as e:
        print(f"[D] ohlcv/historical FAIL: {e}")

    # ---------- E. ★ CMC proprietary F&G ----------
    try:
        fg = ep.fear_greed_historical(
            start=1, limit=500, save_sample="fear_greed_historical"
        )
        data = fg.get("data") or []
        if data:
            ts = [d.get("timestamp") for d in data if d.get("timestamp")]
            print("[E] fear-and-greed/historical OK  *** core alpha ***")
            print(f"    records          : {len(data)}")
            print(f"    earliest         : {min(ts) if ts else 'n/a'}")
            print(f"    latest           : {max(ts) if ts else 'n/a'}")
            print(f"    sample row keys  : {list(data[0].keys())}")
            print(f"    => FG_HISTORY_MAX_DAYS >= {len(data)} "
                  f"(paginate via start= to fetch more)")
        else:
            print("[E] F&G returned empty payload")
    except Exception as e:
        print(f"[E] fear-and-greed FAIL: {e}")

    # ---------- F. global metrics historical ----------
    try:
        gm = ep.global_metrics_historical(
            time_start=d30, time_end=d1,
            save_sample="global_metrics_historical",
        )
        quotes = (gm.get("data") or {}).get("quotes") or []
        print(f"[F] global-metrics/historical OK, points: {len(quotes)}")
    except Exception as e:
        print(f"[F] global-metrics/historical FAIL: {e}")

    # ---------- G. global metrics latest ----------
    try:
        gl = ep.global_metrics_latest(save_sample="global_metrics_latest")
        top_keys = list((gl.get("data") or {}).keys())
        print(f"[G] global-metrics/latest OK, top-level keys: {top_keys}")
        print("    check for 'altcoin_season' / 'market_cycle' fields "
              "-- if absent, build proxy in §4.2")
    except Exception as e:
        print(f"[G] global-metrics/latest FAIL: {e}")

    print("=" * 60)
    print(f"Cumulative credit consumption: {ep.c.total_credits}")
    print("Samples dumped to data/raw/_samples/")
    print("Next step: back-fill schemas.py field names + constants.py M0 values")
    print("=" * 60)
    ep.c.close()


if __name__ == "__main__":
    main()
