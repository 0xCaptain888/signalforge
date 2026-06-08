# SignalForge — MuleRun 可执行开发文档 (Build-Ready)

> 本文件是**可直接执行**的工程文档。MuleRun 应按 §0 的执行协议,从 §2 开始**逐文件创建代码**,每个代码块都是可复制的完整内容(非伪代码)。占位符仅限密钥和 M0 实测后才能确定的字段(已用 `# TODO(M0)` 标注)。
>
> - **项目:** SignalForge — CMC 专有指标因子研究引擎
> - **目标:** BNB Hack Track 2 第一名 $3,000 + CMC 特殊奖 $2,000
> - **LLM:** DeepSeek (`deepseek-chat` / `deepseek-reasoner`)
> - **执行器:** MuleRun AI Agent
> - **Python:** 3.11

---

## 0. MuleRun 执行协议

按顺序执行,**每步跑完"验收"再进下一步**:

1. **§2 脚手架** → 创建所有目录与配置文件。验收: `pip install -e .` 成功。
2. **§3 数据层** → 创建 `src/cmc/*`。验收: `python scripts/00_smoke_test.py` 全 200,样本落盘。**这是 go/no-go**。
3. **§3.9 回填 TODO(M0)** → 用 smoke test 的真实返回,修正 `schemas.py` 字段名 + 填 plan 档位常量。
4. **§4 因子层** → 创建 `src/factors/*` + 单测。验收: `pytest tests/ -v` 全绿。
5. **§5 研究层** → 创建 `src/research/*`。验收: `python scripts/03_run_research.py` 出 json + 图。
6. **§6 策略层** → 创建 `src/strategy/*`。验收: `python scripts/04_backtest.py` 出绩效。
7. **§7 LLM 层** → 创建 `src/llm/*`。验收: `python scripts/05_generate_spec.py` 出 spec json。
8. **§8 输出层** → 报告 + 复现。验收: `python scripts/reproduce.py` 复现一致数字。

**铁律:**
- 任何 CMC 字段解析,必须先看 `data/raw/_samples/` 里的真实 JSON,不凭文档猜。
- 所有随机性 `seed=42`。
- LLM 不算数字。数字全来自 Python。
- 密钥只在 `.env`,永不入库。

---

## 1. 快速开始 (人类/Agent 都适用)

```bash
# 1. 克隆/创建项目后
cp .env.example .env
# 编辑 .env,填入 CMC_API_KEY 和 DEEPSEEK_API_KEY

# 2. 安装
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 3. 冒烟测试 (go/no-go)
python scripts/00_smoke_test.py

# 4. 全流程
python scripts/01_pull_data.py
python scripts/02_build_factors.py
python scripts/03_run_research.py
python scripts/04_backtest.py
python scripts/05_generate_spec.py
python scripts/06_write_report.py

# 5. 一键复现 (评委用)
python scripts/reproduce.py
```

---

## 2. 项目脚手架

### 2.1 创建目录

```bash
mkdir -p signalforge/{config,data/raw/_samples,data/processed,src/{cmc,factors,research,strategy,llm,spec},scripts,tests,outputs/{specs,reports,figures,llm_logs}}
cd signalforge
touch src/__init__.py src/cmc/__init__.py src/factors/__init__.py src/research/__init__.py src/strategy/__init__.py src/llm/__init__.py src/spec/__init__.py config/__init__.py
```

### 2.2 `pyproject.toml`

```toml
[project]
name = "signalforge"
version = "0.1.0"
description = "CMC proprietary-indicator factor research engine"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "pandas>=2.2",
    "numpy>=1.26",
    "pyarrow>=16.0",
    "scipy>=1.13",
    "statsmodels>=0.14",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "matplotlib>=3.9",
    "plotly>=5.22",
    "openai>=1.30",
    "python-dotenv>=1.0",
    "tenacity>=8.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.2", "ruff>=0.4"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*", "config*"]
```

### 2.3 `.env.example`

```bash
# CoinMarketCap Pro API (https://pro.coinmarketcap.com/account)
CMC_API_KEY=your_cmc_key_here
CMC_BASE_URL=https://pro-api.coinmarketcap.com

# DeepSeek (https://platform.deepseek.com)
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Runtime
REQUEST_TIMEOUT=30
MAX_RETRIES=5
RATE_LIMIT_PER_MIN=28
```

### 2.4 `.gitignore`

```gitignore
.venv/
__pycache__/
*.pyc
.env
data/raw/*
!data/raw/_samples/
outputs/llm_logs/*
.pytest_cache/
*.egg-info/
```

### 2.5 `config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cmc_api_key: str = ""
    cmc_base_url: str = "https://pro-api.coinmarketcap.com"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    request_timeout: int = 30
    max_retries: int = 5
    rate_limit_per_min: int = 28

    cache_dir: str = "data/raw"
    sample_dir: str = "data/raw/_samples"
    processed_dir: str = "data/processed"
    outputs_dir: str = "outputs"

    seed: int = 42


settings = Settings()
```

### 2.6 `config/constants.py`

```python
"""项目级常量。TODO(M0) 标注的需在冒烟测试后回填真实值。"""

# 回测/因子通用
SEED = 42
UNIVERSE_TOP_N = 100          # 横截面 universe 规模
CONVERT = "USD"

# 交易成本假设 (bps)
FEE_BPS = 10
SLIPPAGE_BPS = {"large_cap": 5, "mid_cap": 10, "small_cap": 20}

# 因子检验门槛
RANK_IC_THRESHOLD = 0.03
T_STAT_THRESHOLD = 2.0
IR_THRESHOLD = 0.3
FDR_Q = 0.10

# Regime 阈值
MA_WINDOW = 200               # BTC 趋势判定均线
FG_FEAR = 33                  # CMC 自有 F&G 恐惧线
FG_GREED = 66                 # CMC 自有 F&G 贪婪线

# 持有期 (IC 衰减检验)
HOLDING_PERIODS = [1, 5, 10, 20, 40]

# TODO(M0): 冒烟测试后回填
CMC_PLAN = "UNKNOWN"          # e.g. "Startup" / "Standard" / "Basic"
FG_HISTORY_MAX_DAYS = None    # F&G 历史端点实际可返回的最大天数
OHLCV_EARLIEST = None         # 你的档位 OHLCV 实际最早日期
LISTINGS_HISTORICAL_AVAILABLE = None  # bool: listings/historical 是否可用
```

---

## 3. 数据层 (L1) — 完整代码

### 3.1 `src/cmc/client.py`

```python
"""CMC API 客户端: 重试 + 限流 + 缓存 + 原始落盘。"""
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
    """简单令牌桶: 每分钟 N 次。"""
    def __init__(self, per_min: int):
        self.interval = 60.0 / max(per_min, 1)
        self._last = 0.0

    def wait(self):
        now = time.monotonic()
        delta = now - self._last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last = time.monotonic()


class CMCClient:
    def __init__(self):
        self.base = settings.cmc_base_url.rstrip("/")
        self.headers = {
            "X-CMC_PRO_API_KEY": settings.cmc_api_key,
            "Accept": "application/json",
        }
        self._client = httpx.Client(timeout=settings.request_timeout, headers=self.headers)
        self._limiter = _RateLimiter(settings.rate_limit_per_min)
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.total_credits = 0

    def _cache_key(self, path: str, params: dict) -> Path:
        raw = path + json.dumps(params or {}, sort_keys=True)
        h = hashlib.md5(raw.encode()).hexdigest()[:16]
        safe = path.strip("/").replace("/", "_")
        return self.cache_dir / f"{safe}__{h}.json"

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        reraise=True,
    )
    def _raw_get(self, path: str, params: dict) -> dict:
        self._limiter.wait()
        r = self._client.get(self.base + path, params=params)
        if r.status_code == 429 or r.status_code >= 500:
            r.raise_for_status()   # 触发重试
        r.raise_for_status()       # 4xx 直接抛 (不重试)
        return r.json()

    def get(self, path: str, params: dict | None = None,
            use_cache: bool = True, save_sample: str | None = None) -> dict:
        params = params or {}
        cache_path = self._cache_key(path, params)
        if use_cache and cache_path.exists():
            return json.loads(cache_path.read_text())

        data = self._raw_get(path, params)

        # 记录 credit
        credit = (data.get("status") or {}).get("credit_count", 0) or 0
        self.total_credits += credit

        # 缓存
        cache_path.write_text(json.dumps(data, indent=2))
        # 样本 (供 schema 开发与复现)
        if save_sample:
            sp = Path(settings.sample_dir)
            sp.mkdir(parents=True, exist_ok=True)
            (sp / f"{save_sample}.json").write_text(json.dumps(data, indent=2)[:200000])
        return data

    def close(self):
        self._client.close()
```

### 3.2 `src/cmc/endpoints.py`

```python
"""七个核心端点的封装。返回 dict (原始 JSON)。解析交给 schemas.py。"""
from __future__ import annotations
from src.cmc.client import CMCClient


