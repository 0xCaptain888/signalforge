"""Pydantic schema for the StrategySpec — the machine-readable contract
that downstream tooling (other agents, judges, paper-trade engines) can
consume to reproduce the strategy without reading the report.

Versioning: bump `spec_version` on any breaking change to field names or
semantics. Additive changes (new optional fields) do not bump the major
version.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class DataSource(BaseModel):
    """One upstream data feed used by the strategy."""
    model_config = ConfigDict(extra="ignore")

    provider: str
    endpoint: str
    field: Optional[str] = None
    note: Optional[str] = None
    is_proprietary: bool = False


class FactorSpec(BaseModel):
    """One factor in the strategy, with the empirical stats that justified it."""
    model_config = ConfigDict(extra="ignore")

    id: str
    definition: str
    type: str  # "timeseries" | "cross_section"
    rank_ic: Optional[float] = None
    ir: Optional[float] = None
    t_stat: Optional[float] = None
    fdr_significant: Optional[bool] = None
    rationale: Optional[str] = None


class StrategySpec(BaseModel):
    """The full strategy specification — backtestable end-to-end if all the
    referenced data sources are accessible and the seed is honoured."""
    model_config = ConfigDict(extra="ignore")

    spec_version: str = "1.0"
    spec_id: str
    name: str
    created_at: str
    description: Optional[str] = None

    data_sources: list[DataSource]
    universe: dict
    factors: list[FactorSpec]
    regime: dict
    signal_to_position: dict
    execution_assumptions: dict
    backtest_window: dict
    reported_performance: dict
    reproducibility: dict
