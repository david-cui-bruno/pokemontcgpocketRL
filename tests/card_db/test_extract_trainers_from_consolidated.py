"""Tests for trainer card extraction from consolidated data."""
import pytest
from pathlib import Path
import json
import tempfile
import shutil
from src.card_db.extract_trainers_from_consolidated import (
    extract_trainers_from_consolidated,
    create_trainer_summary,
    print_trainer_descriptions
)

@pytest.fixture
def sample_cards():
    """Sample card data for testing."""
    return [
        {
            "id": "swsh1-1",
            "name": "Potion",
            "category": "Trainer",
            "trainer_type": "item",
            "effect": "Heal 30 damage from 1 of your Pokemon."
        },
        {
            "id": "swsh1-2",
            "name": "Professor's Research",
            "category": "Trainer",
            "trainer_type": "supporter",
            "effect": "Draw 7 cards."
        },
        {
            "id": "swsh1-3",
            "name": "Air Balloon",
            "category": "Trainer",
            "trainer_type": "tool",
            "effect": "The Pokemon this card is attached to has no Retreat Cost."
        },
        {
            "id": "swsh1-4",
            "name": "Pikachu",
            "category": "Pokemon",
            "hp": 70,
            "type": "Lightning"
        }
    ]

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

def test_basic_extraction(temp_data_dir, sample_cards):
    """Test basic trainer card extraction and categorization."""
    # Setup test data
    consolidated_file = temp_data_dir / "consolidated_cards_moves.json"
    consolidated_file.write_text(json.dumps(sample_cards))
    
    # Run extraction with test directory
    trainer_cards, categorized = extract_trainers_from_consolidated(base_dir=temp_data_dir)
    
    # Verify results
    assert len(trainer_cards) == 3
    assert len([c for c in trainer_cards if c["trainer_type"] == "item"]) == 1
    assert len([c for c in trainer_cards if c["trainer_type"] == "supporter"]) == 1
    assert len([c for c in trainer_cards if c["trainer_type"] == "tool"]) == 1

def test_categorization_logic(temp_data_dir):
    """Test trainer card categorization logic."""
    test_cards = [
        {
            "id": "test-1",
            "name": "Quick Ball",
            "category": "Trainer",
            "effect": "Search your deck for a Basic Pokemon."
        },
        {
            "id": "test-2",
            "name": "Marnie",
            "category": "Trainer",
            "effect": "Each player shuffles their hand and draws 5 cards."
        },
        {
            "id": "test-3",
            "name": "Tool Band",
            "category": "Trainer",
            "effect": "Attach this card to one of your Pokemon."
        }
    ]
    
    # Setup test data
    consolidated_file = temp_data_dir / "consolidated_cards_moves.json"
    consolidated_file.write_text(json.dumps(test_cards))
    
    # Run extraction with test directory
    _, categorized = extract_trainers_from_consolidated(base_dir=temp_data_dir)
    
    # Verify categorization
    assert len(categorized["items"]) >= 1  # Quick Ball should be an item
    assert len(categorized["supporters"]) >= 1  # Marnie should be a supporter
    assert len(categorized["tools"]) >= 1  # Tool Band should be a tool

def test_edge_cases(temp_data_dir):
    """Test edge cases and unusual inputs."""
    edge_cases = [
        {
            "id": "edge-1",
            "name": "Weird Card",
            "category": "Trainer",
            # Missing trainer_type and effect
        },
        {
            "id": "edge-2",
            "category": "Trainer",
            # Missing name
            "effect": "Some effect"
        }
    ]
    
    # Setup test data
    consolidated_file = temp_data_dir / "consolidated_cards_moves.json"
    consolidated_file.write_text(json.dumps(edge_cases))
    
    # Run extraction with test directory
    trainer_cards, categorized = extract_trainers_from_consolidated(base_dir=temp_data_dir)
    
    # Verify handling of edge cases
    assert len(trainer_cards) == 2  # Should still process both cards
    assert all(card["category"] == "Trainer" for card in trainer_cards)
    assert any(card["id"] == "edge-1" for card in trainer_cards)
    assert any(card["id"] == "edge-2" for card in trainer_cards)

def test_empty_input(temp_data_dir):
    """Test handling of empty input."""
    # Setup empty test data
    consolidated_file = temp_data_dir / "consolidated_cards_moves.json"
    consolidated_file.write_text(json.dumps([]))
    
    # Run extraction with test directory
    trainer_cards, categorized = extract_trainers_from_consolidated(base_dir=temp_data_dir)
    
    # Verify empty results
    assert len(trainer_cards) == 0
    assert all(len(cards) == 0 for cards in categorized.values())

def test_file_outputs(temp_data_dir, sample_cards):
    """Test that all expected output files are created."""
    # Setup test data
    consolidated_file = temp_data_dir / "consolidated_cards_moves.json"
    consolidated_file.write_text(json.dumps(sample_cards))
    
    # Run extraction with test directory
    extract_trainers_from_consolidated(base_dir=temp_data_dir)
    
    # Verify output files exist
    assert (temp_data_dir / "all_trainer_cards.json").exists()
    assert (temp_data_dir / "categorized_trainer_cards.json").exists()
    assert (temp_data_dir / "trainer_cards_summary.json").exists()
    assert (temp_data_dir / "all_pokemon_cards.json").exists()

def test_print_trainer_descriptions(temp_data_dir, sample_cards):
    """Test the trainer description printing function."""
    # Setup test data
    trainer_file = temp_data_dir / "all_trainer_cards.json"
    trainers = [card for card in sample_cards if card["category"] == "Trainer"]
    trainer_file.write_text(json.dumps(trainers))
    
    # Test printing with test directory
    print_trainer_descriptions(base_dir=temp_data_dir) 