class Endpoints:
    def __init__(self, client: CMCClient | None = None):
        self.c = client or CMCClient()

    # A. 账户信息 (确认档位/credits) — 0 credit
    def key_info(self, save_sample: str | None = None) -> dict:
        return self.c.get("/v1/key/info", save_sample=save_sample)

    # B. 币种映射 (含 first/last_historical_data) — 0 credit
    def crypto_map(self, listing_status: str = "active,inactive,untracked",
                   limit: int = 5000, save_sample: str | None = None) -> dict:
        return self.c.get("/v1/cryptocurrency/map",
                          {"listing_status": listing_status, "limit": limit},
                          save_sample=save_sample)

    # C. 历史日级排名快照
    def listings_historical(self, date: str, limit: int = 100,
                            convert: str = "USD", save_sample: str | None = None) -> dict:
        return self.c.get("/v1/cryptocurrency/listings/historical",
                          {"date": date, "limit": limit, "sort": "market_cap",
                           "convert": convert},
                          save_sample=save_sample)

    # D. 历史 OHLCV (日线)
    def ohlcv_historical(self, ids: str, time_start: str, time_end: str,
                         interval: str = "daily", convert: str = "USD",
                         save_sample: str | None = None) -> dict:
        return self.c.get("/v2/cryptocurrency/ohlcv/historical",
                          {"id": ids, "time_start": time_start, "time_end": time_end,
                           "interval": interval, "convert": convert},
                          save_sample=save_sample)

    # E. CMC 自有 Fear & Greed 历史 ⭐
    def fear_greed_historical(self, start: int = 1, limit: int = 500,
                              save_sample: str | None = None) -> dict:
        return self.c.get("/v3/fear-and-greed/historical",
                          {"start": start, "limit": limit},
                          save_sample=save_sample)

    # F. 全局指标历史 (dominance / 总市值)
    def global_metrics_historical(self, time_start: str, time_end: str,
                                  interval: str = "1d", convert: str = "USD",
                                  save_sample: str | None = None) -> dict:
        return self.c.get("/v1/global-metrics/quotes/historical",
                          {"time_start": time_start, "time_end": time_end,
                           "interval": interval, "convert": convert},
                          save_sample=save_sample)

    # G. 全局指标最新 (altseason / market cycle 探测)
    def global_metrics_latest(self, convert: str = "USD",
                              save_sample: str | None = None) -> dict:
        return self.c.get("/v1/global-metrics/quotes/latest",
                          {"convert": convert}, save_sample=save_sample)
