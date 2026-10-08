"""HIVEMIND Authoritative Action Validation Module."""

from typing import Any

ALLOWED_MAYORAL_ACTIONS = {
    "FOOD_SUBSIDY",
    "WELFARE_STIMULUS",
    "PUBLIC_WORKS",
    "ANTI_CORRUPTION_CRACKDOWN",
    "AUSTERITY",
    "NO_ACTION",
}

ALLOWED_CORPORATE_ACTIONS = {
    "EXPAND_PRODUCTION",
    "DOWNSIZE_PAYROLL",
    "CUT_PRICES",
    "RAISE_PRICES",
    "CONSERVE_CAPITAL",
    "NO_ACTION",
}


def validate_mayoral_proposal(
    action: str,
    world_state: Any,
) -> tuple[bool, str, str]:
    """
    Validate whether the proposed Mayoral decree satisfies physical and budgetary laws.
    Returns (is_valid, sanitized_action, reason).
    """
    normalized_action = action.upper().strip()

    if normalized_action not in ALLOWED_MAYORAL_ACTIONS:
        return (
            False,
            "NO_ACTION",
            f"Action '{action}' is not in allowed policies {ALLOWED_MAYORAL_ACTIONS}.",
        )

    treasury = world_state.government.treasury

    # Budget feasibility checks
    if normalized_action == "PUBLIC_WORKS" and treasury < 4000.0:
        return (
            False,
            "AUSTERITY",
            f"Insufficient treasury ({treasury:.2f} C < 4000 C) for PUBLIC_WORKS. Downscaled to AUSTERITY.",
        )

    if normalized_action == "WELFARE_STIMULUS" and treasury < 2500.0:
        return (
            False,
            "AUSTERITY",
            f"Insufficient treasury ({treasury:.2f} C < 2500 C) for WELFARE_STIMULUS. Downscaled to AUSTERITY.",
        )

    if normalized_action == "FOOD_SUBSIDY" and treasury < 1500.0:
        return (
            False,
            "NO_ACTION",
            f"Insufficient treasury ({treasury:.2f} C < 1500 C) for FOOD_SUBSIDY.",
        )

    return (True, normalized_action, "Policy proposal verified as feasible.")


def validate_corporate_proposal(
    action: str,
    company: Any,
) -> tuple[bool, str, str]:
    """
    Validate whether the proposed corporate strategy satisfies corporate solvency laws.
    Returns (is_valid, sanitized_action, reason).
    """
    normalized_action = action.upper().strip()

    if normalized_action not in ALLOWED_CORPORATE_ACTIONS:
        return (
            False,
            "CONSERVE_CAPITAL",
            f"Action '{action}' is not in allowed corporate actions {ALLOWED_CORPORATE_ACTIONS}.",
        )

    # Cash constraint checks
    if normalized_action == "EXPAND_PRODUCTION" and company.cash < 500.0:
        return (
            False,
            "CONSERVE_CAPITAL",
            f"Insufficient cash reserves ({company.cash:.2f} C < 500 C) to expand production.",
        )

    return (True, normalized_action, "Corporate strategy proposal verified.")
