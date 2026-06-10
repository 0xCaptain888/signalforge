"""
APEX adjudication server — wraps signal adjudication as an on-chain settleable
agent service (ERC-8183 + UMA OOv3 on BSC Testnet).

asyncio compatibility note (P3-8):
- uvicorn runs an asyncio event loop
- bnbagent.apex.server is async internally
- run_adjudication below is `async def` -> fully compatible with uvicorn

Contracts (BSC Testnet):
  Identity Registry : 0x8004A818BFB912233c491871b3d84c89A494BD9e
  Commerce ERC-8183 : 0x3464e64dD53bC093c53050cE5114062765e9F1b6
  Evaluator UMA OOv3: 0x5f4976ACBCD2968D08273bA9f4a67FA43C4A3af3
  Payment Token U   : 0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logger = logging.getLogger(__name__)

ONCHAIN_DIR = Path(__file__).resolve().parent.parent.parent / "outputs" / "onchain"
JOB_LIFECYCLE_FILE = ONCHAIN_DIR / "job_lifecycle.json"


def _parse_adjudication_request(job: dict):
    """Parse the adjudication request from the APEX job description field."""
    description = job.get("description", "{}")
    try:
        req = json.loads(description)
    except json.JSONDecodeError:
        req = {
            "candidate_signal": {
                "name": "unknown",
                "source": "unknown",
                "definition": description,
                "holding_period_days": 5,
            }
        }
    asset = req.get("asset")
    candidate_signal = req.get("candidate_signal", {
        "name": "default",
        "source": "cmc_fear_greed",
        "definition": "fg < 20 -> long; fg > 80 -> short",
        "holding_period_days": 5,
    })
    risk = req.get("risk", "balanced")
    return asset, candidate_signal, risk


async def run_adjudication(job: dict):
    """
    APEX on_job callback — runs adjudication for every funded job.

    Returns:
        (deliverable_str, metadata_dict)
        deliverable_str: verdict JSON (uploaded to IPFS, hash on-chain)
        metadata_dict: summary metadata (recorded on-chain)
    """
    job_id = job.get("jobId")
    logger.info("[APEX] Processing job #%s ...", job_id)

    asset, candidate_signal, risk = _parse_adjudication_request(job)

    from src.adjudicator.core import adjudicate
    verdict = adjudicate(
        asset=asset,
        candidate_signal=candidate_signal,
        risk=risk,
        include_cmc_snapshot=True,
    )

    deliverable_str = json.dumps(verdict, default=str, indent=2)
    meta = {
        "jobId": job_id,
        "verdict": verdict["verdict"],
        "edge_confidence": verdict["edge_confidence"],
        "adjudicator_version": "2.1.0",
        "leaked": verdict["leakage_check"]["leaked"],
        "cmc_channels": verdict["cmc_data_provenance"]["access_channels_used"],
    }
    logger.info("[APEX] Job #%s: verdict=%s, confidence=%s",
                job_id, meta["verdict"], meta["edge_confidence"])

    _record_job(job_id, job, meta)
    return deliverable_str, meta


def _record_job(job_id, job: dict, meta: dict):
    """Append job execution record to outputs/onchain/job_lifecycle.json."""
    ONCHAIN_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    if JOB_LIFECYCLE_FILE.exists():
        try:
            with open(JOB_LIFECYCLE_FILE) as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.append({
        "jobId": job_id,
        "client": job.get("client"),
        "budget_wei": job.get("budget"),
        "meta": meta,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    })
    with open(JOB_LIFECYCLE_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def on_job_skipped(job: dict, reason: str):
    logger.warning("[APEX] Job #%s skipped: %s", job.get("jobId"), reason)


def create_app():
    """Build the APEX FastAPI app (routes: /negotiate /submit /job/execute ...)."""
    try:
        from bnbagent.apex.server import create_apex_app
    except ImportError:
        raise ImportError("bnbagent not installed. Run: pip install 'bnbagent[server,ipfs]'")

    return create_apex_app(
        on_job=run_adjudication,
        on_job_skipped=on_job_skipped,
        job_timeout=60.0,
        task_metadata={"service": "signalforge-adjudicator", "version": "2.1.0"},
    )


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    logger.info("[APEX] Starting SignalForge APEX server on port %s...",
                os.getenv("APEX_PORT", "8001"))
    uvicorn.run(create_app(), host="0.0.0.0", port=int(os.getenv("APEX_PORT", "8001")))
