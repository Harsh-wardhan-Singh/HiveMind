"""Unit tests for Societal Roles."""

from backend.agents.roles import ROLE_DEFINITIONS, RoleType, get_role_definition


def test_roles_completeness():
    assert len(RoleType) == 11
    for role_type in RoleType:
        assert role_type in ROLE_DEFINITIONS
        role_def = get_role_definition(role_type)
        assert role_def.base_annual_salary >= 0.0
        assert role_def.base_daily_wage == round(
            role_def.base_annual_salary / 365.25, 2
        )
        assert 0 <= role_def.required_education_level <= 3


def test_engineer_role():
    role_def = get_role_definition(RoleType.ENGINEER)
    assert role_def.title == "Engineer"
    assert role_def.base_annual_salary == 75_000.0
    assert role_def.required_education_level == 2


def test_fallback_unknown_role():
    role_def = get_role_definition("NON_EXISTENT")
    assert role_def.role_type == RoleType.UNEMPLOYED
