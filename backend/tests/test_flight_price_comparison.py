"""Tests for flight price comparison and multi-site search features."""

import pytest
from unittest.mock import MagicMock
from app.streaming.session import SpectraStreamingSession


class MockWebSocket:
    def __init__(self):
        self.messages = []
        self.is_connected = True

    async def send_json(self, data):
        self.messages.append(data)

    async def close(self, code=None, reason=None):
        self.is_connected = False


@pytest.fixture
def session():
    """Create a test session with mocked dependencies."""
    ws = MockWebSocket()
    session = SpectraStreamingSession(ws, user_id="test-user")
    return session


class TestFlightPriceMemory:
    """Tests for flight price tracking and comparison."""

    def test_save_single_flight_price(self, session):
        """Should save a single flight price."""
        session._save_flight_price(
            site="Google Flights",
            airline="Ryanair",
            price=79.0,
            currency="EUR",
            route="DUB-LHR",
            flight_time="6am"
        )

        assert len(session._flight_prices) == 1
        assert session._flight_prices[0]["airline"] == "Ryanair"
        assert session._flight_prices[0]["price"] == 79.0
        assert session._flight_prices[0]["site"] == "Google Flights"

    def test_save_multiple_flight_prices(self, session):
        """Should save multiple flight prices from different sites."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR", "6am")
        session._save_flight_price("Skyscanner", "Vueling", 72.0, "EUR", "DUB-LHR", "7am")
        session._save_flight_price("Kayak", "EasyJet", 84.0, "EUR", "DUB-LHR", "8am")

        assert len(session._flight_prices) == 3

    def test_get_cheapest_flight(self, session):
        """Should return the cheapest flight from tracked prices."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR")
        session._save_flight_price("Skyscanner", "Vueling", 72.0, "EUR", "DUB-LHR")
        session._save_flight_price("Kayak", "EasyJet", 84.0, "EUR", "DUB-LHR")

        cheapest = session._get_cheapest_flight()
        assert cheapest is not None
        assert cheapest["airline"] == "Vueling"
        assert cheapest["price"] == 72.0
        assert cheapest["site"] == "Skyscanner"

    def test_get_cheapest_flight_empty(self, session):
        """Should return None when no prices tracked."""
        cheapest = session._get_cheapest_flight()
        assert cheapest is None

    def test_compare_flight_prices(self, session):
        """Should generate a formatted comparison summary."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR", "6am")
        session._save_flight_price("Skyscanner", "Vueling", 72.0, "EUR", "DUB-LHR", "7am")
        session._save_flight_price("Kayak", "EasyJet", 84.0, "EUR", "DUB-LHR", "8am")

        comparison = session._compare_flight_prices()

        assert "Vueling" in comparison
        assert "EUR72" in comparison
        assert "Skyscanner" in comparison
        assert "Recommendation" in comparison
        assert "1." in comparison  # Should be numbered list
        assert "2." in comparison
        assert "3." in comparison

    def test_compare_flight_prices_empty(self, session):
        """Should return appropriate message when no prices tracked."""
        comparison = session._compare_flight_prices()
        assert "No flight prices tracked" in comparison

    def test_clear_flight_prices(self, session):
        """Should clear all tracked prices."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR")
        session._save_flight_price("Skyscanner", "Vueling", 72.0, "EUR", "DUB-LHR")

        assert len(session._flight_prices) == 2

        session._clear_flight_prices()

        assert len(session._flight_prices) == 0

    def test_current_search_route(self, session):
        """Should use current search route when route not specified."""
        session._current_search_route = "Dublin to Paris"
        session._save_flight_price("Google Flights", "Ryanair", 110.0, "EUR")

        assert session._flight_prices[0]["route"] == "Dublin to Paris"

    def test_flight_price_has_timestamp(self, session):
        """Should include timestamp for each saved price."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR")

        assert "timestamp" in session._flight_prices[0]
        assert isinstance(session._flight_prices[0]["timestamp"], float)
        assert session._flight_prices[0]["timestamp"] > 0


class TestMultiSiteComparison:
    """Tests for multi-site price comparison workflows."""

    def test_price_comparison_sorted_by_price(self, session):
        """Should sort prices from cheapest to most expensive."""
        session._save_flight_price("Kayak", "EasyJet", 84.0, "EUR", "DUB-LHR")
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR")
        session._save_flight_price("Skyscanner", "Vueling", 72.0, "EUR", "DUB-LHR")

        comparison = session._compare_flight_prices()
        lines = comparison.split("\n")

        # First line should be cheapest (Vueling 72)
        assert "Vueling" in lines[0]
        assert "EUR72" in lines[0]

    def test_price_comparison_includes_site_info(self, session):
        """Should include site name in comparison output."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR")
        session._save_flight_price("Skyscanner", "Vueling", 72.0, "EUR", "DUB-LHR")

        comparison = session._compare_flight_prices()

        assert "Google Flights" in comparison
        assert "Skyscanner" in comparison

    def test_recommendation_shows_cheapest(self, session):
        """Recommendation should highlight the cheapest option."""
        session._save_flight_price("Google Flights", "Expensive", 200.0, "EUR", "DUB-LHR")
        session._save_flight_price("Skyscanner", "Cheap", 50.0, "EUR", "DUB-LHR")
        session._save_flight_price("Kayak", "Medium", 100.0, "EUR", "DUB-LHR")

        comparison = session._compare_flight_prices()

        assert "Recommendation" in comparison
        assert "Cheap" in comparison
        assert "EUR50" in comparison
        assert "Skyscanner" in comparison


