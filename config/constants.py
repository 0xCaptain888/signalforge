"""Project-level constants.

TODO(M0) marked items must be back-filled after running scripts/00_smoke_test.py
against the live CMC API, based on what your plan actually returns.
"""

# Backtest / factor universals
SEED = 42
UNIVERSE_TOP_N = 100          # cross-section universe size
CONVERT = "USD"

# Trading cost assumptions (bps)
FEE_BPS = 10
SLIPPAGE_BPS = {"large_cap": 5, "mid_cap": 10, "small_cap": 20}

# Factor screening thresholds
RANK_IC_THRESHOLD = 0.03
T_STAT_THRESHOLD = 2.0
IR_THRESHOLD = 0.3
FDR_Q = 0.10

# Regime thresholds
MA_WINDOW = 200               # BTC trend MA
FG_FEAR = 33                  # CMC proprietary F&G fear line
FG_GREED = 66                 # CMC proprietary F&G greed line

# Holding periods (for IC-decay test)
HOLDING_PERIODS = [1, 5, 10, 20, 40]

# --- M0 back-fill (filled 2026-06-08 from scripts/00_smoke_test.py) ---
# Key tested: 4466eccb… (CMC_API_KEY in .env). 7-endpoint smoke produced:
#   [A] key/info             OK   (Basic plan, 15000 credits/mo, 50 req/min)
#   [B] crypto/map           OK   (id/name/symbol/slug/rank/is_active/
#                                  first_historical_data/last_historical_data/platform)
#   [C] listings/historical  403  (NOT available on Basic plan)
#   [D] ohlcv/historical     403  (NOT available on Basic plan)
#   [E] /v3/fear-and-greed/  OK   ★ 500 rows newest-first, value=int 0-100,
#                                  timestamp=UNIX-seconds-as-string
#   [F] global-metrics/hist  403  (NOT available on Basic plan)
#   [G] global-metrics/latest OK  (has btc/eth dominance + defi/stablecoin/
#                                  derivatives mkt cap; NO altcoin_season field)
CMC_PLAN = "Basic"
CMC_PLAN_CREDITS_PER_MONTH = 15_000
CMC_PLAN_RATE_LIMIT_PER_MIN = 50
FG_HISTORY_MAX_DAYS = 500             # per page; paginate via start= for more
OHLCV_EARLIEST = None                 # CMC ohlcv/historical NOT available on Basic
# Effective OHLCV start achieved via the Binance fallback
# (scripts/01_pull_data.py::pull_ohlcv_via_binance). Filled by the
# Stage 2-7 audit re-pass so downstream tooling never has to re-read
# the parquet to know the data window.
OHLCV_EARLIEST_VIA_FALLBACK = "2023-06-29"  # earliest BTCUSDT 1d kline in cached pull
OHLCV_LATEST_VIA_FALLBACK = "2026-06-07"    # latest BTCUSDT 1d kline in cached pull
OHLCV_FALLBACK_PROVIDER = "binance"         # public /api/v3/klines; no key required
LISTINGS_HISTORICAL_AVAILABLE = False # listings/historical NOT available on Basic
GLOBAL_METRICS_HISTORICAL_AVAILABLE = False
GLOBAL_LATEST_HAS_ALTSEASON_FIELD = False  # build proxy in §4.2 per doc

# Fallback price source for backtest (CMC ohlcv/historical 403 on Basic).
# Resolved during Stage 2.9: Binance public klines are used (see
# scripts/01_pull_data.py::pull_ohlcv_via_binance). Kept as documentation
# so future plan upgrades can swap providers without grepping comments.
PRICE_SOURCE_FALLBACK = "binance"     # one of: "binance" | "coingecko" | "yahoo" | None
