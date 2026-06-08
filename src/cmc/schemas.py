"""Pydantic contracts for CMC responses.

WARNING: CMC's v3 endpoints (especially fear-and-greed) are in beta and field
names may differ from documentation. These are initial/expected shapes.
TODO(M0): after running scripts/00_smoke_test.py, open data/raw/_samples/*.json
and correct any field name mismatches found here.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel


class FearGreedPoint(BaseModel):
    """One row of /v3/fear-and-greed/historical."""
    timestamp: str
    value: float
    value_classification: Optional[str] = None


class OHLCVQuote(BaseModel):
    """One daily candle (quote.USD.*)."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    market_cap: Optional[float] = None


class ListingRow(BaseModel):
    """One coin in /v1/cryptocurrency/listings/historical (flattened)."""
    id: int
    name: str
    symbol: str
    cmc_rank: Optional[int] = None
    # flattened from quote.USD.*
    price: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None


class MapEntry(BaseModel):
    """One coin in /v1/cryptocurrency/map."""
    id: int
    name: str
    symbol: str
    first_historical_data: Optional[str] = None
    last_historical_data: Optional[str] = None
    is_active: Optional[int] = None
