"""Pydantic contracts for CMC responses.

Field shapes verified against data/raw/_samples/*.json on 2026-06-08
(CMC Basic plan, key 4466eccb…). Notes baked in below.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FearGreedPoint(BaseModel):
    """One row of /v3/fear-and-greed/historical.

    Verified sample (newest-first ordering):
        {"timestamp": "1780790400", "value": 15, "value_classification": "Extreme fear"}
    - timestamp is UNIX seconds AS A STRING (not ISO-8601).
    - value is an integer 0-100 (pydantic coerces to float for math convenience).
    """
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    value: float
    value_classification: Optional[str] = None


class OHLCVQuote(BaseModel):
    """One daily candle from /v2/cryptocurrency/ohlcv/historical
    (under data.<id>.quotes[].quote.USD on Standard+ plans).

    NOT verified on Basic plan (endpoint returns 403). Shape preserved from
    CMC docs; re-verify on first paid-tier sample.
    """
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    market_cap: Optional[float] = None


class ListingRow(BaseModel):
    """One coin from /v1/cryptocurrency/listings/historical (flattened).

    NOT verified on Basic plan (endpoint returns 403).
    """
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    symbol: str
    cmc_rank: Optional[int] = None
    price: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None


class MapEntry(BaseModel):
    """One coin from /v1/cryptocurrency/map.

    Verified sample:
        {"id": 1, "name": "Bitcoin", "symbol": "BTC", "slug": "bitcoin",
         "rank": 1, "is_active": 1,
         "first_historical_data": "2010-07-13T00:05:00.000Z",
         "last_historical_data": "2026-06-08T00:10:00.000Z",
         "platform": null}
    """
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    symbol: str
    slug: Optional[str] = None
    rank: Optional[int] = None
    is_active: Optional[int] = None
    first_historical_data: Optional[str] = None
    last_historical_data: Optional[str] = None