class TestMultiCityRouting:
    """Tests for multi-city route planning."""

    def test_track_multi_leg_prices(self, session):
        """Should track prices for multiple legs of a journey."""
        # Leg 1: Dublin to London
        session._current_search_route = "Dublin to London"
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", flight_time="6am")

        # Leg 2: London to Paris
        session._current_search_route = "London to Paris"
        session._save_flight_price("Google Flights", "EasyJet", 45.0, "EUR", flight_time="10am")

        assert len(session._flight_prices) == 2
        assert session._flight_prices[0]["route"] == "Dublin to London"
        assert session._flight_prices[1]["route"] == "London to Paris"

    def test_calculate_multi_leg_total(self, session):
        """Should support calculating total for multi-leg journeys."""
        session._save_flight_price("Google Flights", "Ryanair", 79.0, "EUR", "DUB-LHR")
        session._save_flight_price("Google Flights", "EasyJet", 45.0, "EUR", "LHR-CDG")

        total = sum(price["price"] for price in session._flight_prices)
        assert total == 124.0


class TestSystemInstructionIntegration:
    """Tests that system instructions include flight booking guidance."""

    def test_travel_booking_section_exists(self):
        """System instructions should include TRAVEL BOOKING section."""
        from app.agents.system_instruction import WORKFLOW
        assert "TRAVEL BOOKING" in WORKFLOW

    def test_multi_site_comparison_section_exists(self):
        """System instructions should include multi-site comparison guidance."""
        from app.agents.system_instruction import WORKFLOW
        assert "MULTI-SITE PRICE COMPARISON" in WORKFLOW

    def test_price_comparison_example_exists(self):
        """Examples should include price comparison workflow."""
        from app.agents.system_instruction import EXAMPLES
        assert "price_comparison" in EXAMPLES

    def test_multi_city_example_exists(self):
        """Examples should include multi-city routing workflow."""
        from app.agents.system_instruction import EXAMPLES
        assert "multi_city_route" in EXAMPLES

    def test_price_memory_instructions(self):
        """System instructions should mention price tracking."""
        from app.agents.system_instruction import WORKFLOW
        workflow_lower = WORKFLOW.lower()
        assert "price" in workflow_lower
        assert "track" in workflow_lower or "remember" in workflow_lower

    def test_route_optimisation_instructions(self):
        """System instructions should include route optimisation guidance."""
        from app.agents.system_instruction import WORKFLOW
        assert "ROUTE OPTIMISATION" in WORKFLOW or "optimisation" in WORKFLOW.lower()
