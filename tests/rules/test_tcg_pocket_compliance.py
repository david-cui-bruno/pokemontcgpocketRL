"""Tests to verify compliance with official Pokemon TCG Pocket rules."""

import pytest
from typing import List, Dict, Optional

from src.rules.game_engine import GameEngine, CoinFlipResult, DamageResult
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import (
    PokemonCard, Attack, Effect, EnergyType, Stage, StatusCondition,
    TargetType, TrainerCard, SupporterCard, Card
)
import dataclasses
from collections import Counter


@pytest.fixture
def game_engine():
    """Create a GameEngine instance."""
    return GameEngine()


@pytest.fixture
def basic_pokemon():
    """Create a basic Pokemon for testing."""
    return PokemonCard(
        id="TEST-001",
        name="Test Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        attacks=[
            Attack(
                name="Basic Attack",
                cost=[EnergyType.COLORLESS],
                damage=30
            )
        ],
        retreat_cost=1
    )


@pytest.fixture
def fire_pokemon():
    """Create a Fire Pokemon for testing."""
    return PokemonCard(
        id="TEST-002",
        name="Fire Pokemon",
        hp=80,
        pokemon_type=EnergyType.FIRE,
        stage=Stage.BASIC,
        attacks=[
            Attack(
                name="Fire Attack",
                cost=[EnergyType.FIRE],
                damage=40
            )
        ]
    )


@pytest.fixture
def grass_pokemon():
    """Create a Grass Pokemon for testing."""
    return PokemonCard(
        id="TEST-003",
        name="Grass Pokemon",
        hp=90,
        pokemon_type=EnergyType.GRASS,
        stage=Stage.BASIC,
        attacks=[
            Attack(
                name="Grass Attack",
                cost=[EnergyType.GRASS],
                damage=35
            )
        ],
        weakness=(EnergyType.FIRE, 20)
    )


@pytest.fixture
def basic_game_state(basic_pokemon):
    """Create a basic game state for testing."""
    player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=basic_pokemon)
    opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=dataclasses.replace(basic_pokemon, id="OPPONENT-001"))
    return GameState(player=player, opponent=opponent, phase=GamePhase.MAIN)


@pytest.fixture
def mock_card():
    """Create a mock card for testing."""
    return PokemonCard(
        id="MOCK-001",
        name="Mock Card",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        attacks=[Attack(name="Mock Attack", cost=[EnergyType.COLORLESS], damage=10)],
        retreat_cost=1
    )


class TestWeaknessMechanics:
    """Test that weakness adds +20 damage (not multiplies by 2)."""
    
    def test_weakness_adds_20_damage(self, game_engine, basic_game_state):
        """Test that weakness adds exactly 20 damage."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.FIRE], damage=30)],
            attached_energies=[EnergyType.FIRE],
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Grass Pokemon",
            hp=100,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            attacks=[],
            weakness=(EnergyType.FIRE, 20),  # Weak to Fire
        )
        
        damage, _ = game_engine._calculate_damage(attacker.attacks[0], attacker, target)
        assert damage == 50 # 30 base + 20 weakness


class TestNoResistance:
    """Test that resistance mechanics are completely removed."""
    
    def test_no_resistance_damage_reduction(self, game_engine, basic_game_state):
        """Test that resistance doesn't reduce damage."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.FIRE], damage=30)],
            attached_energies=[EnergyType.FIRE],
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Water Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC,
            attacks=[],
            # No resistance field in PokemonCard anymore
        )
        
        damage, _ = game_engine._calculate_damage(attacker.attacks[0], attacker, target)
        assert damage == 30


class TestBenchLimits:
    """Test that bench limit is 3 Pokemon (not 5)."""
    
    def test_bench_limit_3_pokemon(self, game_engine):
        """Test that bench size is limited to 3."""
        assert game_engine.max_bench_size == 3


