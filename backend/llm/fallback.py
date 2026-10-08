"""HIVEMIND Deterministic Mathematical Fallback Engine.

Guarantees 100% mathematical sovereignty if Ollama is unavailable, times out,
or produces invalid proposals.
"""

from typing import Any


def fallback_mayoral_decision(world_state: Any) -> tuple[str, str]:
    """
    100% deterministic mathematical utility calculation for mayoral crisis decisions.
    Returns (action, rationale).
    """
    metrics = world_state.metrics
    treasury = world_state.government.treasury
    corruption = world_state.government.corruption_index

    # 1. Critical unrest or riots
    if metrics.rioting_districts_count > 0 or metrics.city_unrest > 0.40:
        if treasury >= 4000.0:
            return (
                "PUBLIC_WORKS",
                "Deterministic utility: High unrest and civil riots detected. Deployed Public Works.",
            )
        else:
            return (
                "AUSTERITY",
                "Deterministic utility: Critical unrest but insufficient treasury. Enacted Austerity.",
            )

    # 2. Food inflation spike
    if (metrics.cpi > 115.0 or metrics.inflation_rate > 8.0) and treasury >= 1500.0:
        return (
            "FOOD_SUBSIDY",
            "Deterministic utility: High inflation eroding purchasing power. Enacted Food Subsidy.",
        )

    # 3. Rampant corruption
    if corruption > 0.08:
        return (
            "ANTI_CORRUPTION_CRACKDOWN",
            "Deterministic utility: High graft detected. Enacted Anti-Corruption Crackdown.",
        )

    # 4. Low civic favorability
    if metrics.city_favorability < 0.40 and treasury >= 2500.0:
        return (
            "WELFARE_STIMULUS",
            "Deterministic utility: Low approval rating. Disbursed Welfare Stimulus.",
        )

    # 5. Treasury emergency deficit
    if treasury < 300.0:
        return (
            "AUSTERITY",
            "Deterministic utility: Depleted municipal treasury. Imposed Austerity budget.",
        )

    return (
        "NO_ACTION",
        "Deterministic utility: Municipal conditions stable; no emergency policy required.",
    )


def fallback_corporate_decision(
    company: Any,
    world_state: Any,
) -> tuple[str, float, str]:
    """
    100% deterministic mathematical corporate strategy fallback.
    Returns (action, wage_adjustment_pct, rationale).
    """
    # Liquidity stress
    if company.cash < 500.0 and company.daily_profit < 0.0:
        return (
            "CONSERVE_CAPITAL",
            -5.0,
            "Deterministic utility: Cash runway depleted and negative profit. Conserving capital.",
        )

    # Inventory glut
    if company.inventory > 120.0:
        return (
            "CUT_PRICES",
            0.0,
            "Deterministic utility: Excess unsold inventory. Stimulating sales via price cut.",
        )

    # Robust expansion
    if (
        company.inventory < 25.0
        and company.cash > 3000.0
        and company.daily_profit > 50.0
    ):
        return (
            "EXPAND_PRODUCTION",
            3.0,
            "Deterministic utility: Low inventory and high cash surplus. Expanding production capacity.",
        )

    return (
        "NO_ACTION",
        0.0,
        "Deterministic utility: Corporate operations balanced within target parameters.",
    )
