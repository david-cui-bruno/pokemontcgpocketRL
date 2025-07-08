"""Tests for card database scraper."""

import pytest
from src.card_db.scraper import (
    RawCardData,
    parse_card_data,
    PokemonCard,
    ItemCard,
    SupporterCard,
)

def test_parse_pokemon_card() -> None:
    """Test parsing raw data into a Pokemon card."""
    raw = RawCardData(
        id="sv1_001",
        name="Pikachu",
        card_type="Pokemon",
        set_code="SV1",
        rarity="Rare",
        hp=70,
        pokemon_type="electric",
        stage="basic",
        retreat_cost=1,
        attacks=[{
            "name": "Thunder Shock",
            "cost": ["electric"],
            "damage": 20,
            "effects": []
        }]
    )
    
    with pytest.raises(NotImplementedError):
        card = parse_card_data(raw)
        # TODO: Add assertions once parse_card_data is implemented

def test_parse_item_card() -> None:
    """Test parsing raw data into an Item card."""
    raw = RawCardData(
        id="sv1_100",
        name="Potion",
        card_type="Item",
        set_code="SV1",
        rarity="Common",
        effects=[{
            "type": "heal",
            "amount": 20,
            "target": "any_pokemon"
        }]
    )
    
    with pytest.raises(NotImplementedError):
        card = parse_card_data(raw)
        # TODO: Add assertions once parse_card_data is implemented

def test_parse_supporter_card() -> None:
    """Test parsing raw data into a Supporter card."""
    raw = RawCardData(
        id="sv1_200",
        name="Professor Oak",
        card_type="Supporter",
        set_code="SV1",
        rarity="Uncommon",
        effects=[{
            "type": "draw_cards",
            "amount": 2
        }]
    )
    
    with pytest.raises(NotImplementedError):
        card = parse_card_data(raw)
        # TODO: Add assertions once parse_card_data is implemented 