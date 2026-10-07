"""Unit tests for Households and Family dynamics."""

from backend.society.households import create_household


def test_household_creation():
    hh = create_household(
        district_id="dist_central",
        head_agent_id="agent_0001",
        initial_cash=5000.0,
    )
    assert hh.district_id == "dist_central"
    assert hh.head_agent_id == "agent_0001"
    assert hh.size == 1
    assert "agent_0001" in hh.member_agent_ids
    assert hh.pooled_cash == 5000.0


def test_household_add_remove_member():
    hh = create_household(district_id="dist_north", head_agent_id="agent_0001")
    hh.add_member("agent_0002")
    assert hh.size == 2
    assert "agent_0002" in hh.member_agent_ids

    # Adding duplicate should not change size
    hh.add_member("agent_0002")
    assert hh.size == 2

    # Remove head: second member becomes new head
    hh.remove_member("agent_0001")
    assert hh.size == 1
    assert hh.head_agent_id == "agent_0002"

    # Remove remaining member
    hh.remove_member("agent_0002")
    assert hh.size == 0


def test_household_to_dict():
    hh = create_household(
        district_id="dist_south",
        head_agent_id="agent_0005",
        initial_cash=1200.50,
    )
    hh.rent_share = 350.0
    data = hh.to_dict()
    assert data["district_id"] == "dist_south"
    assert data["head_agent_id"] == "agent_0005"
    assert data["pooled_cash"] == 1200.50
    assert data["rent_share"] == 350.0
    assert data["member_count"] == 1
