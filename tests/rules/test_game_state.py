"""Tests for game state functionality."""

import pytest
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import PokemonCard, ItemCard, SupporterCard, EnergyType, Stage


@pytest.fixture
def sample_pokemon() -> PokemonCard:
    """Create a sample Pokemon card for testing."""
    return PokemonCard(
        id="TEST_001",
        name="Test Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        retreat_cost=1
    )

@pytest.fixture
def empty_player_state() -> PlayerState:
    """Create an empty player state."""
    return PlayerState()

@pytest.fixture
def empty_game_state() -> GameState:
    """Create an empty game state."""
    return GameState()

def test_player_state_initialization():
    """Test that PlayerState initializes with correct defaults."""
    state = PlayerState()
    assert state.active_pokemon is None
    assert len(state.bench) == 0
    assert len(state.hand) == 0
    assert len(state.deck) == 0
    assert len(state.discard) == 0
    assert state.points == 0
    assert state.energy_zone is None
    assert not state.has_played_supporter
    assert not state.has_attached_energy

def test_player_state_bench_limit(sample_pokemon):
    """Test that bench cannot exceed 3 Pokemon (TCG Pocket limit)."""
    with pytest.raises(ValueError):
        PlayerState(bench=[sample_pokemon] * 4)

def test_player_state_point_limit():
    """Test that points cannot exceed 3."""
    with pytest.raises(ValueError):
        PlayerState(points=4)

def test_pokemon_in_play(sample_pokemon):
    """Test getting all Pokemon in play."""
    state = PlayerState(
        active_pokemon=sample_pokemon,
        bench=[sample_pokemon, sample_pokemon]
    )
    assert len(state.pokemon_in_play) == 3

def test_can_play_supporter():
    """Test supporter play restrictions."""
    state = PlayerState()
    assert state.can_play_supporter()
    state.has_played_supporter = True
    assert not state.can_play_supporter()

def test_can_attach_energy():
    """Test energy attachment restrictions."""
    state = PlayerState()
    assert not state.can_attach_energy()
    state.energy_zone = EnergyType.FIRE
    assert state.can_attach_energy()
    state.has_attached_energy = True
    assert not state.can_attach_energy()

def test_game_state_initialization():
    """Test that GameState initializes with correct defaults."""
    state = GameState()
    assert state.active_player == PlayerTag.PLAYER
    assert state.phase == GamePhase.DRAW
    assert state.turn_number == 1
    assert not state.is_finished
    assert state.winner is None

def test_active_player_state():
    """Test getting active player state."""
    state = GameState()
    assert state.active_player_state == state.player
    state.active_player = PlayerTag.OPPONENT
    assert state.active_player_state == state.opponent

def test_phase_advancement():
    """Test phase advancement and turn changes."""
    state = GameState()
    
    # Test phase progression
    assert state.phase == GamePhase.DRAW
    state.advance_phase()
    assert state.phase == GamePhase.MAIN
    state.advance_phase()
    assert state.phase == GamePhase.ATTACK
    state.advance_phase()
    assert state.phase == GamePhase.CHECK_UP
    state.advance_phase()
    assert state.phase == GamePhase.END
    
    # Test turn change
    state.advance_phase()
    assert state.phase == GamePhase.DRAW
    assert state.active_player == PlayerTag.OPPONENT
    assert state.turn_number == 2
    
    # Test flag reset
    state.active_player_state.has_played_supporter = False
    state.active_player_state.has_attached_energy = False 