# SignalForge — 开发周期表 (Development Schedule)

> 基于《SignalForge — MuleRun 可执行开发文档 (Build-Ready)》(2040 行,§0–§10) 整理。
>
> 本文件按 **§0 执行协议 + §10 文件清单 + §8 提交物料 + §3.9/M0 回填指引** 拆解为 9 个阶段,
> 每个阶段给出任务粒度、顺序依赖、输入/输出、文件位置 (§ 编号)、验收标准。
>
> **不含小时/天数估计**:每环节实际耗时强依赖 CMC 档位、API 限流、数据可得性、调试反复次数。
> 你可按自己节奏推进或自行折算工时。
>
> - **项目:** SignalForge — CMC 专有指标因子研究引擎
> - **目标:** BNB Hack Track 2 第一名 $3,000 + CMC 特殊奖 $2,000
> - **LLM:** DeepSeek (`deepseek-chat` / `deepseek-reasoner`)
> - **执行器:** MuleRun AI Agent
> - **Python:** 3.11
> - **截止:** 2026-06-21 12:00 UTC

---

## 关键依赖关系 (必须严格按顺序)

```
阶段0 ──► 阶段1 ──► 阶段2 (M0冒烟+回填) ──► 阶段3 (M1+pytest) ──► 阶段4 (M2研究)
                                                                          │
                                                                          ▼
                                                            阶段5 (M3回测) ──► 阶段6 (M4 LLM+Spec)
                                                                                       │
                                                                                       ▼
                                                                       阶段7 (M5复现) ──► 阶段8 (M6提交)
                                                                                                │
                                                                                                ▼
                                                                                       阶段9 (M7可选)
```

**阻塞点 (任一失败必须停下回头改):**
- 阶段 2.5 冒烟 7 端点 → 决定 M0 后整张图的可行路径
- 阶段 3.8 `pytest` → 决定研究层数字是否可信
- 阶段 4.7 至少 1 个 FDR 显著因子 → 决定能否进入回测
- 阶段 5.6 OOS Sharpe > MC 95% → 决定是否需要回头加因子/换 horizon
- 阶段 7.2 复现一致 → 决定能否提交

---

## 铁律 (全程遵守)

- 任何 CMC 字段解析,**必须先看 `data/raw/_samples/` 里的真实 JSON**,不凭文档猜
- 所有随机性 `seed=42` (numpy / random / bootstrap 全部)
- **LLM 不算数字**,数字全来自 Python
- 密钥只在 `.env`,**永不入库**
- `signal_t` 必须配 `return_{t+1}` (shift),严禁 `signal_t` 配 `return_t`
- 标准化/排名全部 **point-in-time** (滚动/截面内,严禁全样本)
- OOS 只验证,参数在 IS 定

---

## 阶段 0 — 仓库初始化 (Pre-M0)

| # | 任务 | 输出物 | 验收 |
|---|---|---|---|
| 0.1 | 用 GitHub Token 创建新仓库 `signalforge` (私有/公开按需) | `github.com/<owner>/signalforge` | `gh repo view` 可见 |
| 0.2 | 本地建 Python 3.11 venv | `.venv/` | `python -V` == 3.11 |
| 0.3 | 写 `.gitignore` (§2.4) — 必须含 `.env`, `data/raw/*`, `!data/raw/_samples/`, `outputs/llm_logs/*` | `.gitignore` | `git status` 不显示 `.env` |
| 0.4 | 写 `.env.example` (§2.3) + 本地 `.env` 填入三把密钥 (CMC / DeepSeek;BNB 钱包私钥后续 M7 才用) | `.env.example`, `.env` | `.env` 已被 ignore |
| 0.5 | 写 `README.md` 第一段用 §8.1 模板 (叙事关键:CMC 专有 F&G) | `README.md` | 第一段即为 "The first systematic factor-research engine for CoinMarketCap's **proprietary** Fear & Greed index…" |
| 0.6 | 首次 commit + push | 远端 main 分支有初始 commit | GitHub 可见 |

