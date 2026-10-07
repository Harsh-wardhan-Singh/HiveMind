"""HIVEMIND Cobb-Douglas Production Function Module."""

from collections.abc import Sequence


def calculate_cobb_douglas_output(
    tfp: float,
    capital: float,
    worker_skills: Sequence[float],
    alpha: float = 0.3,
    beta: float = 0.7,
) -> float:
    """
    Calculate physical commodity output using Cobb-Douglas production function:
    Y = A * (K^alpha) * (L^beta)
    where:
    - A is Total Factor Productivity (TFP)
    - K is physical installed capital
    - L is effective aggregate labor (sum of employee skills)
    - alpha + beta = 1.0 (constant returns to scale)
    """
    effective_labor = sum(worker_skills)
    if effective_labor <= 0.0 or capital <= 0.0 or tfp <= 0.0:
        return 0.0

    output = tfp * (capital**alpha) * (effective_labor**beta)
    return max(0.0, output)
