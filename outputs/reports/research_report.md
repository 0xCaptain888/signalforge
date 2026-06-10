# CMC Proprietary Fear & Greed as a Cross-Sectional Alpha Source: A Rigorous Empirical Evaluation

## 1. Executive Summary

This research investigates whether CoinMarketCap's proprietary Fear & Greed (F&G) index—a distinct metric from the widely-known Alternative.me version—contains predictive information for cross-sectional cryptocurrency returns. Despite the popularity of sentiment-based trading strategies, the CMC F&G index remains surprisingly under-researched as a systematic alpha source.

**Key Findings:**
- Raw F&G level shows negligible overall predictive power (IC = 0.0063, p = 0.837)
- However, regime-conditional analysis reveals statistically significant predictive ability during specific market states
- The F&G momentum factor achieves IC of 0.226 (p = 0.022) during BEAR_FEAR regimes
- The extreme reversal factor shows IC of 0.289 (p = 0.008) during CHOP_GREED regimes
- After multiple-testing correction (FDR), **no factor survives as statistically significant** (all p_adj > 0.05)
- Out-of-sample strategy performance is negative (Sharpe = -0.99), suggesting the in-sample patterns may not be tradeable

**Bottom Line:** CMC F&G contains regime-dependent signals, but the overall evidence for a robust, tradeable alpha factor is weak. The signals are most promising during fear/greed extremes in choppy markets, but transaction costs and out-of-sample degradation eliminate any edge.

## 2. Data & Methodology

### Data Sources
- **Primary:** CoinMarketCap proprietary Fear & Greed Index (daily)
- **Universe:** Top 100 cryptocurrencies by market capitalization (rebalanced monthly)
- **Sample Period:** ~1,071 trading days (approximately 3 years)
- **Return Horizon:** 5-day forward returns

### Excluded Data & Rationale

| Data Type | Reason for Exclusion |
|-----------|---------------------|
| ETF flows | No historical API available for point-in-time backtesting |
| Social sentiment | Cannot verify historical accuracy; survivorship bias concerns |
| On-chain metrics | Inconsistent historical coverage across universe |

**Critical Methodological Choices:**
1. **Point-in-time construction:** All factor values use only information available at the signal date
2. **Survivorship-bias-free:** Universe includes coins that were top-100 at each rebalance, even if subsequently delisted
3. **No look-ahead:** F&G index values are used as published, without any forward-filling or interpolation

### Backtest Structure
- **In-sample:** 752 days (through 2025-07-20)
- **Out-of-sample:** 322 days (2025-07-21 onward)
- **Rebalance frequency:** Daily (signal-based)
- **Transaction costs:** 10 bps per trade (baseline), sensitivity tested from 0-40 bps

## 3. Factor Definitions

We constructed five factors from the CMC F&G index:

| Factor | Definition | Rationale |
|--------|------------|-----------|
| **fg_level** | Raw F&G value (0-100) | Tests linear predictive power of sentiment level |
| **fg_zscore_90** | Z-score of F&G relative to 90-day rolling mean | Captures deviations from recent sentiment norms |
| **fg_momentum_7** | 7-day change in F&G | Tests whether sentiment momentum predicts returns |
| **fg_extreme_rev** | Binary: 1 if F&G > 90 or < 10, else 0 | Tests extreme sentiment reversal hypothesis |
| **fg_regime_dur** | Days since last regime change | Tests whether regime persistence has predictive power |

All factors are cross-sectionally ranked and normalized to z-scores at each time point.

## 4. Factor Efficacy

### Overall Information Coefficients

| Factor | IC | p-value | IR | t-stat |
|--------|-----|---------|-----|--------|
| fg_level | 0.0063 | 0.837 | -1.388 | -44.15 |
| fg_zscore_90 | 0.0171 | 0.594 | -0.826 | -25.09 |
| fg_momentum_7 | -0.0311 | 0.311 | -0.684 | -21.69 |
| fg_extreme_rev | -0.0256 | 0.403 | 0.828 | 18.74 |
| fg_regime_dur | -0.0282 | 0.357 | -0.125 | -3.97 |

**Interpretation:** None of the factors show statistically significant overall predictive power at conventional levels. The high t-statistics (in absolute value) with non-significant ICs suggest the factors have consistent but very small effects.

