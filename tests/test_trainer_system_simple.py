#!/usr/bin/env python3
"""
Simple test to verify the trainer effects system is working.
"""

import pytest
from src.card_db.core import PokemonCard, ItemCard, ToolCard, SupporterCard, EnergyType
from src.card_db.trainer_effects import EffectContext
from src.rules.game_state import GameState, PlayerState
from src.rules.game_engine import GameEngine

def test_effect_context_creation():
    """Test that EffectContext can be created without circular imports."""
    # Create minimal game state
    player = PlayerState()
    opponent = PlayerState()
    game_state = GameState(player, opponent)
    game_engine = GameEngine()
    
    # Create context with game_engine
    ctx = EffectContext(game_state, player, game_engine)
    
    assert ctx.game_state == game_state
    assert ctx.player == player
    assert ctx.opponent == opponent
    assert ctx.game_engine == game_engine
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
    # ItemCard doesn't have a 'category' attribute - it's a TrainerCard type
    
    # Test Supporter card
    supporter_card = SupporterCard(
        id="test-supporter-001", 
        name="Test Supporter",
        effects=[]
    )
    assert supporter_card.name == "Test Supporter"
    
    # Test Tool card
    tool_card = ToolCard(
        id="test-tool-001",
        name="Test Tool", 
        effects=[]
    )
    assert tool_card.name == "Test Tool"
    
    # Test that they're all different types but all trainer cards
    assert isinstance(item_card, ItemCard)
    assert isinstance(supporter_card, SupporterCard)
    assert isinstance(tool_card, ToolCard)

def test_trainer_executor_imports():
    """Test that trainer executor can be imported without circular imports."""
    from src.card_db.trainer_executor import execute_trainer_card, can_play_trainer_card
    
    # Test that functions exist
    assert callable(execute_trainer_card)
    assert callable(can_play_trainer_card)

def test_trainer_registry_imports():
    """Test that trainer registry can be imported."""
    from src.card_db.comprehensive_trainer_registry import TRAINER_EFFECTS
    
    # Test that TRAINER_EFFECTS exists and is a dict
    assert isinstance(TRAINER_EFFECTS, dict)
    assert len(TRAINER_EFFECTS) > 0

def test_trainer_effects_imports():
    """Test that trainer effects modules can be imported."""
    from src.card_db.trainer_effects import (
        EffectContext,
        require_bench_pokemon,
        player_chooses_target,
        heal_pokemon
    )
    
    # Test that key functions exist
    assert callable(require_bench_pokemon)
    assert callable(player_chooses_target)
    assert callable(heal_pokemon)

def test_basic_trainer_functionality():
    """Test basic trainer card functionality."""
    # Create game state
    player = PlayerState()
    opponent = PlayerState()
    game_state = GameState(player, opponent)
    game_engine = GameEngine()
    
    # Create a trainer card
    trainer_card = ItemCard(
        id="test-item-001",
        name="Test Item",
        effects=[]
    )
    
    # Test that we can check if it can be played
    from src.card_db.trainer_executor import can_play_trainer_card
    can_play = can_play_trainer_card(trainer_card, game_state, player, game_engine)
    assert can_play is not None  # Should return a boolean
    
    # Test that we can execute it (even if it fails due to missing effect)
    from src.card_db.trainer_executor import execute_trainer_card
    success = execute_trainer_card(trainer_card, game_state, player, game_engine)
    # This might fail because we don't have the effect defined, but shouldn't crash
    assert isinstance(success, bool)