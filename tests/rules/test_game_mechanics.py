"""Comprehensive test suite for Pokemon TCG Pocket game mechanics."""

import pytest
import dataclasses
from typing import List
from dataclasses import replace

from src.rules.game_engine import GameEngine, DamageResult, CoinFlipResult
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag, EnergyZone
from src.card_db.core import (
    PokemonCard, ItemCard, SupporterCard, ToolCard, Attack, Effect
)
from src.rules.constants import (
    EnergyType, Stage, StatusCondition, GameConstants
)

# ---- Fixtures ----

@pytest.fixture
def engine():
    """Create a game engine with fixed seed for deterministic tests."""
    return GameEngine(random_seed=42)

@pytest.fixture
def basic_pokemon():
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
        ],
        retreat_cost=1
    )

@pytest.fixture
def ex_pokemon():
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
def valid_deck(basic_pokemon):
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

@pytest.fixture
def basic_game_state(basic_pokemon):
    """Create a basic game state for testing."""
    player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=basic_pokemon)
    opponent = PlayerState(
        player_tag=PlayerTag.OPPONENT,
        active_pokemon=dataclasses.replace(basic_pokemon, id="OPPONENT-001")
    )
    return GameState(player=player, opponent=opponent, phase=GamePhase.MAIN)

# ---- Test Classes ----

class TestGameSetupAndValidation:
    """Tests for game setup and deck validation."""
    
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


class TestTurnStructureAndPhases:
    """Tests for turn structure and phase transitions."""
    
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

    def test_phase_transitions(self, engine, basic_game_state):
        """Test phase transition logic."""
        state = basic_game_state
        
        # Start in MAIN phase
        assert state.phase == GamePhase.MAIN
        
        # Advance to ATTACK phase
        state = state.advance_phase()
        assert state.phase == GamePhase.ATTACK
        
        # Advance to CHECK_UP phase
        state = state.advance_phase()
        assert state.phase == GamePhase.CHECK_UP
        
        # Advance to next turn
        state = state.advance_phase()
        assert state.phase == GamePhase.MAIN
        assert state.turn_count == 2


class TestCombatMechanics:
    """Tests for combat and attack resolution."""
    
    def test_attack_resolution_basic(self, engine, basic_pokemon):
        """Test basic attack resolution."""
        attack = basic_pokemon.attacks[0]
        target = PokemonCard(
            id="TARGET-001",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Add energy to attacker
        attacker = dataclasses.replace(basic_pokemon, attached_energies=[EnergyType.COLORLESS])
        
        player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=attacker)
        opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=target)
        game_state = GameState(player=player, opponent=opponent, phase=GamePhase.ATTACK)
        
        result = engine.resolve_attack(attacker, attack, target, game_state)
        
        assert result.damage_dealt == 20
        assert result.damage_result == DamageResult.NORMAL
        assert not result.target_ko
        assert len(result.energy_discarded) > 0  # Cost should be paid

    def test_weakness_damage(self, engine):
        """Test weakness damage calculation (+20)."""
        attacker = PokemonCard(
            id="ATK-1",
            name="Attacker",
            pokemon_type=EnergyType.FIRE,
            hp=100,
            attacks=[Attack(name="Test", cost=[], damage=50)]
        )
        
        defender = PokemonCard(
            id="DEF-1",
            name="Defender",
            pokemon_type=EnergyType.GRASS,
            hp=100,
            weakness=EnergyType.FIRE
        )
        
        damage = engine._calculate_damage(attacker.attacks[0], attacker, defender)
        assert damage == 70  # Base 50 + 20 weakness

    def test_status_conditions(self, engine, basic_pokemon):
        """Test status condition mechanics."""
        pokemon = dataclasses.replace(basic_pokemon, status_condition=StatusCondition.POISONED)
        state = basic_game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=pokemon),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.CHECK_UP
        )
        
        # Process status effects
        state = engine.process_checkup(state)
        
        # Verify poison damage
        assert state.player.active_pokemon.damage_counters == GameConstants.POISON_DAMAGE


class TestEvolutionAndRetreat:
    """Tests for evolution and retreat mechanics."""
    
    def test_evolution_mechanics(self, engine, basic_pokemon):
        """Test evolution mechanics."""
        evolution_card = PokemonCard(
            id="EVOLUTION-001",
            name="Evolved Pokemon",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            evolves_from="Test Pokemon",
            attacks=[]
        )

        player_state = PlayerState(
            player_tag=PlayerTag.PLAYER,
            active_pokemon=basic_pokemon,
            hand=[evolution_card],
            pokemon_entered_play_this_turn=[]  # Can evolve on turn 1
        )
        game_state = GameState(
            player=player_state,
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN,
            turn_number=2,
            is_first_turn=False
        )
        
        # Should be able to evolve
        new_state = engine.evolve_pokemon(evolution_card, basic_pokemon, game_state)
        assert new_state.player.active_pokemon.id == "EVOLUTION-001"
        assert evolution_card not in new_state.player.hand

    def test_retreat_mechanics(self, engine, basic_pokemon):
        """Test retreat mechanics."""
        bench_pokemon = PokemonCard(
            id="BENCH-001",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Test with retreat cost and sufficient energy
        active_with_energy = dataclasses.replace(
            basic_pokemon,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        player_state = PlayerState(
            player_tag=PlayerTag.PLAYER,
            active_pokemon=active_with_energy,
            bench=[bench_pokemon]
        )
        game_state = GameState(
            player=player_state,
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN
        )
        
        # Retreat should succeed
        new_state = engine.retreat_pokemon(player_state, bench_pokemon, game_state)
        assert new_state.player.active_pokemon.id == "BENCH-001"
        assert basic_pokemon.id in [p.id for p in new_state.player.bench]


class TestEnergyAndEffects:
    """Tests for energy mechanics and card effects."""
    
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

    def test_status_condition_effects(self, engine, basic_pokemon):
        """Test status condition application and effects."""
        pokemon = dataclasses.replace(basic_pokemon)
        
        # Test poison
        poisoned = engine.apply_status_condition(pokemon, StatusCondition.POISONED)
        assert poisoned.status_condition == StatusCondition.POISONED
        
        # Test burn
        burned = engine.apply_status_condition(pokemon, StatusCondition.BURNED)
        assert burned.status_condition == StatusCondition.BURNED
        
        # Test paralysis
        paralyzed = engine.apply_status_condition(pokemon, StatusCondition.PARALYZED)
        assert paralyzed.status_condition == StatusCondition.PARALYZED


class TestVictoryConditions:
    """Tests for victory conditions and point system."""
    
    def test_victory_conditions(self, engine, basic_pokemon, ex_pokemon):
        """Test win conditions (points or no Pokemon)."""
        state = engine.create_game([basic_pokemon] * 20, [ex_pokemon] * 20)

        # Test points victory
        state = replace(
            state,
            player=replace(state.player, points=GameConstants.POINTS_TO_WIN)
        )
        assert engine.check_game_over(state) == "player"

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
        assert engine.check_game_over(state) == "player"

    def test_point_awarding_system(self, engine):
        """Test TCG Pocket point awarding system."""
        player = PlayerState(player_tag=PlayerTag.PLAYER)
        
        # Award 1 point for regular Pokemon KO
        updated_player = engine.award_points(player, 1)
        assert updated_player.points == 1
        
        # Award 2 points for ex Pokemon KO
        updated_player = engine.award_points(updated_player, 2)
        assert updated_player.points == 3
        
        # Try to award more points (should raise error)
        with pytest.raises(ValueError, match="Cannot award"):
            engine.award_points(updated_player, 1)
