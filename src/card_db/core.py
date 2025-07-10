"""Core card data structures.

This module defines the fundamental immutable dataclasses for all card types,
attacks, abilities, and effects in Pokemon TCG Pocket. All classes are frozen
dataclasses to ensure immutability and type safety.

Examples
--------
>>> pikachu = PokemonCard(
...     id="pikachu_ex_001",
...     name="Pikachu ex", 
...     hp=120,
...     pokemon_type=EnergyType.ELECTRIC,
...     stage=Stage.BASIC,
...     attacks=[Attack(name="Thunderbolt", cost=[EnergyType.ELECTRIC, EnergyType.ELECTRIC], damage=90)],
...     retreat_cost=1,
...     is_ex=True
... )
>>> print(pikachu.name)
Pikachu ex
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from typing import Dict, List, Optional, Tuple, Any, Callable, Union


# --- Enums and Type Definitions FIRST ---

class PlayerTag(Enum):
    """Identifies the player and opponent."""
    PLAYER = auto()
    OPPONENT = auto()


class EnergyType(Enum):
    """Energy types available in Pokemon TCG Pocket."""
    
    GRASS = "grass"
    FIRE = "fire" 
    WATER = "water"
    ELECTRIC = "electric"
    PSYCHIC = "psychic"
    FIGHTING = "fighting"
    DARKNESS = "darkness"
    METAL = "metal"
    COLORLESS = "colorless"
    DRAGON = "dragon"
    FAIRY = "fairy"


class Stage(IntEnum):
    """Pokemon evolution stages."""
    
    BASIC = 0
    STAGE_1 = 1
    STAGE_2 = 2

    @property
    def name(self) -> str:
        return super().name.replace('_', ' ').title()

    @classmethod
    def from_string(cls, stage_str: str) -> 'Stage':
        stage_str = stage_str.upper().replace(' ', '_')
        return cls[stage_str]


class StatusCondition(Enum):
    """Special status conditions."""
    
    ASLEEP = "asleep"
    BURNED = "burned"
    CONFUSED = "confused"
    PARALYZED = "paralyzed"
    POISONED = "poisoned"


class AbilityType(Enum):
    """Types of Pokemon abilities."""
    
    STATIC = "static"          # Always active (passive)
    ACTIVATED = "activated"    # Must be activated by player
    TRIGGERED = "triggered"    # Activates on certain conditions


class TargetType(Enum):
    """Valid targets for attacks and abilities."""
    
    ACTIVE_POKEMON = "active_pokemon"
    BENCHED_POKEMON = "benched_pokemon"
    ANY_POKEMON = "any_pokemon"
    OPPONENT_ACTIVE = "opponent_active"
    OPPONENT_BENCHED = "opponent_benched"
    OPPONENT_ANY = "opponent_any"
    SELF = "self"


@dataclass(frozen=True)
class Effect:
    """Represents a card effect."""
    text: str
    effect_type: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "effect_type": self.effect_type,
            "parameters": self.parameters
        }


@dataclass(frozen=True)
class Attack:
    """Represents a Pokemon attack."""
    name: str
    cost: List[EnergyType]
    damage: int
    effects: List[Effect] = field(default_factory=list)
    description: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert attack to a dictionary for JSON serialization."""
        return {
            "name": self.name,
            "cost": [e.value for e in self.cost],
            "damage": self.damage,
            "effects": [e.to_dict() for e in self.effects],
            "description": self.description
        }


@dataclass(frozen=True)
class Ability:
    """Represents a Pokemon ability."""
    name: str
    ability_type: AbilityType
    effects: List[Effect]
    cost: List[EnergyType] = field(default_factory=list)
    usage_limit: Optional[str] = None
    trigger: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class Card:
    """Base class for all cards. Contains only universally required fields."""
    id: str
    name: str
    
    def to_dict(self) -> dict:
        """Convert card to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name
        }


@dataclass(frozen=True)
class PokemonCard(Card):
    """Represents a Pokemon card."""
    hp: int
    pokemon_type: EnergyType
    stage: Stage
    attacks: List[Attack]
    ability: Optional[Ability] = None
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None
    evolves_from: Optional[str] = None
    retreat_cost: int = 0
    weakness: Optional[EnergyType] = None
    is_ex: bool = False
    attached_energies: List[EnergyType] = field(default_factory=list)
    damage_counters: int = 0
    status_condition: Optional[StatusCondition] = None
    attached_tool: Optional['ToolCard'] = None  # Use string type hint

    def __post_init__(self):
        if self.hp < 0:
            raise ValueError("HP cannot be negative")

    def to_dict(self) -> dict:
        """Convert Pokemon card to a dictionary for JSON serialization."""
        return {
            **super().to_dict(),
            "hp": self.hp,
            "pokemon_type": self.pokemon_type.value,
            "stage": self.stage.value,
            "attacks": [attack.to_dict() for attack in self.attacks],
            "ability": self.ability.to_dict() if self.ability else None,
            "owner": self.owner.value if self.owner else None,
            "set_code": self.set_code,
            "rarity": self.rarity,
            "evolves_from": self.evolves_from,
            "retreat_cost": self.retreat_cost,
            "weakness": self.weakness.value if self.weakness else None,
            "is_ex": self.is_ex,
            "attached_energies": [e.value for e in self.attached_energies],
            "damage_counters": self.damage_counters,
            "status_condition": self.status_condition.value if self.status_condition else None
        }


@dataclass(frozen=True)
class ItemCard(Card):
    """Represents an Item card."""
    effects: List[Effect]
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None
    description: Optional[str] = None
    card_type: str = "Item"  # Add this field
    
    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "effects": [e.to_dict() for e in self.effects],
            "owner": self.owner.value if self.owner else None,
            "set_code": self.set_code,
            "rarity": self.rarity,
            "description": self.description,
            "card_type": self.card_type
        }


@dataclass(frozen=True)
class ToolCard(Card):
    """Represents a Tool card."""
    effects: List[Effect]
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None
    description: Optional[str] = None
    attached_to: Optional['PokemonCard'] = None  # Use string type hint


@dataclass(frozen=True)
class SupporterCard(Card):
    """Represents a Supporter card."""
    effects: List[Effect]
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class EnergyCard(Card):
    """Represents an Energy card."""
    energy_type: EnergyType
    owner: Optional[PlayerTag] = None
    set_code: Optional[str] = None
    rarity: Optional[str] = None
    provides: List[EnergyType] = field(default_factory=list)


# Type aliases for convenience
AnyCard = Union[PokemonCard, ItemCard, ToolCard, SupporterCard, EnergyCard]
TrainerCard = Union[ItemCard, ToolCard, SupporterCard]

# PlayerTag has been moved to the top of the file to resolve circular dependencies. 