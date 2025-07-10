"""Tests for the GameEngine class."""

import pytest
from typing import List

from src.rules.game_engine import GameEngine, DamageResult, CoinFlipResult
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import PokemonCard, Attack, EnergyType, Stage, StatusCondition, Card


@pytest.fixture
def game_engine():
    """Create a GameEngine instance."""
    return GameEngine()


@pytest.fixture
def basic_pokemon():
    """Create a basic Pokemon for testing."""
    pokemon = PokemonCard(
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
        ]
    )
    # Initialize the mutable fields
    pokemon.attached_energies = []
    pokemon.damage_counters = 0
    pokemon.energy_attached = 0
    return pokemon


@pytest.fixture
def fire_pokemon():
    """Create a Fire Pokemon for testing."""
    pokemon = PokemonCard(
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
    # Initialize the mutable fields
    pokemon.attached_energies = []
    pokemon.damage_counters = 0
    pokemon.energy_attached = 0
    return pokemon


@pytest.fixture
def grass_pokemon():
    """Create a Grass Pokemon for testing."""
    pokemon = PokemonCard(
        id="TEST-003",
        name="Grass Pokemon",
        hp=90,
        pokemon_type=EnergyType.GRASS,
        stage=Stage.BASIC,
        weakness=EnergyType.FIRE,  # Removed resistance field
        attacks=[
            Attack(
                name="Grass Attack",
                cost=[EnergyType.GRASS],
                damage=35
            )
        ]
    )
    # Initialize the mutable fields
    pokemon.attached_energies = []
    pokemon.damage_counters = 0
    pokemon.energy_attached = 0
    return pokemon


@pytest.fixture
def basic_game_state():
    """Create a basic game state for testing."""
    state = GameState()
    state.phase = GamePhase.ATTACK
    return state


@pytest.fixture
def mock_card():
    """Create a mock card for testing."""
    return Card(id="MOCK-001", name="Mock Card")


class TestGameEngine:
    
    def test_attack_resolution_basic(self, game_engine, basic_pokemon):
        """Test basic attack resolution."""
        attack = basic_pokemon.attacks[0]
        target = PokemonCard(
            id="TARGET-001",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Add energy to attacker
        basic_pokemon.attached_energies = [EnergyType.COLORLESS]
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        result = game_engine.resolve_attack(basic_pokemon, attack, target, game_state)
        
        assert result.damage_dealt == 30
        assert result.damage_result == DamageResult.NORMAL
        assert not result.target_ko
        # Fixed: energy_discarded only includes effect-based discards, not attack costs
        assert len(result.energy_discarded) == 0
    
    def test_attack_resolution_weakness(self, game_engine, fire_pokemon, grass_pokemon):
        """Test attack resolution with weakness."""
        attack = fire_pokemon.attacks[0]
        
        # Add energy to attacker
        fire_pokemon.attached_energies = [EnergyType.FIRE]
        
        # Ensure target starts with no damage
        grass_pokemon.damage_counters = 0
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        result = game_engine.resolve_attack(fire_pokemon, attack, grass_pokemon, game_state)
        
        # Fixed: Weakness adds +20 damage (rulebook §1)
        assert result.damage_dealt == 60  # 40 + 20 for weakness
        assert result.damage_result == DamageResult.WEAKNESS
        assert not result.target_ko  # 60 damage vs 90 HP should NOT KO (60 < 90)
        assert grass_pokemon.damage_counters == 60  # Verify damage was applied
    
    def test_attack_resolution_no_resistance(self, game_engine, fire_pokemon):
        """Test attack resolution without resistance (TCG Pocket has no resistance)."""
        attack = fire_pokemon.attacks[0]
        target = PokemonCard(
            id="NORMAL-001",
            name="Normal Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC
            # No resistance field in TCG Pocket
        )
        
        # Add energy to attacker
        fire_pokemon.attached_energies = [EnergyType.FIRE]
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        result = game_engine.resolve_attack(fire_pokemon, attack, target, game_state)
        
        # Should be normal damage, no resistance reduction
        assert result.damage_dealt == 40  # No resistance reduction
        assert result.damage_result == DamageResult.NORMAL
        assert not result.target_ko
    
    def test_evolution_mechanics(self, game_engine, basic_pokemon):
        """Test evolution mechanics."""
        evolution = PokemonCard(
            id="EVOLUTION-001",
            name="Evolved Pokemon",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            evolves_from="Test Pokemon"
        )
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        game_state.player.hand = [evolution]
        
        # Should be able to evolve
        assert game_engine.evolve_pokemon(evolution, basic_pokemon, game_state)
        
        # Should not be able to evolve if evolution not in hand
        game_state.player.hand = []
        assert not game_engine.evolve_pokemon(evolution, basic_pokemon, game_state)
    
    def test_retreat_mechanics(self, game_engine, basic_pokemon):
        """Test retreat mechanics."""
        bench_pokemon = PokemonCard(
            id="BENCH-001",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        game_state.player.bench = [bench_pokemon]
        game_state.player.active_pokemon = basic_pokemon
        
        # Should be able to retreat (no retreat cost)
        assert game_engine.retreat_pokemon(basic_pokemon, bench_pokemon, game_state)
        
        # Test with retreat cost
        basic_pokemon.retreat_cost = 1
        assert not game_engine.retreat_pokemon(basic_pokemon, bench_pokemon, game_state)
        
        # Add energy and should be able to retreat
        basic_pokemon.attached_energies = [EnergyType.COLORLESS]
        
        # Fix: Set the active Pokemon back to basic_pokemon (it was changed in the previous retreat)
        game_state.player.active_pokemon = basic_pokemon
        game_state.player.bench = [bench_pokemon]
        
        assert game_engine.retreat_pokemon(basic_pokemon, bench_pokemon, game_state)
    
    def test_retreat_restrictions_status_conditions(self, game_engine, basic_pokemon):
        """Test that status conditions prevent retreat."""
        bench_pokemon = PokemonCard(
            id="BENCH-001",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        game_state.player.bench = [bench_pokemon]
        
        # Test asleep Pokemon cannot retreat
        basic_pokemon.status_condition = StatusCondition.ASLEEP
        assert not game_engine.retreat_pokemon(basic_pokemon, bench_pokemon, game_state)
        
        # Test paralyzed Pokemon cannot retreat
        basic_pokemon.status_condition = StatusCondition.PARALYZED
        assert not game_engine.retreat_pokemon(basic_pokemon, bench_pokemon, game_state)
        
        # Test normal Pokemon can retreat
        basic_pokemon.status_condition = None
        assert game_engine.retreat_pokemon(basic_pokemon, bench_pokemon, game_state)
    
    def test_point_awarding_system(self, game_engine):
        """Test TCG Pocket point awarding system."""
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
    
    def test_game_over_conditions(self, game_engine):
        """Test game over detection with point system."""
        game_state = GameState()
        game_state.phase = GamePhase.DRAW
        
        # Add some Pokemon to avoid the "no Pokemon in play" condition
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        game_state.player.active_pokemon = basic_pokemon
        game_state.opponent.active_pokemon = basic_pokemon
        
        # Add some deck cards
        game_state.player.deck = [None, None, None]
        game_state.opponent.deck = [None, None, None]
        
        # Game should continue normally
        result = game_engine.check_game_over(game_state)
        assert result is None
        
        # Player wins by reaching 3 points
        game_state.player.points = 3
        assert game_engine.check_game_over(game_state) == "player"
        
        # Reset and test opponent wins
        game_state.player.points = 0
        game_state.opponent.points = 3
        assert game_engine.check_game_over(game_state) == "opponent"
        
        # Reset and test deck depletion (only in DRAW phase)
        game_state.player.points = 0
        game_state.opponent.points = 0
        game_state.player.deck = []
        game_state.phase = GamePhase.DRAW
        game_state.active_player = PlayerTag.PLAYER
        assert game_engine.check_game_over(game_state) == "opponent"
    
    def test_draw_cards(self, game_engine):
        """Test drawing cards."""
        player = PlayerState()
        player.deck = [None, None, None, None, None]  # Mock cards
        
        drawn = game_engine.draw_cards(player, 3)
        assert len(drawn) == 3
        assert len(player.deck) == 2
        
        # Test drawing more cards than available
        drawn = game_engine.draw_cards(player, 5)
        assert len(drawn) == 2  # Only 2 cards left
        assert len(player.deck) == 0
    
    def test_attack_resolution_ko(self, game_engine, fire_pokemon):
        """Test attack resolution that results in KO."""
        attack = fire_pokemon.attacks[0]
        target = PokemonCard(
            id="WEAK-001",
            name="Weak Pokemon",
            hp=30,  # Low HP
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Add energy to attacker
        fire_pokemon.attached_energies = [EnergyType.FIRE]
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        result = game_engine.resolve_attack(fire_pokemon, attack, target, game_state)
        
        assert result.damage_dealt == 40
        assert result.target_ko  # 40 damage vs 30 HP should KO
        assert target.damage_counters >= target.hp  # Verify KO condition
    
    def test_status_condition_prevents_attack(self, game_engine, basic_game_state):
        """Test that status conditions prevent attacking."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        attack = Attack(
            name="Test Attack",
            cost=[EnergyType.COLORLESS],
            damage=30
        )
        
        # Should not be able to attack while asleep
        can_attack = game_engine._can_use_attack(asleep_pokemon, attack, basic_game_state)
        assert not can_attack
        
        # Should not be able to attack while paralyzed
        asleep_pokemon.status_condition = StatusCondition.PARALYZED
        can_attack = game_engine._can_use_attack(asleep_pokemon, attack, basic_game_state)
        assert not can_attack
        
        # Should be able to attack when normal
        asleep_pokemon.status_condition = None
        can_attack = game_engine._can_use_attack(asleep_pokemon, attack, basic_game_state)
        assert can_attack
    
    def test_coin_flip_mechanics(self, game_engine):
        """Test coin flip mechanics."""
        # Test single coin flip
        result = game_engine.flip_coin()
        assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
        
        # Test multiple coin flips
        results = game_engine.flip_coins(3)
        assert len(results) == 3
        for result in results:
            assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
    
    def test_healing_mechanics(self, game_engine):
        """Test healing mechanics."""
        pokemon = PokemonCard(
            id="TEST-001",
            name="Damaged Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            damage_counters=50
        )
        
        # Test healing
        healed = game_engine.heal_pokemon(pokemon, 30)
        assert healed
        assert pokemon.damage_counters == 20  # 50 - 30 = 20
        
        # Test healing to full
        healed = game_engine.heal_pokemon(pokemon, 30)
        assert healed
        assert pokemon.damage_counters == 0  # Cannot go below 0
        
        # Test healing with no damage (should still return True if amount > 0)
        healed = game_engine.heal_pokemon(pokemon, 10)
        assert healed  # The method returns True if amount > 0, regardless of actual healing
        assert pokemon.damage_counters == 0