"""Tests for the card database loader functionality."""

import pytest
from pathlib import Path
import json
import tempfile
from typing import Dict, List

from src.card_db.core import (
    ItemCard,
    SupporterCard,
    PokemonCard,
    Effect,
    EnergyType,
    Stage,
)
from src.card_db.loader import load_card_db, _parse_trainer, _parse_pokemon, _to_energy, _to_stage

# Test Data Fixtures

@pytest.fixture
def sample_item_card() -> Dict:
    return {
        "id": "test_potion_001",
        "name": "Test Potion",
        "category": "Trainer",
        "subtype": "Item",
        "effect": "Heal 30 damage from one of your Pokemon.",
        "set": "TEST",
        "rarity": "Common"
    }

@pytest.fixture
def sample_supporter_card() -> Dict:
    return {
        "id": "test_prof_001",
        "name": "Test Professor",
        "category": "Trainer",
        "subtype": "Supporter",
        "effect": "Draw 3 cards.",
        "set": "TEST",
        "rarity": "Rare"
    }

@pytest.fixture
def sample_pokemon_card() -> Dict:
    return {
        "id": "test_pika_001",
        "name": "Test Pikachu",
        "category": "Pokemon",
        "hp": "70",
        "types": ["Lightning"],
        "stage": "Basic",
        "attacks": [
            {
                "name": "Thunder Shock",
                "cost": ["Lightning"],
                "damage": "20",
                "effect": "Flip a coin. If heads, your opponent's Active Pokemon is now Paralyzed."
            }
        ],
        "weaknesses": [{"type": "Fighting", "value": "×2"}],
        "retreat": 1
    }

