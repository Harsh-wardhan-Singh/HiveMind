"""HIVEMIND Agents Package."""

from backend.agents.agent import Agent
from backend.agents.lifecycle import (
    LifeStage,
    calculate_gompertz_makeham_daily_hazard,
    evaluate_daily_mortality,
    get_life_stage,
)
from backend.agents.personality import Personality, generate_personality
from backend.agents.roles import (
    ROLE_DEFINITIONS,
    RoleDefinition,
    RoleType,
    get_role_definition,
)

__all__ = [
    "ROLE_DEFINITIONS",
    "Agent",
    "LifeStage",
    "Personality",
    "RoleDefinition",
    "RoleType",
    "calculate_gompertz_makeham_daily_hazard",
    "evaluate_daily_mortality",
    "generate_personality",
    "get_life_stage",
    "get_role_definition",
]
