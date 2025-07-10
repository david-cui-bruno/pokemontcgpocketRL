"""Tests for game state functionality and coverage."""

import pytest
import dataclasses
from unittest.mock import MagicMock
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import PokemonCard, EnergyType, Stage, Attack

# ---- Fixtures ----

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

# ---- Core State Tests ----

class TestStateInitialization:
    """Tests for state initialization and basic properties."""
    
    def test_player_state_initialization(self, empty_player_state: PlayerState):
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

    def test_game_state_initialization(self, empty_game_state: GameState):
        """Test that GameState initializes with correct defaults."""
        assert empty_game_state.active_player == PlayerTag.PLAYER
        assert empty_game_state.phase == GamePhase.START_OF_TURN
        assert empty_game_state.turn_number == 1
        assert not empty_game_state.is_finished
        assert empty_game_state.winner is None

# ---- Game Rules Tests ----

class TestGameRules:
    """Tests for game rule enforcement."""
    
    def test_player_state_bench_limit(self, sample_pokemon):
        """Test that bench cannot exceed 3 Pokemon (TCG Pocket limit)."""
        with pytest.raises(ValueError):
            PlayerState(player_tag=PlayerTag.PLAYER, bench=[sample_pokemon] * 4)

    def test_player_state_point_limit(self):
        """Test that points cannot exceed 3."""
        with pytest.raises(ValueError):
            PlayerState(player_tag=PlayerTag.PLAYER, points=4)

    def test_pokemon_in_play(self, sample_pokemon):
        """Test getting all Pokemon in play."""
        state = PlayerState(
            player_tag=PlayerTag.PLAYER,
            active_pokemon=sample_pokemon,
            bench=[sample_pokemon, sample_pokemon]
        )
        assert len(state.pokemon_in_play) == 3

# ---- Energy System Tests ----

class TestEnergySystem:
    """Tests for energy zone and attachment mechanics."""
    
    def test_player_state_energy_zone(self):
        """Test energy zone mechanics."""
        player = PlayerState()
        
        # Test energy generation
        player.registered_energy_types = [EnergyType.FIRE, EnergyType.WATER]
        success = player.generate_energy(EnergyType.FIRE)
        assert success is True
        assert player.energy_zone == EnergyType.FIRE

    def test_can_attach_energy(self, sample_pokemon):
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

# ---- Phase Management Tests ----

class TestPhaseManagement:
    """Tests for game phase management."""
    
    def test_phase_advancement(self, empty_game_state: GameState):
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

    def test_active_player_state(self, empty_game_state: GameState):
        """Test getting active and inactive player state."""
        assert empty_game_state.active_player_state == empty_game_state.player
        assert empty_game_state.inactive_player_state == empty_game_state.opponent

# ---- Pokemon Management Tests ----

class TestPokemonManagement:
    """Tests for Pokemon management and tracking."""
    
    def test_player_state_bench_management(self):
        """Test bench management."""
        player = PlayerState()
        pokemon1 = PokemonCard(id="test1", name="Test1", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        
        # Test can bench pokemon
        assert player.can_bench_pokemon() is True
        player.bench.append(pokemon1)
        assert len(player.bench) == 1
        
        # Test bench limit
        for i in range(2):
            player.bench.append(PokemonCard(id=f"test{i+2}", name=f"Test{i+2}", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[]))
        
        assert player.can_bench_pokemon() is False

    def test_game_state_pokemon_entered_play_tracking(self):
        """Test Pokemon entered play tracking."""
        game_state = GameState()
        
        # Test adding Pokemon
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        game_state.player.pokemon_entered_play_this_turn.append(pokemon.id)
        
        assert game_state.player.has_pokemon_entered_play_this_turn(pokemon.id) is True 