"""
SignalForge Skill Service — FastAPI main application (v2.1.0).

Routes:
  POST /adjudicate                    — core: signal adjudication (x402-gated)
  POST /generate_spec                 — StrategySpec generation (x402-gated)
  GET  /spec/{spec_id}                — fetch a StrategySpec JSON (free)
  GET  /.well-known/skill-card.json   — Skills Marketplace discovery (free)
  GET  /status                        — pricing + provenance summary (free)
  GET  /health                        — health check (free)

P0-2 fix applied: _run_spec_safe() defensive wrapper around v1 run_skill().
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make repo root importable regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.adjudicator.core import adjudicate
from service.x402_middleware import X402Middleware

app = FastAPI(
    title="SignalForge — Signal Edge Adjudicator",
    description=(
        "Validates trading signals for real alpha vs overfit/leakage. "
        "Powered by CMC proprietary Fear & Greed + Lopez de Prado Deflated Sharpe."
    ),
    version="2.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(X402Middleware)


# -- P0-2: defensive wrapper around v1 skill_wrapper --------------------------
def _run_spec_safe(asset: str, risk: str) -> dict:
    """Safely call v1 skill_wrapper.run_skill(); never crash the endpoint."""
    try:
        from src.spec.skill_wrapper import run_skill  # type: ignore
        try:
            return run_skill(asset=asset, risk=risk)
        except TypeError:
            return run_skill(asset, risk)  # positional-args signature
    except ImportError:
        return {
            "spec_id": f"signalforge-{asset.lower()}-basic-v2",
            "spec_version": "2.1.0",
            "asset": asset,
            "risk_profile": risk,
            "signal": {
                "name": "CMC F&G Extreme Reversal",
                "source": "CMC proprietary /v3/fear-and-greed/historical",
                "entry_rule": "fg < 20 -> long; fg > 80 -> short",
                "holding_period_days": 5,
            },
            "verdict": "LEAKAGE_DETECTED",
            "edge_confidence": 12,
            "note": (
                "Full spec requires v1 pipeline output. "
                "Run scripts/05_generate_spec.py first. See outputs/specs/."
            ),
        }


# -- Routes -------------------------------------------------------------------
@app.post("/adjudicate")
async def adjudicate_endpoint(request: Request):
    """Signal adjudication (x402-gated by middleware)."""
    body = await request.json()
    candidate_signal = body.get("candidate_signal")
    if not candidate_signal:
        raise HTTPException(status_code=422, detail="candidate_signal is required")

    verdict = adjudicate(
        asset=body.get("asset"),
        candidate_signal=candidate_signal,
        risk=body.get("risk", "balanced"),
        include_cmc_snapshot=True,
    )
    return JSONResponse(content=json.loads(json.dumps(verdict, default=str)))


@app.post("/generate_spec")
async def generate_spec_endpoint(request: Request):
    """StrategySpec generation (x402-gated)."""
    body = await request.json()
    spec = _run_spec_safe(
        asset=body.get("asset", "ETH"),
        risk=body.get("risk", "balanced"),
    )
    return JSONResponse(content=spec)


@app.get("/spec/{spec_id}")
async def get_spec(spec_id: str):
    spec_path = Path(__file__).resolve().parent.parent / "outputs" / "specs" / f"{spec_id}.json"
    if not spec_path.exists():
        raise HTTPException(status_code=404, detail=f"spec '{spec_id}' not found")
    with open(spec_path) as f:
        return JSONResponse(content=json.load(f))


@app.get("/.well-known/skill-card.json")
async def skill_card():
    """CMC Skills Marketplace discovery endpoint (find_skill fetches this)."""
    public_url = os.getenv("SKILL_PUBLIC_URL", "http://localhost:8000")
    return JSONResponse(content={
        "name": "signalforge-adjudicator",
        "version": "2.1.0",
        "description": (
            "Signal Edge Adjudicator: validates any trading signal for real alpha "
            "vs overfitting/leakage. Powered by CMC proprietary Fear & Greed + "
            "Lopez de Prado Deflated Sharpe Ratio."
        ),
        "author": "SignalForge / 0xCaptain888",
        "license": "Apache-2.0",
        "keywords": [
            "signal validation", "overfitting detection", "backtest audit",
            "deflated sharpe", "fear and greed", "edge confidence",
            "quant research", "leakage detection", "CMC", "alpha",
            "strategy skills", "backtestable spec",
        ],
        "capabilities": {
            "adjudicate_signal": {
                "description": "Adjudicate a trading signal for real edge vs noise/leakage",
                "endpoint": f"{public_url}/adjudicate",
                "method": "POST",
                "payment": {"protocol": "x402", "price_usdc": 0.50, "network": "base"},
            },
            "generate_spec": {
                "description": "Generate a backtestable StrategySpec from CMC data",
                "endpoint": f"{public_url}/generate_spec",
                "method": "POST",
                "payment": {"protocol": "x402", "price_usdc": 0.50, "network": "base"},
            },
        },
        "data_sources": [
            "CMC proprietary Fear & Greed /v3/fear-and-greed/historical",
            "CMC Data MCP mcp.coinmarketcap.com/mcp",
            "CMC x402 mcp.coinmarketcap.com/x402",
        ],
        "links": {
            "repo": "https://github.com/0xCaptain888/signalforge",
            "docs": f"{public_url}/docs",
        },
    })


@app.get("/status")
async def status():
    try:
        from src.cmc.provenance import summary as provenance_summary
        prov = provenance_summary()
    except Exception:
        prov = {}
    return JSONResponse(content={
        "service": "SignalForge Signal Edge Adjudicator",
        "version": "2.1.0",
        "status": "operational",
        "pricing": {
            "adjudicate": {"usdc": 0.50, "protocol": "x402", "network": "base"},
            "generate_spec": {"usdc": 0.50, "protocol": "x402", "network": "base"},
        },
        "cmc_provenance_summary": prov,
        "endpoints": {
            "adjudicate": "POST /adjudicate",
            "generate_spec": "POST /generate_spec",
            "skill_card": "GET /.well-known/skill-card.json",
            "docs": "GET /docs",
        },
    })


@app.get("/health")
async def health():
    return {"ok": True, "service": "signalforge-adjudicator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "service.app:app",
        host=os.getenv("SKILL_HOST", "0.0.0.0"),
        port=int(os.getenv("SKILL_PORT", "8000")),
    )
