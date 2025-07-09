"""Card database module.

Parses card JSON and exposes immutable dataclasses for all card types,
effects, and game objects. This module provides the foundational data
structures that the rules engine operates on.
"""

from .core import (
    PokemonCard, ItemCard, SupporterCard, EnergyCard, Card,
    Attack, Effect, Ability, EnergyType, Stage, StatusCondition, 
    AbilityType, TargetType
)
from .loader import CardLoader

# Create a global card loader instance
_card_loader = CardLoader()

def load_card_db():
    """Load all cards from the data directory."""
    return _card_loader.load_all_cards()

def get_cards_by_set(set_code: str):
    """Load cards from a specific set."""
    return _card_loader.load_cards_by_set(set_code)

# Load the card database on import
try:
    CARD_DB = load_card_db()
except Exception as e:
    print(f"Warning: Could not load card database: {e}")
    CARD_DB = [] 