### `.gitignore` 关键条目 (§2.4)

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

### `.env.example` 模板 (§2.3)

```bash
# CoinMarketCap Pro API
CMC_API_KEY=your_cmc_key_here
CMC_BASE_URL=https://pro-api.coinmarketcap.com

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Runtime
REQUEST_TIMEOUT=30
MAX_RETRIES=5
RATE_LIMIT_PER_MIN=28
```

---

## 阶段 1 — 项目脚手架 (§2)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 1.1 | 建目录树 (§2.1) | `signalforge/{config,data/raw/_samples,data/processed,src/{cmc,factors,research,strategy,llm,spec},scripts,tests,outputs/{specs,reports,figures,llm_logs}}` | `tree -L 3` 结构正确 |
| 1.2 | 全部 `__init__.py` 占位 | 9 个空文件 (`src/__init__.py`, `src/cmc/__init__.py`, `src/factors/__init__.py`, `src/research/__init__.py`, `src/strategy/__init__.py`, `src/llm/__init__.py`, `src/spec/__init__.py`, `config/__init__.py`) | `python -c "import src.cmc"` 不报错 |
| 1.3 | `pyproject.toml` (§2.2) — 含 httpx/pandas/numpy/pyarrow/scipy/statsmodels/pydantic/matplotlib/plotly/openai/python-dotenv/tenacity + dev:pytest/ruff | `pyproject.toml` | — |
| 1.4 | `config/settings.py` (§2.5) — pydantic Settings 加载 `.env` | — | `from config.settings import settings` ok |
| 1.5 | `config/constants.py` (§2.6) — 保留 `# TODO(M0)` 占位 (CMC_PLAN / FG_HISTORY_MAX_DAYS / OHLCV_EARLIEST / LISTINGS_HISTORICAL_AVAILABLE) | — | — |
| 1.6 | `pip install -e .` | — | **验收:安装成功,无依赖冲突** |

### `config/constants.py` 关键常量

```python
SEED = 42
UNIVERSE_TOP_N = 100
CONVERT = "USD"
FEE_BPS = 10
SLIPPAGE_BPS = {"large_cap": 5, "mid_cap": 10, "small_cap": 20}
RANK_IC_THRESHOLD = 0.03
T_STAT_THRESHOLD = 2.0
IR_THRESHOLD = 0.3
FDR_Q = 0.10
MA_WINDOW = 200
FG_FEAR = 33
FG_GREED = 66
HOLDING_PERIODS = [1, 5, 10, 20, 40]
# TODO(M0): 冒烟测试后回填
CMC_PLAN = "UNKNOWN"
FG_HISTORY_MAX_DAYS = None
OHLCV_EARLIEST = None
LISTINGS_HISTORICAL_AVAILABLE = None
```

---

