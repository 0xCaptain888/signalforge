#!/usr/bin/env python3
"""init_outputs.py — create outputs/ structure + initial REST provenance record."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUTS = ROOT / "outputs"
for d in ["specs", "verdicts", "onchain", "reports", "figures", "llm_logs"]:
    (OUTPUTS / d).mkdir(parents=True, exist_ok=True)
    gitkeep = OUTPUTS / d / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(f"  {OUTPUTS.name}/{d}/")

prov = OUTPUTS / "cmc_provenance.json"
if not prov.exists():
    prov.write_text("[]")

# P3-6: seed an initial REST provenance record (idempotent)
try:
    from src.cmc.provenance import record, load
    if not load():
        record(
            channel="rest",
            endpoint="https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical",
            description=("Historical F&G data: 1075 days (2023-06-29 to 2026-06-07). "
                         "CMC proprietary signal — primary alpha source in v1 research."),
            credits_used=1,
            response_summary="1075 daily F&G readings committed to data/fear_greed.parquet",
        )
        print("  Initial REST provenance record added")
    else:
        print("  provenance.json already has records, skipping seed")
except Exception as e:
    print(f"  NOTE: could not add initial provenance record: {e}")

print("\noutputs/ initialized")
