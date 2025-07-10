"""Tests for Energy Zone mechanics."""

import pytest
import dataclasses
from unittest.mock import patch, MagicMock

from src.rules.game_engine import GameEngine
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import EnergyType, PokemonCard, Stage, Attack

class TestEnergyZone:
    @pytest.fixture
    def fire_deck(self):
        """Create a deck with Fire Pokemon."""
        return [
            PokemonCard(
                id=f"FIRE-{i}",
                name=f"Fire Pokemon {i}",
                pokemon_type=EnergyType.FIRE,
                hp=100,
                stage=Stage.BASIC
            ) for i in range(20)
        ]

    def test_energy_generation(self, engine, fire_deck):
        """Test energy generation rules."""
        state = engine.create_game(fire_deck, fire_deck)
        state = engine.start_turn(state)
        
        # Skip first turn (no energy)
        state = state.advance_phase()
        
        # Second turn should generate energy
        state = engine.start_turn(state)
        assert state.active_player.energy_zone.current_energy == EnergyType.FIRE

    def test_energy_attachment(self, engine, fire_deck):
        """Test energy attachment rules."""
        state = engine.create_game(fire_deck, fire_deck)
        
        # Setup: Play a Pokemon and generate energy
        state = engine.play_pokemon(state, 0, to_bench=False)
        state = engine._generate_energy(state)
        
        # Attach energy
        pokemon_id = state.player.active_pokemon.id
        state = engine.attach_energy(state, pokemon_id)
        
        # Verify attachment
        assert len(state.player.active_pokemon.attached_energies) == 1
        assert state.player.energy_zone.current_energy is None
        
        # Try to attach again
        with pytest.raises(ValueError, match="Already attached energy this turn"):
            state = engine.attach_energy(state, pokemon_id) 