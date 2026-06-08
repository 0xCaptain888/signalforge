"""SignalForge as a CMC-style Skills-Marketplace skill — dev doc §8.2.

Exposes ``run_skill(asset, risk)`` so other agents (and the optional
x402 pay-per-call wrapper) can request a *customised* StrategySpec
without re-running the full research / backtest pipeline.

Design rules (kept in lock-step with the rest of the project):

* **No heavy compute at skill-call time.** The cached
  ``outputs/research_results.json`` and ``outputs/backtest_results.json``
  are the source of truth — they were produced by the deterministic
  pipeline under ``seed=42`` and verified by the manifest hash gate in
  ``scripts/reproduce.py``. The skill only customises the *presentation*
  of those numbers; it never invents new factor stats.
* **Latest-CMC enrichment is optional.** When a CMC key is configured we
  attach a single fresh snapshot from the proprietary F&G + global
  metrics endpoints into ``runtime_inputs`` so callers can see what
  market regime they are about to enter. The cached pipeline numbers are
  never overwritten by this snapshot.
* **Risk preference only tunes the position-sizing block.** Factor
  selection and IC numbers do NOT depend on caller risk preference —
  that would amount to data-mining per request. We only resize
  ``signal_to_position`` (max gross / max asset weight) and the
  execution slippage assumption.
* **Asset filter respects factor type.** Asking for a single asset
  drops the cross-section factors from the returned spec, since they
  are panel-level by construction.
* **Honest degradation.** If a cached spec is missing the function
  raises ``FileNotFoundError`` with a clear message; if the CMC key is
  absent the skill still returns a valid spec, with
  ``runtime_inputs.cmc_snapshot = None`` and a note explaining why.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import constants as C
from config.settings import settings
from src.spec.schema import FactorSpec, StrategySpec

# --------------------------------------------------------------------------- #
# Risk-preference profiles. Conservative scales gross + per-asset down;
# aggressive raises them. None of these numbers change factor selection;
# they only resize the ``signal_to_position`` block.
# --------------------------------------------------------------------------- #
RISK_PROFILES: dict[str, dict[str, Any]] = {
    "conservative": {
        "max_asset_weight": 0.15,
        "max_gross_leverage": 0.5,
        "slippage_multiplier": 1.5,
        "note": "Sized for capital preservation; halves gross exposure.",
    },
    "moderate": {
        "max_asset_weight": 0.30,
        "max_gross_leverage": 1.0,
        "slippage_multiplier": 1.0,
        "note": "Default sizing — matches the as-reported backtest.",
    },
    "aggressive": {
        "max_asset_weight": 0.50,
        "max_gross_leverage": 1.5,
        "slippage_multiplier": 1.0,
        "note": "Lifts gross by 50 %% and raises per-asset cap to 0.5.",
    },
}

_DEFAULT_SPEC_ID = "signalforge-cmc-fg-regime-v1"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_cached_spec(spec_id: str = _DEFAULT_SPEC_ID) -> dict:
    """Read the canonical spec emitted by ``scripts/05_generate_spec.py``."""
    path = Path(settings.outputs_dir) / "specs" / f"{spec_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"cached spec missing: {path}. Run the pipeline first "
            "(scripts/03_run_research.py -> 04 -> 05)."
        )
    return json.loads(path.read_text())


def _scale_slippage(
    slippage: dict[str, int] | None, factor: float
) -> dict[str, int]:
    """Multiply each bucket of the slippage assumption by ``factor`` and
    round to the nearest bp. Falls back to the project constant when the
    cached spec did not include the block."""
    base = slippage or C.SLIPPAGE_BPS
    return {k: int(round(v * factor)) for k, v in base.items()}


def _filter_factors_for_asset(
    factors: list[dict], asset: str
) -> list[dict]:
    """If a single asset is requested (anything other than the panel
    sentinels ``PANEL`` / ``ALL``), cross-section factors are dropped
    because they are panel-level by construction. Re-validated through
    the pydantic schema so callers always get a clean payload."""
    if asset.upper() in {"PANEL", "ALL"}:
        return factors
    keep = [f for f in factors if (f.get("type") != "cross_section")]
    # Round-trip via the pydantic model to validate the shape.
    return [FactorSpec(**f).model_dump() for f in keep]


def _fetch_cmc_snapshot(asset: str) -> dict | None:
    """Best-effort latest snapshot from CMC. Returns ``None`` (and prints
    a diagnostic note) when the key is missing or the call fails so the
    skill stays usable in no-key reproduction mode."""
    if not settings.cmc_api_key:
        return None
    try:  # pragma: no cover - thin network wrapper; covered by manual run
        from src.cmc.endpoints import Endpoints

        ep = Endpoints()
        fg = ep.fear_greed_historical(start=1, limit=1)
        gm = ep.global_metrics_latest(convert=C.CONVERT)
        fg_rows = (fg or {}).get("data") or []
        latest_fg = fg_rows[0] if fg_rows else None
        gm_quote = (
            (gm or {}).get("data", {}).get("quote", {}).get(C.CONVERT, {})
        )
        return {
            "asset": asset.upper(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "cmc_fg_latest": latest_fg,
            "btc_dominance": (gm or {}).get("data", {}).get("btc_dominance"),
            "total_market_cap_usd": gm_quote.get("total_market_cap"),
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "asset": asset.upper(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
        }


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def run_skill(
    asset: str = "BTC",
    risk: str = "moderate",
    spec_id: str = _DEFAULT_SPEC_ID,
    fetch_live: bool = True,
) -> dict:
    """Return a customised ``StrategySpec`` payload (already
    ``model_dump``-ed) for the requested asset and risk preference.

    Parameters
    ----------
    asset
        Target asset symbol (e.g. ``"BTC"``, ``"ETH"``). Pass
        ``"PANEL"`` / ``"ALL"`` to keep the cross-section factor block.
    risk
        One of ``"conservative" | "moderate" | "aggressive"``. Resizes
        ``signal_to_position`` and ``execution_assumptions.slippage_bps_by_size``
        only — never the factor set.
    spec_id
        Cached spec to base the response on. Defaults to the v1 spec
        emitted by ``scripts/05_generate_spec.py``.
    fetch_live
        When ``True`` (and a CMC key is configured), attach a single
        proprietary-F&G + global-metrics snapshot under
        ``runtime_inputs.cmc_snapshot``.

    Returns
    -------
    dict
        Output of ``StrategySpec.model_dump()`` with two added
        skill-specific blocks: ``skill_inputs`` (the caller's request,
        echoed) and ``runtime_inputs`` (the live CMC snapshot or a
        note explaining why it is absent).
    """
    risk_key = risk.lower().strip()
    if risk_key not in RISK_PROFILES:
        raise ValueError(
            f"unknown risk preference: {risk!r}. "
            f"Expected one of: {sorted(RISK_PROFILES)}"
        )
    profile = RISK_PROFILES[risk_key]

    cached = _load_cached_spec(spec_id=spec_id)

    # Tailor signal_to_position
    sig_to_pos = dict(cached.get("signal_to_position", {}))
    sig_to_pos.update(
        max_asset_weight=profile["max_asset_weight"],
        max_gross_leverage=profile["max_gross_leverage"],
        risk_preference=risk_key,
        risk_profile_note=profile["note"],
    )

    # Tailor execution_assumptions (slippage scales with risk)
    exec_assump = dict(cached.get("execution_assumptions", {}))
    exec_assump["slippage_bps_by_size"] = _scale_slippage(
        exec_assump.get("slippage_bps_by_size"), profile["slippage_multiplier"]
    )

    # Tailor factors based on requested asset
    factors = _filter_factors_for_asset(cached.get("factors", []), asset)

    # Re-validate the whole thing through pydantic to guarantee shape.
    tailored = StrategySpec(
        **{
            **cached,
            "spec_id": f"{cached['spec_id']}::{asset.upper()}::{risk_key}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "signal_to_position": sig_to_pos,
            "execution_assumptions": exec_assump,
            "factors": factors,
        }
    )

    snapshot = _fetch_cmc_snapshot(asset) if fetch_live else None

    payload = tailored.model_dump()
    payload["skill_inputs"] = {
        "asset": asset.upper(),
        "risk": risk_key,
        "source_spec_id": cached.get("spec_id"),
    }
    payload["runtime_inputs"] = {
        "cmc_snapshot": snapshot,
        "snapshot_note": (
            "Live snapshot omitted: CMC_API_KEY not set (judge "
            "no-key mode)."
            if snapshot is None
            else "Snapshot is informational only; cached pipeline "
                 "numbers are unchanged."
        ),
    }
    return payload


# --------------------------------------------------------------------------- #
# CLI: ``python -m src.spec.skill_wrapper --asset ETH --risk aggressive``
# --------------------------------------------------------------------------- #
def _cli() -> None:  # pragma: no cover - thin argparse shim
    import argparse

    parser = argparse.ArgumentParser(
        description="SignalForge skill wrapper — emits a tailored StrategySpec."
    )
    parser.add_argument("--asset", default="BTC")
    parser.add_argument(
        "--risk", default="moderate", choices=sorted(RISK_PROFILES)
    )
    parser.add_argument("--spec-id", default=_DEFAULT_SPEC_ID)
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip the live CMC snapshot even if a key is configured.",
    )
    args = parser.parse_args()
    out = run_skill(
        asset=args.asset,
        risk=args.risk,
        spec_id=args.spec_id,
        fetch_live=not args.no_fetch,
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":  # pragma: no cover
    _cli()