### IC Decay

The predictive power of factors decays over longer horizons:

| Horizon | fg_level | fg_zscore_90 | fg_momentum_7 | fg_extreme_rev | fg_regime_dur |
|---------|----------|--------------|---------------|----------------|---------------|
| 1 day | 0.014 | 0.014 | -0.024 | -0.018 | -0.002 |
| 5 days | 0.006 | 0.017 | -0.031 | -0.026 | -0.028 |
| 10 days | 0.032 | 0.046 | 0.010 | -0.033 | -0.007 |
| 20 days | 0.024 | 0.061 | 0.029 | -0.008 | 0.070 |
| 40 days | -0.008 | 0.050 | 0.060 | 0.061 | 0.040 |

**Key insight:** Predictive power is generally weak at short horizons but shows some reversal at longer horizons (20-40 days), suggesting potential mean-reversion in sentiment effects.

### Regime-Conditional IC Heatmap

The most striking finding emerges when we condition on market regimes:

| Regime | fg_level | fg_zscore_90 | fg_momentum_7 | fg_extreme_rev | fg_regime_dur |
|--------|----------|--------------|---------------|----------------|---------------|
| **CHOP_FEAR** | 0.135 | 0.011 | 0.090 | 0.042 | -0.265* |
| **BEAR_NEUTRAL** | 0.112 | 0.015 | 0.076 | NaN | -0.168 |
| **BEAR_FEAR** | 0.034 | **0.200*** | **0.226*** | -0.103 | **0.228*** |
| **BULL_GREED** | -0.012 | 0.128 | -0.021 | 0.013 | -0.166* |
| **BULL_NEUTRAL** | -0.112* | -0.082 | -0.116* | NaN | 0.061 |
| **BULL_FEAR** | -0.197 | -0.550** | -0.480* | 0.184 | -0.555** |
| **CHOP_NEUTRAL** | -0.295*** | -0.096 | -0.092 | NaN | -0.189** |
| **CHOP_GREED** | -0.313** | 0.040 | -0.232* | **0.289**** | **0.258*** |

*Significance: * p < 0.05, ** p < 0.01, *** p < 0.001*

**Critical regime-specific signals:**
1. **BEAR_FEAR:** fg_zscore_90 (IC = 0.200, p = 0.043) and fg_momentum_7 (IC = 0.226, p = 0.022) show positive predictive power
2. **CHOP_GREED:** fg_extreme_rev (IC = 0.289, p = 0.008) and fg_regime_dur (IC = 0.258, p = 0.019) show strong positive signals
3. **BULL_FEAR:** Multiple factors show strong negative ICs, suggesting contrarian signals during fear in bull markets

## 5. CMC vs Alternative.me F&G Comparison

While a direct head-to-head comparison was not possible due to data limitations, we note several important distinctions:

| Feature | CMC F&G | Alternative.me |
|---------|---------|----------------|
| **Data sources** | Proprietary CMC data | Public market data |
| **Calculation methodology** | Not publicly disclosed | Transparent formula |
| **Historical availability** | Limited (~3 years) | Extended history |
| **Cross-sectional application** | Directly applicable | Not designed for ranking |

**Key advantage of CMC F&G:** The index is constructed from CMC's proprietary data streams, potentially capturing unique signals not available in public alternatives. However, the lack of transparency in methodology makes it difficult to attribute performance to specific data sources.

## 6. Multiple-Testing Correction

Given we tested 5 factors across 8 regimes (40 regime-conditional tests) plus 5 overall tests (45 total trials), we apply rigorous correction:

### False Discovery Rate (FDR) Correction

| Factor | Raw p-value | Adjusted p-value | FDR Significant? |
|--------|-------------|------------------|------------------|
| fg_level | 0.837 | 0.837 | No |
| fg_zscore_90 | 0.594 | 0.742 | No |
| fg_momentum_7 | 0.311 | 0.672 | No |
| fg_extreme_rev | 0.403 | 0.672 | No |
| fg_regime_dur | 0.357 | 0.672 | No |

**Result:** After FDR correction, **no factor achieves statistical significance** at the 5% level.

### Deflated Sharpe Ratio

The out-of-sample strategy achieves:
- **Annualized Sharpe:** -0.99
- **Deflated Sharpe probability:** 0.08%
- **Number of trials:** 45
- **Number of observations:** 322

