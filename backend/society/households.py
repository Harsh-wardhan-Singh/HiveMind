"""HIVEMIND Household & Family Structure Module."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Household:
    id: str
    district_id: str
    head_agent_id: str
    member_agent_ids: list[str] = field(default_factory=list)
    pooled_cash: float = 0.0
    rent_share: float = 0.0

    def add_member(self, agent_id: str) -> None:
        if agent_id not in self.member_agent_ids:
            self.member_agent_ids.append(agent_id)

    def remove_member(self, agent_id: str) -> None:
        if agent_id in self.member_agent_ids:
            self.member_agent_ids.remove(agent_id)
        if self.head_agent_id == agent_id and self.member_agent_ids:
            self.head_agent_id = self.member_agent_ids[0]

    @property
    def size(self) -> int:
        return len(self.member_agent_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "district_id": self.district_id,
            "head_agent_id": self.head_agent_id,
            "member_count": self.size,
            "member_agent_ids": list(self.member_agent_ids),
            "pooled_cash": round(self.pooled_cash, 2),
            "rent_share": round(self.rent_share, 2),
        }


def create_household(
    district_id: str,
    head_agent_id: str,
    initial_cash: float = 0.0,
    household_id: str | None = None,
) -> Household:
    """Factory helper to form a new household with deterministic ID."""
    hh_id = household_id or f"hh_{head_agent_id}"
    return Household(
        id=hh_id,
        district_id=district_id,
        head_agent_id=head_agent_id,
        member_agent_ids=[head_agent_id],
        pooled_cash=initial_cash,
    )

