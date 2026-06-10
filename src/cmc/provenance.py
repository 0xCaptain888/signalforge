"""
CMC data-provenance recorder.
Every CMC access through any channel (rest/mcp/x402) is appended to
outputs/cmc_provenance.json — the hard evidence that all three channels
of the CMC stack were used (CMC special prize).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"
PROVENANCE_FILE = OUTPUTS_DIR / "cmc_provenance.json"


def record(
    channel: str,           # "rest" | "mcp" | "x402"
    endpoint: str,
    description: str,
    payment_tx: Optional[str] = None,
    credits_used: int = 0,
    response_summary: Optional[str] = None,
) -> dict:
    """Record one CMC data access (appends to outputs/cmc_provenance.json)."""
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "endpoint": endpoint,
        "description": description,
        "payment_tx": payment_tx,
        "credits_used": credits_used,
        "response_summary": response_summary,
    }

    existing = []
    if PROVENANCE_FILE.exists():
        try:
            with open(PROVENANCE_FILE) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []

    existing.append(entry)
    PROVENANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVENANCE_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    return entry


def load() -> list:
    """Read all provenance records."""
    if not PROVENANCE_FILE.exists():
        return []
    with open(PROVENANCE_FILE) as f:
        return json.load(f)


def summary() -> dict:
    """Three-channel usage summary for README / judges."""
    records = load()
    channels: dict = {}
    for r in records:
        channels.setdefault(r["channel"], []).append(r)
    return {
        "total_calls": len(records),
        "channels_used": sorted(channels.keys()),
        "rest_calls": len(channels.get("rest", [])),
        "mcp_calls": len(channels.get("mcp", [])),
        "x402_calls": len(channels.get("x402", [])),
        "x402_txs": [r["payment_tx"] for r in channels.get("x402", []) if r.get("payment_tx")],
        "total_credits_used": sum(r.get("credits_used", 0) for r in records),
    }
