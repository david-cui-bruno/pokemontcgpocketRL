"""Context object for trainer effect execution."""

from typing import Dict, Any, List
from src.card_db.core import PokemonCard
from src.rules.game_state import GameState, PlayerState
from src.rules.game_engine import GameEngine
import dataclasses

@dataclasses.dataclass
class EffectContext:
    """Context for executing trainer effects."""
    game_state: 'GameState'
    player: 'PlayerState'
    opponent: 'PlayerState'
    game_engine: 'GameEngine'
    targets: List[Any] = dataclasses.field(default_factory=list)
    data: Dict[str, Any] = dataclasses.field(default_factory=dict)
    failed: bool = False