@pytest.fixture
def temp_data_dir(
    sample_item_card: Dict,
    sample_supporter_card: Dict,
    sample_pokemon_card: Dict
) -> Path:
    """Create a temporary data directory with test card data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_path = Path(temp_dir)
        
        # Create test set file
        test_set = [sample_item_card, sample_supporter_card, sample_pokemon_card]
        with open(data_path / "test_set.json", "w") as f:
            json.dump(test_set, f)
            
        yield data_path

# Trainer Card Parsing Tests

def test_parse_item_card(sample_item_card: Dict):
    """Test parsing an Item card."""
    card = _parse_trainer(sample_item_card)
    
    assert isinstance(card, ItemCard)
    assert card.id == "test_potion_001"
    assert card.name == "Test Potion"
    assert len(card.effects) == 1
    assert card.effects[0].effect_type == "text"
    assert card.effects[0].parameters["text"] == "Heal 30 damage from one of your Pokemon."
    assert card.set_code == "TEST"
    assert card.rarity == "Common"

def test_parse_supporter_card(sample_supporter_card: Dict):
    """Test parsing a Supporter card."""
    card = _parse_trainer(sample_supporter_card)
    
    assert isinstance(card, SupporterCard)
    assert card.id == "test_prof_001"
    assert card.name == "Test Professor"
    assert len(card.effects) == 1
    assert card.effects[0].effect_type == "text"
    assert card.effects[0].parameters["text"] == "Draw 3 cards."
    assert card.set_code == "TEST"
    assert card.rarity == "Rare"

def test_parse_trainer_missing_subtype():
    """Test parsing a trainer card with missing subtype defaults to Item."""
    card_data = {
        "id": "test_item_002",
        "name": "Test Item",
        "category": "Trainer",
        "effect": "Test effect"
    }
    
    card = _parse_trainer(card_data)
    assert isinstance(card, ItemCard)

def test_parse_trainer_invalid_subtype():
    """Test parsing a trainer card with unknown subtype defaults to Item."""
    card_data = {
        "id": "test_item_003",
        "name": "Test Item",
        "category": "Trainer",
        "subtype": "InvalidType",
        "effect": "Test effect"
    }
    
    card = _parse_trainer(card_data)
    assert isinstance(card, ItemCard)

def test_parse_trainer_empty_effect():
    """Test parsing a trainer card with no effect text."""
    card_data = {
        "id": "test_item_004",
        "name": "Test Item",
        "category": "Trainer",
        "subtype": "Item"
    }
    
    card = _parse_trainer(card_data)
    assert isinstance(card, ItemCard)
    assert len(card.effects) == 0

# Pokemon Card Parsing Tests

def test_parse_pokemon_card(sample_pokemon_card: Dict):
    """Test parsing a Pokemon card."""
    card = _parse_pokemon(sample_pokemon_card)
    
    assert isinstance(card, PokemonCard)
    assert card.id == "test_pika_001"
    assert card.name == "Test Pikachu"
    assert card.hp == 70
    assert card.pokemon_type == EnergyType.ELECTRIC
    assert card.stage == Stage.BASIC
    assert len(card.attacks) == 1
    assert card.attacks[0].name == "Thunder Shock"
    assert card.attacks[0].cost == [EnergyType.ELECTRIC]
    assert card.attacks[0].damage == 20
    assert card.weakness == EnergyType.FIGHTING
    assert card.retreat_cost == 1

def test_parse_pokemon_with_resistance():
    """Test parsing Pokemon with resistance (TCG Pocket has no resistance)."""
    raw = {
        "id": "test_pika_003",
        "name": "Test Pikachu",
        "category": "Pokemon",
        "hp": "70",
        "types": ["Lightning"],
        "stage": "Basic",
        "resistances": [{"type": "Fighting", "value": "-20"}]  # Should be ignored
    }
    card = _parse_pokemon(raw)
    
    # TCG Pocket has no resistance (rulebook §1)
    # The resistance data should be ignored, not parsed
    assert not hasattr(card, 'resistance')  # No resistance attribute
    assert card.weakness is None  # No weakness in this test
    assert card.pokemon_type == EnergyType.ELECTRIC

# Database Loading Tests

def test_load_card_db(temp_data_dir: Path):
    """Test loading a complete card database."""
    db = load_card_db(temp_data_dir)
    
    assert len(db) == 3
    
    # Test card lookup by ID
    item = db.get("test_potion_001")
    assert isinstance(item, ItemCard)
    
    supporter = db.get("test_prof_001")
    assert isinstance(supporter, SupporterCard)
    
    pokemon = db.get("test_pika_001")
    assert isinstance(pokemon, PokemonCard)
    
    # Test card lookup by name
    assert isinstance(db.find("Test Potion"), ItemCard)
    assert isinstance(db.find("Test Professor"), SupporterCard)
    assert isinstance(db.find("Test Pikachu"), PokemonCard)

def test_load_card_db_missing_directory():
    """Test loading from a non-existent directory."""
    with pytest.raises(FileNotFoundError):
        load_card_db("nonexistent_directory")

def test_load_card_db_empty_directory(tmp_path: Path):
    """Test loading from an empty directory."""
    db = load_card_db(tmp_path)
    assert len(db) == 0

def test_load_card_db_invalid_json(tmp_path: Path):
    """Test handling invalid JSON files."""
    # Create invalid JSON file
    with open(tmp_path / "invalid.json", "w") as f:
        f.write("invalid json content")
    
    # Should not raise exception but print warning
    db = load_card_db(tmp_path)
    assert len(db) == 0

def test_load_card_db_invalid_card_data(tmp_path: Path):
    """Test handling valid JSON but invalid card data."""
    invalid_card = [{"category": "Pokemon", "name": "Invalid"}]  # Missing required fields
    
    with open(tmp_path / "invalid_card.json", "w") as f:
        json.dump(invalid_card, f)
    
    # Should not raise exception but print warning
    db = load_card_db(tmp_path)
    assert len(db) == 0

# Edge Cases and Error Handling

def test_parse_trainer_case_insensitive():
    """Test that subtype parsing is case-insensitive."""
    card_data = {
        "id": "test_item_005",
        "name": "Test Item",
        "category": "Trainer",
        "subtype": "sUpPoRtEr",
        "effect": "Test effect"
    }
    
    card = _parse_trainer(card_data)
    assert isinstance(card, SupporterCard)

def test_parse_trainer_list_effect():
    """Test parsing a trainer card with effect as a list."""
    card_data = {
        "id": "test_item_006",
        "name": "Test Item",
        "category": "Trainer",
        "subtype": "Item",
        "effect": ["Effect 1", "Effect 2"]
    }
    
    card = _parse_trainer(card_data)
    assert isinstance(card, ItemCard)
    # TCG Pocket rulebook doesn't specify how to handle multiple effects
    # For now, we take the first effect only
    assert len(card.effects) == 1
    assert card.effects[0].parameters["text"] == "Effect 1"

def test_to_energy_invalid():
    """Test handling invalid energy type."""
    with pytest.raises(ValueError):
        _to_energy("invalid_type")

def test_to_stage_invalid():
    """Test handling invalid stage."""
    with pytest.raises(ValueError):
        _to_stage("invalid_stage")

def test_parse_pokemon_with_ability():
    """Test parsing Pokemon with ability."""
    raw = {
        "id": "test_pika_002",
        "name": "Test Pikachu",
        "category": "Pokemon",
        "hp": "70",
        "types": ["Lightning"],
        "stage": "Basic",
        "abilities": [{
            "name": "Static",
            "type": "Ability",
            "effect": "When this Pokemon is hit..."
        }]
    }
    card = _parse_pokemon(raw)
    assert card.ability is not None
    assert card.ability.name == "Static" 
    assert card.ability.name == "Static"

# Remove the duplicate test_parse_pokemon_with_resistance() function at the end
# Keep only the first one that correctly states TCG Pocket has no resistance 