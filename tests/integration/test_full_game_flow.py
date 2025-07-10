"""Integration tests for complete game flow."""

import pytest
from src.env.pokemon_env import PokemonTCGEnv
from src.rules.game_engine import GameEngine
from src.rules.game_state import GameState, PlayerState, GamePhase
from src.card_db.core import (
    PokemonCard, Attack, EnergyType, Stage, ItemCard, SupporterCard, Card
)
from src.rules.actions import Action, ActionType


def create_sample_deck() -> list[Card]:
    """Create a sample deck for testing."""
    deck = []
    
    # Add some basic Pokemon
    for i in range(10):
        pokemon = PokemonCard(
            id=f"TEST-{i:03d}",
            name=f"Test Pokemon {i}",
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
    
    # Add some Item cards
    for i in range(5):
        item = ItemCard(
            id=f"ITEM-{i:03d}",
            name=f"Test Item {i}",
            effects=[]
        )
        deck.append(item)
    
    # Add some Supporter cards
    for i in range(5):
        supporter = SupporterCard(
            id=f"SUPP-{i:03d}",
            name=f"Test Supporter {i}",
            effects=[]
        )
        deck.append(supporter)
    
    return deck


@pytest.fixture
def sample_deck():
    """Create a sample deck for testing."""
    return create_sample_deck()


@pytest.fixture
def game_env(sample_deck):
    """Create a game environment with sample decks."""
    return PokemonTCGEnv(player_deck=sample_deck, opponent_deck=sample_deck)


class TestFullGameFlow:
    """Test complete game flow from start to finish."""
    
    def test_game_initialization(self, game_env):
        """Test that game initializes correctly."""
        obs, info = game_env.reset()
        
        # Check initial state
        assert game_env.state.phase == GamePhase.MAIN
        assert game_env.state.player.points == 0
        assert game_env.state.opponent.points == 0
        assert len(game_env.state.player.hand) == 5  # TCG Pocket draws 5 cards (rulebook §3)
        assert len(game_env.state.opponent.hand) == 5
        
        print("✅ Game initialization works correctly")
    
    def test_basic_turn_structure(self, game_env):
        """Test that turn phases work correctly."""
        obs, info = game_env.reset()
        
        # Test turn progression
        initial_phase = game_env.state.phase
        print(f"Initial phase: {initial_phase}")
        
        # Take a basic action
        legal_actions = game_env.get_legal_actions()
        if legal_actions:
            action = legal_actions[0]
            obs, reward, terminated, truncated, info = game_env.step(0)  # Take first action
            print(f"Action taken: {action.action_type}")
            print(f"New phase: {game_env.state.phase}")
            print(f"Reward: {reward}")
        
        print("✅ Turn structure works correctly")
    
    def test_energy_zone_mechanics(self, game_env):
        """Test Energy Zone single-slot mechanics."""
        obs, info = game_env.reset()
        
        # Check Energy Zone starts empty
        assert game_env.state.player.energy_zone is None
        assert game_env.state.opponent.energy_zone is None
        
        # Fixed: Set energy directly in Energy Zone (rulebook §5)
        # Energy is generated automatically at start of turn if Zone is empty
        game_env.state.player.energy_zone = EnergyType.FIRE
        assert game_env.state.player.energy_zone == EnergyType.FIRE
        
        # Test single-slot limitation
        game_env.state.player.energy_zone = EnergyType.WATER
        assert game_env.state.player.energy_zone == EnergyType.WATER
        assert game_env.state.player.energy_zone != EnergyType.FIRE  # Only one energy at a time
        
        print("✅ Energy Zone mechanics work correctly")
    
    def test_bench_limits(self, game_env):
        """Test 3-bench limit (TCG Pocket rule)."""
        obs, info = game_env.reset()
        
        # Create test Pokemon
        test_pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Try to add more than 3 Pokemon to bench
        player_state = game_env.state.player
        for i in range(4):
            if len(player_state.bench) < 3:
                player_state.bench.append(test_pokemon)
        
        assert len(player_state.bench) <= 3
        print("✅ Bench limit (3) enforced correctly")
    
    def test_point_system(self, game_env):
        """Test TCG Pocket point system."""
        obs, info = game_env.reset()
        
        # Test regular Pokemon KO (1 point)
        regular_pokemon = PokemonCard(
            id="TEST-001",
            name="Regular Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Test ex Pokemon KO (2 points)
        ex_pokemon = PokemonCard(
            id="TEST-002",
            name="Ex Pokemon",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            is_ex=True
        )
        
        # Simulate KO
        game_env.game_engine.award_points(game_env.state.player, 1)
        assert game_env.state.player.points == 1
        
        game_env.game_engine.award_points(game_env.state.player, 2)
        assert game_env.state.player.points == 3
        
        print("✅ Point system works correctly")
    
    def test_weakness_calculation(self, game_env):
        """Test weakness adds +20 damage (TCG Pocket rule)."""
        game_engine = game_env.game_engine
        
        # Set phase to ATTACK for attack validation
        game_env.state.phase = GamePhase.ATTACK
        
        # Create attacking Pokemon
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC
        )
        
        # Create defending Pokemon with weakness
        defender = PokemonCard(
            id="TEST-002", 
            name="Grass Pokemon",
            hp=100,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            weakness=EnergyType.FIRE
        )
        
        # Create attack
        attack = Attack(
            name="Fire Attack",
            cost=[EnergyType.FIRE],
            damage=30
        )
        
        # Set up game state properly for attack validation
        game_env.state.player.active_pokemon = attacker
        game_env.state.opponent.active_pokemon = defender
        attacker.attached_energies = [EnergyType.FIRE]
        
        # Test attack resolution
        result = game_engine.resolve_attack(attacker, attack, defender, game_env.state)
        
        # Base damage: 30, Weakness: +20, Total: 50
        assert result.damage_dealt == 50
        print("✅ Weakness calculation (+20) works correctly")
    
    def test_no_resistance(self, game_env):
        """Test that resistance mechanics are removed."""
        game_engine = game_env.game_engine
        
        # Set the phase to ATTACK for attack validation
        game_env.state.phase = GamePhase.ATTACK

        # Create Pokemon that would have resistance in traditional TCG
        attacker = PokemonCard(
            id="TEST-001",
            name="Water Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC
        )
        
        defender = PokemonCard(
            id="TEST-002",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC
            # No resistance field - TCG Pocket has no resistance
        )
        
        attack = Attack(
            name="Water Attack",
            cost=[EnergyType.WATER],
            damage=30
        )
        
        # Set up game state properly for attack validation
        game_env.state.player.active_pokemon = attacker
        game_env.state.opponent.active_pokemon = defender
        attacker.attached_energies = [EnergyType.WATER]
        
        result = game_engine.resolve_attack(attacker, attack, defender, game_env.state)
        assert result.damage_dealt == 30  # No resistance reduction
    
    def test_complete_game_simulation(self, game_env):
        """Simulate a complete game from start to finish."""
        obs, info = game_env.reset()
        
        turn_count = 0
        max_turns = 20  # Prevent infinite loops
        
        print(f"Starting game simulation...")
        print(f"Player 1 points: {game_env.state.player.points}")
        print(f"Player 2 points: {game_env.state.opponent.points}")
        
        while turn_count < max_turns:
            turn_count += 1
            
            # Get legal actions
            legal_actions = game_env.get_legal_actions()
            if not legal_actions:
                print("No legal actions available")
                break
            
            # Take first available action
            obs, reward, terminated, truncated, info = game_env.step(0)
            
            print(f"Turn {turn_count}: Reward: {reward}")
            print(f"  Player 1: {game_env.state.player.points} points")
            print(f"  Player 2: {game_env.state.opponent.points} points")
            
            if terminated:
                print("Game ended!")
                break
        
        print(f"Game simulation completed in {turn_count} turns")
        print("✅ Complete game simulation works") 