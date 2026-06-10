"""
Verdict pydantic schema — the adjudication report data model.

P0-3 fix applied: LeakageCheck includes direction_flip_detected and
lookahead_flag fields (Plan A from MasterAnalysis), plus extra="ignore"
to guard against future field drift.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class VerdictEnum(str, Enum):
    STRONG_ACCEPT = "STRONG_ACCEPT"        # edge_confidence >= 75
    ACCEPT = "ACCEPT"                      # 60 <= edge_confidence < 75
    WEAK = "WEAK"                          # 40 <= edge_confidence < 60
    REJECT = "REJECT"                      # edge_confidence < 40
    LEAKAGE_DETECTED = "LEAKAGE_DETECTED"  # leakage overrides any score


class LeakageCheck(BaseModel):
    """Full leakage analysis — all fields kept so judges see the mechanism."""
    model_config = ConfigDict(extra="ignore")

    lookahead_test: str = Field(description="Look-ahead bias test: PASS / FAIL")
    is_only_calibration: str = Field(default="ENFORCED")
    naive_sharpe_if_leaked: float = Field(description="Inflated Sharpe under leaky calibration")
    honest_sharpe: float = Field(description="IS-only honest Sharpe")
    gap: float = Field(description="naive - honest; larger = worse leakage")
    threshold: float = Field(default=0.80)
    direction_flip_detected: bool = Field(
        default=False,
        description="naive>0 and honest<=0 — the core leakage signature",
    )
    lookahead_flag: bool = Field(
        default=False,
        description="True when lookahead_test != PASS",
    )
    leaked: bool = Field(description="Final leakage verdict")


class RegimeConditional(BaseModel):
    model_config = ConfigDict(extra="ignore")
    note: str
    bucket: str
    ic: float
    t_stat: float
    p_value: float
    interpretation: str


class Statistics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dsr_probability: float = Field(description="Deflated Sharpe Ratio probability (Lopez de Prado)")
    fdr_significant_factors: int = Field(description="Factors passing BH-FDR q=0.10")
    walk_forward_median_sharpe: float
    walk_forward_windows: int
    oos_sharpe_is_only: float
    oos_max_drawdown: float
    parameter_plateau: str = Field(description="plateau / spike")
    strongest_regime_bucket: Optional[str] = None
    strongest_ic: Optional[float] = None
    strongest_t_stat: Optional[float] = None


class CMCProvenance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    fear_greed_source: str = Field(
        default="CMC proprietary /v3/fear-and-greed/historical (NOT Alternative.me)"
    )
    sample_size: int
    date_range: str
    access_channels_used: List[str] = Field(description="channels used in THIS call")
    historical_channels_documented: List[str] = Field(
        default=["rest", "mcp", "x402"],
        description="channels used across the project (see outputs/cmc_provenance.json)",
    )
    x402_tx: Optional[str] = None


class Billing(BaseModel):
    model_config = ConfigDict(extra="ignore")
    protocol: str = "x402"
    price_usdc: float = 0.50
    payment_tx: Optional[str] = None
    network: str = "base"


class VerdictMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    adjudicator_version: str = "2.1.0"
    seed: int = 42
    timestamp_utc: str
    reproducible: bool = True


class Verdict(BaseModel):
    """Adjudication report: SignalForge's full evaluation of a candidate signal."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    verdict: VerdictEnum
    edge_confidence: int = Field(ge=0, le=100)
    reasons: List[str]
    verdict_summary: str

    leakage_check: LeakageCheck
    statistics: Statistics
    regime_conditional_finding: Optional[RegimeConditional] = None

    strategy_spec_ref: str
    spec_id: str

    cmc_data_provenance: CMCProvenance
    billing: Billing
    meta: VerdictMeta
