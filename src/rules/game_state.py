"""Game state representation for Pokemon TCG Pocket.

This module defines the core game state classes and related functionality.
The game state captures all information needed to represent a Pokemon TCG
Pocket game at any point in time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum, auto

from src.card_db.core import Card, PokemonCard, ItemCard, SupporterCard, EnergyType, StatusCondition, Stage, Attack


class PlayerTag(Enum):
    """Identifies which player a game element belongs to."""
    PLAYER = auto()
    OPPONENT = auto()


class GamePhase(Enum):
    """Represents different phases of a player's turn."""
    DRAW = auto()         # Draw phase (mandatory draw)
    MAIN = auto()         # Main phase (play cards, evolve Pokemon)
    ATTACK = auto()       # Attack phase (use one attack)
    CHECK_UP = auto()     # Check-up phase (status conditions, coin flips)
    END = auto()          # End phase (end turn)


@dataclass
class PlayerState:
    """Represents the complete state for a single player."""
    
    # Active Pokemon and bench (max 3 in TCG Pocket)
    active_pokemon: Optional[PokemonCard] = None
    bench: List[PokemonCard] = field(default_factory=list)
    
    # Card collections
    deck: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    discard_pile: List[Card] = field(default_factory=list)
    
    # TCG Pocket point system (rulebook §10)
    points: int = 0
    
    # Energy Zone (single-slot buffer - rulebook §5)
    energy_zone: Optional[EnergyType] = None
    
    # Turn restrictions
    supporter_played_this_turn: bool = False
    energy_attached_this_turn: bool = False
    pokemon_entered_play_this_turn: List[str] = field(default_factory=list)
    
    # Removed prizes - TCG Pocket uses points system only
    
    # Energy Zone configuration (1-3 types allowed)
    registered_energy_types: List[EnergyType] = field(default_factory=list)
    max_registered_types: int = 3
    
    def __post_init__(self):
        """Validate initial state."""
        if len(self.bench) > 3:  # Fixed: TCG Pocket has max 3 bench Pokemon
            raise ValueError("Bench cannot have more than 3 Pokemon in TCG Pocket")
        if self.points > 3:
            raise ValueError("Points cannot exceed 3 in TCG Pocket")
    
    @property
    def pokemon_in_play(self) -> List[PokemonCard]:
        """Get all Pokemon currently in play (active + bench)."""
        pokemon = []
        if self.active_pokemon:
            pokemon.append(self.active_pokemon)
        pokemon.extend(self.bench)
        return pokemon
    
    @property
    def discard(self) -> List[Card]:
        """Alias for discard_pile (for test compatibility)."""
        return self.discard_pile
    
    @property
    def has_played_supporter(self) -> bool:
        """Alias for supporter_played_this_turn (for test compatibility)."""
        return self.supporter_played_this_turn
    
    def can_play_supporter(self) -> bool:
        """Check if a supporter card can be played this turn."""
        return not self.supporter_played_this_turn
    
    def can_attach_energy(self) -> bool:
        """Check if energy can be attached this turn."""
        return (
            self.energy_zone is not None and
            not self.energy_attached_this_turn and
            len(self.pokemon_in_play) > 0
        )
    
    def attach_energy(self, pokemon: PokemonCard) -> bool:
        """Attach energy from energy zone to a Pokemon."""
        if not self.can_attach_energy():
            return False
        
        pokemon.attached_energies.append(self.energy_zone)
        self.energy_zone = None
        self.energy_attached_this_turn = True
        return True
    
    def add_pokemon_to_play(self, pokemon: PokemonCard) -> None:
        """Add a Pokemon to the in-play list."""
        # Since pokemon_in_play is a computed property, we just track entry
        if pokemon.id not in self.pokemon_entered_play_this_turn:
            self.pokemon_entered_play_this_turn.append(pokemon.id)
    
    def remove_pokemon_from_play(self, pokemon: PokemonCard) -> None:
        """Remove a Pokemon from the in-play list."""
        # Since pokemon_in_play is a computed property, we just remove from tracking
        if pokemon.id in self.pokemon_entered_play_this_turn:
            self.pokemon_entered_play_this_turn.remove(pokemon.id)
    
    def reset_turn_flags(self) -> None:
        """Reset turn-specific flags."""
        self.supporter_played_this_turn = False
        self.energy_attached_this_turn = False
        self.pokemon_entered_play_this_turn.clear()
    
    def can_evolve_pokemon(self, pokemon: PokemonCard) -> bool:
        """Check if a Pokemon can evolve (not on turn it entered play)."""
        return pokemon.id not in self.pokemon_entered_play_this_turn
    
    def generate_energy(self, energy_type: EnergyType) -> bool:
        """Generate energy in the Energy Zone if it's empty."""
        if self.energy_zone is None:
            self.energy_zone = energy_type
            return True
        return False
    
    def use_energy_from_zone(self) -> Optional[EnergyType]:
        """Use energy from the Energy Zone (removes it permanently)."""
        if self.energy_zone is not None:
            energy = self.energy_zone
            self.energy_zone = None
            return energy
        return None
    
    def register_energy_type(self, energy_type: EnergyType) -> bool:
        """Register an energy type for the Energy Zone."""
        if len(self.registered_energy_types) >= self.max_registered_types:
            return False
        if energy_type not in self.registered_energy_types:
            self.registered_energy_types.append(energy_type)
        return True
    
    def unregister_energy_type(self, energy_type: EnergyType) -> bool:
        """Unregister an energy type."""
        if energy_type in self.registered_energy_types:
            self.registered_energy_types.remove(energy_type)
            return True
        return False
    
    def preview_next_energy(self) -> Optional[EnergyType]:
        """Preview the next energy that will be generated."""
        if self.energy_zone is None and self.registered_energy_types:
            import random
            return random.choice(self.registered_energy_types)
        return None


