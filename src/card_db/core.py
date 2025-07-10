"""Core card data structures for Pokemon TCG Pocket.

This module defines the fundamental card types and their behaviors.
All classes use frozen dataclasses to ensure immutability.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from src.rules.constants import EnergyType, Stage, StatusCondition, GameConstants

@dataclass(frozen=True)
class Effect:
    """Represents a card effect."""
    effect_type: str
    text: str
    target: Optional[str] = None
    amount: Optional[int] = None
    conditions: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_coin_flip: bool = False

@dataclass(frozen=True)
class Attack:
    """Represents a Pokemon attack."""
    name: str
    cost: List[EnergyType]  # Energy requirements
    damage: int = 0
    effects: List[Effect] = field(default_factory=list)
    requires_coin_flip: bool = False

    def can_use(self, attached_energies: List[EnergyType]) -> bool:
        """Check if attack can be used with given energies."""
        available = attached_energies.copy()
        
        for required in self.cost:
            if required in available:
                available.remove(required)
            elif EnergyType.COLORLESS in available:
                available.remove(EnergyType.COLORLESS)
            else:
                return False
        return True

@dataclass(frozen=True)
class Ability:
    """Represents a Pokemon ability."""
    name: str
    text: str
    is_passive: bool  # True for always-on effects, False for activated abilities
    effects: List[Effect] = field(default_factory=list)

@dataclass(frozen=True)
class Card:
    """Base class for all cards."""
    id: str  # Set code + number (e.g., "SWSH1-123")
    name: str

    @property
    def points_when_kod(self) -> int:
        """Points awarded when knocked out."""
        return 0  # Base cards award no points

@dataclass(frozen=True)
class PokemonCard(Card):
    """Represents a Pokemon card."""
    pokemon_type: EnergyType
    hp: int
    stage: Stage = Stage.BASIC
    evolves_from: Optional[str] = None  # Name of pre-evolution
    retreat_cost: int = 0
    weakness: Optional[EnergyType] = None  # Only weakness, no resistance in Pocket
    is_ex: bool = False  # ex Pokemon award 2 points when KO'd
    is_tera: bool = False  # Tera Pokemon also award 2 points
    attacks: List[Attack] = field(default_factory=list)
    ability: Optional[Ability] = None
    
    # State tracking (not part of card definition)
    attached_energies: List[EnergyType] = field(default_factory=list)
    damage_counters: int = 0
    status_condition: Optional[StatusCondition] = None
    turns_in_play: int = 0  # Track for evolution restriction
    attached_tool: Optional[ToolCard] = None

    def __post_init__(self):
        """Validate Pokemon card."""
        if not self.pokemon_type:
            raise ValueError("Pokemon must have a type")
        if self.hp <= 0:
            raise ValueError("HP must be greater than 0")
        if self.retreat_cost < 0:
            raise ValueError("Retreat cost cannot be negative")
        if self.stage != Stage.BASIC and not self.evolves_from:
            raise ValueError("Evolution Pokemon must specify evolves_from")

    @property
    def is_knocked_out(self) -> bool:
        """Check if Pokemon is knocked out."""
        return self.damage_counters >= self.hp

    @property
    def points_when_kod(self) -> int:
        """Points awarded when knocked out."""
        return 2 if (self.is_ex or self.is_tera) else 1

    @property
    def can_attack(self) -> bool:
        """Check if Pokemon can attack based on status conditions."""
        return not self.status_condition in [
            StatusCondition.ASLEEP,
            StatusCondition.PARALYZED
        ]

    @property
    def can_retreat(self) -> bool:
        """Check if Pokemon can retreat."""
        return (
            len(self.attached_energies) >= self.retreat_cost and
            not self.status_condition in [
                StatusCondition.ASLEEP,
                StatusCondition.PARALYZED
            ]
        )

    def calculate_damage_taken(self, amount: int, attacker_type: Optional[EnergyType]) -> int:
        """Calculate actual damage taken considering weakness."""
        if attacker_type and self.weakness == attacker_type:
            return amount + GameConstants.WEAKNESS_BONUS
        return amount

@dataclass(frozen=True)
class TrainerCard(Card):
    """Base class for trainer cards."""
    effects: List[Effect]
    text: str  # Card text/description

@dataclass(frozen=True)
class ItemCard(TrainerCard):
    """Item card that can be played any time during Action Phase.
    No limit on number played per turn.
    """
    pass

@dataclass(frozen=True)
class SupporterCard(TrainerCard):
    """Supporter card limited to one per turn."""
    pass

@dataclass(frozen=True)
class ToolCard(TrainerCard):
    """Tool card that attaches to Pokemon.
    Only one tool can be attached to a Pokemon at a time.
    Cannot be moved once attached.
    """
    attached_to: Optional[str] = None  # ID of Pokemon it's attached to

    def can_attach_to(self, pokemon: PokemonCard) -> bool:
        """Check if tool can be attached to Pokemon."""
        return (
            not self.attached_to and  # Tool isn't already attached
            not pokemon.attached_tool  # Pokemon doesn't have a tool
        ) 