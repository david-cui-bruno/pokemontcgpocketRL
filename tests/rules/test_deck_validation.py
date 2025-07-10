"""Tests for deck validation rules."""

import pytest
from src.rules.game_engine import GameEngine
from src.card_db.core import PokemonCard, ItemCard, SupporterCard
from src.rules.constants import EnergyType, Stage

def test_deck_size():
    """Test deck size must be exactly 20 cards."""
    engine = GameEngine()
    
    # Create a valid deck
    valid_deck = [
        PokemonCard(
            id=f"TEST-{i}",
            name=f"Test Pokemon {i}",
            pokemon_type=EnergyType.COLORLESS,
            hp=100,
            stage=Stage.BASIC
        ) for i in range(20)
    ]
    
    assert engine._validate_deck(valid_deck)
    
    # Test too small
    assert not engine._validate_deck(valid_deck[:-1])
    
    # Test too large
    assert not engine._validate_deck(valid_deck + [valid_deck[0]])

def test_basic_pokemon_requirement():
    """Test deck must contain at least one Basic Pokemon."""
    engine = GameEngine()
    
    # Create deck with no Basic Pokemon
    invalid_deck = [
        ItemCard(
            id=f"ITEM-{i}",
            name=f"Test Item {i}",
            effects=[],
            text="Test effect"
        ) for i in range(20)
    ]
    
    assert not engine._validate_deck(invalid_deck) 