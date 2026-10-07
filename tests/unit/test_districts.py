"""Unit tests for Districts and initialization."""

from backend.simulation.districts import District, initialize_districts


def test_initialize_districts():
    districts = initialize_districts()
    assert len(districts) == 10

    expected_ids = [
        "dist_central",
        "dist_north",
        "dist_south",
        "dist_east",
        "dist_west",
        "dist_industrial",
        "dist_university",
        "dist_suburban",
        "dist_low_income",
        "dist_high_income",
    ]
    for d_id in expected_ids:
        assert d_id in districts
        district = districts[d_id]
        assert isinstance(district, District)
        assert district.land_price > 0
        assert district.rent > 0
        assert 0.0 <= district.safety_score <= 1.0
        assert 0.0 <= district.transport_connectivity <= 1.0
        assert district.housing_units > 0
        assert district.population == 0


def test_district_to_dict():
    districts = initialize_districts()
    central = districts["dist_central"]
    data = central.to_dict()
    assert data["name"] == "Central"
    assert data["housing_units"] == 60
    assert "safety_score" in data