class TestEnergyZone:
    """Test Energy Zone mechanics."""
    
    def test_energy_zone_single_slot(self, basic_game_state):
        """Test that Energy Zone can hold only one energy."""
        player_state = basic_game_state.player
        
        # Initially empty
        assert player_state.energy_zone is None
        
        # Generate energy
        assert player_state.generate_energy(EnergyType.FIRE) == True
        assert player_state.energy_zone == EnergyType.FIRE
        
        # Cannot generate more energy
        assert player_state.generate_energy(EnergyType.WATER) == False
        assert player_state.energy_zone == EnergyType.FIRE
        
        # Use energy
        energy = player_state.use_energy_from_zone()
        assert energy == EnergyType.FIRE
        assert player_state.energy_zone is None


class TestRetreatRestrictions:
    """Test retreat restrictions for status conditions."""
    
    def test_cannot_retreat_when_asleep(self, game_engine, basic_game_state):
        """Test that asleep Pokemon cannot retreat."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS],
        )
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
        )
        assert (
            game_engine._can_retreat(asleep_pokemon, bench_pokemon, basic_game_state)
            is False
        )
    
    def test_cannot_retreat_when_paralyzed(self, game_engine, basic_game_state):
        """Test that paralyzed Pokemon cannot retreat."""
        paralyzed_pokemon = PokemonCard(
            id="TEST-001",
            name="Paralyzed Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.PARALYZED,
            attached_energies=[EnergyType.COLORLESS],
        )
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
        )
        assert (
            game_engine._can_retreat(
                paralyzed_pokemon, bench_pokemon, basic_game_state
            )
            is False
        )


class TestStatusConditionDamage:
    """Test correct status condition damage values."""
    
    def test_poison_damage_10(self, game_engine, basic_game_state):
        """Test poison damage is 10 in TCG Pocket (rulebook §7)."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.POISONED,
        )

        updated_pokemon = game_engine.apply_status_condition_effects(poisoned_pokemon, basic_game_state)

        # Fixed: TCG Pocket poison damage is 10 (rulebook §7)
        assert updated_pokemon.damage_counters == poisoned_pokemon.damage_counters + 10
    
    def test_burn_damage_20(self, game_engine, basic_game_state):
        """Test that burn does exactly 20 damage."""
        burned_pokemon = PokemonCard(
            id="TEST-001",
            name="Burned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.BURNED,
        )

        updated_pokemon = game_engine.apply_status_condition_effects(burned_pokemon, basic_game_state)

        assert updated_pokemon.damage_counters == burned_pokemon.damage_counters + 20


@pytest.mark.skip(reason="Checkup is part of end-of-turn, not a distinct phase.")
class TestGamePhaseStructure:
    """Test game phase structure (rulebook §4)."""

    def test_check_up_phase_exists(self):
        """Test that CHECK_UP phase is defined."""
        assert "CHECK_UP" in GamePhase.__members__

    def test_phase_advancement_order(self, basic_game_state):
        """Test the full phase advancement order."""
        state = basic_game_state
        assert state.phase == GamePhase.START
        
        state = state.advance_phase()
        assert state.phase == GamePhase.MAIN
        
        state = state.advance_phase()
        assert state.phase == GamePhase.ATTACK
        
        state = state.advance_phase()
        assert state.phase == GamePhase.CHECK_UP
        
        state = state.advance_phase()
        assert state.phase == GamePhase.END
        
        state = state.advance_phase()
        assert state.phase == GamePhase.START  # New turn
        assert state.turn_number == 2


class TestWeaknessMechanics:
    """Test weakness mechanics (rulebook §1)."""
    
    def test_weakness_adds_20_damage(self, game_engine, basic_game_state):
        """Test that weakness adds exactly 20 damage."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.FIRE], damage=30)],
            attached_energies=[EnergyType.FIRE],
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Grass Pokemon",
            hp=100,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            attacks=[],
            weakness=(EnergyType.FIRE, 20),  # Weak to Fire
        )
        
        damage, _ = game_engine._calculate_damage(attacker.attacks[0], attacker, target)
        assert damage == 50 # 30 base + 20 weakness


class TestNoResistance:
    """Test that resistance mechanics are completely removed."""
    
    def test_no_resistance_damage_reduction(self, game_engine, basic_game_state):
        """Test that resistance doesn't reduce damage."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.FIRE], damage=30)],
            attached_energies=[EnergyType.FIRE],
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Water Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC,
            attacks=[],
            # No resistance field in PokemonCard anymore
        )
        
        damage, _ = game_engine._calculate_damage(attacker.attacks[0], attacker, target)
        assert damage == 30


