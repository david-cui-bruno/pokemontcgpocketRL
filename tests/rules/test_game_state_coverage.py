# tests/rules/test_game_state_coverage.py
import pytest
from unittest.mock import MagicMock
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import PokemonCard, EnergyType, Stage, Attack

class TestGameStateCoverage:
    """Tests to improve game state coverage."""
    
    def test_player_state_energy_zone(self):
        """Test energy zone mechanics."""
        player = PlayerState()
        
        # Test energy generation
        player.registered_energy_types = [EnergyType.FIRE, EnergyType.WATER]
        success = player.generate_energy(EnergyType.FIRE)
        assert success is True
        assert player.energy_zone == EnergyType.FIRE

        # Test energy attachment - need a Pokemon in play first
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        player.pokemon_in_play.append(pokemon)

        # Test can attach energy
        assert player.can_attach_energy() is True
        player.energy_attached_this_turn = True
        assert player.can_attach_energy() is False

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

    def test_game_state_pokemon_in_play(self):
        """Test Pokemon in play checking."""
        game_state = GameState()
        
        # Test with no Pokemon
        assert len(game_state.player.pokemon_in_play) == 0
        
        # Test with active Pokemon
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        game_state.player.active_pokemon = pokemon
        assert len(game_state.player.pokemon_in_play) == 1
        
        # Test with bench Pokemon
        game_state.player.bench.append(pokemon)
        assert len(game_state.player.pokemon_in_play) == 2

    def test_game_state_can_attach_energy(self):
        """Test energy attachment validation."""
        game_state = GameState()
        
        # Test can attach energy (should be False by default since no energy in zone)
        assert game_state.player.can_attach_energy() is False
        
        # Test can attach energy when energy is in zone
        game_state.player.energy_zone = EnergyType.FIRE
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        game_state.player.pokemon_in_play.append(pokemon)
        assert game_state.player.can_attach_energy() is True

    def test_game_state_pokemon_entered_play_tracking(self):
        """Test Pokemon entered play tracking."""
        game_state = GameState()
        
        # Test adding Pokemon
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        game_state.player.pokemon_entered_play_this_turn.append(pokemon.id)
        
        assert game_state.player.has_pokemon_entered_play_this_turn(pokemon.id) is True