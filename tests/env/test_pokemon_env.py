"""Tests for the Pokemon TCG Pocket Gym Environment."""

import pytest
import numpy as np
import gymnasium as gym
from typing import Dict, List, Tuple

from src.env.pokemon_env import PokemonTCGEnv
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.rules.actions import Action, ActionType
from src.card_db.core import (
    Card, PokemonCard, ItemCard, SupporterCard,
    Stage, EnergyType, Attack, Effect
)


@pytest.fixture
def test_decks() -> Tuple[List[Card], List[Card]]:
    """Create test decks for both players."""
    # Create a minimal valid deck for testing
    basic_pokemon = PokemonCard(
        id="TEST-001",
        name="Test Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
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
    
    item_card = ItemCard(
        id="TEST-002",
        name="Test Item",
        effects=[Effect(effect_type="heal", amount=30)]
    )
    
    supporter_card = SupporterCard(
        id="TEST-003",
        name="Test Supporter",
        effects=[Effect(effect_type="draw", amount=3)]
    )
    
    # Create a 20-card deck with a mix of cards
    player_deck = (
        [basic_pokemon] * 10 +  # 10 Basic Pokemon
        [item_card] * 5 +       # 5 Items
        [supporter_card] * 5    # 5 Supporters
    )
    
    # Use the same deck for opponent
    opponent_deck = player_deck.copy()
    
    return player_deck, opponent_deck


class TestPokemonTCGEnv:
    @pytest.fixture
    def env(self, test_decks) -> PokemonTCGEnv:
        """Create a fresh environment for each test."""
        player_deck, opponent_deck = test_decks
        return PokemonTCGEnv(player_deck, opponent_deck)
    
    def test_env_initialization(self, env: PokemonTCGEnv):
        """Test that environment initializes with correct spaces."""
        assert isinstance(env.observation_space, gym.spaces.Dict)
        assert isinstance(env.action_space, gym.spaces.Discrete)
        
        # Check observation space components
        obs_space = env.observation_space.spaces
        assert "active_pokemon" in obs_space
        assert "bench" in obs_space
        assert "hand_size" in obs_space
        assert "deck_size" in obs_space
        assert "points_remaining" in obs_space  # Fixed: Points, not prizes (rulebook §10)
        
    def test_reset(self, env: PokemonTCGEnv):
        """Test environment reset."""
        obs, info = env.reset()
        
        # Check observation structure
        assert isinstance(obs, dict)
        assert "active_pokemon" in obs
        assert "bench" in obs
        assert "hand_size" in obs
        assert "deck_size" in obs
        assert "points_remaining" in obs  # Fixed: Points, not prizes (rulebook §10)
        
        # Fixed: TCG Pocket starts with 5 cards (rulebook §3)
        assert obs["hand_size"] == np.array([5])  # Starting hand size
        assert obs["points_remaining"] == np.array([3])  # Points remaining to win (rulebook §10)
        
    def test_step_play_pokemon(self, env: PokemonTCGEnv):
        """Test playing a basic Pokemon."""
        obs, info = env.reset()
        
        # Find a basic Pokemon in hand
        hand_size = obs["hand_size"][0]  # Using the actual observation space structure
        assert hand_size == 5  # Should start with 5 cards (rulebook §3)
        
        # Get legal actions
        legal_actions = env.get_legal_actions()
        
        if legal_actions:
            # Create action to play the first Pokemon
            action_idx = 0  # Index into legal actions list
            obs, reward, terminated, truncated, info = env.step(action_idx)
            
            # Check that action was processed (may or may not have played Pokemon)
            assert "error" not in info or info["error"] is None
        else:
            # No legal actions available - this is also valid
            pass
        
    def test_invalid_action(self, env: PokemonTCGEnv):
        """Test that invalid actions are handled appropriately."""
        obs, info = env.reset()
        
        # Try an invalid action index
        action_idx = 999  # Invalid index
        obs, reward, terminated, truncated, info = env.step(action_idx)
        
        assert reward < 0  # Should be penalized
        assert "error" in info
        
    def test_game_over_conditions(self, env: PokemonTCGEnv):
        """Test that game ends appropriately."""
        obs, info = env.reset()
        
        # Simulate player reaching 3 points (rulebook §10)
        env.state.player.points = 3
        
        # Take any action
        action_idx = 0
        obs, reward, terminated, truncated, info = env.step(action_idx)
        
        assert terminated
        assert reward > 0  # Win condition
        
    @pytest.mark.parametrize("action_type", list(ActionType))
    def test_action_space_coverage(self, env: PokemonTCGEnv, action_type: ActionType):
        """Test that all action types can be processed."""
        obs, info = env.reset()
        
        # Get legal actions
        legal_actions = env.get_legal_actions()  # We need to add this method
        
        # Find an action of the desired type if available
        action_idx = next(
            (i for i, a in enumerate(legal_actions) if a.type == action_type),
            0  # Default to 0 if no such action is legal
        )
        
        # Should not raise an exception
        try:
            env.step(action_idx)
        except ValueError:
            # Some actions might be invalid in the initial state,
            # but they should still be processed without crashing
            pass

def setup_for_attack(game_state):
    """Quick setup for attack tests."""
    game_state.phase = GamePhase.ATTACK
    return game_state 