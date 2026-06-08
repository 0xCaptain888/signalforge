"""Seven core CMC endpoints. Returns raw dict; parsing is delegated to schemas.py.

A. /v1/key/info                              (0 credit, plan & usage)
B. /v1/cryptocurrency/map                    (0 credit, id <-> symbol + first/last_historical_data)
C. /v1/cryptocurrency/listings/historical    (point-in-time snapshots, survivorship-bias-free)
D. /v2/cryptocurrency/ohlcv/historical       (daily OHLCV per id)
E. /v3/fear-and-greed/historical             ★ CMC proprietary F&G (DISTINCT from Alternative.me)
F. /v1/global-metrics/quotes/historical      (BTC dominance / total market cap series)
G. /v1/global-metrics/quotes/latest          (current snapshot - probe for altseason/cycle field)
"""
from __future__ import annotations

from src.cmc.client import CMCClient


class Endpoints:
    def __init__(self, client: CMCClient | None = None):
        self.c = client or CMCClient()

    # A
    def key_info(self, save_sample: str | None = None) -> dict:
        return self.c.get("/v1/key/info", save_sample=save_sample)

    # B
    def crypto_map(
        self,
        listing_status: str = "active,inactive,untracked",
        limit: int = 5000,
        save_sample: str | None = None,
    ) -> dict:
        return self.c.get(
            "/v1/cryptocurrency/map",
            {"listing_status": listing_status, "limit": limit},
            save_sample=save_sample,
        )

    # C
    def listings_historical(
        self,
        date: str,
        limit: int = 100,
        convert: str = "USD",
        save_sample: str | None = None,
    ) -> dict:
        return self.c.get(
            "/v1/cryptocurrency/listings/historical",
            {
                "date": date,
                "limit": limit,
                "sort": "market_cap",
                "convert": convert,
            },
            save_sample=save_sample,
        )

    # D
    def ohlcv_historical(
        self,
        ids: str,
        time_start: str,
        time_end: str,
        interval: str = "daily",
        convert: str = "USD",
        save_sample: str | None = None,
    ) -> dict:
        return self.c.get(
            "/v2/cryptocurrency/ohlcv/historical",
            {
                "id": ids,
                "time_start": time_start,
                "time_end": time_end,
                "interval": interval,
                "convert": convert,
            },
            save_sample=save_sample,
        )

    # E  ★ CMC proprietary F&G
    def fear_greed_historical(
        self,
        start: int = 1,
        limit: int = 500,
        save_sample: str | None = None,
    ) -> dict:
        return self.c.get(
            "/v3/fear-and-greed/historical",
            {"start": start, "limit": limit},
            save_sample=save_sample,
        )

    # F
    def global_metrics_historical(
        self,
        time_start: str,
        time_end: str,
        interval: str = "1d",
        convert: str = "USD",
        save_sample: str | None = None,
    ) -> dict:
        return self.c.get(
            "/v1/global-metrics/quotes/historical",
            {
                "time_start": time_start,
                "time_end": time_end,
                "interval": interval,
                "convert": convert,
            },
            save_sample=save_sample,
        )

    # G
    def global_metrics_latest(
        self, convert: str = "USD", save_sample: str | None = None
    ) -> dict:
        return self.c.get(
            "/v1/global-metrics/quotes/latest",
            {"convert": convert},
            save_sample=save_sample,
        )
