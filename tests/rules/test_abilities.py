"""Tests for ability system."""

import pytest
from src.rules.actions import ActionValidator, AbilityTriggerChecker, AbilityAction, ActionType
from src.rules.game_state import GameState, PlayerState, GamePhase
from src.card_db.core import (
    PokemonCard, Ability, AbilityType, Effect, EnergyType, Stage, StatusCondition
)


@pytest.fixture
def ability_pokemon():
    """Create a Pokemon with an activated ability."""
    return PokemonCard(
        id="TEST_003",
        name="Test Ability Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        ability=Ability(
            name="Test Ability",
            ability_type=AbilityType.ACTIVATED,
            effects=[Effect(effect_type="draw_cards", amount=1, target=None, conditions=[], parameters={})],
            cost=[],
            usage_limit=None,
            trigger=None,
            description=None
        )
    )


@pytest.fixture
def energy_ability_pokemon():
    """Create a Pokemon with an ability that costs energy."""
    return PokemonCard(
        id="TEST_005",
        name="Energy Ability Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        ability=Ability(
            name="Energy Ability",
            ability_type=AbilityType.ACTIVATED,
            effects=[Effect(effect_type="damage", amount=30, target=None, conditions=[], parameters={})],
            cost=[EnergyType.COLORLESS],
            usage_limit=None,
            trigger=None,
            description=None
        ),
        attached_energies=[EnergyType.COLORLESS]  # Add energy to make ability usable
    )


@pytest.fixture
def trigger_pokemon():
    """Create a Pokemon with a triggered ability."""
    return PokemonCard(
        id="TEST_004",
        name="Test Trigger Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        ability=Ability(
            name="Test Trigger",
            ability_type=AbilityType.TRIGGERED,
            effects=[Effect(effect_type="heal", amount=20, target=None, conditions=[], parameters={})],
            cost=[],
            usage_limit=None,
            trigger="when_damaged",
            description=None
        )
    )


class TestAbilityValidation:
    """Test ability validation logic."""
    
    def test_can_use_activated_ability(self, ability_pokemon):
        """Test that activated abilities can be used."""
        player_state = PlayerState(
            active_pokemon=ability_pokemon
        )
        state = GameState(player=player_state, phase=GamePhase.MAIN)
        
        # Should be able to use activated ability
        assert ActionValidator.can_use_ability(state, ability_pokemon, ability_pokemon.ability)
    
    def test_ability_with_energy_cost(self, energy_ability_pokemon):
        """Test that abilities with energy costs work correctly."""
        player_state = PlayerState(
            active_pokemon=energy_ability_pokemon
        )
        state = GameState(player=player_state, phase=GamePhase.MAIN)
        
        # Should be able to use ability since Pokemon has required energy
        assert ActionValidator.can_use_ability(state, energy_ability_pokemon, energy_ability_pokemon.ability)
    
    def test_trigger_ability_check(self, trigger_pokemon):
        """Test that triggered abilities are detected correctly."""
        player_state = PlayerState(
            active_pokemon=trigger_pokemon
        )
        state = GameState(player=player_state, phase=GamePhase.MAIN)
        
        # Check for triggered abilities - should find none for this trigger type
        triggered = AbilityTriggerChecker.check_triggers(state, "start_of_turn")
        assert len(triggered) == 0
        
        # Check for the correct trigger type
        triggered = AbilityTriggerChecker.check_triggers(state, "when_damaged")
        assert len(triggered) == 1
        assert triggered[0].ability == trigger_pokemon.ability
    
    def test_get_legal_actions_with_abilities(self, ability_pokemon):
        """Test that ability actions are included in legal actions."""
        player_state = PlayerState(
            active_pokemon=ability_pokemon
        )
        state = GameState(player=player_state, phase=GamePhase.MAIN)
        
        actions = ActionValidator.get_legal_actions(state)
        ability_actions = [action for action in actions if action.type == ActionType.USE_ABILITY]
        
        assert len(ability_actions) == 1 