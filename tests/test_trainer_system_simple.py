#!/usr/bin/env python3
"""
Simple test to verify the trainer effects system is working.
"""

import pytest
from src.card_db.core import PokemonCard, ItemCard, ToolCard, SupporterCard, EnergyType
from src.card_db.trainer_effects import EffectContext
from src.rules.game_state import GameState, PlayerState

def test_effect_context_creation():
    """Test that EffectContext can be created without circular imports."""
    # Create minimal game state
    player = PlayerState()
    opponent = PlayerState()
    game_state = GameState(player, opponent)
    
    # Create context without game_engine
    ctx = EffectContext(game_state, player)
    
    assert ctx.game_state == game_state
    assert ctx.player == player
    assert ctx.opponent == opponent
    assert ctx.game_engine is None
    assert ctx.failed is False
    assert len(ctx.targets) == 0
    assert len(ctx.data) == 0

def test_trainer_card_creation():
    """Test that trainer cards can be created."""
    # Test Item card
    item_card = ItemCard(
        id="test-item-001",
        name="Test Item",
        effects=[]
    )
    assert item_card.name == "Test Item"
    assert item_card.category == "Trainer"
    
    # Test Supporter card
    supporter_card = SupporterCard(
        id="test-supporter-001", 
        name="Test Supporter",
        effects=[]
    )
    assert supporter_card.name == "Test Supporter"
    assert supporter_card.category == "Trainer"
    
    # Test Tool card
    tool_card = ToolCard(
        id="test-tool-001",
        name="Test Tool", 
        effects=[]
    )
    assert tool_card.name == "Test Tool"
    assert tool_card.category == "Trainer"

def test_trainer_executor_imports():
    """Test that trainer executor can be imported without circular imports."""
    from src.card_db.trainer_executor import execute_trainer_card, can_play_trainer_card
    
    # Test that functions exist
    assert callable(execute_trainer_card)
    assert callable(can_play_trainer_card)