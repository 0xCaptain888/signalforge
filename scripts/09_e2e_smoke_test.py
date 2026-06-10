#!/usr/bin/env python3
"""09_e2e_smoke_test.py — end-to-end smoke test (no network needed)."""

import base64
import json as _json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("X402_DEMO_MODE", "true")


def main():
    from service.app import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    print("=" * 55)
    print("SignalForge v2.1 — End-to-End Smoke Test")
    print("=" * 55)

    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"]
    print("  [1/5] /health PASS")

    body = {
        "asset": "ETH",
        "candidate_signal": {
            "name": "t",
            "source": "cmc_fear_greed",
            "definition": "fg<20",
            "holding_period_days": 5,
        },
    }
    r = client.post("/adjudicate", json=body)
    assert r.status_code == 402 and r.json().get("x402Version") == 1
    print("  [2/5] /adjudicate 402 gate PASS")

    demo = base64.b64encode(
        _json.dumps(
            {
                "x402Version": 1,
                "network": "base",
                "payload": {"signature": "0xdemo", "authorization": {}},
            }
        ).encode()
    ).decode()
    r = client.post("/adjudicate", json=body, headers={"X-PAYMENT": demo})
    assert r.status_code == 200
    data = r.json()
    assert data["leakage_check"]["leaked"] is True
    # Live pipeline loads real v1 research JSON, yielding confidence=47 (not demo fallback 12)
    assert data["edge_confidence"] == 47, f"Expected 47, got {data['edge_confidence']}"
    print(f"  [3/5] /adjudicate verdict={data['verdict']}, confidence=47 PASS")

    r = client.get("/.well-known/skill-card.json")
    assert r.status_code == 200
    assert "signal validation" in r.json().get("keywords", [])
    print("  [4/5] skill-card.json PASS")

    from src.adjudicator.scoring import verify_v1_score

    assert verify_v1_score()
    print("  [5/5] scoring verify_v1_score()=12 PASS")

    print("\nAll e2e smoke tests passed!")
    print("=" * 55)


if __name__ == "__main__":
    main()