## 阶段 2 — M0 数据层冒烟 (§3,**go/no-go 检查点**)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 2.1 | `src/cmc/client.py` (§3.1) — 重试 (tenacity 指数退避) + 限流 (令牌桶 28/min) + 缓存 (md5 path+params) + 原始落盘 + credit 计数 | — | import 通过 |
| 2.2 | `src/cmc/endpoints.py` (§3.2) — 7 个端点封装:<br>**A** `/v1/key/info` (0 credit, 档位/credits)<br>**B** `/v1/cryptocurrency/map` (0 credit, 含 first/last_historical_data)<br>**C** `/v1/cryptocurrency/listings/historical` (历史排名快照)<br>**D** `/v2/cryptocurrency/ohlcv/historical` (日线 OHLCV)<br>**E** ⭐ `/v3/fear-and-greed/historical` (CMC 自有 F&G)<br>**F** `/v1/global-metrics/quotes/historical` (dominance / 总市值)<br>**G** `/v1/global-metrics/quotes/latest` (altseason / cycle 探测) | — | — |
| 2.3 | `src/cmc/schemas.py` (§3.4) 初版 — `FearGreedPoint` / `OHLCVQuote` / `ListingRow` / `MapEntry` | — | — |
| 2.4 | `scripts/00_smoke_test.py` (§3.3) — 跑 7 端点,落样本,报告 plan 档位与数据可得性 | — | — |
| 2.5 | **运行冒烟** `python scripts/00_smoke_test.py` | `data/raw/_samples/*.json` 7 份 (`key_info.json` / `crypto_map.json` / `listings_historical.json` / `ohlcv_historical.json` / `fear_greed_historical.json` / `global_metrics_historical.json` / `global_metrics_latest.json`) | **验收 (go/no-go):7 端点除可选 [C]/[G] 外全 200;样本落盘;打印 plan 名、credits、F&G 最早/最晚日期** |
| 2.6 | **M0 回填** (§3.9):据样本核对 `schemas.py` 字段名 | 修改后的 `schemas.py` | 字段与样本 JSON 真实键一致 |
| 2.7 | **M0 回填**:据 [A]/[E]/[C]/[G] 输出填 `constants.py` 中 `CMC_PLAN` / `FG_HISTORY_MAX_DAYS` / `OHLCV_EARLIEST` / `LISTINGS_HISTORICAL_AVAILABLE` | `constants.py` | 无 `UNKNOWN`/`None` 占位 |
| 2.8 | (条件) 若 [C] 失败 → 标记走"纯时序退化方案",后续 §4.2 横截面会被跳过;若 [G] 无 altseason/cycle 字段 → 用 §4.2 的 `altseason_proxy` 自建 | — | — |
| 2.9 | `scripts/01_pull_data.py` (§3.5) — 翻页拉全部 F&G + 拉 global_metrics + 拉 map + 拉 top-N OHLCV + (条件) 拉月度 listings 快照 | — | — |
| 2.10 | 运行全量拉取 `python scripts/01_pull_data.py` | `data/processed/fear_greed.parquet`<br>`data/processed/global_metrics.parquet`<br>`data/processed/crypto_map.parquet`<br>`data/processed/ohlcv.parquet`<br>(条件) `data/processed/listings_snapshots.parquet` | parquet 行数 > 0,日期范围合理;终端打印总 credit 消耗 |

> ⚠️ **铁律检查**:`.env` 未入库;`data/raw/` 大文件未入库 (只入 `_samples/`)。

---

## 阶段 3 — M1 因子层 (§4)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 3.1 | `src/factors/timeseries.py` (§4.1) — `_roll_z` (滚动 z, min_periods=window 防早期 NaN) / `build_fg_factors` (fg_level, fg_zscore_90, fg_momentum_7, fg_extreme_rev, fg_regime_dur) / `build_dominance_factors` (dom_trend_30, dom_zscore_90, mktcap_mom_30) / `build_fg_dominance_cross` (fg_cross_dom 交互因子) | — | — |
| 3.2 | `src/factors/cross_section.py` (§4.2) — `build_cross_section_factors` (point-in-time, xs_rank_mom_30 / xs_size / xs_ret_mom_90 / xs_vol_60,日内 rank 标准化) | — | — |
| 3.3 | `src/factors/regime.py` (§4.3) — `label_regime` (BULL/BEAR/CHOP × FEAR/NEUTRAL/GREED 9 态,BTC vs MA200 + slope) | — | — |
| 3.4 | `tests/test_no_lookahead.py` (§4.5) — 前视偏差单测 (改最后一天不影响历史 + 前 89 天 zscore_90 必须 NaN) | — | — |
| 3.5 | `tests/test_survivorship.py` (§4.6) — point-in-time universe 单测 (t1={1,2}, t2={1,3} 币 2 退市/币 3 新上) | — | — |
| 3.6 | `scripts/02_build_factors.py` (§4.4) — 组装时序面板 + regime + (条件) 横截面 | — | — |
| 3.7 | 运行因子构建 `python scripts/02_build_factors.py` | `data/processed/factors_timeseries.parquet`<br>`data/processed/regime.parquet`<br>(条件) `data/processed/factors_cross_section.parquet` | regime 分布打印合理 (9 态都出现或解释为何缺) |
| 3.8 | **验收** `pytest tests/ -v` | — | **全绿** |

