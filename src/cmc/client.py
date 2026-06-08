"""CMC API client: retry + rate limit + cache + raw sample dump.

- Token-bucket rate limiter (RATE_LIMIT_PER_MIN, default 28).
- Exponential-backoff retry on 5xx / 429 / transport errors (tenacity).
- File cache keyed by (path, params) hash; cache-hit avoids re-spending credits.
- Optional sample dump to data/raw/_samples/<tag>.json for schema dev.
- Tracks cumulative credit consumption per session.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type,
)

from config.settings import settings


class _RateLimiter:
    """Simple token bucket: at most N calls per minute."""

    def __init__(self, per_min: int):
        self.interval = 60.0 / max(per_min, 1)
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self._last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last = time.monotonic()


class CMCClient:
    """Thin wrapper around httpx with caching + rate-limiting + sample dump."""

    def __init__(self):
        self.base = settings.cmc_base_url.rstrip("/")
        self.headers = {
            "X-CMC_PRO_API_KEY": settings.cmc_api_key,
            "Accept": "application/json",
        }
        self._client = httpx.Client(
            timeout=settings.request_timeout, headers=self.headers
        )
        self._limiter = _RateLimiter(settings.rate_limit_per_min)
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.total_credits = 0

    # ---------- internal ----------

    def _cache_key(self, path: str, params: dict) -> Path:
        raw = path + json.dumps(params or {}, sort_keys=True)
        h = hashlib.md5(raw.encode()).hexdigest()[:16]
        safe = path.strip("/").replace("/", "_")
        return self.cache_dir / f"{safe}__{h}.json"

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.TransportError)
        ),
        reraise=True,
    )
    def _raw_get(self, path: str, params: dict) -> dict:
        self._limiter.wait()
        r = self._client.get(self.base + path, params=params)
        if r.status_code == 429 or r.status_code >= 500:
            r.raise_for_status()  # triggers retry
        r.raise_for_status()       # 4xx -> raise, no retry
        return r.json()

    # ---------- public ----------

    def get(
        self,
        path: str,
        params: dict | None = None,
        use_cache: bool = True,
        save_sample: str | None = None,
    ) -> dict[str, Any]:
        """GET <path> with rate-limit + retry + file cache.

        If save_sample is provided, also dump pretty-printed (truncated) JSON to
        data/raw/_samples/<save_sample>.json for schema development.
        """
        params = params or {}
        cache_path = self._cache_key(path, params)
        if use_cache and cache_path.exists():
            return json.loads(cache_path.read_text())

        data = self._raw_get(path, params)

        credit = (data.get("status") or {}).get("credit_count", 0) or 0
        self.total_credits += credit

        cache_path.write_text(json.dumps(data, indent=2))

        if save_sample:
            sp = Path(settings.sample_dir)
            sp.mkdir(parents=True, exist_ok=True)
            (sp / f"{save_sample}.json").write_text(
                json.dumps(data, indent=2)[:200000]
            )
        return data

    def close(self) -> None:
        self._client.close()
