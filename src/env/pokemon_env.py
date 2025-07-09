"""Pokemon TCG Pocket Gym Environment.

A Gymnasium environment for training RL agents to play Pokemon TCG Pocket.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.rules.actions import Action, ActionType, ActionValidator
from src.card_db.core import (
    Card, 
    PokemonCard, 
    ItemCard, 
    SupporterCard,
    EnergyType,
    Stage
)
from src.rules.game_engine import GameEngine


class PokemonTCGEnv(gym.Env):
    """Pokemon TCG Pocket environment for reinforcement learning."""
    
    def __init__(self, player_deck: List[Card], opponent_deck: List[Card]):
        """Initialize the environment with player and opponent decks."""
        super().__init__()
        
        # Validate deck sizes (TCG Pocket: exactly 20 cards)
        if len(player_deck) != 20:
            raise ValueError(f"Player deck must have exactly 20 cards, got {len(player_deck)}")
        if len(opponent_deck) != 20:
            raise ValueError(f"Opponent deck must have exactly 20 cards, got {len(opponent_deck)}")
        
        self.player_deck = player_deck
        self.opponent_deck = opponent_deck
        
        # Track turn information
        self.turn_number = 0
        self.is_player_turn = True
        
        # Define action space (discrete actions)
        self.action_space = gym.spaces.Discrete(100)  # Placeholder - will be dynamic
        
        # Define observation space
        self.observation_space = gym.spaces.Dict({
            # Active Pokemon stats
            'active_pokemon': gym.spaces.Dict({
                'hp': gym.spaces.Box(0, 300, (1,), dtype=np.int32),
                'damage': gym.spaces.Box(0, 300, (1,), dtype=np.int32),
                'energy': gym.spaces.Box(0, 10, (1,), dtype=np.int32),
                'is_basic': gym.spaces.Discrete(2),
                # Add more stats as needed
            }),
            
            # Bench information (max 3 in TCG Pocket)
            'bench': gym.spaces.Tuple([
                gym.spaces.Dict({
                    'hp': gym.spaces.Box(0, 300, (1,), dtype=np.int32),
                    'damage': gym.spaces.Box(0, 300, (1,), dtype=np.int32),
                    'energy': gym.spaces.Box(0, 10, (1,), dtype=np.int32),
                    'is_basic': gym.spaces.Discrete(2),
                }) for _ in range(3)
            ]),
            
            # Game state information
            'game_info': gym.spaces.Dict({
                'hand_size': gym.spaces.Box(0, 60, (1,), dtype=np.int32),
                'deck_size': gym.spaces.Box(0, 60, (1,), dtype=np.int32),
                'points_remaining': gym.spaces.Box(0, 3, (1,), dtype=np.int32),  # Fixed: Points, not prizes
                'energy_zone': gym.spaces.Box(0, 1, (1,), dtype=np.int32),  # Fixed: Add energy zone
            }),
            
            # Add bench information
            "bench": gym.spaces.Dict({
                "pokemon_count": gym.spaces.Box(low=0, high=3, shape=(1,), dtype=np.int32),  # Fixed: Max 3
                "hp": gym.spaces.Box(low=0, high=500, shape=(3,), dtype=np.int32),  # Fixed: 3 slots
                "types": gym.spaces.Box(low=0, high=10, shape=(3,), dtype=np.int32),  # Fixed: 3 slots
                "stages": gym.spaces.Box(low=0, high=2, shape=(3,), dtype=np.int32),  # Fixed: 3 slots
                "energy_counts": gym.spaces.Box(low=0, high=8, shape=(3,), dtype=np.int32),  # Fixed: 3 slots
            }),
        })
        
        # Add game engine
        self.game_engine = GameEngine()
        
        self.reset()
    
    def reset(self, seed: Optional[int] = None) -> Tuple[Dict, Dict]:
        """Reset environment to initial state."""
        super().reset(seed=seed)
        
        # Reset turn tracking
        self.turn_number = 0
        self.is_player_turn = True
        
        # Initialize new game state
        self.state = GameState()
        
        # Setup player's cards
        self.state.player.deck = self.player_deck.copy()
        np.random.shuffle(self.state.player.deck)
        
        # Draw opening hand (7 cards in TCG Pocket)
        for _ in range(7):
            if self.state.player.deck:
                self.state.player.hand.append(self.state.player.deck.pop())
        
        # TCG Pocket uses points, not prize cards
        # Points start at 0 and are earned through KOs
        
        # Setup opponent similarly
        self.state.opponent.deck = self.opponent_deck.copy()
        np.random.shuffle(self.state.opponent.deck)
        for _ in range(7):
            if self.state.opponent.deck:
                self.state.opponent.hand.append(self.state.opponent.deck.pop())
        
        return self._get_observation(), {}
    
    def get_legal_actions(self) -> List[Action]:
        """Get list of legal actions in current state."""
        return self._get_legal_actions()
    
    def step(self, action_idx: int) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """Execute one time step within the environment."""
        reward = 0.0
        info = {}
        
        # Get legal actions
        legal_actions = self.get_legal_actions()
        
        # Check if action is valid
        if action_idx >= len(legal_actions):
            return self._get_observation(), -1.0, False, False, {"error": "Invalid action index"}
        
        # Apply the chosen action
        action = legal_actions[action_idx]
        result = self._apply_action(action)
        
        if not result["success"]:
            reward = -1.0
            info["error"] = result["error"]
        else:
            reward = 1.0  # Reward successful actions
        
        # Check for game over
        winner = self.game_engine.check_game_over(self.state)
        if winner:
            terminated = True
            reward = 100.0 if winner == "player" else -100.0
        else:
            terminated = False
            reward = self._calculate_reward(result)
        
        return self._get_observation(), reward, terminated, False, info
    
    def _get_observation(self) -> Dict[str, Any]:
        """Convert game state to observation."""
        # Get active Pokemon stats safely
        active_pokemon = self.state.player.active_pokemon
        active_pokemon_stats = {
            "hp": np.array([active_pokemon.hp if active_pokemon else 0], dtype=np.int32),
            "type": np.array([list(EnergyType).index(active_pokemon.pokemon_type) if active_pokemon else 0], dtype=np.int32),
            "stage": np.array([list(Stage).index(active_pokemon.stage) if active_pokemon else 0], dtype=np.int32),
            "energy_count": np.array([len(active_pokemon.attached_energies) if active_pokemon else 0], dtype=np.int32),
        }
        
        # Get bench information
        bench_hp = np.zeros(3, dtype=np.int32)  # Fixed: 3 bench slots
        bench_types = np.zeros(3, dtype=np.int32)  # Fixed: 3 bench slots
        bench_stages = np.zeros(3, dtype=np.int32)  # Fixed: 3 bench slots
        bench_energy = np.zeros(3, dtype=np.int32)  # Fixed: 3 bench slots
        
        for i, pokemon in enumerate(self.state.player.bench[:3]):  # Fixed: Max 3 bench
            bench_hp[i] = pokemon.hp
            bench_types[i] = list(EnergyType).index(pokemon.pokemon_type)
            bench_stages[i] = list(Stage).index(pokemon.stage)
            bench_energy[i] = len(pokemon.attached_energies)
        
        bench_info = {
            "pokemon_count": np.array([len(self.state.player.bench)], dtype=np.int32),
            "hp": bench_hp,
            "types": bench_types,
            "stages": bench_stages,
            "energy_counts": bench_energy,
        }
        
        # Get opponent's active Pokemon stats safely
        opponent_active = self.state.opponent.active_pokemon
        opponent_active_stats = {
            "hp": np.array([opponent_active.hp if opponent_active else 0], dtype=np.int32),
            "type": np.array([list(EnergyType).index(opponent_active.pokemon_type) if opponent_active else 0], dtype=np.int32),
            "stage": np.array([list(Stage).index(opponent_active.stage) if opponent_active else 0], dtype=np.int32),
            "energy_count": np.array([len(opponent_active.attached_energies) if opponent_active else 0], dtype=np.int32),
        }
        
        # Fixed: Add energy zone information
        energy_zone_status = np.array([1 if self.state.player.energy_zone else 0], dtype=np.int32)
        
        # Fixed: Add missing fields expected by tests
        obs = {
            # Player state
            "hand_size": np.array([len(self.state.player.hand)], dtype=np.int32),
            "deck_size": np.array([len(self.state.player.deck)], dtype=np.int32),
            "points_remaining": np.array([3 - self.state.player.points], dtype=np.int32),  # Fixed: Points remaining
            "bench_size": np.array([len(self.state.player.bench)], dtype=np.int32),
            "energy_zone": energy_zone_status,  # Fixed: Add energy zone
            
            # Active Pokemon and bench
            "active_pokemon": active_pokemon_stats,
            "bench": bench_info,
            
            # Opponent state
            "opponent_hand_size": np.array([len(self.state.opponent.hand)], dtype=np.int32),
            "opponent_deck_size": np.array([len(self.state.opponent.deck)], dtype=np.int32),
            "opponent_points_remaining": np.array([3 - self.state.opponent.points], dtype=np.int32),  # Fixed: Points remaining
            "opponent_bench_size": np.array([len(self.state.opponent.bench)], dtype=np.int32),
            
            # Opponent's active Pokemon
            "opponent_active_pokemon": opponent_active_stats,
            
            # Fixed: Add missing fields expected by tests
            "is_player_turn": int(self.is_player_turn),
            "current_phase": int(self.state.phase.value),
            "turn_number": np.array([self.turn_number], dtype=np.int32),
            "opponent": opponent_active_stats,  # Simplified opponent info
        }
        
        return obs
    
    def _get_pokemon_obs(self, pokemon: Optional[PokemonCard]) -> Dict:
        """Get observation for a Pokemon."""
        if pokemon is None:
            return {
                "hp": np.array([0], dtype=np.int32),
                "damage": np.array([0], dtype=np.int32),
                "energy": np.array([0], dtype=np.int32),
                "is_basic": np.array([0], dtype=np.int32),
            }
        
        return {
            "hp": np.array([pokemon.hp], dtype=np.int32),
            "damage": np.array([pokemon.damage_counters], dtype=np.int32),
            "energy": np.array([len(pokemon.attached_energies)], dtype=np.int32),
            "is_basic": np.array([1 if pokemon.stage == Stage.BASIC else 0], dtype=np.int32),
        }
    
    def _get_legal_actions(self) -> List[Action]:
        """Get list of legal actions in current state."""
        return ActionValidator.get_legal_actions(self.state)
    
    def _apply_action(self, action: Action) -> Dict[str, Any]:
        """Apply an action to the game state."""
        try:
            if action.type == ActionType.PLAY_ITEM:
                success = self.game_engine.play_trainer_card(
                    action.source_card, self.state
                )
                return {"success": success, "error": None if success else "Failed to play item"}
            
            elif action.type == ActionType.PLAY_TOOL:
                success = self.game_engine.play_trainer_card(
                    action.source_card, self.state, action.target_card
                )
                return {"success": success, "error": None if success else "Failed to play tool"}
            
            elif action.type == ActionType.PLAY_SUPPORTER:
                success = self.game_engine.play_trainer_card(
                    action.source_card, self.state
                )
                return {"success": success, "error": None if success else "Failed to play supporter"}
            
            elif action.type == ActionType.PASS:
                # Handle pass action
                self.state.advance_phase()
                return {"success": True, "error": None}
            
            # Add other action types as needed
            else:
                return {"success": False, "error": f"Unhandled action type: {action.type}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_reward(self, result: Dict[str, Any]) -> float:
        """Calculate reward for the current state."""
        # This is a placeholder - implement actual reward calculation
        # based on game state, actions taken, etc.
        
        return 0.0
    
    @property
    def is_finished(self) -> bool:
        """Check if the game is finished."""
        return self.state.is_finished
    
    @property
    def game_state(self) -> GameState:
        """Get the current game state."""
        return self.state 