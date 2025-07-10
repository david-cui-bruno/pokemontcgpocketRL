"""Core data structures for the game state.

This module defines the immutable dataclasses for GameState and PlayerState,
which together represent the entire state of a Pokemon TCG Pocket game.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import dataclasses

from src.card_db.core import Card, PokemonCard, SupporterCard, EnergyType, PlayerTag
from enum import Enum, auto


class GamePhase(Enum):
    DRAW = 1
    START_OF_TURN = 2
    MAIN = 3
    ATTACK = 4
    END = 5

    def next_phase(self) -> 'GamePhase':
        """Get the next phase in sequence."""
        phases = [GamePhase.DRAW, GamePhase.START_OF_TURN, GamePhase.MAIN, 
                 GamePhase.ATTACK, GamePhase.END]
        current_idx = phases.index(self)
        return phases[(current_idx + 1) % len(phases)]


@dataclass(frozen=False)  # Change from frozen=True
class PlayerState:
    """Represents the complete state for a single player."""
    
    player_tag: PlayerTag
    
    # Active Pokemon and bench (max 3 in TCG Pocket)
    active_pokemon: Optional[PokemonCard] = None
    bench: List[PokemonCard] = field(default_factory=list)
    
    # Card piles
    deck: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    discard_pile: List[Card] = field(default_factory=list)
    
    # Game state variables
    points: int = 0
    energy_zone: Optional[EnergyType] = None
    supporter_played_this_turn: bool = False
    energy_attached_this_turn: bool = False
    pokemon_entered_play_this_turn: List[str] = field(default_factory=list)
    registered_energy_types: List[EnergyType] = field(default_factory=list)
    max_registered_types: int = 3
    
    def __post_init__(self):
        if len(self.bench) > 3:
            raise ValueError("Bench cannot exceed 3 Pokemon.")
        if self.points > 3:
            raise ValueError("Points cannot exceed 3.")
    
    @property
    def pokemon_in_play(self) -> List[PokemonCard]:
        """Returns a list of all Pokemon in play (active and benched)."""
        in_play = []
        if self.active_pokemon:
            in_play.append(self.active_pokemon)
        in_play.extend(self.bench)
        return in_play

    def can_play_supporter(self) -> bool:
        """Check if a supporter can be played."""
        return not self.supporter_played_this_turn

    def can_attach_energy(self) -> bool:
        """Check if energy can be attached."""
        return not self.energy_attached_this_turn and self.energy_zone is not None

    def can_bench_pokemon(self) -> bool:
        """Check if a Pokemon can be benched."""
        return len(self.bench) < 3

    def has_pokemon_entered_play_this_turn(self, pokemon_id: str) -> bool:
        """Check if a Pokemon entered play this turn."""
        return pokemon_id in self.pokemon_entered_play_this_turn

    def generate_energy(self, energy_type: EnergyType) -> bool:
        """Generate energy into the energy zone."""
        if self.energy_zone is not None:
            return False
        self.energy_zone = energy_type
        return True

    def attach_energy(self, pokemon: PokemonCard, energy_type: Optional[EnergyType] = None) -> bool:
        """Attach energy from zone to a Pokemon."""
        if self.energy_attached_this_turn:
            return False
        if energy_type is None:
            energy_type = self.energy_zone
        if energy_type is None:
            return False
            
        pokemon.attached_energies.append(energy_type)
        self.energy_zone = None
        self.energy_attached_this_turn = True
        return True

    def register_energy_type(self, energy_type: EnergyType) -> 'PlayerState':
        """Register an energy type for the zone if not already full."""
        if len(self.registered_energy_types) >= self.max_registered_types:
            raise ValueError("Maximum number of energy types already registered.")
        if energy_type in self.registered_energy_types:
            return self  # No change needed
        new_types = self.registered_energy_types + [energy_type]
        return dataclasses.replace(self, registered_energy_types=new_types)

    def unregister_energy_type(self, energy_type: EnergyType) -> 'PlayerState':
        """Unregister an energy type."""
        if energy_type not in self.registered_energy_types:
            return self
        new_types = [et for et in self.registered_energy_types if et != energy_type]
        return dataclasses.replace(self, registered_energy_types=new_types)


@dataclass(frozen=False)  # Change from frozen=True
class GameState:
    """Represents the complete state of the game."""
    
    player: PlayerState
    opponent: PlayerState
    active_player: PlayerTag = PlayerTag.PLAYER
    phase: GamePhase = GamePhase.START_OF_TURN  # Fixed: Start with START_OF_TURN phase
    turn_number: int = 1
    is_finished: bool = False
    winner: Optional[PlayerTag] = None
    is_first_turn: bool = True
    
    @property
    def active_player_state(self) -> PlayerState:
        """Get the state of the currently active player."""
        return self.player if self.active_player == PlayerTag.PLAYER else self.opponent
        
    @property
    def inactive_player_state(self) -> PlayerState:
        """Get the state of the currently inactive player."""
        return self.opponent if self.active_player == PlayerTag.PLAYER else self.player

    def get_player_state(self, player_tag: PlayerTag) -> PlayerState:
        """Get the state for a specific player tag."""
        if player_tag == PlayerTag.PLAYER:
            return self.player
        return self.opponent

    def advance_phase(self) -> 'GameState':
        """Advance the game to the next phase or turn."""
        if self.phase == GamePhase.START_OF_TURN:
            return dataclasses.replace(self, phase=GamePhase.DRAW)
        elif self.phase == GamePhase.DRAW:
            return dataclasses.replace(self, phase=GamePhase.MAIN)
        elif self.phase == GamePhase.MAIN:
            return dataclasses.replace(self, phase=GamePhase.ATTACK)
        elif self.phase == GamePhase.ATTACK:
            return dataclasses.replace(self, phase=GamePhase.END)
        elif self.phase == GamePhase.END:
            # End of turn, switch active player
            new_active_player = PlayerTag.OPPONENT if self.active_player == PlayerTag.PLAYER else PlayerTag.PLAYER
            return dataclasses.replace(
                self,
                phase=GamePhase.START_OF_TURN,
                active_player=new_active_player,
                turn_number=self.turn_number + 1,
                is_first_turn=False  # No longer the first turn after it passes
            )
        return self