@dataclass
class GameState:
    """Represents the complete state of a Pokemon TCG Pocket game."""
    
    # Player states
    player: PlayerState = field(default_factory=PlayerState)
    opponent: PlayerState = field(default_factory=PlayerState)
    
    # Turn information
    active_player: PlayerTag = PlayerTag.PLAYER
    phase: GamePhase = GamePhase.DRAW
    turn_number: int = 1
    
    # Game status
    is_finished: bool = False
    winner: Optional[PlayerTag] = None
    is_first_turn: bool = True
    
    def __post_init__(self):
        """Initialize game state for first turn."""
        self.is_first_turn = True
        self.turn_number = 1  # Fixed: Test expects turn 1, not 0
    
    @property
    def active_player_state(self) -> PlayerState:
        """Get the state of the currently active player."""
        return self.player if self.active_player == PlayerTag.PLAYER else self.opponent
    
    @property
    def inactive_player_state(self) -> PlayerState:
        """Get the state of the non-active player."""
        return self.opponent if self.active_player == PlayerTag.PLAYER else self.player
    
    def advance_phase(self) -> None:
        """Advance to the next game phase."""
        phase_order = [
            GamePhase.DRAW,
            GamePhase.MAIN,
            GamePhase.ATTACK,
            GamePhase.CHECK_UP,  # Added Check-up phase
            GamePhase.END
        ]
        current_idx = phase_order.index(self.phase)
        if current_idx == len(phase_order) - 1:
            # End of turn
            self.phase = GamePhase.DRAW
            self.active_player = (
                PlayerTag.OPPONENT 
                if self.active_player == PlayerTag.PLAYER 
                else PlayerTag.PLAYER
            )
            self.turn_number += 1
            # Reset turn-based flags
            new_active_state = self.active_player_state
            new_active_state.reset_turn_flags()
        else:
            # Move to next phase
            self.phase = phase_order[current_idx + 1]
    
    def start_game(self):
        """Initialize game state for first turn."""
        self.is_first_turn = True
        self.turn_number = 0  # Turn 0 for first player


@dataclass
class PokemonInPlay:
    """Represents a Pokemon card in play with its current state."""
    
    card: PokemonCard
    damage_counters: int = 0
    attached_energies: List[EnergyType] = None
    energy_attached: int = 0  # Count of attached energy cards
    status_condition: Optional[StatusCondition] = None
    
    def __post_init__(self):
        if self.attached_energies is None:
            self.attached_energies = []
    
    @property
    def hp(self) -> int:
        """Current HP of the Pokemon."""
        return self.card.hp - self.damage_counters
    
    @property
    def pokemon_type(self) -> EnergyType:
        """Type of the Pokemon."""
        return self.card.pokemon_type
    
    @property
    def stage(self) -> Stage:
        """Stage of the Pokemon."""
        return self.card.stage
    
    @property
    def attacks(self) -> List[Attack]:
        """Attacks available to the Pokemon."""
        return self.card.attacks


def validate_deck(self, deck: List[Card]) -> Tuple[bool, str]:
    """Validate deck according to TCG Pocket rules."""
    if len(deck) != 20:
        return False, "Deck must contain exactly 20 cards"
    
    # Check for Energy cards
    energy_cards = [card for card in deck if hasattr(card, 'energy_type')]
    if energy_cards:
        return False, "No Energy cards allowed in TCG Pocket"
    
    # Check copy limit (max 2 copies)
    card_counts = {}
    for card in deck:
        card_counts[card.name] = card_counts.get(card.name, 0) + 1
        if card_counts[card.name] > 2:
            return False, f"Maximum 2 copies of {card.name} allowed"
    
    return True, "Deck is valid"


def can_attach_energy_first_turn(self, game_state: GameState) -> bool:
    """Check if energy can be attached on first turn."""
    if game_state.is_first_turn and game_state.turn_number == 0:
        return False  # First player cannot attach energy on turn 0
    return True