---

## 阶段 4 — M2 研究层 (§5,**评分核心**)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 4.1 | `src/research/ic.py` (§5.1) — `forward_returns` (shift(-h) 严格未来) / `timeseries_ic` (整体 spearman) / `rolling_ic_series` (滚动 60d) / `ir_and_tstat` / `cross_section_ic` (面板 rank-IC) / `ic_decay` (各持有期) | — | — |
| 4.2 | `src/research/regime_attrib.py` (§5.2) — `regime_layered_ic` (分 regime IC + t-stat) / `regime_ic_matrix` (因子×regime 热力图矩阵) | — | — |
| 4.3 | `src/research/multiple_testing.py` (§5.3) — `bh_fdr` (Benjamini-Hochberg FDR) + `deflated_sharpe` (López de Prado 防选择偏差) | — | — |
| 4.4 | `src/research/robustness.py` (§5.4) — `time_split` (IS/OOS 切分) / `walk_forward_windows` / `parameter_plateau` (网格扫描查高原) / `cost_sensitivity` | — | — |
| 4.5 | `scripts/03_run_research.py` (§5.5) — 跑全因子 IC/IR/t-stat/decay/regime + FDR 校正 + 出 2 张图 | — | — |
| 4.6 | 运行研究 `python scripts/03_run_research.py` | `outputs/research_results.json`<br>`outputs/figures/ic_decay.png`<br>`outputs/figures/regime_ic_heatmap.png` | json 含每因子 ic / p / ir / t_stat / decay / regime_ic / fdr_significant / p_adj;两张图清晰 |
| 4.7 | **验收**:至少 1 个因子 `fdr_significant=True` (否则需检查数据/扩展样本/换 horizon) | — | 打印行 "显著因子(FDR):" 列表非空 |

---

## 阶段 5 — M3 策略层 (§6)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 5.1 | `src/strategy/signals.py` (§6.1) — `factor_to_signal` (tanh 压缩 [-1,1]) / `combine_signals` (按权重归一合成) | — | — |
| 5.2 | `src/strategy/portfolio.py` (§6.2) — `regime_conditional_positions` (单资产择时按当日 regime 取权重) / `cross_section_positions` (top/bottom 分位等权 + 单资产上限 30%) / `default_regime_weights` (初始占位) | — | — |
| 5.3 | `src/strategy/backtest.py` (§6.3) — `backtest_single` (t→t+1 严格对齐 + turnover 成本) / `backtest_panel` / `_perf` (ann_return/vol/sharpe/sortino/calmar/max_dd/win_rate/turnover/alpha/beta) / `monte_carlo_random` (随机信号基准) | — | — |
| 5.4 | `scripts/04_backtest.py` (§6.4) — 含 `build_weights_from_research` (自动从 §4 结果按 \|IC\|>RANK_IC_THRESHOLD 生成 regime 权重) + IS/OOS 切分 + Deflated Sharpe + 成本敏感 + 蒙特卡洛 + OOS 净值图 | — | — |
| 5.5 | 运行回测 `python scripts/04_backtest.py` | `outputs/backtest_results.json`<br>`outputs/figures/walkforward_oos.png` | json 含 IS/OOS perf / deflated_sharpe / monte_carlo / cost_sensitivity / regime_weights_used / is_oos_cut;OOS 净值图 vs BTC HODL |
| 5.6 | **验收**:策略 OOS Sharpe 显著高于 `monte_carlo.random_sharpe_95pct` (否则需迭代因子/权重) | — | 终端打印两者并通过 |

---

