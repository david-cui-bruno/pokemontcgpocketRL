"""Tests for the comprehensive trainer registry."""
import pytest
from src.card_db.comprehensive_trainer_registry import (
    get_trainer_effect_function,
    get_effect_for_card,
    get_all_covered_effects,
    get_missing_effects,
    COMPREHENSIVE_TRAINER_EFFECTS,
    CARD_NAME_TO_EFFECT
)
from src.card_db.trainer_effects.context import EffectContext
from src.card_db.core import PokemonCard, EnergyType, Stage
from src.rules.game_state import GameState, PlayerState, PlayerTag

@pytest.fixture
def basic_context():
    """Create a basic context for testing."""
    player = PlayerState(
        deck=[],
        hand=[],
        active_pokemon=PokemonCard(
            name="Test Pokemon",
            hp=100,
            stage=Stage.BASIC,
            pokemon_type=EnergyType.COLORLESS,
            retreat_cost=1,
            damage_counters=30
        ),
        benched_pokemon=[],
        prizes_remaining=6
    )
    game_state = GameState(
        player=player,
        opponent=PlayerState(prizes_remaining=6),
        active_player_tag=PlayerTag.PLAYER
    )
    return EffectContext(
        player=player,
        game_state=game_state,
        targets=[],
        failed=False
    )

def test_get_trainer_effect_function():
    """Test getting trainer effect functions."""
    # Test known effect
    heal_effect = get_trainer_effect_function("Heal 20 damage from 1 of your Pokémon.")
    assert heal_effect is not None
    
    # Test unknown effect
    unknown_effect = get_trainer_effect_function("Not a real effect")
    assert unknown_effect is None

def test_get_effect_for_card():
    """Test getting effect text for specific cards."""
    # Test known card
    potion_effect = get_effect_for_card("Potion")
    assert potion_effect == "Heal 20 damage from 1 of your Pokémon."
    
    # Test unknown card
    unknown_effect = get_effect_for_card("Not a real card")
    assert unknown_effect is None

def test_get_all_covered_effects():
    """Test getting all covered effects."""
    effects = get_all_covered_effects()
    assert isinstance(effects, list)
    assert len(effects) > 0
    assert "Heal 20 damage from 1 of your Pokémon." in effects

def test_get_missing_effects():
    """Test getting missing effects."""
    missing = get_missing_effects()
    assert isinstance(missing, set)
    # Note: This might be empty if all effects are covered

def test_healing_effects(basic_context):
    """Test healing effect functions."""
    heal_effect = get_trainer_effect_function("Heal 20 damage from 1 of your Pokémon.")
    assert heal_effect is not None
    
    # Set target to active Pokemon
    context = basic_context
    context.targets = [context.player.active_pokemon]
    
    # Apply healing effect
    for effect_fn in heal_effect:
        context = effect_fn(context)
    
    # Check healing was applied
    assert context.player.active_pokemon.damage_counters == 10

def test_type_specific_healing(basic_context):
    """Test type-specific healing effects."""
    heal_effect = get_trainer_effect_function("Heal 30 damage from 1 of your Grass Pokémon.")
    assert heal_effect is not None
    
    # Test with non-Grass Pokemon
    context = basic_context
    context.targets = [context.player.active_pokemon]
    
    for effect_fn in heal_effect:
        context = effect_fn(context)
    
    # Healing should fail due to wrong type
    assert context.failed
    assert context.player.active_pokemon.damage_counters == 30

def test_tool_attachment(basic_context):
    """Test tool card attachment effect."""
    attach_effect = get_trainer_effect_function("Attach this card to 1 of your Pokémon.")
    assert attach_effect is not None
    
    # Set up context with tool card
    context = basic_context
    context.targets = [context.player.active_pokemon]
    context.data = {'card': {'name': 'Test Tool', 'card_type': 'Tool'}}
    
    for effect_fn in attach_effect:
        context = effect_fn(context)
    
    # Check tool was attached
    assert not context.failed

def test_card_name_mappings():
    """Test card name to effect mappings."""
    # Test all trainer cards have valid effects
    for card_name, effect_text in CARD_NAME_TO_EFFECT.items():
        assert effect_text in COMPREHENSIVE_TRAINER_EFFECTS, f"Effect for {card_name} not found in registry"

def test_effect_composition():
    """Test that effect functions can be composed."""
    heal_effect = get_trainer_effect_function("Heal 30 damage from 1 of your Grass Pokémon.")
    assert isinstance(heal_effect, list)
    assert len(heal_effect) == 3  # player_chooses_target, require_pokemon_type, heal_pokemon
