"""Tests for game state functionality."""

import pytest
import dataclasses
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import PokemonCard, EnergyType, Stage, Attack


@pytest.fixture
def sample_pokemon() -> PokemonCard:
    """Create a sample Pokemon card for testing."""
    return PokemonCard(
        id="TEST_001",
        name="Test Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        attacks=[Attack(name="Test Attack", cost=[], damage=10)]
    )


@pytest.fixture
def empty_player_state() -> PlayerState:
    """Create an empty player state."""
    return PlayerState(player_tag=PlayerTag.PLAYER)


@pytest.fixture
def empty_game_state() -> GameState:
    """Create an empty game state."""
    return GameState(
        player=PlayerState(player_tag=PlayerTag.PLAYER),
        opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
    )


def test_player_state_initialization(empty_player_state: PlayerState):
    """Test that PlayerState initializes with correct defaults."""
    assert empty_player_state.active_pokemon is None
    assert len(empty_player_state.bench) == 0
    assert len(empty_player_state.hand) == 0
    assert len(empty_player_state.deck) == 0
    assert len(empty_player_state.discard_pile) == 0
    assert empty_player_state.points == 0
    assert empty_player_state.energy_zone is None
    assert not empty_player_state.supporter_played_this_turn
    assert not empty_player_state.energy_attached_this_turn


def test_player_state_bench_limit(sample_pokemon):
    """Test that bench cannot exceed 3 Pokemon (TCG Pocket limit)."""
    with pytest.raises(ValueError):
        PlayerState(player_tag=PlayerTag.PLAYER, bench=[sample_pokemon] * 4)


def test_player_state_point_limit():
    """Test that points cannot exceed 3."""
    with pytest.raises(ValueError):
        PlayerState(player_tag=PlayerTag.PLAYER, points=4)


def test_pokemon_in_play(sample_pokemon):
    """Test getting all Pokemon in play."""
    state = PlayerState(
        player_tag=PlayerTag.PLAYER,
        active_pokemon=sample_pokemon,
        bench=[sample_pokemon, sample_pokemon]
    )
    assert len(state.pokemon_in_play) == 3


def test_can_play_supporter(empty_player_state):
    """Test supporter play restrictions."""
    assert empty_player_state.can_play_supporter()
    
    state_after_supporter = dataclasses.replace(empty_player_state, supporter_played_this_turn=True)
    assert not state_after_supporter.can_play_supporter()


def test_can_attach_energy(sample_pokemon):
    """Test energy attachment restrictions."""
    # Cannot attach with no energy in zone
    state = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=sample_pokemon)
    assert not state.can_attach_energy()

    # Can attach with energy in zone
    state_with_energy = dataclasses.replace(state, energy_zone=[EnergyType.FIRE])
    assert state_with_energy.can_attach_energy()
    
    # Cannot attach if already attached this turn
    state_after_attachment = dataclasses.replace(state_with_energy, energy_attached_this_turn=True)
    assert not state_after_attachment.can_attach_energy()


def test_game_state_initialization(empty_game_state: GameState):
    """Test that GameState initializes with correct defaults."""
    assert empty_game_state.active_player == PlayerTag.PLAYER
    assert empty_game_state.phase == GamePhase.START_OF_TURN
    assert empty_game_state.turn_number == 1
    assert not empty_game_state.is_finished
    assert empty_game_state.winner is None


def test_active_player_state(empty_game_state: GameState):
    """Test getting active and inactive player state."""
    assert empty_game_state.active_player_state == empty_game_state.player
    assert empty_game_state.inactive_player_state == empty_game_state.opponent
    
    state_opponent_turn = dataclasses.replace(empty_game_state, active_player=PlayerTag.OPPONENT)
    assert state_opponent_turn.active_player_state == state_opponent_turn.opponent
    assert state_opponent_turn.inactive_player_state == state_opponent_turn.player


def test_phase_advancement(empty_game_state: GameState):
    """Test phase advancement and turn changes."""
    state = empty_game_state
    
    # Test phase progression
    assert state.phase == GamePhase.START_OF_TURN
    state = dataclasses.replace(state, phase=state.phase.next_phase())
    assert state.phase == GamePhase.DRAW
    state = dataclasses.replace(state, phase=state.phase.next_phase())
    assert state.phase == GamePhase.MAIN
    state = dataclasses.replace(state, phase=state.phase.next_phase())
    assert state.phase == GamePhase.ATTACK
    state = dataclasses.replace(state, phase=state.phase.next_phase())
    assert state.phase == GamePhase.END_OF_TURN
    
    # Test turn change
    state = dataclasses.replace(state, phase=state.phase.next_phase())
    assert state.phase == GamePhase.START_OF_TURN
    assert state.active_player == PlayerTag.OPPONENT
    assert state.turn_number == 2 