## 阶段 6 — M4 LLM 层 + Spec 输出 (§7)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 6.1 | `src/llm/deepseek_client.py` (§7.1) — `chat` (deepseek-chat) + `reason` (deepseek-reasoner) + **全量 prompt/response 落盘** `outputs/llm_logs/` (防幻觉审计) | — | 测试调一次能正常返回,日志有 usage |
| 6.2 | `src/llm/research_synth.py` (§7.2) — 用 `deepseek-reasoner` 为每个 fdr 显著因子生成 2-3 句经济学/行为金融解释 (LLM 只解释,不造数字) | — | — |
| 6.3 | `src/llm/report_writer.py` (§7.3) — `write_report` (8 章报告) + **`verify_numbers` 抽取小数与 research/backtest JSON 比对,标记疑似幻觉** | — | — |
| 6.4 | `src/spec/schema.py` (§7.4) — `DataSource` / `FactorSpec` / `StrategySpec` (pydantic, spec_version="1.0") | — | — |
| 6.5 | `src/spec/builder.py` (§7.4) — `build_spec` (**只放 `fdr_significant=True` 因子**;附 data_sources/universe/regime/signal_to_position/execution_assumptions/backtest_window/reported_performance/reproducibility) | — | — |
| 6.6 | `scripts/05_generate_spec.py` (§7.5) — `DEFINITIONS` 字典 (fg_level/fg_zscore_90/fg_momentum_7/fg_extreme_rev/fg_regime_dur/fg_cross_dom/dom_trend_30/dom_zscore_90/mktcap_mom_30) + 跑 reasoner 生成 explanations + 写 spec JSON | — | `outputs/specs/signalforge-cmc-fg-regime-v1.json` 通过 pydantic 校验 |
| 6.7 | `scripts/06_write_report.py` (§7.6) | `outputs/reports/research_report.md` | `verify_numbers` 警告列表为空 (或全部人工核对解释) |
| 6.8 | **验收**:spec JSON 自包含、含 `is_proprietary: true`、引用三张图相对路径正确、含 reproducibility.seed=42 | — | — |

### 报告 8 章结构 (§7.3)

1. Executive Summary (lead with the CMC-proprietary-F&G narrative)
2. Data & Methodology (CMC endpoints used;why ETF/social/on-chain were EXCLUDED — no historical API;point-in-time & survivorship-bias-free)
3. Factor Definitions
4. Factor Efficacy (IC/IR/t-stat/decay, regime heatmap)
5. CMC vs Alternative.me F&G comparison
6. Multiple-Testing Correction (FDR + Deflated Sharpe)
7. Strategy & Backtest (OOS curve, vs BTC HODL, cost sensitivity, monte-carlo)
8. Limitations & Future Work (be honest about sample/plan limits)

---

## 阶段 7 — M5 复现与一致性 (§7.7)

| # | 任务 | 文件 | 验收 |
|---|---|---|---|
| 7.1 | `scripts/reproduce.py` (§7.7) — 串 02 → 03 → 04 → 05,固定 seed | — | — |
| 7.2 | 清空 `outputs/` 后跑 `python scripts/reproduce.py` | 重新生成 outputs | **验收:与提交版数字逐项一致 (seed=42)** |
| 7.3 | 评委零密钥复现验证:仅靠 `data/raw/_samples/` + `data/processed/` 缓存,跑 02 → 05 可还原核心数字 | — | 通过 |

---

## 阶段 8 — M6 提交物料 (§8)

| # | 任务 | 输出 | 验收 |
|---|---|---|---|
| 8.1 | README 补齐 §8.1 全部章节 (Why this is different / 架构图 / Quickstart / Rigor 6 条 / Outputs / CMC data usage 叙事) | `README.md` | — |
| 8.2 | 报告 PDF (将 `research_report.md` 渲染为 PDF) | `outputs/reports/research_report.pdf` | 含全部 8 章 + 三张图 |
| 8.3 | Demo 视频 (3 分钟,按 §8.4 脚本) | `.mp4` | 含 6 段 |
| 8.4 | **§8.5 提交前检查清单 26 项**逐项过 | clipboard 全 ✅ | 必过项全 ✅ |
| 8.5 | DoraHacks 提交 (仓库 + PDF + 视频 + spec) | 提交记录 | **截止 2026-06-21 12:00 UTC 前完成** |

### Demo 视频脚本 (§8.4)

