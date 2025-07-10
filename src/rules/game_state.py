"""Game state management for Pokemon TCG Pocket.

This module defines the immutable state classes that represent the complete
game state, including player states, energy zones, and turn tracking.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict
from enum import Enum, auto

from src.rules.constants import (
    EnergyType, GamePhase, StatusCondition, GameConstants
)
from src.card_db.core import (
    Card, PokemonCard, SupporterCard, ToolCard, ItemCard
)

class PlayerTag(Enum):
    """Player identifier."""
    PLAYER = auto()
    OPPONENT = auto()

    @property
    def other(self) -> PlayerTag:
        """Get the opposing player's tag."""
        return PlayerTag.OPPONENT if self == PlayerTag.PLAYER else PlayerTag.PLAYER

@dataclass(frozen=True)
class EnergyZone:
    """Represents a player's Energy Zone (single-slot buffer)."""
    registered_types: Set[EnergyType]  # Types that can be generated (1-3)
    current_energy: Optional[EnergyType] = None  # Current energy in buffer
    
    def __post_init__(self):
        """Validate energy zone setup."""
        if len(self.registered_types) > GameConstants.MAX_ENERGY_TYPES:
            raise ValueError(
                f"Cannot register more than {GameConstants.MAX_ENERGY_TYPES} energy types"
            )
        if len(self.registered_types) == 0:
            raise ValueError("Must register at least one energy type")

    def can_generate_energy(self) -> bool:
        """Check if zone can generate new energy."""
        return self.current_energy is None

    def generate_energy(self, rng) -> Optional[EnergyType]:
        """Generate a random energy of registered type if buffer is empty."""
        if not self.can_generate_energy():
            return None
        return rng.choice(list(self.registered_types))

@dataclass(frozen=True)
class TurnState:
    """Tracks actions taken during a turn."""
    energy_attached: bool = False  # Track energy attachment
    supporter_played: bool = False  # One supporter per turn
    retreated: bool = False  # One retreat per turn
    attacked: bool = False  # Attack ends turn
    pokemon_played_this_turn: Set[str] = field(default_factory=set)  # IDs of Pokemon played
    pokemon_evolved_this_turn: Set[str] = field(default_factory=set)  # IDs of evolved Pokemon

    def can_play_supporter(self) -> bool:
        """Check if a supporter can be played."""
        return not self.supporter_played

    def can_attach_energy(self) -> bool:
        """Check if energy can be attached."""
        return not self.energy_attached

    def can_retreat(self) -> bool:
        """Check if a retreat can be performed."""
        return not self.retreated

@dataclass(frozen=True)
class PlayerState:
    """Represents a player's complete game state."""
    tag: PlayerTag
    deck: List[Card]
    hand: List[Card]
    active_pokemon: Optional[PokemonCard] = None
    bench: List[PokemonCard] = field(default_factory=list)
    discard_pile: List[Card] = field(default_factory=list)
    energy_zone: EnergyZone
    points: int = 0
    
    def __post_init__(self):
        """Validate player state."""
        if len(self.bench) > GameConstants.MAX_BENCH_SIZE:
            raise ValueError(f"Bench cannot exceed {GameConstants.MAX_BENCH_SIZE} Pokemon")
        if len(self.hand) > GameConstants.MAX_HAND_SIZE:
            raise ValueError(f"Hand cannot exceed {GameConstants.MAX_HAND_SIZE} cards")
        if self.points > GameConstants.POINTS_TO_WIN:
            raise ValueError(f"Points cannot exceed {GameConstants.POINTS_TO_WIN}")

    @property
    def has_active_pokemon(self) -> bool:
        """Check if player has an active Pokemon."""
        return self.active_pokemon is not None

    @property
    def can_bench_pokemon(self) -> bool:
        """Check if player can add Pokemon to bench."""
        return len(self.bench) < GameConstants.MAX_BENCH_SIZE

    @property
    def all_pokemon(self) -> List[PokemonCard]:
        """Get all Pokemon in play (active + bench)."""
        pokemon = []
        if self.active_pokemon:
            pokemon.append(self.active_pokemon)
        pokemon.extend(self.bench)
        return pokemon

    @property
    def has_valid_attack_target(self) -> bool:
        """Check if player has a Pokemon that can be attacked."""
        return self.active_pokemon is not None

    def can_evolve_pokemon(self, evolution: PokemonCard, pokemon_id: str) -> bool:
        """Check if specific Pokemon can evolve into the given evolution."""
        if not evolution.evolves_from:
            return False
            
        # Find target Pokemon
        target = None
        if self.active_pokemon and self.active_pokemon.id == pokemon_id:
            target = self.active_pokemon
        else:
            for pokemon in self.bench:
                if pokemon.id == pokemon_id:
                    target = pokemon
                    break
                    
        if not target:
            return False
            
        return (
            target.name == evolution.evolves_from and
            target.turns_in_play > 0  # Can't evolve Pokemon played this turn
        )

    def must_discard_hand(self) -> bool:
        """Check if cards must be discarded due to hand size limit."""
        return len(self.hand) > GameConstants.MAX_HAND_SIZE

