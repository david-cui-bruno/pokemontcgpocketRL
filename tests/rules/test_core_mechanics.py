"""Tests for fundamental game mechanics."""

import pytest
from src.rules.game_engine import GameEngine
from src.card_db.core import PokemonCard, ItemCard, SupporterCard, ToolCard
from src.rules.constants import EnergyType, Stage, GamePhase, StatusCondition
from src.rules.game_state import PlayerTag
from src.rules.card_effects import Attack
from src.rules.game_state import replace

class TestCoreMechanics:
    @pytest.fixture
    def engine(self):
        """Create a game engine with fixed seed for deterministic tests."""
        return GameEngine(random_seed=42)

    @pytest.fixture
    def basic_deck(self):
        """Create a minimal valid deck."""
        return [
            PokemonCard(
                id=f"BASIC-{i}",
                name=f"Basic Pokemon {i}",
                pokemon_type=EnergyType.COLORLESS,
                hp=100,
                stage=Stage.BASIC
            ) for i in range(15)
        ] + [
            ItemCard(
                id=f"ITEM-{i}",
                name=f"Test Item {i}",
                effects=[],
                text="Test effect"
            ) for i in range(5)
        ]

    def test_game_creation(self, engine, basic_deck):
        """Test initial game setup."""
        state = engine.create_game(basic_deck, basic_deck)
        
        # Check initial hands
        assert len(state.player.hand) == 5
        assert len(state.opponent.hand) == 5
        
        # Check remaining deck sizes
        assert len(state.player.deck) == 15
        assert len(state.opponent.deck) == 15
        
        # Check initial phase
        assert state.phase == GamePhase.START
        assert state.is_first_turn
        assert state.active_player_tag == PlayerTag.PLAYER

    def test_first_turn_restrictions(self, engine, basic_deck):
        """Test first turn rules."""
        state = engine.create_game(basic_deck, basic_deck)
        
        # First player shouldn't draw or generate energy on first turn
        state = engine.start_turn(state)
        assert len(state.player.hand) == 5  # No draw
        assert state.player.energy_zone.current_energy is None  # No energy

        # Second player should draw and generate energy
        state = engine.start_turn(state.advance_phase())
        assert len(state.opponent.hand) == 6  # Drew a card
        assert state.opponent.energy_zone.current_energy is not None

    def test_bench_limit(self, engine, basic_deck):
        """Test bench size limit of 3."""
        state = engine.create_game(basic_deck, basic_deck)
        
        # Try to bench 4 Pokemon
        for i in range(4):
            if i < 3:
                state = engine.play_pokemon(state, 0, to_bench=True)
            else:
                with pytest.raises(ValueError, match="Bench is full"):
                    state = engine.play_pokemon(state, 0, to_bench=True)

    def test_hand_size_limit(self, engine, basic_deck):
        """Test hand size limit of 10."""
        state = engine.create_game(basic_deck, basic_deck)
        
        # Add cards until hand would exceed 10
        while len(state.player.hand) < 10:
            state = engine.draw_cards(state, 1)
            
        # Try to draw one more
        with pytest.raises(ValueError, match="Would exceed hand size limit"):
            state = engine.draw_cards(state, 1) 