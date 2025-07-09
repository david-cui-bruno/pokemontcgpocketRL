"""Tests for the TCG Pocket point system."""

import pytest
from src.rules.game_engine import GameEngine
from src.rules.game_state import GameState, PlayerState
from src.card_db.core import (
    PokemonCard, Attack, EnergyType, Stage, StatusCondition
)


@pytest.fixture
def game_engine():
    return GameEngine()


@pytest.fixture
def basic_game_state():
    return GameState()


class TestPointSystem:
    """Test the TCG Pocket point system."""
    
    def test_basic_point_awarding(self, game_engine):
        """Test basic point awarding."""
        player = PlayerState()
        
        # Award 1 point for regular Pokemon KO
        assert game_engine.award_points(player, 1)
        assert player.points == 1
        
        # Award 2 points for ex Pokemon KO
        assert game_engine.award_points(player, 2)
        assert player.points == 3
        
        # Try to award more points (should not exceed 3)
        assert not game_engine.award_points(player, 1)
        assert player.points == 3
    
    def test_ko_awards_points(self, game_engine, basic_game_state):
        """Test that KOing Pokemon awards points."""
        # Create attacker
        attacker = PokemonCard(
            id="TEST-001",
            name="Attacker",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        # Create target (regular Pokemon)
        target = PokemonCard(
            id="TEST-002",
            name="Target",
            hp=30,  # Low HP to ensure KO
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        attack = Attack(
            name="Strong Attack",
            cost=[EnergyType.COLORLESS],
            damage=40  # Enough to KO
        )
        
        # Set up game state
        basic_game_state.player.active_pokemon = target
        basic_game_state.opponent.active_pokemon = attacker
        
        # Resolve attack
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should KO and award 1 point
        assert result.target_ko
        assert basic_game_state.opponent.points == 1
    
    def test_ex_pokemon_awards_2_points(self, game_engine, basic_game_state):
        """Test that KOing ex Pokemon awards 2 points."""
        # Create attacker
        attacker = PokemonCard(
            id="TEST-001",
            name="Attacker",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        # Create target (ex Pokemon)
        target = PokemonCard(
            id="TEST-002",
            name="Ex Target",
            hp=30,  # Low HP to ensure KO
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            is_ex=True  # This is an ex Pokemon
        )
        
        attack = Attack(
            name="Strong Attack",
            cost=[EnergyType.COLORLESS],
            damage=40  # Enough to KO
        )
        
        # Set up game state
        basic_game_state.player.active_pokemon = target
        basic_game_state.opponent.active_pokemon = attacker
        
        # Resolve attack
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should KO and award 2 points
        assert result.target_ko
        assert basic_game_state.opponent.points == 2
    
    def test_game_over_at_3_points(self, game_engine):
        """Test that game ends when a player reaches 3 points."""
        game_state = GameState()
        
        # Add some Pokemon and deck cards to avoid other win conditions
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        game_state.player.active_pokemon = basic_pokemon
        game_state.opponent.active_pokemon = basic_pokemon
        game_state.player.deck = [None, None, None]
        game_state.opponent.deck = [None, None, None]
        
        # Game should continue normally
        assert game_engine.check_game_over(game_state) is None
        
        # Player reaches 3 points and wins
        game_state.player.points = 3
        assert game_engine.check_game_over(game_state) == "player"
        
        # Reset and test opponent wins
        game_state.player.points = 0
        game_state.opponent.points = 3
        assert game_engine.check_game_over(game_state) == "opponent"


class TestTCGPocketCompliance:
    """Test compliance with TCG Pocket rules."""
    
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
            weakness=EnergyType.FIRE
        )
        
        attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should be 30 + 20 = 50 damage, not 30 * 2 = 60
        assert result.damage_dealt == 50
    
    def test_no_resistance_mechanics(self, game_engine, basic_game_state):
        """Test that there are no resistance mechanics."""
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
            # No resistance field
        )
        
        attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should be exactly 30 damage, no reduction
        assert result.damage_dealt == 30
    
    def test_bench_limit_3(self, game_engine):
        """Test that bench limit is 3 Pokemon."""
        assert game_engine.max_bench_size == 3
    
    def test_poison_damage_10(self, game_engine, basic_game_state):
        """Test that poison does exactly 10 damage."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.POISONED
        )
        
        effects = game_engine.apply_status_condition_effects(poisoned_pokemon, basic_game_state)
        
        assert effects["poison_damage"] == 10
        assert poisoned_pokemon.damage_counters == 10 