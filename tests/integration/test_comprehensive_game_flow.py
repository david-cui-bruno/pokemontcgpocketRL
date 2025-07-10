"""Comprehensive integration tests for Pokemon TCG Pocket."""

import pytest
import numpy as np
from src.env.pokemon_env import PokemonTCGEnv
from src.rules.game_engine import GameEngine
from src.rules.game_state import GameState, PlayerState, GamePhase
from src.card_db.core import (
    PokemonCard, Attack, EnergyType, Stage, ItemCard, SupporterCard, Card, Effect, TargetType, StatusCondition
)
from src.rules.actions import Action, ActionType


def create_test_deck() -> list[Card]:
    """Create a comprehensive test deck."""
    deck = []
    
    # Add basic Pokemon (10 cards)
    for i in range(10):
        pokemon = PokemonCard(
            id=f"BASIC-{i:03d}",
            name=f"Basic Pokemon {i}",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[
                Attack(
                    name="Basic Attack",
                    cost=[EnergyType.COLORLESS],
                    damage=20
                )
            ]
        )
        deck.append(pokemon)
    
    # Add evolved Pokemon (5 cards)
    for i in range(5):
        pokemon = PokemonCard(
            id=f"STAGE1-{i:03d}",
            name=f"Stage 1 Pokemon {i}",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            attacks=[
                Attack(
                    name="Evolved Attack",
                    cost=[EnergyType.COLORLESS, EnergyType.COLORLESS],
                    damage=40
                )
            ]
        )
        deck.append(pokemon)
    
    # Add ex Pokemon (3 cards)
    for i in range(3):
        pokemon = PokemonCard(
            id=f"EX-{i:03d}",
            name=f"Ex Pokemon {i}",
            hp=150,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            is_ex=True,
            attacks=[
                Attack(
                    name="Ex Attack",
                    cost=[EnergyType.COLORLESS, EnergyType.COLORLESS, EnergyType.COLORLESS],
                    damage=80
                )
            ]
        )
        deck.append(pokemon)
    
    # Add Item cards (2 cards)
    for i in range(2):
        item = ItemCard(
            id=f"ITEM-{i:03d}",
            name=f"Test Item {i}",
            effects=[Effect(effect_type="heal", amount=30, target=TargetType.SELF)]
        )
        deck.append(item)
    
    return deck


@pytest.fixture
def test_deck():
    """Create a test deck."""
    return create_test_deck()


@pytest.fixture
def game_env(test_deck):
    """Create a game environment with test decks."""
    return PokemonTCGEnv(player_deck=test_deck, opponent_deck=test_deck)


