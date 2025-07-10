"""Comprehensive test suite for Pokemon TCG Pocket rules."""

import pytest
from dataclasses import replace
from src.rules.game_engine import GameEngine
from src.card_db.core import (
    PokemonCard, ItemCard, SupporterCard, ToolCard, Attack, Effect
)
from src.rules.constants import (
    EnergyType, Stage, GamePhase, StatusCondition, GameConstants
)
from src.rules.game_state import PlayerTag, EnergyZone

class TestPokemonTCGPocket:
    @pytest.fixture
    def engine(self):
        """Create a game engine with fixed seed for deterministic tests."""
        return GameEngine(random_seed=42)

    @pytest.fixture
    def basic_pokemon(self):
        """Create a basic test Pokemon."""
        return PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            pokemon_type=EnergyType.COLORLESS,
            hp=100,
            stage=Stage.BASIC,
            attacks=[
                Attack(
                    name="Test Attack",
                    cost=[EnergyType.COLORLESS],
                    damage=20
                )
            ]
        )

    @pytest.fixture
    def ex_pokemon(self):
        """Create an ex Pokemon."""
        return PokemonCard(
            id="TEST-EX001",
            name="Test Pokemon-ex",
            pokemon_type=EnergyType.FIRE,
            hp=200,
            stage=Stage.BASIC,
            is_ex=True,
            attacks=[
                Attack(
                    name="EX Attack",
                    cost=[EnergyType.FIRE, EnergyType.FIRE],
                    damage=120
                )
            ]
        )

    @pytest.fixture
    def valid_deck(self, basic_pokemon):
        """Create a valid 20-card deck."""
        return (
            [basic_pokemon] * 2 +  # 2 copies of basic Pokemon
            [
                PokemonCard(
                    id=f"TEST-{i:03d}",
                    name=f"Pokemon {i}",
                    pokemon_type=EnergyType.COLORLESS,
                    hp=100,
                    stage=Stage.BASIC
                ) for i in range(13)
            ] +
            [
                ItemCard(
                    id=f"ITEM-{i:03d}",
                    name=f"Test Item {i}",
                    effects=[],
                    text="Test effect"
                ) for i in range(5)
            ]
        )

    def test_deck_validation(self, engine, valid_deck, basic_pokemon):
        """Test deck construction rules."""
        # Test valid deck
        assert engine._validate_deck(valid_deck)

        # Test deck size limit
        invalid_size = valid_deck[:-1]
        assert not engine._validate_deck(invalid_size)

        # Test copy limit
        too_many_copies = [basic_pokemon] * 3 + valid_deck[3:]
        assert not engine._validate_deck(too_many_copies)

        # Test basic Pokemon requirement
        no_basics = [
            ItemCard(
                id=f"ITEM-{i}",
                name=f"Item {i}",
                effects=[],
                text="Test"
            ) for i in range(20)
        ]
        assert not engine._validate_deck(no_basics)

    def test_game_setup(self, engine, valid_deck):
        """Test initial game setup."""
        state = engine.create_game(valid_deck, valid_deck)

        # Check initial hands
        assert len(state.player.hand) == GameConstants.INITIAL_HAND_SIZE
        assert len(state.opponent.hand) == GameConstants.INITIAL_HAND_SIZE

        # Check remaining deck sizes
        assert len(state.player.deck) == GameConstants.DECK_SIZE - GameConstants.INITIAL_HAND_SIZE
        assert len(state.opponent.deck) == GameConstants.DECK_SIZE - GameConstants.INITIAL_HAND_SIZE

        # Check initial game state
        assert state.phase == GamePhase.START
        assert state.is_first_turn
        assert state.active_player_tag == PlayerTag.PLAYER
        assert state.turn_count == 1

    def test_first_turn_rules(self, engine, valid_deck):
        """Test first turn restrictions."""
        state = engine.create_game(valid_deck, valid_deck)

        # First player's first turn
        state = engine.start_turn(state)
        assert len(state.player.hand) == GameConstants.INITIAL_HAND_SIZE  # No draw
        assert state.player.energy_zone.current_energy is None  # No energy

        # Can play supporter on first turn (unique to TCG Pocket)
        if any(isinstance(card, SupporterCard) for card in state.player.hand):
            card_idx = next(i for i, card in enumerate(state.player.hand) 
                          if isinstance(card, SupporterCard))
            state = engine.play_trainer(state, card_idx)
            assert state.turn_state.supporter_played

    def test_energy_zone_mechanics(self, engine, valid_deck):
        """Test Energy Zone rules."""
        state = engine.create_game(valid_deck, valid_deck)
        
        # Skip first turn
        state = state.advance_phase()
        state = engine.start_turn(state)

        # Check energy generation
        assert state.active_player.energy_zone.current_energy is not None

        # Test attachment
        if state.active_player.active_pokemon:
            pokemon_id = state.active_player.active_pokemon.id
            initial_energy = len(state.active_player.active_pokemon.attached_energies)
            
            state = engine.attach_energy(state, pokemon_id)
            
            assert len(state.active_player.active_pokemon.attached_energies) == initial_energy + 1
            assert state.active_player.energy_zone.current_energy is None
            assert state.turn_state.energy_attached

            # Try to attach again
            with pytest.raises(ValueError):
                state = engine.attach_energy(state, pokemon_id)

    def test_combat_mechanics(self, engine, basic_pokemon, ex_pokemon):
        """Test combat rules including weakness and KO points."""
        # Create a state with active Pokemon
        state = engine.create_game([basic_pokemon] * 20, [ex_pokemon] * 20)
        
        # Setup Pokemon
        state = engine.play_pokemon(state, 0, to_bench=False)
        state = state.advance_phase()
        state = engine.play_pokemon(state, 0, to_bench=False)

        # Test weakness damage
        defender = replace(
            state.inactive_player.active_pokemon,
            weakness=state.active_player.active_pokemon.pokemon_type
        )
        damage = engine._calculate_damage(
            state.active_player.active_pokemon.attacks[0],
            state.active_player.active_pokemon,
            defender
        )
        assert damage == state.active_player.active_pokemon.attacks[0].damage + GameConstants.WEAKNESS_BONUS

        # Test KO points
        state = self._simulate_knockout(engine, state)
        assert state.active_player.points == (2 if defender.is_ex else 1)

    def test_status_conditions(self, engine, basic_pokemon):
        """Test status condition mechanics."""
        state = engine.create_game([basic_pokemon] * 20, [basic_pokemon] * 20)
        
        # Setup Pokemon with status
        pokemon = replace(basic_pokemon, status_condition=StatusCondition.POISONED)
        state = replace(state, 
                       player=replace(state.player, active_pokemon=pokemon))

        # Process status effects
        state = engine.process_checkup(state)
        
        # Verify poison damage
        assert state.player.active_pokemon.damage_counters == GameConstants.POISON_DAMAGE

    def test_victory_conditions(self, engine, basic_pokemon, ex_pokemon):
        """Test win conditions (points or no Pokemon)."""
        state = engine.create_game([basic_pokemon] * 20, [ex_pokemon] * 20)

        # Test points victory
        state = replace(
            state,
            player=replace(state.player, points=GameConstants.POINTS_TO_WIN)
        )
        assert state.is_game_over
        assert state.winner == PlayerTag.PLAYER

        # Test no Pokemon victory
        state = replace(
            state,
            player=replace(state.player, points=0),
            opponent=replace(
                state.opponent,
                active_pokemon=None,
                bench=[],
                deck=[]
            )
        )
        assert state.is_game_over
        assert state.winner == PlayerTag.PLAYER

    @staticmethod
    def _simulate_knockout(engine, state):
        """Helper to simulate a knockout."""
        defender = state.inactive_player.active_pokemon
        new_defender = replace(
            defender,
            damage_counters=defender.hp
        )
        state = engine._handle_knockout(state, new_defender)
        return engine._award_points(
            state,
            state.active_player_tag,
            2 if defender.is_ex else 1
        ) 