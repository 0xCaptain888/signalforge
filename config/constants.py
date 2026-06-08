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

# TODO(M0): Back-fill after smoke test
CMC_PLAN = "UNKNOWN"                  # e.g. "Startup" / "Standard" / "Basic"
FG_HISTORY_MAX_DAYS = None            # Actual max records F&G history endpoint returns
OHLCV_EARLIEST = None                 # Earliest OHLCV date your plan can fetch
LISTINGS_HISTORICAL_AVAILABLE = None  # bool: is listings/historical available on this plan
