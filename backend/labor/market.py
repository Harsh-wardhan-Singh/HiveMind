"""HIVEMIND Labor Market Matching & Payroll Settlement Engine."""

import random

from backend.agents.agent import Agent
from backend.agents.roles import RoleType, get_role_definition
from backend.companies.company import Company


def calculate_reservation_wage(agent: Agent) -> float:
    """Calculate agent's minimum acceptable daily wage based on role and ambition."""
    role_def = get_role_definition(agent.role)
    base_wage = role_def.base_daily_wage
    ambition_bonus = agent.personality.ambition * 0.20
    return max(15.0, base_wage * (1.0 + ambition_bonus))


def match_labor_market(
    agents: dict[str, Agent],
    companies: dict[str, Company],
    rng: random.Random,
) -> list[tuple[str, str]]:
    """
    Match unemployed or job-seeking agents with companies needing labor.
    Returns list of (agent_id, company_id) newly hired.
    """
    new_hires: list[tuple[str, str]] = []

    # Eligible job seekers (unemployed or looking for work)
    job_seekers = [
        a
        for a in agents.values()
        if a.alive
        and a.employer_id is None
        and a.role
        not in (
            RoleType.MAYOR,
            RoleType.INVESTOR,
            RoleType.RETIRED if hasattr(RoleType, "RETIRED") else "RETIRED",
        )
    ]
    rng.shuffle(job_seekers)

    for company in companies.values():
        if not company.solvency:
            continue

        # Sustainable labor demand based on runway and market need
        runway_limit = max(1, int(company.cash / max(company.target_wage * 10.0, 1.0)))
        cap_target = max(2, min(8, int(company.capital / 3000.0)))

        # If inventory is depleted, firm expands headcount to meet market demand
        if company.inventory < 25.0:
            cap_target = min(
                runway_limit, max(cap_target, len(company.employee_ids) + 1)
            )
        # If inventory is high and firm is losing money, don't expand headcount
        elif company.inventory > 100.0 and company.daily_profit < 0:
            cap_target = max(1, min(cap_target, len(company.employee_ids)))

        target_employees = min(runway_limit, cap_target)

        # Gentle downsizing if firm is under severe cash stress
        if (
            len(company.employee_ids) > 1
            and company.cash < company.target_wage * 5.0
            and company.daily_profit < 0
        ):
            laid_off = company.employee_ids.pop()
            if laid_off in agents:
                agents[laid_off].employer_id = None

        openings = target_employees - len(company.employee_ids)

        if openings <= 0:
            continue

        remaining_seekers: list[Agent] = []
        for candidate in job_seekers:
            if openings <= 0:
                remaining_seekers.append(candidate)
                continue

            res_wage = calculate_reservation_wage(candidate)

            # Match if company wage is within 20% bargaining range, or if agent is unemployed/student
            is_willing = company.target_wage >= res_wage * 0.80 or candidate.role in (
                RoleType.UNEMPLOYED,
                RoleType.STUDENT,
            )

            if is_willing:
                company.add_employee(candidate.id)
                candidate.employer_id = company.id
                new_hires.append((candidate.id, company.id))
                openings -= 1
            else:
                remaining_seekers.append(candidate)

        job_seekers = remaining_seekers

        # Wage discovery: raise wage offer slightly if firm has persistent unfulfilled openings
        if openings > 0 and company.cash > 5000.0:
            company.target_wage = round(min(250.0, company.target_wage * 1.01), 2)

    return new_hires


def process_daily_payroll(
    agents: dict[str, Agent],
    companies: dict[str, Company],
) -> dict[str, float]:
    """
    Disburse daily wages from companies to employees.
    If company runs out of cash, it initiates emergency layoffs.
    Returns mapping of company_id to total payroll paid.
    """
    payroll_payouts: dict[str, float] = {}

    for comp_id, company in companies.items():
        if not company.solvency:
            continue

        total_payroll = 0.0
        employees_to_keep: list[str] = []

        for emp_id in company.employee_ids:
            if emp_id not in agents or not agents[emp_id].alive:
                continue

            wage = company.target_wage
            if company.cash >= wage:
                company.cash -= wage
                agents[emp_id].cash += wage
                total_payroll += wage
                employees_to_keep.append(emp_id)
            else:
                # Inability to pay triggers layoff
                agents[emp_id].employer_id = None

        company.employee_ids = employees_to_keep
        company.daily_expenses = total_payroll
        payroll_payouts[comp_id] = total_payroll

        # Check solvency boundary
        if company.cash < -5000.0:
            company.solvency = False

    return payroll_payouts
