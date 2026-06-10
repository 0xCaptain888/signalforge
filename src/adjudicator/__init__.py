"""SignalForge Adjudicator — Signal Edge Adjudicator module."""
from .core import adjudicate, adjudicate_preset_leakage, adjudicate_preset_honest
from .schema import Verdict, VerdictEnum, LeakageCheck
from .scoring import edge_confidence, verdict_from_score, verify_v1_score
from .leakage import detect_leakage

__all__ = [
    "adjudicate", "adjudicate_preset_leakage", "adjudicate_preset_honest",
    "Verdict", "VerdictEnum", "LeakageCheck",
    "edge_confidence", "verdict_from_score", "verify_v1_score",
    "detect_leakage",
]
