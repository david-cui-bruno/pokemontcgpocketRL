"""Tests for the card storage functionality."""

import json
import pytest
from pathlib import Path
from src.card_db.storage import CardStorage

@pytest.fixture
def temp_storage(tmp_path: Path) -> CardStorage:
    """Create a temporary CardStorage instance."""
    return CardStorage(str(tmp_path))

@pytest.fixture
def sample_set_data() -> dict:
    """Sample set data for testing."""
    return {
        "set_id": "TEST1",
        "name": "Test Set",
        "cards": [
            {"id": "TEST1-001", "name": "Test Card 1"},
            {"id": "TEST1-002", "name": "Test Card 2"}
        ]
    }

@pytest.fixture
def sample_card_data() -> dict:
    """Sample card data for testing."""
    return {
        "id": "TEST1-001",
        "name": "Test Card",
        "category": "Pokemon",
        "hp": 100,
        "types": ["Fire"],
        "attacks": [
            {
                "name": "Test Attack",
                "damage": 50,
                "cost": ["Fire", "Colorless"]
            }
        ]
    }

def test_storage_initialization(temp_storage: CardStorage, tmp_path: Path):
    """Test that storage directories are created properly."""
    assert (tmp_path / "sets").exists()
    assert (tmp_path / "sets").is_dir()
    assert (tmp_path / "cards").exists()
    assert (tmp_path / "cards").is_dir()

def test_store_and_get_set(temp_storage: CardStorage, sample_set_data: dict):
    """Test storing and retrieving set data."""
    set_id = "TEST1"
    
    # Store set data
    temp_storage.store_set(set_id, sample_set_data)
    
    # Verify file exists
    set_path = temp_storage.sets_dir / f"{set_id}.json"
    assert set_path.exists()
    
    # Verify data was stored correctly
    stored_data = temp_storage.get_set(set_id)
    assert stored_data == sample_set_data
    
    # Verify raw JSON content
    with open(set_path) as f:
        raw_data = json.load(f)
    assert raw_data == sample_set_data

def test_store_and_get_card(temp_storage: CardStorage, sample_card_data: dict):
    """Test storing and retrieving card data."""
    card_id = "TEST1-001"
    
    # Store card data
    temp_storage.store_card(card_id, sample_card_data)
    
    # Verify file exists
    card_path = temp_storage.cards_dir / f"{card_id}.json"
    assert card_path.exists()
    
    # Verify data was stored correctly
    stored_data = temp_storage.get_card(card_id)
    assert stored_data == sample_card_data

def test_get_nonexistent_set(temp_storage: CardStorage):
    """Test retrieving a set that doesn't exist."""
    assert temp_storage.get_set("NONEXISTENT") is None

def test_get_nonexistent_card(temp_storage: CardStorage):
    """Test retrieving a card that doesn't exist."""
    assert temp_storage.get_card("NONEXISTENT-001") is None

def test_list_sets(temp_storage: CardStorage, sample_set_data: dict):
    """Test listing all available sets."""
    # Store multiple sets
    sets = ["TEST1", "TEST2", "TEST3"]
    for set_id in sets:
        temp_storage.store_set(set_id, sample_set_data)
    
    # Verify list
    stored_sets = temp_storage.list_sets()
    assert sorted(stored_sets) == sorted(sets)

def test_list_cards(temp_storage: CardStorage, sample_card_data: dict):
    """Test listing all available cards."""
    # Store multiple cards
    cards = ["TEST1-001", "TEST1-002", "TEST1-003"]
    for card_id in cards:
        temp_storage.store_card(card_id, sample_card_data)
    
    # Verify list
    stored_cards = temp_storage.list_cards()
    assert sorted(stored_cards) == sorted(cards)

def test_list_cards_empty_directory(temp_storage: CardStorage):
    """Test listing cards when directory is empty."""
    assert temp_storage.list_cards() == []

def test_invalid_json_handling(temp_storage: CardStorage):
    """Test handling of invalid JSON data."""
    # Create invalid JSON file
    set_path = temp_storage.sets_dir / "invalid.json"
    with open(set_path, "w") as f:
        f.write("invalid json content")
    
    # Should return None instead of raising exception
    assert temp_storage.get_set("invalid") is None