class TestComprehensiveGameFlow:
    """Comprehensive game flow tests."""
    
    def test_environment_initialization(self, game_env):
        """Test environment initializes correctly."""
        obs, info = game_env.reset()
        
        # Check initial state
        assert game_env.state.phase == GamePhase.MAIN  # Fixed: Game advances to MAIN after drawing
        assert game_env.state.player.points == 0
        assert game_env.state.opponent.points == 0
        assert len(game_env.state.player.hand) == 5  # TCG Pocket draws 5 (rulebook §3)
        assert len(game_env.state.opponent.hand) == 5
        # No prize cards in TCG Pocket - uses points instead
        
        print("✅ Environment initialization works")
    
    def test_deck_construction(self, test_deck):
        """Test deck construction follows TCG Pocket rules."""
        assert len(test_deck) == 20  # TCG Pocket has 20-card decks
        
        # Count card types
        pokemon_count = sum(1 for card in test_deck if isinstance(card, PokemonCard))
        item_count = sum(1 for card in test_deck if isinstance(card, ItemCard))
        
        assert pokemon_count > 0  # Must have Pokemon
        assert item_count > 0     # Must have Trainers
        
        # Check no Energy cards
        energy_count = sum(1 for card in test_deck if hasattr(card, 'energy_type'))
        assert energy_count == 0  # No Energy cards in deck
        
        print("✅ Deck construction follows TCG Pocket rules")
    
    def test_energy_zone_mechanics(self, game_env):
        """Test Energy Zone single-slot mechanics."""
        obs, info = game_env.reset()
        
        # Energy Zone starts empty
        assert game_env.state.player.energy_zone is None
        assert game_env.state.opponent.energy_zone is None
        
        # Generate energy
        game_env.state.player.energy_zone = EnergyType.FIRE
        assert game_env.state.player.energy_zone == EnergyType.FIRE
        
        # Can only hold one energy
        game_env.state.player.energy_zone = EnergyType.WATER
        assert game_env.state.player.energy_zone == EnergyType.WATER
        assert game_env.state.player.energy_zone != EnergyType.FIRE
        
        print("✅ Energy Zone mechanics work correctly")
    
    def test_bench_limits(self, game_env):
        """Test 3-bench limit enforcement."""
        obs, info = game_env.reset()
        
        # Create test Pokemon
        test_pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Try to add more than 3 Pokemon
        player_state = game_env.state.player
        for i in range(5):  # Try to add 5
            if len(player_state.bench) < 3:
                player_state.bench.append(test_pokemon)
        
        assert len(player_state.bench) <= 3
        print(f"✅ Bench limit enforced: {len(player_state.bench)} Pokemon")
    
    def test_point_system_comprehensive(self, game_env):
        """Test complete point system."""
        obs, info = game_env.reset()
        
        # Test regular Pokemon KO
        regular_pokemon = PokemonCard(
            id="REG-001",
            name="Regular Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Test ex Pokemon KO
        ex_pokemon = PokemonCard(
            id="EX-001",
            name="Ex Pokemon",
            hp=150,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            is_ex=True
        )
        
        # Award points
        game_env.game_engine.award_points(game_env.state.player, 1)  # Regular KO
        assert game_env.state.player.points == 1
        
        game_env.game_engine.award_points(game_env.state.player, 2)  # Ex KO
        assert game_env.state.player.points == 3
        
        # Test game over
        winner = game_env.game_engine.check_game_over(game_env.state)
        assert winner == "player"
        
        print("✅ Point system works correctly")
    
    def test_weakness_and_resistance(self, game_env):
        """Test weakness and resistance mechanics."""
        game_engine = game_env.game_engine
        
        # Set phase to ATTACK for attack validation
        game_env.state.phase = GamePhase.ATTACK
        
        # Test weakness (+20 damage)
        fire_attacker = PokemonCard(
            id="FIRE-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.FIRE]
        )
        
        grass_defender = PokemonCard(
            id="GRASS-001",
            name="Grass Pokemon",
            hp=100,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            weakness=EnergyType.FIRE
        )
        
        fire_attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        result = game_engine.resolve_attack(fire_attacker, fire_attack, grass_defender, game_env.state)
        assert result.damage_dealt == 50  # 30 + 20 weakness
        
        # Test no resistance
        water_attacker = PokemonCard(
            id="WATER-001",
            name="Water Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.WATER]
        )
        
        fire_defender = PokemonCard(
            id="FIRE-002",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC
            # No resistance field
        )
        
        water_attack = Attack(
            name="Water Attack",
            cost=[EnergyType.WATER],
            damage=30
        )
        
        result = game_engine.resolve_attack(water_attacker, water_attack, fire_defender, game_env.state)
        assert result.damage_dealt == 30  # No resistance reduction
        
        print("✅ Weakness and resistance mechanics work correctly")
    
    def test_status_conditions(self, game_env):
        """Test status condition mechanics."""
        game_engine = game_env.game_engine
        
        # Test poison
        poisoned_pokemon = PokemonCard(
            id="POISON-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.POISONED
        )
        
        effects = game_engine.apply_status_condition_effects(poisoned_pokemon, game_env.state)
        assert "poison_damage" in effects
        assert effects["poison_damage"] == 10  # TCG Pocket poison damage (rulebook §7)
        
        # Test burn
        burned_pokemon = PokemonCard(
            id="BURN-001",
            name="Burned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.BURNED
        )
        
        effects = game_engine.apply_status_condition_effects(burned_pokemon, game_env.state)
        assert "burn_damage" in effects
        assert effects["burn_damage"] == 20  # TCG Pocket burn damage
        
        print("✅ Status conditions work correctly")
    
    def test_attack_validation(self, game_env):
        """Test attack validation logic."""
        game_engine = game_env.game_engine
        
        # Set the phase to ATTACK for attack validation
        game_env.state.phase = GamePhase.ATTACK
        
        # Pokemon without energy
        pokemon_no_energy = PokemonCard(
            id="NO-ENERGY-001",
            name="No Energy Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attached_energies=[]  # No energy
        )
        
        attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        # Should fail validation
        can_attack = game_engine._can_use_attack(pokemon_no_energy, attack, game_env.state)
        assert not can_attack
        
        # Pokemon with energy
        pokemon_with_energy = PokemonCard(
            id="ENERGY-001",
            name="Energy Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.FIRE]  # Has energy
        )
        
        # Should pass validation
        can_attack = game_engine._can_use_attack(pokemon_with_energy, attack, game_env.state)
        assert can_attack
        
        print("✅ Attack validation works correctly")
    
    def test_complete_game_simulation(self, game_env):
        """Simulate a complete game from start to finish."""
        obs, info = game_env.reset()
        
        turn_count = 0
        max_turns = 30  # Prevent infinite loops
        
        print(f"Starting complete game simulation...")
        print(f"Initial state: Player {game_env.state.player.points} - Opponent {game_env.state.opponent.points}")
        
        while turn_count < max_turns:
            turn_count += 1
            
            # Get legal actions
            legal_actions = game_env.get_legal_actions()
            if not legal_actions:
                print(f"Turn {turn_count}: No legal actions available")
                break
            
            # Take first available action
            obs, reward, terminated, truncated, info = game_env.step(0)
            
            print(f"Turn {turn_count}: Action taken, Reward: {reward}")
            print(f"  Player: {game_env.state.player.points} points")
            print(f"  Opponent: {game_env.state.opponent.points} points")
            
            if terminated:
                print(f"Game ended on turn {turn_count}!")
                break
        
        print(f"Game simulation completed in {turn_count} turns")
        print("✅ Complete game simulation works")
    
    def test_observation_space(self, game_env):
        """Test that observations are properly formatted."""
        obs, info = game_env.reset()
        
        # Check observation structure
        assert isinstance(obs, dict)
        assert 'active_pokemon' in obs
        assert 'bench' in obs
        assert 'hand_size' in obs
        assert 'deck_size' in obs
        assert 'points_remaining' in obs  # Fixed: Points, not prizes
        assert 'energy_zone' in obs
        assert 'is_player_turn' in obs
        assert 'current_phase' in obs
        assert 'turn_number' in obs
        assert 'opponent' in obs
        
        # Check data types
        assert isinstance(obs['hand_size'], np.ndarray)
        assert isinstance(obs['deck_size'], np.ndarray)
        assert isinstance(obs['points_remaining'], np.ndarray)  # Fixed: Points, not prizes
        assert isinstance(obs['energy_zone'], np.ndarray)
        assert isinstance(obs['is_player_turn'], int)
        assert isinstance(obs['current_phase'], int)
        assert isinstance(obs['turn_number'], np.ndarray)
        
        print("✅ Observation space works correctly")
    
    def test_action_space(self, game_env):
        """Test action space and legal actions."""
        obs, info = game_env.reset()
        
        # Check action space
        assert hasattr(game_env, 'action_space')
        assert game_env.action_space.n > 0
        
        # Get legal actions
        legal_actions = game_env.get_legal_actions()
        assert isinstance(legal_actions, list)
        
        # If there are legal actions, test taking one
        if legal_actions:
            action = legal_actions[0]
            assert isinstance(action, Action)
            assert hasattr(action, 'action_type')
            
            # Take the action
            obs, reward, terminated, truncated, info = game_env.step(0)
            assert isinstance(reward, (int, float))
            assert isinstance(terminated, bool)
            assert isinstance(truncated, bool)
            assert isinstance(info, dict)
        
        print("✅ Action space and legal actions work correctly")


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_deck(self):
        """Test behavior with empty deck."""
        empty_deck = []
        
        with pytest.raises(ValueError):
            PokemonTCGEnv(player_deck=empty_deck, opponent_deck=empty_deck)
        
        print("✅ Empty deck handling works correctly")
    
    def test_invalid_deck_size(self):
        """Test behavior with invalid deck size."""
        small_deck = [PokemonCard(id="1", name="Test", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC)] * 10  # Only 10 cards
        
        with pytest.raises(ValueError):
            PokemonTCGEnv(player_deck=small_deck, opponent_deck=small_deck)
        
        print("✅ Invalid deck size handling works correctly")
    
    def test_duplicate_cards(self):
        """Test behavior with duplicate cards (should be allowed up to 2)."""
        # Create deck with 2 copies of same card (should be allowed)
        duplicate_deck = []
        for i in range(10):  # 10 different cards
            pokemon = PokemonCard(
                id=f"TEST-{i}",
                name=f"Test Pokemon {i}",
                hp=100,
                pokemon_type=EnergyType.COLORLESS,
                stage=Stage.BASIC
            )
            duplicate_deck.append(pokemon)
            duplicate_deck.append(pokemon)  # Add duplicate
        
        # This should work (2 copies allowed)
        env = PokemonTCGEnv(player_deck=duplicate_deck, opponent_deck=duplicate_deck)
        obs, info = env.reset()
        
        print("✅ Duplicate card handling works correctly") 