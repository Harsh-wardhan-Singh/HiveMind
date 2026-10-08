"""HIVEMIND Structured Action Schemas for Strategic LLM Decisions."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class MayoralCrisisProposal(BaseModel):
    """Structured action proposal emitted by LLM for Mayoral crisis decisions."""

    action: str = Field(
        ...,
        description="The executive policy choice (FOOD_SUBSIDY, WELFARE_STIMULUS, PUBLIC_WORKS, ANTI_CORRUPTION_CRACKDOWN, AUSTERITY, NO_ACTION)",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score for this policy selection",
    )
    rationale: str = Field(
        default="",
        description="Reasoning explaining why this policy addresses the crisis",
    )


class CorporateStrategyProposal(BaseModel):
    """Structured action proposal emitted by LLM for corporate executive decisions."""

    action: str = Field(
        ...,
        description="Strategic corporate action (EXPAND_PRODUCTION, DOWNSIZE_PAYROLL, CUT_PRICES, RAISE_PRICES, CONSERVE_CAPITAL, NO_ACTION)",
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    wage_adjustment_pct: float = Field(default=0.0, ge=-25.0, le=25.0)
    rationale: str = Field(default="")


@dataclass
class StrategicDecisionResult:
    """Authoritative result of a strategic decision, recording source and rationale."""

    agent_id: str
    role: str
    decision_type: str
    chosen_action: str
    confidence: float
    rationale: str
    source: str  # "LLM_REASONING" or "MATHEMATICAL_FALLBACK"
    model_used: str | None = None
    latency_ms: float = 0.0
    is_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "decision_type": self.decision_type,
            "chosen_action": self.chosen_action,
            "confidence": round(self.confidence, 4),
            "rationale": self.rationale,
            "source": self.source,
            "model_used": self.model_used,
            "latency_ms": round(self.latency_ms, 2),
            "is_valid": self.is_valid,
        }
