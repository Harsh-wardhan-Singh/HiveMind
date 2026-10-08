import logging
from typing import Any

logger = logging.getLogger(__name__)

from backend.agents.agent import Agent
from backend.companies.company import Company
from backend.llm.fallback import (
    fallback_corporate_decision,
    fallback_mayoral_decision,
)
from backend.llm.provider import LLMProvider, MockProvider, OllamaProvider
from backend.llm.schemas import (
    CorporateStrategyProposal,
    MayoralCrisisProposal,
    StrategicDecisionResult,
)
from backend.llm.validator import (
    validate_corporate_proposal,
    validate_mayoral_proposal,
)


class StrategicLLMGateway:
    """
    Authoritative strategic decision gateway.
    Delegates 3-5% of high-impact choices to local Ollama LLM, with guaranteed
    100% mathematical fallback if Ollama is unavailable, times out, or produces invalid output.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        model: str = "qwen2.5:1.5b",
        base_url: str = "http://127.0.0.1:11434",
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        if provider is not None:
            self.provider: LLMProvider = provider
        elif self.enabled:
            self.provider = OllamaProvider(base_url=base_url, model=model)
        else:
            self.provider = MockProvider()

        # Telemetry counters
        self.total_decisions: int = 0
        self.llm_decisions: int = 0
        self.fallback_decisions: int = 0
        self.total_latency_ms: float = 0.0

    @property
    def is_llm_active(self) -> bool:
        """True if LLM inference is enabled and backend provider is reachable."""
        return self.enabled and self.provider.is_available()

    @property
    def average_latency_ms(self) -> float:
        """Average latency in milliseconds for decisions processed."""
        if self.total_decisions == 0:
            return 0.0
        return round(self.total_latency_ms / self.total_decisions, 2)

    def decide_mayoral_crisis(
        self,
        mayor: Agent,
        world_state: Any,
    ) -> StrategicDecisionResult:
        """
        Evaluate an executive mayoral crisis policy.
        Attempts LLM reasoning; seamlessly falls back to mathematical utility if needed.
        """
        self.total_decisions += 1
        metrics = world_state.metrics
        govt = world_state.government

        # Check if LLM inference is available
        if self.is_llm_active:
            prompt = (
                f"You are the Mayor of Hivemind City (Agent {mayor.id}).\n"
                f"District conditions:\n"
                f"- Inflation Rate: {metrics.inflation_rate:.1f}%\n"
                f"- CPI Index: {metrics.cpi:.1f}\n"
                f"- City Unrest: {metrics.city_unrest:.4f} (Rioting Districts: {metrics.rioting_districts_count})\n"
                f"- Citizen Approval: {metrics.approval_rating:.1f}%\n"
                f"- Treasury Balance: {govt.treasury:.2f} C\n"
                f"- Government Corruption: {govt.corruption_index:.4f}\n"
                f"Choose an emergency policy from: ['FOOD_SUBSIDY', 'WELFARE_STIMULUS', 'PUBLIC_WORKS', 'ANTI_CORRUPTION_CRACKDOWN', 'AUSTERITY', 'NO_ACTION'].\n"
                f'Return ONLY valid JSON: {{"action": "<CHOICE>", "confidence": <float 0.0-1.0>, "rationale": "<explanation>"}}.'
            )

            raw_text, success, latency_ms = self.provider.generate(
                prompt=prompt,
                system_prompt="You are an economic municipal governance AI. Output strict valid JSON only.",
                json_format=True,
                temperature=0.2,
            )
            self.total_latency_ms += latency_ms

            if success and raw_text:
                try:
                    proposal = MayoralCrisisProposal.model_validate_json(raw_text)
                    is_valid, sanitized_action, reason = validate_mayoral_proposal(
                        proposal.action, world_state
                    )

                    self.llm_decisions += 1
                    return StrategicDecisionResult(
                        agent_id=mayor.id,
                        role="MAYOR",
                        decision_type="MAYORAL_CRISIS_POLICY",
                        chosen_action=sanitized_action,
                        confidence=proposal.confidence,
                        rationale=proposal.rationale or reason,
                        source="LLM_REASONING",
                        model_used=self.provider.model_name,
                        latency_ms=latency_ms,
                        is_valid=is_valid,
                    )
                except (ValueError, KeyError, TypeError, Exception) as exc:  # noqa: BLE001
                    logger.debug(
                        "Ollama mayoral proposal parsing/validation failed: %s", exc
                    )

        # 100% Mathematical Deterministic Fallback
        self.fallback_decisions += 1
        action, rationale = fallback_mayoral_decision(world_state)
        return StrategicDecisionResult(
            agent_id=mayor.id,
            role="MAYOR",
            decision_type="MAYORAL_CRISIS_POLICY",
            chosen_action=action,
            confidence=1.0,
            rationale=rationale,
            source="MATHEMATICAL_FALLBACK",
            model_used=None,
            latency_ms=0.0,
            is_valid=True,
        )

    def decide_corporate_strategy(
        self,
        ceo: Agent,
        company: Company,
        world_state: Any,
    ) -> StrategicDecisionResult:
        """
        Evaluate a corporate strategic intervention during operational stress.
        Attempts LLM reasoning; seamlessly falls back to mathematical utility if needed.
        """
        self.total_decisions += 1

        if self.is_llm_active:
            prompt = (
                f"You are the executive director of corporate firm {company.name} ({company.ticker}).\n"
                f"Financial status:\n"
                f"- Commodity: {company.commodity_type.value}\n"
                f"- Cash Reserves: {company.cash:.2f} C\n"
                f"- Inventory: {company.inventory:.1f} units\n"
                f"- Daily Profit: {company.daily_profit:.2f} C\n"
                f"- Target Wage: {company.target_wage:.2f} C\n"
                f"- Employees: {len(company.employee_ids)}\n"
                f"Choose an operational strategy from: ['EXPAND_PRODUCTION', 'DOWNSIZE_PAYROLL', 'CUT_PRICES', 'RAISE_PRICES', 'CONSERVE_CAPITAL', 'NO_ACTION'].\n"
                f'Return ONLY valid JSON: {{"action": "<CHOICE>", "confidence": <float 0.0-1.0>, "wage_adjustment_pct": <float -20.0 to 20.0>, "rationale": "<explanation>"}}.'
            )

            raw_text, success, latency_ms = self.provider.generate(
                prompt=prompt,
                system_prompt="You are an industrial corporate executive AI. Output strict valid JSON only.",
                json_format=True,
                temperature=0.2,
            )
            self.total_latency_ms += latency_ms

            if success and raw_text:
                try:
                    proposal = CorporateStrategyProposal.model_validate_json(raw_text)
                    is_valid, sanitized_action, reason = validate_corporate_proposal(
                        proposal.action, company
                    )

                    self.llm_decisions += 1
                    return StrategicDecisionResult(
                        agent_id=ceo.id,
                        role="BUSINESS_OWNER",
                        decision_type="CORPORATE_STRATEGY",
                        chosen_action=sanitized_action,
                        confidence=proposal.confidence,
                        rationale=proposal.rationale or reason,
                        source="LLM_REASONING",
                        model_used=self.provider.model_name,
                        latency_ms=latency_ms,
                        is_valid=is_valid,
                    )
                except (ValueError, KeyError, TypeError, Exception) as exc:  # noqa: BLE001
                    logger.debug(
                        "Ollama corporate proposal parsing/validation failed: %s", exc
                    )

        # 100% Mathematical Corporate Fallback
        self.fallback_decisions += 1
        action, _wage_pct, rationale = fallback_corporate_decision(company, world_state)
        return StrategicDecisionResult(
            agent_id=ceo.id,
            role="BUSINESS_OWNER",
            decision_type="CORPORATE_STRATEGY",
            chosen_action=action,
            confidence=1.0,
            rationale=rationale,
            source="MATHEMATICAL_FALLBACK",
            model_used=None,
            latency_ms=0.0,
            is_valid=True,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize gateway telemetry and operational status."""
        avg_lat = (
            self.total_latency_ms / self.llm_decisions
            if self.llm_decisions > 0
            else 0.0
        )
        return {
            "llm_enabled": self.enabled,
            "is_active": self.is_llm_active,
            "provider_model": self.provider.model_name,
            "total_decisions": self.total_decisions,
            "llm_decisions": self.llm_decisions,
            "fallback_decisions": self.fallback_decisions,
            "avg_latency_ms": round(avg_lat, 2),
        }
