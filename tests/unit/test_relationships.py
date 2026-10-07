"""Unit tests for Social Relationships and Graph."""

from backend.society.relationships import (
    RelationshipGraph,
    RelationType,
    SocialEdge,
)


def test_add_and_get_edge():
    graph = RelationshipGraph()
    edge = graph.add_edge("agent_0001", "agent_0002", RelationType.SPOUSE, trust=0.95)

    assert isinstance(edge, SocialEdge)
    assert edge.relation == RelationType.SPOUSE
    assert edge.trust == 0.95

    fetched = graph.get_edge("agent_0001", "agent_0002")
    assert fetched is not None
    assert fetched.trust == 0.95

    # Reverse direction is directional
    assert graph.get_edge("agent_0002", "agent_0001") is None


def test_neighbors():
    graph = RelationshipGraph()
    graph.add_edge("agent_0001", "agent_0002", RelationType.COWORKER)
    graph.add_edge("agent_0001", "agent_0003", RelationType.NEIGHBOR)

    neighbors = graph.get_neighbors("agent_0001")
    assert len(neighbors) == 2
    assert "agent_0002" in neighbors
    assert "agent_0003" in neighbors


def test_remove_agent_purges_edges():
    graph = RelationshipGraph()
    graph.add_edge("agent_0001", "agent_0002", RelationType.FRIEND)
    graph.add_edge("agent_0003", "agent_0001", RelationType.SIBLING)

    assert graph.get_edge("agent_0001", "agent_0002") is not None
    assert graph.get_edge("agent_0003", "agent_0001") is not None

    graph.remove_agent("agent_0001")

    assert graph.get_edge("agent_0001", "agent_0002") is None
    assert graph.get_edge("agent_0003", "agent_0001") is None
    assert "agent_0001" not in graph.get_neighbors("agent_0003")