```

### 3.3 `scripts/00_smoke_test.py` — go/no-go

```python
"""冒烟测试: 打通 7 个端点,落样本,报告 plan 档位与数据可得性。
这是 go/no-go 检查点。运行后据输出回填 config/constants.py 的 TODO(M0)。"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from src.cmc.endpoints import Endpoints


def main():
    ep = Endpoints()
    today = datetime.utcnow().date()
    d30 = (today - timedelta(days=30)).isoformat()
    d1 = (today - timedelta(days=1)).isoformat()

    print("=" * 60)
    print("SignalForge 冒烟测试")
    print("=" * 60)

    # A. plan 档位
    try:
        info = ep.key_info(save_sample="key_info")
        plan = info.get("data", {}).get("plan", {})
        print(f"[A] key/info OK")
        print(f"    plan name: {plan.get('name')}")
        print(f"    credits/month: {plan.get('credit_limit_monthly')}")
        print(f"    credits used: {info.get('data', {}).get('usage', {})}")
    except Exception as e:
        print(f"[A] key/info FAIL: {e}")

    # B. map
    try:
        m = ep.crypto_map(limit=10, save_sample="crypto_map")
        sample = m.get("data", [])[:1]
        print(f"[B] crypto/map OK, sample fields: {list(sample[0].keys()) if sample else 'none'}")
    except Exception as e:
        print(f"[B] crypto/map FAIL: {e}")

    # C. listings/historical
    try:
        lh = ep.listings_historical(date=d30, limit=10, save_sample="listings_historical")
        print(f"[C] listings/historical OK, rows: {len(lh.get('data', []))}")
        print(f"    LISTINGS_HISTORICAL_AVAILABLE = True")
    except Exception as e:
        print(f"[C] listings/historical FAIL (可能档位不支持): {e}")
        print(f"    LISTINGS_HISTORICAL_AVAILABLE = False -> 用退化方案(纯时序因子)")

    # D. ohlcv (BTC id=1)
    try:
        o = ep.ohlcv_historical(ids="1", time_start=d30, time_end=d1,
                                save_sample="ohlcv_historical")
        quotes = o.get("data", {}).get("quotes", []) or o.get("data", {}).get("1", {}).get("quotes", [])
        print(f"[D] ohlcv/historical OK, points: {len(quotes)}")
    except Exception as e:
        print(f"[D] ohlcv/historical FAIL: {e}")

    # E. F&G 历史 ⭐
    try:
        fg = ep.fear_greed_historical(start=1, limit=500, save_sample="fear_greed_historical")
        data = fg.get("data", [])
        if data:
            ts = [d.get("timestamp") for d in data]
            print(f"[E] fear-and-greed/historical OK ⭐")
            print(f"    records: {len(data)}  earliest: {min(ts)}  latest: {max(ts)}")
            print(f"    FG_HISTORY_MAX_DAYS ~= {len(data)} (若需更久, 翻页 start)")
        else:
            print(f"[E] F&G 返回空")
    except Exception as e:
        print(f"[E] fear-and-greed FAIL: {e}")

    # F. global metrics historical
    try:
        gm = ep.global_metrics_historical(time_start=d30, time_end=d1,
                                          save_sample="global_metrics_historical")
        print(f"[F] global-metrics/historical OK, points: {len(gm.get('data', {}).get('quotes', []))}")
    except Exception as e:
        print(f"[F] global-metrics/historical FAIL: {e}")

    # G. global metrics latest (探 altseason / cycle)
    try:
        gl = ep.global_metrics_latest(save_sample="global_metrics_latest")
        keys = list(gl.get("data", {}).keys())
        print(f"[G] global-metrics/latest OK, top-level keys: {keys}")
        print(f"    检查是否含 altcoin season / market cycle 字段 -> 决定是否需自建代理")
    except Exception as e:
        print(f"[G] global-metrics/latest FAIL: {e}")

    print("=" * 60)
    print(f"累计 credit 消耗: {ep.c.total_credits}")
    print("样本已落盘 data/raw/_samples/  ->  据此回填 schemas.py 与 constants.py")
    print("=" * 60)
    ep.c.close()


if __name__ == "__main__":
    main()
```

### 3.4 `src/cmc/schemas.py` — pydantic 契约 (M0 后据真实样本校正字段名)

```python
"""返回契约。⚠️ TODO(M0): 跑完 00_smoke_test 后,对照 data/raw/_samples/*.json
核对/修正字段名。CMC 处于 beta,字段可能与此处预期不符。"""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class FearGreedPoint(BaseModel):
    timestamp: str
    value: float
    value_classification: Optional[str] = None


class OHLCVQuote(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    market_cap: Optional[float] = None


class ListingRow(BaseModel):
    id: int
    name: str
    symbol: str
    cmc_rank: Optional[int] = None
    # quote.USD.* 解析时展平
    price: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None


class MapEntry(BaseModel):
    id: int
    name: str
    symbol: str
    first_historical_data: Optional[str] = None
    last_historical_data: Optional[str] = None
    is_active: Optional[int] = None
```

### 3.5 `scripts/01_pull_data.py` — 全量拉取与落盘

```python
"""拉取全部历史数据并存 parquet。强缓存,绝不重复拉。"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.cmc.endpoints import Endpoints
from config.settings import settings
from config import constants as C

PROC = Path(settings.processed_dir)
PROC.mkdir(parents=True, exist_ok=True)


def pull_fear_greed(ep: Endpoints) -> pd.DataFrame:
    """翻页拉全部 F&G 历史。"""
    rows, start = [], 1
    while True:
        resp = ep.fear_greed_historical(start=start, limit=500)
        data = resp.get("data", [])
        if not data:
            break
        rows.extend(data)
        if len(data) < 500:
            break
        start += 500
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.normalize()
    df = df.rename(columns={"value": "cmc_fg"}).sort_values("date")
    df = df[["date", "cmc_fg", "value_classification"]].drop_duplicates("date")
    df.to_parquet(PROC / "fear_greed.parquet", index=False)
    print(f"F&G: {len(df)} rows, {df['date'].min()} ~ {df['date'].max()}")
    return df


def pull_global_metrics(ep: Endpoints, start_date: str, end_date: str) -> pd.DataFrame:
    resp = ep.global_metrics_historical(time_start=start_date, time_end=end_date, interval="1d")
    quotes = resp.get("data", {}).get("quotes", [])
    rows = []
    for q in quotes:
        usd = q.get("quote", {}).get("USD", {})
        rows.append({
            "date": pd.to_datetime(q.get("timestamp")).normalize(),
            "btc_dominance": q.get("btc_dominance"),
            "eth_dominance": q.get("eth_dominance"),
            "total_market_cap": usd.get("total_market_cap"),
            "total_volume_24h": usd.get("total_volume_24h"),
        })
    df = pd.DataFrame(rows).sort_values("date")
    df.to_parquet(PROC / "global_metrics.parquet", index=False)
    print(f"global_metrics: {len(df)} rows")
    return df


def pull_map(ep: Endpoints) -> pd.DataFrame:
    resp = ep.crypto_map()
    df = pd.DataFrame(resp.get("data", []))
    keep = [c for c in ["id", "name", "symbol", "first_historical_data",
                        "last_historical_data", "is_active", "rank"] if c in df.columns]
    df = df[keep]
    df.to_parquet(PROC / "crypto_map.parquet", index=False)
    print(f"map: {len(df)} coins")
    return df


def pull_ohlcv(ep: Endpoints, ids: list[int], start_date: str, end_date: str) -> pd.DataFrame:
    """分批拉 OHLCV (每次最多几个 id,视 plan)。"""
    all_rows = []
    for i in range(0, len(ids), 5):
        batch = ",".join(str(x) for x in ids[i:i + 5])
        resp = ep.ohlcv_historical(ids=batch, time_start=start_date, time_end=end_date)
        data = resp.get("data", {})
        # data 可能是 {id: {quotes:[...]}} 或 {quotes:[...]}
        items = data.values() if isinstance(data, dict) and "quotes" not in data else [data]
        for item in items:
            cid = item.get("id")
            for q in item.get("quotes", []):
                usd = q.get("quote", {}).get("USD", {})
                all_rows.append({
                    "id": cid,
                    "date": pd.to_datetime(q.get("timestamp")).normalize(),
                    "close": usd.get("close"),
                    "volume": usd.get("volume"),
                    "market_cap": usd.get("market_cap"),
                })
    df = pd.DataFrame(all_rows).sort_values(["id", "date"])
    df.to_parquet(PROC / "ohlcv.parquet", index=False)
    print(f"ohlcv: {len(df)} rows, {df['id'].nunique()} coins")
    return df


def pull_listings_snapshots(ep: Endpoints, dates: list[str], limit: int = 100):
    """按需拉历史排名快照 (用于横截面 universe)。"""
    rows = []
    for d in dates:
        try:
            resp = ep.listings_historical(date=d, limit=limit)
            for r in resp.get("data", []):
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
    print(f"listings snapshots: {len(df)} rows over {len(dates)} dates")
    return df


def main():
    ep = Endpoints()
    today = datetime.utcnow().date()
    end = (today - timedelta(days=1)).isoformat()
    # 起始日尽量早 (受 plan 限制,失败则自动被 API 截断)
    start = "2018-01-01"

    fg = pull_fear_greed(ep)
    gm = pull_global_metrics(ep, start, end)
    cmap = pull_map(ep)

    # universe: 用最新一日的 top-N 作为 OHLCV 拉取集合 (横截面则用快照)
    # 这里取 F&G 与 global 都覆盖的区间起点
    common_start = max(fg["date"].min(), gm["date"].min()).date().isoformat()

    # 取当前 top-N id (用 map 的 rank 或单独 listings/latest)
    top_ids = cmap.sort_values("rank").head(C.UNIVERSE_TOP_N)["id"].tolist() \
        if "rank" in cmap.columns else cmap["id"].head(C.UNIVERSE_TOP_N).tolist()
    pull_ohlcv(ep, top_ids, common_start, end)

    # 横截面快照: 每月首日 (省 credits)
    if C.LISTINGS_HISTORICAL_AVAILABLE is not False:
        month_dates = pd.date_range(common_start, end, freq="MS").strftime("%Y-%m-%d").tolist()
        pull_listings_snapshots(ep, month_dates, limit=C.UNIVERSE_TOP_N)

    print(f"\n总 credit 消耗: {ep.c.total_credits}")
    ep.c.close()


if __name__ == "__main__":
    main()
```

### 3.9 M0 回填指引

跑完 `00_smoke_test.py` 后,据输出**回填两处**:
1. `config/constants.py` 的 `CMC_PLAN`, `FG_HISTORY_MAX_DAYS`, `OHLCV_EARLIEST`, `LISTINGS_HISTORICAL_AVAILABLE`。
2. `src/cmc/schemas.py` 字段名 — 对照 `data/raw/_samples/*.json` 的真实键名修正。
若 `[C]` 失败 → 设 `LISTINGS_HISTORICAL_AVAILABLE=False`,后续走纯时序因子退化方案 (跳过 §4.3 横截面)。
若 `[G]` 无 altseason/cycle 字段 → 用 §4.2 的 `altseason_proxy` 自建。

---

## 4. 因子层 (L2) — 完整代码

### 4.1 `src/factors/timeseries.py`

```python
"""时序因子 (point-in-time)。所有滚动窗口右端 <= t。"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _roll_z(s: pd.Series, window: int) -> pd.Series:
    """滚动 z-score,仅用历史窗 (min_periods 防早期 NaN 误用)。"""
    m = s.rolling(window, min_periods=window).mean()
    sd = s.rolling(window, min_periods=window).std()
    return (s - m) / sd.replace(0, np.nan)


def build_fg_factors(fg: pd.DataFrame) -> pd.DataFrame:
    """fg: columns [date, cmc_fg, value_classification]"""
    df = fg.sort_values("date").copy().set_index("date")
    out = pd.DataFrame(index=df.index)
    out["fg_level"] = df["cmc_fg"]
    out["fg_zscore_90"] = _roll_z(df["cmc_fg"], 90)
    out["fg_momentum_7"] = df["cmc_fg"] - df["cmc_fg"].shift(7)
    out["fg_extreme_rev"] = np.select(
        [df["cmc_fg"] < 20, df["cmc_fg"] > 80], [1.0, -1.0], default=0.0)
    # F&G 分类持续天数
    cls = df["value_classification"].fillna("NA")
    grp = (cls != cls.shift()).cumsum()
    out["fg_regime_dur"] = cls.groupby(grp).cumcount() + 1
    return out.reset_index()


def build_dominance_factors(gm: pd.DataFrame) -> pd.DataFrame:
    """gm: [date, btc_dominance, eth_dominance, total_market_cap, total_volume_24h]"""
    df = gm.sort_values("date").copy().set_index("date")
    out = pd.DataFrame(index=df.index)
    out["dom_trend_30"] = df["btc_dominance"].diff(30) / 30.0
    out["dom_zscore_90"] = _roll_z(df["btc_dominance"], 90)
    out["mktcap_mom_30"] = df["total_market_cap"].pct_change(30)
    return out.reset_index()


def build_fg_dominance_cross(fg_f: pd.DataFrame, dom_f: pd.DataFrame) -> pd.DataFrame:
    """交互因子: 恐惧 + dominance 上升 = 避险轮动。"""
    m = fg_f.merge(dom_f, on="date", how="inner")
    m["fg_cross_dom"] = (-m["fg_zscore_90"]) * m["dom_trend_30"]
    return m[["date", "fg_cross_dom"]]
```

### 4.2 `src/factors/cross_section.py`

```python
"""横截面因子 (无幸存者偏差)。universe 来自当日 listings 快照。"""
from __future__ import annotations
import numpy as np
import pandas as pd


def build_cross_section_factors(snapshots: pd.DataFrame, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    snapshots: [date, id, symbol, cmc_rank, price, market_cap]  (point-in-time universe)
    ohlcv:     [id, date, close, volume, market_cap]
    返回长表: [date, id, xs_rank_mom_30, xs_size, xs_ret_mom_90, xs_vol_60]
    """
    px = ohlcv.sort_values(["id", "date"]).copy()
    px["ret_90"] = px.groupby("id")["close"].pct_change(90)
    px["ret_1"] = px.groupby("id")["close"].pct_change()
    px["vol_60"] = px.groupby("id")["ret_1"].transform(
        lambda s: s.rolling(60, min_periods=60).std())

    rows = []
    snaps = snapshots.sort_values("date")
    snap_dates = snaps["date"].unique()
    for d in snap_dates:
        uni = snaps[snaps["date"] == d]
        ids = uni["id"].tolist()
        # 该日排名 (用快照) + 30 日前排名
        prev = snaps[snaps["date"] <= d - pd.Timedelta(days=25)]
        prev = prev[prev["date"] >= d - pd.Timedelta(days=35)]
        prev_rank = prev.groupby("id")["cmc_rank"].last()
        px_d = px[(px["date"] == d) & (px["id"].isin(ids))].set_index("id")
        for cid in ids:
            cur_rank = uni[uni["id"] == cid]["cmc_rank"].iloc[0]
            rows.append({
                "date": d, "id": cid,
                "xs_rank_mom_30": (prev_rank.get(cid, np.nan) - cur_rank),  # 排名上升=正
                "xs_size": np.log(uni[uni["id"] == cid]["market_cap"].iloc[0] + 1),
                "xs_ret_mom_90": px_d["ret_90"].get(cid, np.nan) if cid in px_d.index else np.nan,
                "xs_vol_60": px_d["vol_60"].get(cid, np.nan) if cid in px_d.index else np.nan,
            })
    df = pd.DataFrame(rows)
    # 横截面 rank 标准化 (每个截面日内)
    for col in ["xs_rank_mom_30", "xs_size", "xs_ret_mom_90", "xs_vol_60"]:
        df[col] = df.groupby("date")[col].rank(pct=True) - 0.5
    return df
```

### 4.3 `src/factors/regime.py`

```python
"""Regime 标注 (point-in-time)。维度1 方向 × 维度2 情绪。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from config import constants as C


def label_regime(btc_close: pd.Series, fg: pd.Series) -> pd.DataFrame:
    """
    btc_close: index=date 的 BTC 收盘
    fg:        index=date 的 CMC 自有 F&G
    返回: [date, dir_regime, sent_regime, regime]
    """
    df = pd.DataFrame({"btc": btc_close}).join(pd.DataFrame({"fg": fg}), how="inner")
    ma = df["btc"].rolling(C.MA_WINDOW, min_periods=C.MA_WINDOW).mean()
    slope = ma.diff(20)
    df["dir_regime"] = np.select(
        [(df["btc"] > ma) & (slope > 0), (df["btc"] < ma) & (slope < 0)],
        ["BULL", "BEAR"], default="CHOP")
    df["sent_regime"] = np.select(
        [df["fg"] < C.FG_FEAR, df["fg"] > C.FG_GREED],
        ["FEAR", "GREED"], default="NEUTRAL")
    df["regime"] = df["dir_regime"] + "_" + df["sent_regime"]
    return df.reset_index().rename(columns={"index": "date"})[
        ["date", "dir_regime", "sent_regime", "regime"]]
```

### 4.4 `scripts/02_build_factors.py`

```python
"""组装所有因子面板。"""
from pathlib import Path
import pandas as pd

from config.settings import settings
from config import constants as C
from src.factors.timeseries import (
    build_fg_factors, build_dominance_factors, build_fg_dominance_cross)
from src.factors.cross_section import build_cross_section_factors
from src.factors.regime import label_regime

PROC = Path(settings.processed_dir)


def main():
    fg = pd.read_parquet(PROC / "fear_greed.parquet")
    gm = pd.read_parquet(PROC / "global_metrics.parquet")
    ohlcv = pd.read_parquet(PROC / "ohlcv.parquet")

    fg_f = build_fg_factors(fg)
    dom_f = build_dominance_factors(gm)
    cross = build_fg_dominance_cross(fg_f, dom_f)

    ts = fg_f.merge(dom_f, on="date", how="outer").merge(cross, on="date", how="outer")
    ts = ts.sort_values("date")
    ts.to_parquet(PROC / "factors_timeseries.parquet", index=False)
    print(f"时序因子: {ts.shape}")

    # regime (BTC id=1)
    btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"]
    fg_s = fg.set_index("date")["cmc_fg"]
    reg = label_regime(btc, fg_s)
    reg.to_parquet(PROC / "regime.parquet", index=False)
    print(f"regime 分布:\n{reg['regime'].value_counts()}")

    # 横截面 (若可用)
    snap_path = PROC / "listings_snapshots.parquet"
    if C.LISTINGS_HISTORICAL_AVAILABLE is not False and snap_path.exists():
        snaps = pd.read_parquet(snap_path)
        xs = build_cross_section_factors(snaps, ohlcv)
        xs.to_parquet(PROC / "factors_cross_section.parquet", index=False)
        print(f"横截面因子: {xs.shape}")
    else:
        print("跳过横截面因子 (listings/historical 不可用)")


if __name__ == "__main__":
    main()
```

### 4.5 `tests/test_no_lookahead.py` — 前视偏差单测 (关键)

```python
"""验证因子计算严格因果: 未来值不影响当前及历史因子。"""
import numpy as np
import pandas as pd
from src.factors.timeseries import build_fg_factors


def _make_fg(n=200, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    vals = rng.integers(10, 90, n).astype(float)
    return pd.DataFrame({"date": dates, "cmc_fg": vals,
                         "value_classification": ["Neutral"] * n})


def test_future_does_not_leak():
    base = _make_fg()
    f1 = build_fg_factors(base).set_index("date")

    # 篡改最后一天之后不存在的数据不可能影响; 改最后一天, 断言历史不变
    tampered = base.copy()
    tampered.loc[tampered.index[-1], "cmc_fg"] = 999
    f2 = build_fg_factors(tampered).set_index("date")

    # 除最后一天外, 所有 fg_zscore_90 / momentum 应完全一致
    cols = ["fg_zscore_90", "fg_momentum_7", "fg_level"]
    a = f1[cols].iloc[:-1].fillna(-12345)
    b = f2[cols].iloc[:-1].fillna(-12345)
    assert np.allclose(a.values, b.values), "未来值泄漏到历史因子!"


def test_rolling_uses_only_past():
    base = _make_fg()
    f = build_fg_factors(base).set_index("date")
    # 前 89 天 zscore_90 必须是 NaN (窗口不足)
    assert f["fg_zscore_90"].iloc[:89].isna().all()
```

### 4.6 `tests/test_survivorship.py`

```python
"""验证横截面 universe 来自 point-in-time 快照, 含当日真实在榜币。"""
import pandas as pd
from src.factors.cross_section import build_cross_section_factors


def test_universe_is_point_in_time():
    # 构造: t1 universe = {1,2}, t2 universe = {1,3} (币2退市,币3新上)
    snaps = pd.DataFrame([
        {"date": pd.Timestamp("2023-01-01"), "id": 1, "symbol": "A", "cmc_rank": 1, "price": 10, "market_cap": 1e9},
        {"date": pd.Timestamp("2023-01-01"), "id": 2, "symbol": "B", "cmc_rank": 2, "price": 5, "market_cap": 5e8},
        {"date": pd.Timestamp("2023-02-01"), "id": 1, "symbol": "A", "cmc_rank": 1, "price": 12, "market_cap": 1.2e9},
        {"date": pd.Timestamp("2023-02-01"), "id": 3, "symbol": "C", "cmc_rank": 2, "price": 8, "market_cap": 6e8},
    ])
    ohlcv = pd.DataFrame([
        {"id": i, "date": d, "close": 10.0, "volume": 1, "market_cap": 1e9}
        for i in [1, 2, 3]
        for d in pd.date_range("2022-09-01", "2023-02-01", freq="D")
    ])
    xs = build_cross_section_factors(snaps, ohlcv)
    # t1 截面应只含 id∈{1,2}, t2 截面只含 {1,3}
    t1 = set(xs[xs["date"] == "2023-01-01"]["id"])
    t2 = set(xs[xs["date"] == "2023-02-01"]["id"])
    assert t1 == {1, 2}, f"t1 universe 错误: {t1}"
    assert t2 == {1, 3}, f"t2 universe 错误: {t2}"
```

---

## 5. 研究层 (L3) — 完整代码 (评分核心)

### 5.1 `src/research/ic.py`

```python
"""IC / Rank-IC / IR / t-stat / 衰减。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def forward_returns(close: pd.Series, horizon: int) -> pd.Series:
    """t 日的未来 horizon 期收益 (t -> t+horizon)。严格 shift(-horizon)。"""
    return close.shift(-horizon) / close - 1.0


def timeseries_ic(factor: pd.Series, fwd_ret: pd.Series, method: str = "spearman") -> dict:
    """时序因子: 对齐后整体相关 (factor_t vs fwd_ret_t)。"""
    df = pd.concat([factor, fwd_ret], axis=1, keys=["f", "r"]).dropna()
    if len(df) < 30:
        return {"ic": np.nan, "n": len(df), "t_stat": np.nan, "p": np.nan}
    if method == "spearman":
        ic, p = stats.spearmanr(df["f"], df["r"])
    else:
        ic, p = stats.pearsonr(df["f"], df["r"])
    # 滚动 IC 求 IR/t
    return {"ic": ic, "p": p, "n": len(df)}


def rolling_ic_series(factor: pd.Series, fwd_ret: pd.Series,
                      window: int = 60, method: str = "spearman") -> pd.Series:
    df = pd.concat([factor, fwd_ret], axis=1, keys=["f", "r"]).dropna()
    out = {}
    for i in range(window, len(df)):
        w = df.iloc[i - window:i]
        ic = (stats.spearmanr if method == "spearman" else stats.pearsonr)(w["f"], w["r"])[0]
        out[df.index[i]] = ic
    return pd.Series(out)


def ir_and_tstat(ic_series: pd.Series) -> dict:
    ic_series = ic_series.dropna()
    if len(ic_series) < 10:
        return {"mean_ic": np.nan, "ir": np.nan, "t_stat": np.nan, "n": len(ic_series)}
    mean_ic = ic_series.mean()
    ir = mean_ic / ic_series.std() if ic_series.std() > 0 else np.nan
    t_stat = mean_ic / ic_series.std() * np.sqrt(len(ic_series)) if ic_series.std() > 0 else np.nan
    return {"mean_ic": mean_ic, "ir": ir, "t_stat": t_stat, "n": len(ic_series)}


def cross_section_ic(factor_panel: pd.DataFrame, ret_panel: pd.DataFrame,
                     horizon: int = 5) -> pd.Series:
    """横截面 Rank-IC: 每个截面日, factor rank vs forward return rank。
    factor_panel/ret_panel: index=date, columns=id。返回每日 IC 序列。"""
    out = {}
    for d in factor_panel.index:
        if d not in ret_panel.index:
            continue
        f = factor_panel.loc[d].dropna()
        r = ret_panel.loc[d].reindex(f.index).dropna()
        common = f.index.intersection(r.index)
        if len(common) < 10:
            continue
        out[d] = stats.spearmanr(f[common], r[common])[0]
    return pd.Series(out)


def ic_decay(factor: pd.Series, close: pd.Series, horizons: list[int]) -> dict:
    """各持有期 IC,画衰减。"""
    res = {}
    for h in horizons:
        fr = forward_returns(close, h)
        res[h] = timeseries_ic(factor, fr)["ic"]
    return res
```

### 5.2 `src/research/regime_attrib.py`

```python
"""Regime 分层 IC 归因 — 差异化亮点。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def regime_layered_ic(factor: pd.Series, fwd_ret: pd.Series,
                      regime: pd.Series, method: str = "spearman") -> pd.DataFrame:
    """对每个 regime 分别算 IC/t-stat。
    factor/fwd_ret/regime: index=date。返回 [regime, ic, t_stat, n]。"""
    df = pd.concat([factor, fwd_ret, regime], axis=1, keys=["f", "r", "reg"]).dropna()
    rows = []
    for reg, g in df.groupby("reg"):
        if len(g) < 20:
            rows.append({"regime": reg, "ic": np.nan, "p": np.nan, "n": len(g)})
            continue
        ic, p = (stats.spearmanr if method == "spearman" else stats.pearsonr)(g["f"], g["r"])
        # 近似 t
        t = ic * np.sqrt((len(g) - 2) / max(1 - ic**2, 1e-9))
        rows.append({"regime": reg, "ic": ic, "t_stat": t, "p": p, "n": len(g)})
    return pd.DataFrame(rows).sort_values("ic", ascending=False)


def regime_ic_matrix(factors: dict[str, pd.Series], fwd_ret: pd.Series,
                     regime: pd.Series) -> pd.DataFrame:
    """因子 × regime 的 IC 矩阵 (供热力图)。"""
    mats = {}
    for fname, fser in factors.items():
        lay = regime_layered_ic(fser, fwd_ret, regime).set_index("regime")["ic"]
        mats[fname] = lay
    return pd.DataFrame(mats).T  # rows=factor, cols=regime
```

### 5.3 `src/research/multiple_testing.py`

```python
"""多重检验校正: BH-FDR + Deflated Sharpe。防 data snooping。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def bh_fdr(pvalues: list[float], q: float = 0.10) -> pd.DataFrame:
    p = np.array(pvalues, dtype=float)
    mask = ~np.isnan(p)
    reject = np.full(len(p), False)
    p_adj = np.full(len(p), np.nan)
    if mask.sum() > 0:
        rej, padj, _, _ = multipletests(p[mask], alpha=q, method="fdr_bh")
        reject[mask] = rej
        p_adj[mask] = padj
    return pd.DataFrame({"p": p, "p_adj": p_adj, "significant": reject})


def deflated_sharpe(returns: pd.Series, n_trials: int,
                    sr_benchmark: float = 0.0) -> dict:
    """López de Prado Deflated Sharpe Ratio。
    returns: 策略日收益序列。n_trials: 总共尝试过的策略配置数。"""
    r = returns.dropna()
    n = len(r)
    if n < 30:
        return {"sharpe": np.nan, "dsr": np.nan}
    sr = r.mean() / r.std() if r.std() > 0 else 0.0
    skew = stats.skew(r)
    kurt = stats.kurtosis(r, fisher=False)

    # 预期最大 Sharpe (多次试验下的选择偏差)
    emc = 0.5772156649
    z = stats.norm.ppf(1 - 1.0 / max(n_trials, 2))
    z2 = stats.norm.ppf(1 - 1.0 / max(n_trials, 2) * np.e**-1)
    sr_expected_max = (z * (1 - emc) + z2 * emc)
    # 年化前用日频; 这里用日频 SR 的标准误
    sr_std = np.sqrt((1 - skew * sr + (kurt - 1) / 4.0 * sr**2) / (n - 1))
    dsr = stats.norm.cdf((sr - sr_expected_max * sr_std) / sr_std) if sr_std > 0 else np.nan
    return {
        "sharpe_daily": sr, "sharpe_annual": sr * np.sqrt(365),
        "deflated_sharpe_prob": dsr, "n_trials": n_trials, "n_obs": n,
    }
```

### 5.4 `src/research/robustness.py`

```python
"""稳健性: walk-forward / OOS 切分 / 参数高原 / 成本敏感。"""
from __future__ import annotations
import numpy as np
import pandas as pd


def time_split(dates: pd.DatetimeIndex, is_frac: float = 0.7) -> tuple:
    """时间序列切分 (不打乱)。返回 (is_end_date, oos_start_date)。"""
    cut = dates[int(len(dates) * is_frac)]
    return cut, cut


def walk_forward_windows(dates: pd.DatetimeIndex, train: int = 365,
                         test: int = 90, step: int = 90):
    """生成滚动 (train_idx, test_idx) 窗口。"""
    windows = []
    i = train
    while i + test <= len(dates):
        windows.append((dates[i - train:i], dates[i:i + test]))
        i += step
    return windows


def parameter_plateau(metric_fn, param_grid: dict) -> pd.DataFrame:
    """网格扫描参数, 返回每组参数的绩效 (检查高原而非孤峰)。
    metric_fn(params)->float; param_grid={'window':[30,60,90],...}"""
    import itertools
    keys = list(param_grid.keys())
    rows = []
    for combo in itertools.product(*param_grid.values()):
        params = dict(zip(keys, combo))
        rows.append({**params, "metric": metric_fn(params)})
    return pd.DataFrame(rows)


def cost_sensitivity(backtest_fn, cost_grid_bps: list[int]) -> pd.DataFrame:
    """不同成本下重跑。backtest_fn(fee_bps)->dict(perf)。"""
    return pd.DataFrame([{"fee_bps": c, **backtest_fn(c)} for c in cost_grid_bps])
```

### 5.5 `scripts/03_run_research.py`

```python
"""跑因子检验全流程, 出 research_results.json + 三张图。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config.settings import settings
from config import constants as C
from src.research.ic import (
    forward_returns, rolling_ic_series, ir_and_tstat, ic_decay, timeseries_ic)
from src.research.regime_attrib import regime_ic_matrix, regime_layered_ic
from src.research.multiple_testing import bh_fdr

np.random.seed(C.SEED)
PROC = Path(settings.processed_dir)
FIG = Path(settings.outputs_dir) / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def main():
    ts = pd.read_parquet(PROC / "factors_timeseries.parquet").set_index("date")
    ohlcv = pd.read_parquet(PROC / "ohlcv.parquet")
    regime = pd.read_parquet(PROC / "regime.parquet").set_index("date")["regime"]
    btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"].sort_index()

    fwd5 = forward_returns(btc, 5)
    factor_cols = [c for c in ts.columns if c not in ("value_classification",)]

    results = {"factors": {}, "n_trials": 0}
    pvals, pnames = [], []

    for col in factor_cols:
        f = ts[col].reindex(btc.index)
        # 整体 IC
        base = timeseries_ic(f, fwd5)
        # 滚动 IR/t
        ic_ser = rolling_ic_series(f, fwd5, window=60)
        stat = ir_and_tstat(ic_ser)
        # 衰减
        decay = ic_decay(f, btc, C.HOLDING_PERIODS)
        # regime 分层
        lay = regime_layered_ic(f, fwd5, regime)

        results["factors"][col] = {
            "ic_overall": base["ic"], "p_overall": base["p"], "n": base["n"],
            "mean_ic": stat["mean_ic"], "ir": stat["ir"], "t_stat": stat["t_stat"],
            "ic_decay": {str(k): v for k, v in decay.items()},
            "regime_ic": lay.to_dict(orient="records"),
        }
        if not np.isnan(base["p"]):
            pvals.append(base["p"]); pnames.append(col)
        results["n_trials"] += 1 + len(lay)

    # FDR 校正
    fdr = bh_fdr(pvals, q=C.FDR_Q)
    for name, sig, padj in zip(pnames, fdr["significant"], fdr["p_adj"]):
        results["factors"][name]["fdr_significant"] = bool(sig)
        results["factors"][name]["p_adj"] = float(padj) if not np.isnan(padj) else None

    # === 图1: IC 衰减 ===
    plt.figure(figsize=(8, 5))
    for col in factor_cols[:6]:
        d = results["factors"][col]["ic_decay"]
        plt.plot(list(map(int, d.keys())), list(d.values()), marker="o", label=col)
    plt.axhline(0, color="gray", lw=0.5); plt.xlabel("Holding period (days)")
    plt.ylabel("IC"); plt.title("Factor IC Decay (CMC signals)"); plt.legend(fontsize=7)
    plt.tight_layout(); plt.savefig(FIG / "ic_decay.png", dpi=130); plt.close()

    # === 图2: regime × factor IC 热力图 ===
    factors_dict = {c: ts[c].reindex(btc.index) for c in factor_cols}
    mat = regime_ic_matrix(factors_dict, fwd5, regime)
    plt.figure(figsize=(10, 6))
    plt.imshow(mat.values, aspect="auto", cmap="RdYlGn", vmin=-0.15, vmax=0.15)
    plt.colorbar(label="Rank-IC")
    plt.xticks(range(len(mat.columns)), mat.columns, rotation=45, ha="right", fontsize=7)
    plt.yticks(range(len(mat.index)), mat.index, fontsize=7)
    plt.title("Factor × Regime IC Heatmap (CMC proprietary signals)")
    plt.tight_layout(); plt.savefig(FIG / "regime_ic_heatmap.png", dpi=130); plt.close()

    Path(settings.outputs_dir, "research_results.json").write_text(
        json.dumps(results, indent=2, default=float))
    print(f"研究完成。显著因子(FDR): "
          f"{[k for k,v in results['factors'].items() if v.get('fdr_significant')]}")


if __name__ == "__main__":
    main()
```

---

## 6. 策略层 (L4) — 完整代码

### 6.1 `src/strategy/signals.py`

```python
"""因子 -> 信号。所有信号 t 日生成, t+1 执行 (见 backtest 对齐)。"""
from __future__ import annotations
import numpy as np
import pandas as pd


def factor_to_signal(factor: pd.Series, long_only: bool = False) -> pd.Series:
    """标准化因子 -> [-1,1] 信号 (tanh 压缩)。"""
    s = np.tanh(factor.fillna(0.0))
    if long_only:
        s = s.clip(lower=0.0)
    return s


def combine_signals(signals: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    """加权合成。weights 来自 IR 或 regime 标定。"""
    idx = None
    for s in signals.values():
        idx = s.index if idx is None else idx.union(s.index)
    out = pd.Series(0.0, index=idx)
    wsum = sum(abs(w) for w in weights.values()) or 1.0
    for name, w in weights.items():
        if name in signals:
            out = out.add((w / wsum) * signals[name].reindex(idx).fillna(0.0), fill_value=0.0)
    return out.clip(-1, 1)
```

### 6.2 `src/strategy/portfolio.py`

```python
"""信号 -> 仓位, regime 条件化权重。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from config import constants as C
from src.strategy.signals import factor_to_signal, combine_signals


def regime_conditional_positions(
    factors: pd.DataFrame,          # index=date, cols=factor names
    regime: pd.Series,              # index=date
    weights_by_regime: dict[str, dict[str, float]],
    max_pos: float = 1.0,
) -> pd.Series:
    """对每日, 取该日 regime 对应的因子权重, 合成单资产仓位 (-1..1)。
    (单资产择时版; 横截面版见 cross_section_positions)"""
    sigs = {c: factor_to_signal(factors[c]) for c in factors.columns}
    dates = factors.index
    pos = pd.Series(0.0, index=dates)
    for d in dates:
        reg = regime.get(d, None)
        w = weights_by_regime.get(reg, {})
        if not w:
            continue
        day_sig = {k: pd.Series([v.get(d, 0.0)], index=[d]) for k, v in sigs.items()}
        combined = combine_signals(day_sig, w)
        pos.loc[d] = float(combined.iloc[0])
    return (pos * max_pos).clip(-max_pos, max_pos)


def cross_section_positions(
    factor_panel: pd.DataFrame,     # index=date, cols=id (合成因子分数)
    top_q: float = 0.2, bottom_q: float = 0.2,
    long_only: bool = False, max_asset: float = 0.30,
) -> pd.DataFrame:
    """每日做多 top 分位, (可选)做空 bottom。等权, 单资产上限。
    返回 index=date, cols=id 的权重面板。"""
    pos = pd.DataFrame(0.0, index=factor_panel.index, columns=factor_panel.columns)
    for d in factor_panel.index:
        row = factor_panel.loc[d].dropna()
        if len(row) < 5:
            continue
        n_top = max(int(len(row) * top_q), 1)
        longs = row.nlargest(n_top).index
        pos.loc[d, longs] = min(1.0 / n_top, max_asset)
        if not long_only:
            n_bot = max(int(len(row) * bottom_q), 1)
            shorts = row.nsmallest(n_bot).index
            pos.loc[d, shorts] = -min(1.0 / n_bot, max_asset)
    return pos


def default_regime_weights() -> dict:
    """初始权重 (M3 标定后由 03_run_research 的 regime_ic 覆盖)。
    占位: 每个 regime 给 IC 显著为正的因子正权重。"""
    return {
        "BEAR_FEAR":   {"fg_extreme_rev": 0.6, "fg_zscore_90": -0.4},
        "BULL_GREED":  {"dom_trend_30": 0.5, "fg_momentum_7": 0.5},
        "CHOP_NEUTRAL":{"fg_zscore_90": -0.5, "dom_zscore_90": -0.5},
        # 其余 regime 由 03 结果自动填充
    }
```

### 6.3 `src/strategy/backtest.py`

```python
"""向量化回测引擎。严格 t信号 -> t+1 执行。含成本。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from config import constants as C


def backtest_single(positions: pd.Series, close: pd.Series,
                    fee_bps: float = C.FEE_BPS, slippage_bps: float = 5) -> dict:
    """单资产择时回测。
    positions_t -> 在 t+1 持有, 赚 ret_{t+1->t+2}。"""
    df = pd.DataFrame({"pos": positions, "close": close}).dropna().sort_index()
    df["ret"] = df["close"].pct_change().shift(-1)        # t -> t+1 收益
    df["pos_exec"] = df["pos"].shift(1).fillna(0.0)       # t 信号 t+1 执行
    df["turnover"] = df["pos_exec"].diff().abs().fillna(0.0)
    cost = df["turnover"] * (fee_bps + slippage_bps) / 1e4
    df["strat_ret"] = df["pos_exec"] * df["ret"] - cost
    return _perf(df["strat_ret"].dropna(), df["ret"].dropna(), df["turnover"].mean())


def backtest_panel(positions: pd.DataFrame, close_panel: pd.DataFrame,
                   fee_bps: float = C.FEE_BPS, slippage_bps: float = 10) -> dict:
    """横截面回测。positions/close_panel: index=date, cols=id。"""
    ret = close_panel.pct_change().shift(-1)              # 每资产 t->t+1
    pos_exec = positions.shift(1).fillna(0.0)
    turnover = pos_exec.diff().abs().sum(axis=1).fillna(0.0)
    gross = (pos_exec * ret).sum(axis=1)
    cost = turnover * (fee_bps + slippage_bps) / 1e4
    strat_ret = (gross - cost).dropna()
    bench = ret.mean(axis=1).dropna()                    # 等权基准
    return _perf(strat_ret, bench, turnover.mean())


def _perf(strat: pd.Series, bench: pd.Series, avg_turnover: float) -> dict:
    strat = strat.dropna()
    ann = 365
    mean, sd = strat.mean(), strat.std()
    downside = strat[strat < 0].std()
    cum = (1 + strat).cumprod()
    dd = (cum / cum.cummax() - 1).min()
    sharpe = mean / sd * np.sqrt(ann) if sd > 0 else np.nan
    sortino = mean / downside * np.sqrt(ann) if downside and downside > 0 else np.nan
    ann_ret = (1 + mean) ** ann - 1
    calmar = ann_ret / abs(dd) if dd < 0 else np.nan
    # vs bench
    common = strat.index.intersection(bench.index)
    if len(common) > 10:
        cov = np.cov(strat.reindex(common), bench.reindex(common))
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else np.nan
        alpha = (mean - beta * bench.reindex(common).mean()) * ann
    else:
        beta = alpha = np.nan
    return {
        "ann_return": float(ann_ret), "ann_vol": float(sd * np.sqrt(ann)),
        "sharpe": float(sharpe), "sortino": float(sortino), "calmar": float(calmar),
        "max_drawdown": float(dd), "win_rate": float((strat > 0).mean()),
        "avg_turnover": float(avg_turnover), "alpha_vs_bench": float(alpha),
        "beta_vs_bench": float(beta), "n_days": int(len(strat)),
        "equity_curve": cum,  # 供画图
        "returns": strat,     # 供 deflated sharpe
    }


def monte_carlo_random(close: pd.Series, n_sims: int = 1000,
                       avg_turnover: float = 0.1, seed: int = C.SEED) -> dict:
    """随机信号基准: 证明 alpha 非运气。"""
    rng = np.random.default_rng(seed)
    ret = close.pct_change().shift(-1).dropna()
    sharpes = []
    for _ in range(n_sims):
        rand_pos = pd.Series(rng.choice([-1, 0, 1], len(ret)), index=ret.index)
        sr = (rand_pos * ret).dropna()
        s = sr.mean() / sr.std() * np.sqrt(365) if sr.std() > 0 else 0
        sharpes.append(s)
    return {"random_sharpe_mean": float(np.mean(sharpes)),
            "random_sharpe_95pct": float(np.percentile(sharpes, 95))}
```

### 6.4 `scripts/04_backtest.py`

```python
"""跑回测, 出绩效 + OOS 净值图 + 基准对比 + 蒙特卡洛。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config.settings import settings
from config import constants as C
from src.strategy.portfolio import regime_conditional_positions, default_regime_weights
from src.strategy.backtest import backtest_single, monte_carlo_random
from src.research.robustness import time_split, cost_sensitivity
from src.research.multiple_testing import deflated_sharpe

np.random.seed(C.SEED)
PROC = Path(settings.processed_dir)
FIG = Path(settings.outputs_dir) / "figures"


def main():
    ts = pd.read_parquet(PROC / "factors_timeseries.parquet").set_index("date")
    regime = pd.read_parquet(PROC / "regime.parquet").set_index("date")["regime"]
    ohlcv = pd.read_parquet(PROC / "ohlcv.parquet")
    btc = ohlcv[ohlcv["id"] == 1].set_index("date")["close"].sort_index()

    # 用 03 标定的 regime 权重 (若有), 否则用默认
    research = json.loads(Path(settings.outputs_dir, "research_results.json").read_text())
    weights = build_weights_from_research(research) or default_regime_weights()

    factor_cols = [c for c in ts.columns if c in
                   sum([list(w.keys()) for w in weights.values()], [])]
    factors = ts[factor_cols].reindex(btc.index)

    # IS / OOS 切分
    cut, _ = time_split(btc.index, is_frac=0.7)
    pos = regime_conditional_positions(factors, regime, weights, max_pos=1.0)

    perf_is = backtest_single(pos[pos.index < cut], btc[btc.index < cut])
    perf_oos = backtest_single(pos[pos.index >= cut], btc[btc.index >= cut])

    # Deflated Sharpe (用研究阶段试验数)
    dsr = deflated_sharpe(perf_oos["returns"], n_trials=research.get("n_trials", 20))

    # 成本敏感性
    cost_df = cost_sensitivity(
        lambda fee: backtest_single(pos, btc, fee_bps=fee),
        cost_grid_bps=[0, 5, 10, 20, 40])

    # 蒙特卡洛
    mc = monte_carlo_random(btc)

    # === OOS 净值图 ===
    plt.figure(figsize=(9, 5))
    perf_oos["equity_curve"].plot(label="SignalForge (OOS)")
    btc_oos = btc[btc.index >= cut]
    (btc_oos / btc_oos.iloc[0]).plot(label="BTC HODL", alpha=0.7)
    plt.legend(); plt.title("Out-of-Sample Equity Curve")
    plt.ylabel("Cumulative"); plt.tight_layout()
    plt.savefig(FIG / "walkforward_oos.png", dpi=130); plt.close()

    out = {
        "in_sample": _clean(perf_is), "out_of_sample": _clean(perf_oos),
        "deflated_sharpe": dsr, "monte_carlo": mc,
        "cost_sensitivity": cost_df.drop(columns=["equity_curve", "returns"],
                                         errors="ignore").to_dict("records"),
        "regime_weights_used": weights,
        "is_oos_cut": str(cut),
    }
    Path(settings.outputs_dir, "backtest_results.json").write_text(
        json.dumps(out, indent=2, default=float))
    print(f"OOS Sharpe: {perf_oos['sharpe']:.2f} | Deflated prob: {dsr.get('deflated_sharpe_prob')}")
    print(f"随机信号 95% Sharpe: {mc['random_sharpe_95pct']:.2f} (策略需显著超过此值)")


def build_weights_from_research(research: dict) -> dict | None:
    """从 03 的 regime_ic 自动构建权重: 每 regime 选 IC 显著为正的因子。"""
    weights = {}
    for fname, fr in research.get("factors", {}).items():
        for rec in fr.get("regime_ic", []):
            reg, ic, n = rec.get("regime"), rec.get("ic"), rec.get("n", 0)
            if ic is None or np.isnan(ic) or n < 30:
                continue
            if abs(ic) > C.RANK_IC_THRESHOLD:
                weights.setdefault(reg, {})[fname] = float(np.sign(ic) * abs(ic))
    return weights or None


def _clean(perf: dict) -> dict:
    return {k: v for k, v in perf.items() if k not in ("equity_curve", "returns")}


if __name__ == "__main__":
    main()
```

---

## 7. LLM 层 (L5-a) — DeepSeek 完整集成

### 7.1 `src/llm/deepseek_client.py`

```python
"""DeepSeek 封装 (OpenAI 兼容)。记录所有 prompt/response 到 outputs/llm_logs。"""
from __future__ import annotations
import json
import time
from pathlib import Path

from openai import OpenAI
from config.settings import settings

_client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
_LOG = Path(settings.outputs_dir) / "llm_logs"
_LOG.mkdir(parents=True, exist_ok=True)


def chat(system: str, user: str, model: str = "deepseek-chat",
         temperature: float = 0.5, tag: str = "chat") -> str:
    resp = _client.chat.completions.create(
        model=model, temperature=temperature,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    text = resp.choices[0].message.content
    # 留痕 (可追溯, 防幻觉审计)
    (_LOG / f"{tag}_{int(time.time())}.json").write_text(
        json.dumps({"model": model, "system": system, "user": user,
                    "response": text, "usage": resp.usage.model_dump()}, indent=2))
    return text


def reason(system: str, user: str, temperature: float = 0.3, tag: str = "reason") -> str:
    """用 deepseek-reasoner 做需要推理的任务。"""
    return chat(system, user, model="deepseek-reasoner", temperature=temperature, tag=tag)
```

### 7.2 `src/llm/research_synth.py` — 因子假设综述 (reasoner)

```python
"""为每个有效因子生成经济学解释。LLM 只解释, 不造数字。"""
from __future__ import annotations
import json
from src.llm.deepseek_client import reason

SYSTEM = (
    "You are a quantitative researcher specializing in crypto market microstructure "
    "and behavioral finance. You explain WHY a factor has predictive power, grounded "
    "ONLY in the empirical statistics provided. NEVER invent numbers. If a statistic "
    "is not provided, do not state it. Be concise and rigorous."
)

USER_TMPL = """Factor: {name}
Definition: {definition}
Empirical results (do not alter these numbers):
- Overall Rank-IC: {ic}
- IR: {ir}
- t-stat: {t_stat}
- FDR significant: {fdr}
- Regime breakdown: {regime_ic}

Data source: CoinMarketCap PROPRIETARY Fear & Greed index (distinct from Alternative.me),
plus CMC global metrics (BTC dominance). 

Write 2-3 sentences explaining the economic/behavioral rationale for this factor's
predictive power, and in which regime it works best (based on the regime breakdown).
Frame it as a research hypothesis grounded in the data."""


def synthesize(factor_name: str, definition: str, stats: dict) -> str:
    user = USER_TMPL.format(
        name=factor_name, definition=definition,
        ic=stats.get("ic_overall"), ir=stats.get("ir"),
        t_stat=stats.get("t_stat"), fdr=stats.get("fdr_significant"),
        regime_ic=json.dumps(stats.get("regime_ic", [])[:5]),
    )
    return reason(SYSTEM, user, tag=f"synth_{factor_name}")
```

### 7.3 `src/llm/report_writer.py` — 报告撰写 + 数字核对 (chat)

```python
"""生成研究报告草稿, 并对数字做核对防幻觉。"""
from __future__ import annotations
import json
import re
from src.llm.deepseek_client import chat

SYSTEM = (
    "You are writing a quantitative research report for a hackathon (BNB Hack Track 2). "
    "Audience: CoinMarketCap / quant judges. Tone: rigorous, honest, confident but not "
    "hyped. CRITICAL: use ONLY the numbers in the provided JSON. Do not fabricate any "
    "statistic. The core narrative: CMC's PROPRIETARY Fear & Greed (distinct from "
    "Alternative.me) is an under-researched alpha source. Output GitHub-flavored markdown."
)


def write_report(research: dict, backtest: dict, factor_explanations: dict) -> str:
    user = f"""Write the research report. Sections:
1. Executive Summary (lead with the CMC-proprietary-F&G narrative)
2. Data & Methodology (CMC endpoints used; why ETF/social/on-chain were EXCLUDED -
   no historical API, can't backtest; point-in-time & survivorship-bias-free methods)
3. Factor Definitions
4. Factor Efficacy (IC/IR/t-stat/decay, regime heatmap)
5. CMC vs Alternative.me F&G comparison
6. Multiple-Testing Correction (FDR + Deflated Sharpe)
7. Strategy & Backtest (OOS curve, vs BTC HODL, cost sensitivity, monte-carlo)
8. Limitations & Future Work (be honest about sample/plan limits)

RESEARCH_RESULTS_JSON:
{json.dumps(research, default=float)[:8000]}

BACKTEST_RESULTS_JSON:
{json.dumps(backtest, default=float)[:4000]}

FACTOR_EXPLANATIONS:
{json.dumps(factor_explanations)[:4000]}

Reference figures by relative path: outputs/figures/ic_decay.png,
outputs/figures/regime_ic_heatmap.png, outputs/figures/walkforward_oos.png"""
    return chat(SYSTEM, user, temperature=0.5, tag="report")


def verify_numbers(report_md: str, research: dict, backtest: dict) -> list[str]:
    """抽取报告中的数字, 与 json 中的关键指标比对, 返回可疑项。"""
    warnings = []
    # 收集所有"真实"数字 (round 到 2 位)
    truth = set()
    def collect(o):
        if isinstance(o, dict):
            for v in o.values(): collect(v)
        elif isinstance(o, list):
            for v in o: collect(v)
        elif isinstance(o, (int, float)):
            try: truth.add(round(float(o), 2))
            except Exception: pass
    collect(research); collect(backtest)
    # 报告里出现的小数
    for m in re.findall(r"-?\d+\.\d+", report_md):
        val = round(float(m), 2)
        # 允许 0/1 等通用值
        if abs(val) > 1.5 and val not in truth and -val not in truth:
            warnings.append(f"报告数字 {m} 未在结果 JSON 中找到对应 (可能幻觉, 请人工核对)")
    return warnings
```

### 7.4 `src/spec/schema.py` + `src/spec/builder.py`

```python
# src/spec/schema.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class DataSource(BaseModel):
    provider: str
    endpoint: str
    field: Optional[str] = None
    note: Optional[str] = None
    is_proprietary: bool = False


class FactorSpec(BaseModel):
    id: str
    definition: str
    type: str
    rank_ic: Optional[float] = None
    ir: Optional[float] = None
    t_stat: Optional[float] = None
    fdr_significant: Optional[bool] = None
    rationale: Optional[str] = None


class StrategySpec(BaseModel):
    spec_version: str = "1.0"
    spec_id: str
    name: str
    created_at: str
    description: Optional[str] = None
    data_sources: list[DataSource]
    universe: dict
    factors: list[FactorSpec]
    regime: dict
    signal_to_position: dict
    execution_assumptions: dict
    backtest_window: dict
    reported_performance: dict
    reproducibility: dict
```

```python
# src/spec/builder.py
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from config.settings import settings
from config import constants as C
from src.spec.schema import StrategySpec, DataSource, FactorSpec


def build_spec(research: dict, backtest: dict, explanations: dict,
               descriptions: dict) -> StrategySpec:
    factors = []
    for fid, fr in research.get("factors", {}).items():
        if not fr.get("fdr_significant"):
            continue   # 只放通过检验的因子
        factors.append(FactorSpec(
            id=fid, definition=descriptions.get(fid, ""),
            type="timeseries" if fid.startswith(("fg_", "dom_", "mkt")) else "cross_section",
            rank_ic=fr.get("ic_overall"), ir=fr.get("ir"),
            t_stat=fr.get("t_stat"), fdr_significant=True,
            rationale=explanations.get(fid, ""),
        ))

    spec = StrategySpec(
        spec_id="signalforge-cmc-fg-regime-v1",
        name="CMC Proprietary F&G Regime-Aware Multi-Factor Strategy",
        created_at=datetime.now(timezone.utc).isoformat(),
        description=descriptions.get("_strategy", ""),
        data_sources=[
            DataSource(provider="CoinMarketCap", endpoint="/v3/fear-and-greed/historical",
                       field="value", is_proprietary=True,
                       note="CMC proprietary Fear & Greed, distinct from Alternative.me"),
            DataSource(provider="CoinMarketCap", endpoint="/v1/global-metrics/quotes/historical",
                       field="btc_dominance"),
            DataSource(provider="CoinMarketCap", endpoint="/v1/cryptocurrency/listings/historical",
                       note="point-in-time universe, survivorship-bias-free"),
            DataSource(provider="CoinMarketCap", endpoint="/v2/cryptocurrency/ohlcv/historical"),
        ],
        universe={"selection": "top_N_by_market_cap", "N": C.UNIVERSE_TOP_N,
                  "source": "listings/historical (point-in-time)",
                  "survivorship_handling": "delisted coins included within active window via map"},
        factors=factors,
        regime={"definition": {"direction": "BTC vs MA200 + dominance trend",
                               "sentiment": "CMC F&G percentile"},
                "factor_weights_by_regime": backtest.get("regime_weights_used", {})},
        signal_to_position={"method": "IR-weighted, regime-conditional",
                            "max_asset_weight": 0.30, "max_gross_leverage": 1.0,
                            "rebalance_frequency": "daily"},
        execution_assumptions={"signal_to_trade_lag_days": 1, "fee_bps": C.FEE_BPS,
                               "slippage_bps_by_size": C.SLIPPAGE_BPS},
        backtest_window={"in_sample_to_oos_cut": backtest.get("is_oos_cut")},
        reported_performance={"in_sample": backtest.get("in_sample"),
                              "out_of_sample": backtest.get("out_of_sample"),
                              "deflated_sharpe": backtest.get("deflated_sharpe")},
        reproducibility={"seed": C.SEED, "engine_version": "signalforge-0.1.0",
                         "reproduce_command": "python scripts/reproduce.py"},
    )
    return spec
```

### 7.5 `scripts/05_generate_spec.py`

```python
import json
from pathlib import Path

from config.settings import settings
from src.factors.timeseries import build_fg_factors  # for definitions ref
from src.llm.research_synth import synthesize
from src.llm.deepseek_client import chat
from src.spec.builder import build_spec

DEFINITIONS = {
    "fg_level": "CMC proprietary Fear&Greed raw value (0-100)",
    "fg_zscore_90": "90-day rolling z-score of CMC F&G",
    "fg_momentum_7": "7-day change of CMC F&G",
    "fg_extreme_rev": "+1 if CMC F&G<20, -1 if >80, else 0 (contrarian)",
    "fg_regime_dur": "consecutive days in current F&G classification",
    "fg_cross_dom": "interaction of (neg F&G z-score) and BTC dominance trend",
    "dom_trend_30": "30-day BTC dominance slope",
    "dom_zscore_90": "90-day z-score of BTC dominance",
    "mktcap_mom_30": "30-day total market-cap momentum",
}


def main():
    research = json.loads(Path(settings.outputs_dir, "research_results.json").read_text())
    backtest = json.loads(Path(settings.outputs_dir, "backtest_results.json").read_text())

    # 因子解释 (reasoner)
    explanations = {}
    for fid, fr in research.get("factors", {}).items():
        if fr.get("fdr_significant"):
            explanations[fid] = synthesize(fid, DEFINITIONS.get(fid, ""), fr)

    # 策略整体描述 (chat)
    desc = chat(
        "You write concise strategy descriptions. Use only provided facts.",
        f"Describe this regime-aware multi-factor strategy in 3 sentences. "
        f"Core edge: CMC proprietary F&G. Significant factors: "
        f"{[k for k,v in research['factors'].items() if v.get('fdr_significant')]}. "
        f"OOS Sharpe: {backtest.get('out_of_sample',{}).get('sharpe')}.",
        tag="strategy_desc")
    descriptions = {**DEFINITIONS, "_strategy": desc}

    spec = build_spec(research, backtest, explanations, descriptions)
    out = Path(settings.outputs_dir) / "specs" / f"{spec.spec_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(spec.model_dump_json(indent=2))
    print(f"Spec 已生成: {out}  (含 {len(spec.factors)} 个通过检验的因子)")


if __name__ == "__main__":
    main()
```

### 7.6 `scripts/06_write_report.py`

```python
import json
from pathlib import Path
from config.settings import settings
from src.llm.report_writer import write_report, verify_numbers

def main():
    research = json.loads(Path(settings.outputs_dir, "research_results.json").read_text())
    backtest = json.loads(Path(settings.outputs_dir, "backtest_results.json").read_text())
    spec_dir = Path(settings.outputs_dir) / "specs"
    spec = json.loads(next(spec_dir.glob("*.json")).read_text())
    explanations = {f["id"]: f.get("rationale", "") for f in spec.get("factors", [])}

    md = write_report(research, backtest, explanations)
    warns = verify_numbers(md, research, backtest)
    rpt = Path(settings.outputs_dir) / "reports" / "research_report.md"
    rpt.parent.mkdir(parents=True, exist_ok=True)
    rpt.write_text(md)
    if warns:
        print("⚠️ 数字核对警告 (人工复核):")
        for w in warns: print("  -", w)
    else:
        print("✅ 报告数字核对通过")
    print(f"报告: {rpt}")

if __name__ == "__main__":
    main()
```

### 7.7 `scripts/reproduce.py`

```python
"""一键复现: 从缓存数据出发, 固定 seed, 串联 02->05, 校验数字一致。"""
import subprocess, sys

STEPS = ["scripts/02_build_factors.py", "scripts/03_run_research.py",
         "scripts/04_backtest.py", "scripts/05_generate_spec.py"]

def main():
    for s in STEPS:
        print(f"\n>>> {s}")
        r = subprocess.run([sys.executable, s])
        if r.returncode != 0:
            print(f"FAILED at {s}"); sys.exit(1)
    print("\n✅ 复现完成。对比 outputs/ 下数字与提交版本应一致 (seed=42)。")

if __name__ == "__main__":
    main()
```

---

## 8. 提交物料、可选加分、检查清单

### 8.1 `README.md` 模板 (项目门面)

```markdown
# SignalForge

> The first systematic factor-research engine for CoinMarketCap's **proprietary**
> Fear & Greed index — an under-researched alpha source distinct from Alternative.me.

Built for BNB Hack Track 2 (Strategy Skills). Produces backtestable, regime-aware
strategy specs from CMC proprietary market signals.

## Why this is different
Most F&G research uses Alternative.me's public index. CMC has its OWN F&G algorithm
(volatility + momentum + volume + dominance + social). We're the first to rigorously
test its factor efficacy and engineer it into a reproducible strategy spec.

We deliberately EXCLUDED ETF-flow / social / on-chain signals — they have no
historical API and cannot be honestly backtested. Rigor over hype.

## Architecture
[贴 §2 架构图]

## Quickstart
[贴 §1 quickstart]

## Rigor (what makes this quant research, not a toy)
- Point-in-time factors, survivorship-bias-free universe (listings/historical + map)
- Look-ahead bias unit tests (tests/test_no_lookahead.py)
- IC / Rank-IC / IR / t-stat + IC decay
- Regime-layered attribution (factor × regime IC heatmap)
- Multiple-testing correction: BH-FDR + Deflated Sharpe
- Walk-forward OOS, parameter-plateau, cost sensitivity, monte-carlo baseline

## Outputs
- outputs/specs/*.json — backtestable strategy spec
- outputs/reports/research_report.md — full research report
- outputs/figures/*.png — IC decay, regime heatmap, OOS equity
- python scripts/reproduce.py — one-click reproduction (seed=42)

## CMC data usage (special-prize narrative)
Core alpha = CMC proprietary F&G (/v3/fear-and-greed/historical) +
BTC dominance (/v1/global-metrics) + point-in-time universe
(/v1/cryptocurrency/listings/historical). The strategy does not exist without CMC data.
```

### 8.2 (可选 M7) Skills Marketplace 封装

若要强化 CMC 特殊奖,把 spec 生成封装为可被 agent 调用的 skill:

```python
# src/spec/skill_wrapper.py  (可选)
"""把 SignalForge 暴露为一个 CMC-style skill: 输入资产/风险偏好, 返回定制 spec。"""
def run_skill(asset: str = "BTC", risk: str = "moderate") -> dict:
    # 1. 调 CMC 端点拉该资产最新 + 历史 F&G/dominance
    # 2. 套用预置因子库 + regime 权重
    # 3. 返回一个 StrategySpec.model_dump()
    ...
# 可再用 x402 包一层 pay-per-call (Base 链 0.01 USDC/调用)
```

### 8.3 (可选 M7) 三栈整合优先级

| 加分项 | 触达奖项 | 仅在 M0-M6 全绿后做 |
|---|---|---|
| Skills Marketplace + x402 封装 | 强化 CMC 特殊奖 | ✅ 优先 |
| BNB AI Agent SDK testnet 端到端 demo | BNB 特殊奖 | 次之 |
| Trust Wallet Agent Kit 签名 demo | TWT 特殊奖 | 次之 |

### 8.4 Demo 视频脚本 (3 分钟)

1. **0:00-0:20** 钩子: "所有人用 Alternative.me 的 F&G。CMC 有自己的、没人研究过的 F&G。我们挖出了它的 alpha。"
2. **0:20-0:50** 问题: 竞争者追 ETF/social → 无历史 API → 没法回测。我们选有扎实历史的 CMC 专有指标。
3. **0:50-1:40** 方法 + 展示 regime×因子 IC 热力图 (核心发现)。
4. **1:40-2:20** 严谨性: 反幸存者偏差、前视偏差单测、FDR/Deflated Sharpe。
5. **2:20-2:50** 结果: OOS 净值 vs BTC,一键复现演示。
6. **2:50-3:00** 收尾: 展示 spec JSON, "任何 agent 可消费可复现"。

### 8.5 提交前检查清单

**严谨性 (评分核心):**
- [ ] 所有 CMC 端点字段用真实样本核实
- [ ] `pytest tests/ -v` 全绿 (前视 + 幸存者偏差单测)
- [ ] 标准化/排名全部 point-in-time
- [ ] 报告含 FDR + Deflated Sharpe
- [ ] OOS 与 IS 分离,OOS 未用于调参
- [ ] 成本敏感性 + 蒙特卡洛随机基准

**CMC 特殊奖叙事:**
- [ ] 明确对比 CMC 自有 F&G vs Alternative.me (有对照实验)
- [ ] spec 中 `is_proprietary: true`
- [ ] README 第一段就是专有 F&G 叙事
- [ ] 报告写明为何排除 ETF/social/链上

**Track 2 交付:**
- [ ] spec JSON 通过 pydantic 校验且自包含
- [ ] `reproduce.py` 复现一致
- [ ] 报告完整 (8 章)

**可复现:**
- [ ] 全部 seed=42
- [ ] `.env.example` 提供,真 key 未入库
- [ ] 缓存数据让评委无 key 也能复现核心结果

**提交:**
- [ ] DoraHacks: 仓库 + 报告 PDF + Demo 视频 + spec 文件
- [ ] 06-21 12:00 UTC 前锁定

---

## 9. 关键陷阱速查 (MuleRun 易错点)

| 陷阱 | 正确做法 |
|---|---|
| 凭文档猜字段名写解析 | 先看 `data/raw/_samples/*.json` 真实键名 |
| 全样本标准化 | 只用滚动/截面内 (point-in-time) |
| `signal_t` 配 `return_t` | 必须 `signal_t` 配 `return_{t+1}` (shift) |
| 用今天榜单回溯历史 universe | 用当日 `listings/historical` 快照 |
| 重复拉同一历史端点 | 强缓存,命中即返回 |
| LLM 写数字 | LLM 只写文字,数字来自 Python + 核对脚本 |
| 在 OOS 上调参 | OOS 只验证,参数在 IS 定 |
| 漏设 seed | numpy/random/bootstrap 全设 42 |
| F&G 历史只拉 500 条 | 翻页 (调 start) 拉全历史 |
| 把 ETF flow 当因子 | 无历史 API,排除并在报告说明 |

---

## 10. 文件清单 (MuleRun 据此逐一创建)

```
config/settings.py          §2.5
config/constants.py         §2.6   (M0 后回填 TODO)
config/__init__.py          (空)
src/cmc/client.py           §3.1
src/cmc/endpoints.py        §3.2
src/cmc/schemas.py          §3.4   (M0 后校正字段)
src/factors/timeseries.py   §4.1
src/factors/cross_section.py §4.2
src/factors/regime.py       §4.3
src/research/ic.py          §5.1
src/research/regime_attrib.py §5.2
src/research/multiple_testing.py §5.3
src/research/robustness.py  §5.4
src/strategy/signals.py     §6.1
src/strategy/portfolio.py   §6.2
src/strategy/backtest.py    §6.3
src/llm/deepseek_client.py  §7.1
src/llm/research_synth.py   §7.2
src/llm/report_writer.py    §7.3
src/spec/schema.py          §7.4
src/spec/builder.py         §7.4
scripts/00_smoke_test.py    §3.3
scripts/01_pull_data.py     §3.5
scripts/02_build_factors.py §4.4
scripts/03_run_research.py  §5.5
scripts/04_backtest.py      §6.4
scripts/05_generate_spec.py §7.5
scripts/06_write_report.py  §7.6
scripts/reproduce.py        §7.7
tests/test_no_lookahead.py  §4.5
tests/test_survivorship.py  §4.6
pyproject.toml              §2.2
.env.example                §2.3
.gitignore                  §2.4
README.md                   §8.1
```

> 文档结束。MuleRun: 从 §2 脚手架开始,按 §0 协议逐文件创建并验收。**先跑 §3.3 冒烟测试拿到真实数据,是一切的前提。**