class TestBenchLimits:
    """Test that bench limit is 3 Pokemon (not 5)."""
    
    def test_bench_limit_3_pokemon(self, game_engine):
        """Test that bench size is limited to 3."""
        assert game_engine.max_bench_size == 3


class TestEnergyZone:
    """Test Energy Zone mechanics."""
    
    def test_energy_zone_single_slot(self, basic_game_state):
        """Test that Energy Zone can hold only one energy."""
        player_state = basic_game_state.player
        
        # Initially empty
        assert player_state.energy_zone is None
        
        # Generate energy
        assert player_state.generate_energy(EnergyType.FIRE) == True
        assert player_state.energy_zone == EnergyType.FIRE
        
        # Cannot generate more energy
        assert player_state.generate_energy(EnergyType.WATER) == False
        assert player_state.energy_zone == EnergyType.FIRE
        
        # Use energy
        energy = player_state.use_energy_from_zone()
        assert energy == EnergyType.FIRE
        assert player_state.energy_zone is None


class TestRetreatRestrictions:
    """Test retreat restrictions for status conditions."""
    
    def test_cannot_retreat_when_asleep(self, game_engine, basic_game_state):
        """Test that asleep Pokemon cannot retreat."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS],
        )
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
        )
        assert (
            game_engine._can_retreat(asleep_pokemon, bench_pokemon, basic_game_state)
            is False
        )
    
    def test_cannot_retreat_when_paralyzed(self, game_engine, basic_game_state):
        """Test that paralyzed Pokemon cannot retreat."""
        paralyzed_pokemon = PokemonCard(
            id="TEST-001",
            name="Paralyzed Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.PARALYZED,
            attached_energies=[EnergyType.COLORLESS],
        )
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
        )
        assert (
            game_engine._can_retreat(
                paralyzed_pokemon, bench_pokemon, basic_game_state
            )
            is False
        )


class TestStatusConditionDamage:
    """Test correct status condition damage values."""
    
    def test_poison_damage_10(self, game_engine, basic_game_state):
        """Test poison damage is 10 in TCG Pocket (rulebook §7)."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.POISONED,
        )
        
        updated_pokemon = game_engine.apply_status_condition_effects(poisoned_pokemon, basic_game_state)
        
        # Fixed: TCG Pocket poison damage is 10 (rulebook §7)
        assert updated_pokemon.damage_counters == poisoned_pokemon.damage_counters + 10
    
    def test_burn_damage_20(self, game_engine, basic_game_state):
        """Test that burn does exactly 20 damage."""
        burned_pokemon = PokemonCard(
            id="TEST-001",
            name="Burned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.BURNED,
        )
        
        updated_pokemon = game_engine.apply_status_condition_effects(burned_pokemon, basic_game_state)
        
        assert updated_pokemon.damage_counters == burned_pokemon.damage_counters + 20


@pytest.mark.skip(reason="Checkup is part of end-of-turn, not a distinct phase.")
class TestGamePhaseStructure:
    """Test game phase structure (rulebook §4)."""
    
    def test_check_up_phase_exists(self):
        """Test that CHECK_UP phase is defined."""
        assert "CHECK_UP" in GamePhase.__members__

    def test_phase_advancement_order(self, basic_game_state):
        """Test the full phase advancement order."""
        state = basic_game_state
        assert state.phase == GamePhase.START
        
        state = state.advance_phase()
        assert state.phase == GamePhase.MAIN
        
        state = state.advance_phase()
        assert state.phase == GamePhase.ATTACK
        
        state = state.advance_phase()
        assert state.phase == GamePhase.CHECK_UP
        
        state = state.advance_phase()
        assert state.phase == GamePhase.END
        
        state = state.advance_phase()
        assert state.phase == GamePhase.START  # New turn
        assert state.turn_number == 2 