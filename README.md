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
historical API and cannot be honestly backtested. **Rigor over hype.**

## Status

Stage 1 complete (project installs cleanly via `pip install -e .`).
See full plan in [development schedule](./docs/SignalForge-开发周期表.md).

| Stage | Status |
|---|---|
| 0 — Repo init | ✅ done |
| 1 — Scaffold | ✅ done |
| 2 — M0 Data layer smoke | 🚧 next |
| 3 — M1 Factor layer | ⏳ pending |
| 4 — M2 Research layer | ⏳ pending |
| 5 — M3 Strategy layer | ⏳ pending |
| 6 — M4 LLM + Spec | ⏳ pending |
| 7 — M5 Reproducibility | ⏳ pending |
| 8 — M6 Submission | ⏳ pending |
| 9 — M7 Optional add-ons | ⏳ pending |

## Quickstart

```bash
cp .env.example .env
# edit .env, fill in CMC_API_KEY and DEEPSEEK_API_KEY

python -m venv .venv && source .venv/bin/activate
pip install -e .

# go/no-go smoke test (after Stage 2)
python scripts/00_smoke_test.py
```

## Architecture (planned)

```
config/        runtime settings + project constants
src/cmc/       CMC API client + endpoints + schemas
src/factors/   timeseries + cross-section + regime factors
src/research/  IC / IR / t-stat / FDR / robustness
src/strategy/  signals + portfolio + backtest
src/llm/       DeepSeek client + factor synth + report writer
src/spec/      pydantic StrategySpec schema + builder
scripts/       00_smoke → 06_write_report → reproduce
tests/         no-lookahead + survivorship-bias unit tests
outputs/       specs / reports / figures / llm_logs
```

## License

Apache-2.0 (TBD)
