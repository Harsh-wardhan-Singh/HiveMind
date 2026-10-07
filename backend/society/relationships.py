"""HIVEMIND Social Graph & Interpersonal Relationship System."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RelationType(str, Enum):
    SPOUSE = "SPOUSE"
    PARENT = "PARENT"
    CHILD = "CHILD"
    SIBLING = "SIBLING"
    COWORKER = "COWORKER"
    NEIGHBOR = "NEIGHBOR"
    FRIEND = "FRIEND"


@dataclass
class SocialEdge:
    source_agent_id: str
    target_agent_id: str
    relation: RelationType
    trust: float = 0.5  # [0.0, 1.0]
    interaction_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_agent_id,
            "target": self.target_agent_id,
            "relation": self.relation.value,
            "trust": round(self.trust, 4),
            "interactions": self.interaction_count,
        }


class RelationshipGraph:
    """Manages sparse interpersonal social graph edges."""

    def __init__(self):
        self._edges: dict[tuple[str, str], SocialEdge] = {}
        self._adj: dict[str, list[str]] = {}

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: RelationType,
        trust: float = 0.5,
    ) -> SocialEdge:
        """Add or update a directional social edge."""
        edge = SocialEdge(
            source_agent_id=source_id,
            target_agent_id=target_id,
            relation=relation,
            trust=trust,
        )
        key = (source_id, target_id)
        self._edges[key] = edge

        if source_id not in self._adj:
            self._adj[source_id] = []
        if target_id not in self._adj[source_id]:
            self._adj[source_id].append(target_id)

        return edge

    def get_edge(self, source_id: str, target_id: str) -> SocialEdge | None:
        return self._edges.get((source_id, target_id))

    def get_neighbors(self, agent_id: str) -> list[str]:
        return self._adj.get(agent_id, [])

    def remove_agent(self, agent_id: str) -> None:
        """Purge all edges connected to an agent upon death or emigration."""
        keys_to_delete = [
            k for k in self._edges if k[0] == agent_id or k[1] == agent_id
        ]
        for k in keys_to_delete:
            del self._edges[k]
        if agent_id in self._adj:
            del self._adj[agent_id]
        for neighbors in self._adj.values():
            if agent_id in neighbors:
                neighbors.remove(agent_id)

