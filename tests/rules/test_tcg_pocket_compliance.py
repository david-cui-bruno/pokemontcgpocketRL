"""Tests to verify compliance with official Pokemon TCG Pocket rules."""

import pytest
from typing import List, Dict

from src.rules.game_engine import GameEngine, CoinFlipResult, DamageResult
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import (
    PokemonCard, Attack, Effect, EnergyType, Stage, StatusCondition,
    TargetType
)


@pytest.fixture
def game_engine():
    """Create a GameEngine instance."""
    return GameEngine()


@pytest.fixture
def basic_game_state():
    """Create a basic game state for testing."""
    state = GameState()
    state.phase = GamePhase.ATTACK
    return state


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
            attached_energies=[EnergyType.FIRE]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Grass Pokemon",
            hp=100,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            weakness=EnergyType.FIRE  # Weak to Fire
        )
        
        attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should be 30 + 20 = 50 damage, not 30 * 2 = 60
        assert result.damage_dealt == 50
        assert result.damage_result == DamageResult.WEAKNESS


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
            attached_energies=[EnergyType.FIRE]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Water Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC
            # No resistance field in PokemonCard anymore
        )
        
        attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should be exactly 30 damage, no reduction
        assert result.damage_dealt == 30
        assert result.damage_result == DamageResult.NORMAL


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
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        basic_game_state.player.bench.append(bench_pokemon)
        
        can_retreat = game_engine._can_retreat(asleep_pokemon, bench_pokemon, basic_game_state)
        assert not can_retreat
    
    def test_cannot_retreat_when_paralyzed(self, game_engine, basic_game_state):
        """Test that paralyzed Pokemon cannot retreat."""
        paralyzed_pokemon = PokemonCard(
            id="TEST-001",
            name="Paralyzed Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.PARALYZED,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        basic_game_state.player.bench.append(bench_pokemon)
        
        can_retreat = game_engine._can_retreat(paralyzed_pokemon, bench_pokemon, basic_game_state)
        assert not can_retreat


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
            status_condition=StatusCondition.POISONED
        )
        
        effects = game_engine.apply_status_condition_effects(poisoned_pokemon, basic_game_state)
        
        # Fixed: TCG Pocket poison damage is 10 (rulebook §7)
        assert effects["poison_damage"] == 10
        assert poisoned_pokemon.damage_counters == 10
    
    def test_burn_damage_20(self, game_engine, basic_game_state):
        """Test that burn does exactly 20 damage."""
        burned_pokemon = PokemonCard(
            id="TEST-001",
            name="Burned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.BURNED
        )
        
        effects = game_engine.apply_status_condition_effects(burned_pokemon, basic_game_state)
        
        assert effects["burn_damage"] == 20
        assert burned_pokemon.damage_counters == 20


class TestGamePhaseStructure:
    """Test that game phases include Check-up phase."""
    
    def test_check_up_phase_exists(self):
        """Test that CHECK_UP phase is defined."""
        assert GamePhase.CHECK_UP in GamePhase
        assert GamePhase.CHECK_UP.value == 4  # Fixed: CHECK_UP is value 4, not 3 