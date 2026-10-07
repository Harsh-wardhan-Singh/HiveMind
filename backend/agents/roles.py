"""HIVEMIND Societal Roles Module."""

from dataclasses import dataclass
from enum import Enum


class RoleType(str, Enum):
    STUDENT = "STUDENT"
    MANUAL_WORKER = "MANUAL_WORKER"
    SKILLED_WORKER = "SKILLED_WORKER"
    ENGINEER = "ENGINEER"
    TEACHER = "TEACHER"
    HEALTHCARE_WORKER = "HEALTHCARE_WORKER"
    RESEARCHER = "RESEARCHER"
    BUSINESS_OWNER = "BUSINESS_OWNER"
    INVESTOR = "INVESTOR"
    UNEMPLOYED = "UNEMPLOYED"
    MAYOR = "MAYOR"


@dataclass(frozen=True)
class RoleDefinition:
    role_type: RoleType
    title: str
    base_annual_salary: float
    required_education_level: int  # 0: None, 1: High School, 2: Bachelor, 3: Master/PhD
    base_skill_requirement: float
    work_capacity_hours: float = 8.0

    @property
    def base_daily_wage(self) -> float:
        return round(self.base_annual_salary / 365.25, 2)


ROLE_DEFINITIONS: dict[RoleType, RoleDefinition] = {
    RoleType.STUDENT: RoleDefinition(
        role_type=RoleType.STUDENT,
        title="Student",
        base_annual_salary=12_000.0,
        required_education_level=0,
        base_skill_requirement=0.1,
    ),
    RoleType.MANUAL_WORKER: RoleDefinition(
        role_type=RoleType.MANUAL_WORKER,
        title="Manual Worker",
        base_annual_salary=30_000.0,
        required_education_level=0,
        base_skill_requirement=0.3,
    ),
    RoleType.SKILLED_WORKER: RoleDefinition(
        role_type=RoleType.SKILLED_WORKER,
        title="Skilled Worker",
        base_annual_salary=48_000.0,
        required_education_level=1,
        base_skill_requirement=0.5,
    ),
    RoleType.ENGINEER: RoleDefinition(
        role_type=RoleType.ENGINEER,
        title="Engineer",
        base_annual_salary=75_000.0,
        required_education_level=2,
        base_skill_requirement=0.75,
    ),
    RoleType.TEACHER: RoleDefinition(
        role_type=RoleType.TEACHER,
        title="Teacher",
        base_annual_salary=45_000.0,
        required_education_level=2,
        base_skill_requirement=0.6,
    ),
    RoleType.HEALTHCARE_WORKER: RoleDefinition(
        role_type=RoleType.HEALTHCARE_WORKER,
        title="Healthcare Worker",
        base_annual_salary=65_000.0,
        required_education_level=2,
        base_skill_requirement=0.7,
    ),
    RoleType.RESEARCHER: RoleDefinition(
        role_type=RoleType.RESEARCHER,
        title="Researcher",
        base_annual_salary=85_000.0,
        required_education_level=3,
        base_skill_requirement=0.85,
    ),
    RoleType.BUSINESS_OWNER: RoleDefinition(
        role_type=RoleType.BUSINESS_OWNER,
        title="Business Owner",
        base_annual_salary=100_000.0,
        required_education_level=1,
        base_skill_requirement=0.7,
    ),
    RoleType.INVESTOR: RoleDefinition(
        role_type=RoleType.INVESTOR,
        title="Investor",
        base_annual_salary=120_000.0,
        required_education_level=2,
        base_skill_requirement=0.8,
    ),
    RoleType.UNEMPLOYED: RoleDefinition(
        role_type=RoleType.UNEMPLOYED,
        title="Unemployed",
        base_annual_salary=6_000.0,  # Minimal social safety net / unemployment benefit
        required_education_level=0,
        base_skill_requirement=0.0,
        work_capacity_hours=0.0,
    ),
    RoleType.MAYOR: RoleDefinition(
        role_type=RoleType.MAYOR,
        title="Mayor",
        base_annual_salary=110_000.0,
        required_education_level=2,
        base_skill_requirement=0.8,
    ),
}


def get_role_definition(role_type: RoleType) -> RoleDefinition:
    """Retrieve official metadata definition for a role."""
    return ROLE_DEFINITIONS.get(role_type, ROLE_DEFINITIONS[RoleType.UNEMPLOYED])

