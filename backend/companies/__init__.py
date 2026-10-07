"""HIVEMIND Companies Package."""

from backend.companies.company import Company
from backend.companies.production import calculate_cobb_douglas_output

__all__ = ["Company", "calculate_cobb_douglas_output"]

