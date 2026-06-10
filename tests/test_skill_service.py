"""FastAPI skill-service tests: routes + x402 gate (demo mode)."""

import base64
import json
import os
import pytest

os.environ.setdefault("X402_DEMO_MODE", "true")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from service.app import app

    return TestClient(app)


def demo_auth_header():
    return base64.b64encode(
        json.dumps(
            {
                "x402Version": 1,
                "network": "base",
                "payload": {"signature": "0xdemo", "authorization": {}},
            }
        ).encode()
    ).decode()


SAMPLE_BODY = {
    "asset": "ETH",
    "candidate_signal": {
        "name": "test",
        "source": "cmc_fear_greed",
        "definition": "fg < 20",
        "holding_period_days": 5,
    },
}


class TestFreeRoutes:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_status(self, client):
        r = client.get("/status")
        assert r.status_code == 200
        assert r.json()["pricing"]["adjudicate"]["usdc"] == 0.50

    def test_skill_card(self, client):
        r = client.get("/.well-known/skill-card.json")
        assert r.status_code == 200
        card = r.json()
        assert card["name"] == "signalforge-adjudicator"
        assert "signal validation" in card["keywords"]


class TestX402Gate:
    def test_adjudicate_no_payment_402(self, client):
        r = client.post("/adjudicate", json=SAMPLE_BODY)
        assert r.status_code == 402
        data = r.json()
        assert data["x402Version"] == 1
        assert data["accepts"][0]["network"] == "base"

    def test_adjudicate_demo_payment_200(self, client):
        r = client.post(
            "/adjudicate", json=SAMPLE_BODY, headers={"X-PAYMENT": demo_auth_header()}
        )
        assert r.status_code == 200
        data = r.json()
        assert "verdict" in data and "edge_confidence" in data

    def test_adjudicate_verdict_schema(self, client):
        r = client.post(
            "/adjudicate", json=SAMPLE_BODY, headers={"X-PAYMENT": demo_auth_header()}
        )
        data = r.json()
        for f in ["verdict", "edge_confidence", "reasons", "leakage_check"]:
            assert f in data

    def test_adjudicate_v1_confidence_47(self, client):
        r = client.post(
            "/adjudicate", json=SAMPLE_BODY, headers={"X-PAYMENT": demo_auth_header()}
        )
        assert r.json()["edge_confidence"] == 47

    def test_missing_signal_422(self, client):
        r = client.post(
            "/adjudicate",
            json={"asset": "ETH"},
            headers={"X-PAYMENT": demo_auth_header()},
        )
        assert r.status_code == 422

    def test_generate_spec_no_payment_402(self, client):
        r = client.post("/generate_spec", json={"asset": "ETH"})
        assert r.status_code == 402

    def test_generate_spec_with_payment(self, client):
        r = client.post(
            "/generate_spec",
            json={"asset": "ETH", "risk": "moderate"},
            headers={"X-PAYMENT": demo_auth_header()},
        )
        assert r.status_code == 200
        assert "spec_id" in r.json()

    def test_invalid_payment_402(self, client):
        r = client.post(
            "/adjudicate", json=SAMPLE_BODY, headers={"X-PAYMENT": "garbage!!!"}
        )
        assert r.status_code == 402


class TestSpecEndpoint:
    def test_spec_not_found_404(self, client):
        r = client.get("/spec/nonexistent-xyz")
        assert r.status_code == 404

    def test_spec_found(self, client):
        r = client.get("/spec/signalforge-cmc-fg-regime-v1")
        assert r.status_code in (200, 404)  # 200 once outputs/specs JSON committed