**Interpretation:** The probability that the observed Sharpe ratio is due to luck, given 45 trials, is 0.08%. This suggests the strategy's negative performance is unlikely to be a statistical fluke—but it's also not positive.

## 7. Strategy & Backtest

### Strategy Construction

We built a long-short portfolio using regime-conditional factor weights:

1. **Regime classification:** Daily F&G level + trend filter determines regime (8 regimes)
2. **Factor weighting:** Within each regime, factors with positive IC are weighted proportionally
3. **Portfolio:** Top/bottom decile long/short, equal-weighted within each side
4. **Rebalancing:** Daily, with 10 bps transaction cost assumption

### Out-of-Sample Performance

| Metric | In-Sample | Out-of-Sample |
|--------|-----------|---------------|
| Annual Return | -18.4% | -5.4% |
| Annual Volatility | 19.8% | 5.6% |
| Sharpe Ratio | -1.03 | -0.99 |
| Max Drawdown | -47.0% | -6.0% |
| Win Rate | 46.4% | 15.8% |
| Alpha vs BTC | -4.0% | -4.5% |
| Beta vs BTC | -0.21 | 0.02 |

**Critical observation:** The strategy underperforms a simple BTC HODL strategy in both in-sample and out-of-sample periods. The negative alpha suggests the factors are capturing noise rather than genuine predictive signals.

### Cost Sensitivity Analysis

| Fee (bps) | Annual Return | Sharpe | Max DD |
|-----------|--------------|--------|--------|
| 0 | -12.3% | -0.78 | -44.1% |
| 5 | -13.6% | -0.87 | -45.4% |
| 10 | -14.9% | -0.96 | -47.6% |
| 20 | -17.5% | -1.14 | -51.9% |
| 40 | -22.3% | -1.49 | -59.3% |

**Key insight:** Even at zero transaction costs, the strategy is unprofitable. This is not a cost-driven failure but a fundamental lack of signal.

### Monte Carlo Simulation

To assess whether the strategy's performance could be achieved by random portfolios:

| Metric | Value |
|--------|-------|
| Random Sharpe Mean | 0.03 |
| Random Sharpe 95th %ile | 1.00 |
| Random Sharpe Std Dev | 0.57 |
| Strategy Sharpe | -0.99 |

**Interpretation:** The strategy's Sharpe ratio (-0.99) is approximately 1.8 standard deviations below the mean of random portfolios. This suggests the strategy is systematically destroying value rather than capturing alpha.

## 8. Limitations & Future Work

### Honest Limitations

1. **Short sample period (~3 years):** The crypto market has undergone only one full cycle during this period. Regime-specific findings may not generalize.

2. **Data opacity:** CMC's F&G methodology is proprietary, making it impossible to verify or replicate the index construction.

3. **Survivorship bias in universe:** While we avoid look-ahead bias, the top-100 universe itself is a form of conditioning that may affect results.

4. **Regime classification sensitivity:** The 8-regime classification is arbitrary and may not represent true market states.

5. **Multiple testing:** Even after FDR correction, the number of implicit tests (regime selection, factor construction) is larger than accounted for.

6. **No fundamental anchor:** Unlike traditional factors (value, momentum), sentiment factors lack a clear economic rationale for persistence.

### Future Work

1. **Extend sample period:** As CMC accumulates more F&G history, re-run analysis with 5+ years of data.

2. **Alternative regime definitions:** Test regime classification based on volatility regimes, trend strength, or macroeconomic states.

3. **Non-linear signals:** Explore threshold effects (e.g., only extreme F&G values matter) rather than linear rankings.

4. **Combine with traditional factors:** Test whether F&G adds value beyond momentum, value, and size factors.

5. **Machine learning approaches:** Use random forests or gradient boosting to capture complex interactions between F&G components.

6. **Cross-asset validation:** Test whether F&G signals predict returns in DeFi tokens, stablecoins, or derivatives.

**Conclusion:** While CMC's proprietary F&G index shows intriguing regime-conditional signals, the overall evidence does not support its use as a standalone alpha source. The most promising signals (extreme reversal in choppy markets, momentum in bear/fear regimes) warrant further investigation but currently lack the robustness required for live trading.