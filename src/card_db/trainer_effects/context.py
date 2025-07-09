"""Context object for trainer effect execution."""

from typing import Dict, Any, List
from src.card_db.core import PokemonCard
from src.rules.game_state import GameState, PlayerState
from src.rules.game_engine import GameEngine

class EffectContext:
    """Context object passed between effect functions."""
    
    def __init__(self, game_state: GameState, player: PlayerState, game_engine: GameEngine):
        self.game_state = game_state
        self.player = player
        self.opponent = game_state.inactive_player_state
        self.game_engine = game_engine
        self.targets: List[PokemonCard] = []
        self.failed: bool = False
        self.data: Dict[str, Any] = {}  # For passing data between functions