| 时间 | 内容 |
|---|---|
| 0:00–0:20 | 钩子:"所有人用 Alternative.me 的 F&G。CMC 有自己的、没人研究过的 F&G。我们挖出了它的 alpha。" |
| 0:20–0:50 | 问题:竞争者追 ETF/social → 无历史 API → 没法回测。我们选有扎实历史的 CMC 专有指标。 |
| 0:50–1:40 | 方法 + 展示 regime×因子 IC 热力图 (核心发现)。 |
| 1:40–2:20 | 严谨性:反幸存者偏差、前视偏差单测、FDR/Deflated Sharpe。 |
| 2:20–2:50 | 结果:OOS 净值 vs BTC,一键复现演示。 |
| 2:50–3:00 | 收尾:展示 spec JSON, "任何 agent 可消费可复现"。 |

### §8.5 提交前检查清单 (26 项)

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

## 阶段 9 — M7 可选加分 (§8.2 / §8.3,仅在 M0–M6 全绿后启动)

| 优先级 | 任务 | 文件/动作 | 触达奖项 |
|---|---|---|---|
| ⭐ 高 | Skills Marketplace 封装:`src/spec/skill_wrapper.py` 的 `run_skill(asset, risk)` (§8.2) — 输入资产/风险偏好,返回定制 spec | 新增文件 | 强化 CMC 特殊奖 |
| ⭐ 高 | x402 包一层 pay-per-call (Base 链 0.01 USDC/调用) | 新增 | 强化 CMC 特殊奖 |
| 中 | BNB AI Agent SDK testnet 端到端 demo (用 BNB 测试网钱包做一次签名/交易演示) | 新增 demo 脚本 | BNB 特殊奖 |
| 中 | Trust Wallet Agent Kit 签名 demo | 新增 demo 脚本 | TWT 特殊奖 |

> ⚠️ **安全提示**:文档中给出的 BNB 测试网私钥已在会话中暴露。提交/上线前请把该测试网钱包内的余额转走并**作废该私钥**,改用新生成的钱包,并确认 `.env` (以及任何 demo 脚本) 未把私钥入库。

---

## 总文件清单 (§10,32 个待创建文件)

```
config/settings.py              §2.5
config/constants.py             §2.6   (M0 后回填 TODO)
config/__init__.py              (空)
src/cmc/client.py               §3.1
src/cmc/endpoints.py            §3.2
src/cmc/schemas.py              §3.4   (M0 后校正字段)
src/factors/timeseries.py       §4.1
src/factors/cross_section.py    §4.2
src/factors/regime.py           §4.3
src/research/ic.py              §5.1
src/research/regime_attrib.py   §5.2
src/research/multiple_testing.py §5.3
src/research/robustness.py      §5.4
src/strategy/signals.py         §6.1
src/strategy/portfolio.py       §6.2
src/strategy/backtest.py        §6.3
src/llm/deepseek_client.py      §7.1
src/llm/research_synth.py       §7.2
src/llm/report_writer.py        §7.3
src/spec/schema.py              §7.4
src/spec/builder.py             §7.4
scripts/00_smoke_test.py        §3.3
scripts/01_pull_data.py         §3.5
scripts/02_build_factors.py     §4.4
scripts/03_run_research.py      §5.5
scripts/04_backtest.py          §6.4
scripts/05_generate_spec.py     §7.5
scripts/06_write_report.py      §7.6
scripts/reproduce.py            §7.7
tests/test_no_lookahead.py      §4.5
tests/test_survivorship.py      §4.6
pyproject.toml                  §2.2
.env.example                    §2.3
.gitignore                      §2.4
README.md                       §8.1
```

---

## 关键陷阱速查 (§9 — MuleRun 易错点)

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

## 快速开始命令序列 (§1)

```bash
# 1. 克隆/创建项目后
cp .env.example .env
# 编辑 .env, 填入 CMC_API_KEY 和 DEEPSEEK_API_KEY

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

> **文档结束。** 按阶段 0 → 9 顺序推进,每阶段验收通过再进下一阶段。
> **先跑 §3.3 冒烟测试拿到真实数据,是一切的前提。**
