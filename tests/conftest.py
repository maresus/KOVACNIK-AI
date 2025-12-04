"""
Pytest fixtures za Kovačnik AI teste.
"""
import pytest
import sys
from pathlib import Path

# Dodaj root projekt v path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def reset_reservation_state():
    """Fixture ki resetira reservation_state pred vsakim testom."""
    from app.services.chat_router import reset_reservation_state, reservation_state
    reset_reservation_state()
    yield reservation_state
    reset_reservation_state()


@pytest.fixture
def reset_wine_state():
    """Fixture ki resetira wine query state."""
    from app.services import chat_router
    chat_router.last_wine_query = None
    chat_router.last_shown_products = []
    yield
    chat_router.last_wine_query = None
    chat_router.last_shown_products = []


@pytest.fixture
def reset_all_state(reset_reservation_state, reset_wine_state):
    """Kombiniran fixture za reset vsega."""
    yield
