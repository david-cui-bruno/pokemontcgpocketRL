"""Tests for the action system."""

import pytest
import dataclasses
from src.rules.actions import ActionValidator, ActionType
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import PokemonCard, Attack, EnergyType, Stage, StatusCondition


@pytest.fixture
def basic_pokemon():
    """Create a basic Pokemon for testing."""
    return PokemonCard(
        id="TEST_001",
        name="Test Basic",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=20, effects=[], description=None)],
        retreat_cost=1
    )


@pytest.fixture
def evolution_pokemon():
    """Create an evolution Pokemon for testing."""
    return PokemonCard(
        id="TEST_002",
        name="Test Evolution",
        hp=120,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.STAGE_1,
        evolves_from="Test Basic",
        attacks=[Attack(name="Big Attack", cost=[EnergyType.COLORLESS, EnergyType.COLORLESS], damage=40, effects=[], description=None)],
        retreat_cost=2
    )


@pytest.fixture
def basic_game_state(basic_pokemon, evolution_pokemon):
    """Create a basic game state for testing."""
    player_state = PlayerState(
        player_tag=PlayerTag.PLAYER,
        active_pokemon=basic_pokemon,
        hand=[evolution_pokemon]
    )
    opponent_state = PlayerState(player_tag=PlayerTag.OPPONENT)
    return GameState(player=player_state, opponent=opponent_state, phase=GamePhase.MAIN)


class TestActionValidation:
    """Test action validation logic."""

    def test_can_play_basic_pokemon(self, basic_game_state):
        """Test that basic Pokemon can be played to bench."""
        basic_pokemon = PokemonCard(
            id="TEST_003",
            name="New Basic",
            hp=80,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        game_state = dataclasses.replace(
            basic_game_state,
            player=dataclasses.replace(basic_game_state.player, hand=basic_game_state.player.hand + [basic_pokemon])
        )
        assert ActionValidator.can_play_pokemon(game_state, basic_pokemon)

    def test_can_evolve_pokemon(self, basic_game_state, evolution_pokemon):
        """Test that Pokemon can be evolved."""
        # The test expects evolution to be allowed when conditions are met
        assert ActionValidator.can_play_pokemon(basic_game_state, evolution_pokemon, basic_game_state.player.active_pokemon)

    def test_can_retreat(self, basic_game_state):
        """Test that Pokemon can retreat when conditions are met."""
        bench_pokemon = PokemonCard(
            id="TEST_004",
            name="Bench Pokemon",
            hp=90,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        active_with_energy = dataclasses.replace(basic_game_state.player.active_pokemon, attached_energies=[EnergyType.COLORLESS])
        player_state = dataclasses.replace(
            basic_game_state.player,
            active_pokemon=active_with_energy,
            bench=[bench_pokemon]
        )
        game_state = dataclasses.replace(basic_game_state, player=player_state)
        assert ActionValidator.can_retreat(game_state)

    def test_can_attack(self, basic_game_state):
        """Test that Pokemon can attack when conditions are met."""
        active_pokemon_with_energy = dataclasses.replace(
            basic_game_state.player.active_pokemon,
            attached_energies=[EnergyType.COLORLESS]
        )
        player_state = dataclasses.replace(basic_game_state.player, active_pokemon=active_pokemon_with_energy)
        game_state = dataclasses.replace(basic_game_state, player=player_state, phase=GamePhase.ATTACK)
        assert ActionValidator.can_attack(game_state, 0)

    def test_get_legal_actions(self, basic_game_state):
        """Test that legal actions are returned."""
        actions = ActionValidator.get_legal_actions(basic_game_state)
        # Should include at least PASS action
        assert len(actions) > 0
        assert any(action.type == ActionType.PASS for action in actions) 