@dataclass(frozen=True)
class GameState:
    """Complete game state."""
    player: PlayerState
    opponent: PlayerState
    phase: GamePhase
    turn_count: int = 1
    is_first_turn: bool = True
    turn_state: TurnState = field(default_factory=TurnState)
    active_player_tag: PlayerTag = PlayerTag.PLAYER

    def __post_init__(self):
        """Validate game state."""
        if not isinstance(self.player, PlayerState):
            raise ValueError("Invalid player state")
        if not isinstance(self.opponent, PlayerState):
            raise ValueError("Invalid opponent state")
        if self.player.tag == self.opponent.tag:
            raise ValueError("Players must have different tags")

    @property
    def active_player(self) -> PlayerState:
        """Get the active player's state."""
        return self.player if self.active_player_tag == PlayerTag.PLAYER else self.opponent

    @property
    def inactive_player(self) -> PlayerState:
        """Get the inactive player's state."""
        return self.opponent if self.active_player_tag == PlayerTag.PLAYER else self.player

    @property
    def is_game_over(self) -> bool:
        """Check if game is over (points or no Pokemon)."""
        return (
            self.player.points >= GameConstants.POINTS_TO_WIN or
            self.opponent.points >= GameConstants.POINTS_TO_WIN or
            not any(self.player.all_pokemon) or
            not any(self.opponent.all_pokemon)
        )

    @property
    def winner(self) -> Optional[PlayerTag]:
        """Get the winner if game is over."""
        if self.player.points >= GameConstants.POINTS_TO_WIN:
            return PlayerTag.PLAYER
        if self.opponent.points >= GameConstants.POINTS_TO_WIN:
            return PlayerTag.OPPONENT
        if not any(self.player.all_pokemon):
            return PlayerTag.OPPONENT
        if not any(self.opponent.all_pokemon):
            return PlayerTag.PLAYER
        return None

    def can_play_card(self, card: Card) -> bool:
        """Check if a card can be played in current phase/state."""
        if self.phase != GamePhase.ACTION:
            return False
            
        if isinstance(card, SupporterCard):
            return not self.turn_state.supporter_played
            
        return True

    def advance_phase(self) -> GameState:
        """Advance to the next phase, updating turn count if needed."""
        phase_order = [
            GamePhase.START,
            GamePhase.ACTION,
            GamePhase.ATTACK,
            GamePhase.CHECKUP
        ]
        current_idx = phase_order.index(self.phase)
        next_phase = phase_order[(current_idx + 1) % len(phase_order)]
        
        # If completing a turn
        if next_phase == GamePhase.START:
            return GameState(
                player=self.player,
                opponent=self.opponent,
                phase=next_phase,
                turn_count=self.turn_count + 1,
                is_first_turn=False,
                active_player_tag=self.active_player_tag.other,
                turn_state=TurnState()  # Reset turn state
            )
        
        # Just advancing phases within turn
        return GameState(
            player=self.player,
            opponent=self.opponent,
            phase=next_phase,
            turn_count=self.turn_count,
            is_first_turn=self.is_first_turn,
            active_player_tag=self.active_player_tag,
            turn_state=self.turn_state
        )