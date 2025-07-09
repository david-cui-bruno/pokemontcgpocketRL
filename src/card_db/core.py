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

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


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


class Stage(Enum):
    """Pokemon evolution stages."""
    
    BASIC = "basic"
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"


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
    """Represents a card effect with structured parameters.
    
    Effects are the core building blocks of card abilities, attacks, and
    triggered effects. They use a simple DSL to describe game state mutations.
    
    Parameters
    ----------
    effect_type : str
        The type of effect (e.g., "damage", "heal", "draw_cards", "search")
    amount : int, optional
        Numeric parameter for the effect
    target : TargetType, optional
        What the effect targets
    conditions : List[str], optional
        Conditions that must be met for the effect to apply
    parameters : Dict[str, Any], optional
        Additional effect-specific parameters
        
    Examples
    --------
    >>> damage_effect = Effect(
    ...     effect_type="damage",
    ...     amount=30,
    ...     target=TargetType.OPPONENT_ACTIVE
    ... )
    >>> heal_effect = Effect(
    ...     effect_type="heal", 
    ...     amount=20,
    ...     target=TargetType.SELF
    ... )
    """
    
    effect_type: str
    amount: Optional[int] = None
    target: Optional[TargetType] = None
    conditions: List[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.conditions is None:
            object.__setattr__(self, 'conditions', [])
        if self.parameters is None:
            object.__setattr__(self, 'parameters', {})


@dataclass(frozen=True)
class Attack:
    """Represents a Pokemon attack.
    
    Parameters
    ----------
    name : str
        The attack name
    cost : List[EnergyType]
        Energy cost required to use this attack
    damage : int
        Base damage dealt by this attack
    effects : List[Effect], optional
        Additional effects beyond damage
    description : str, optional
        Human-readable attack description
        
    Examples
    --------
    >>> thunderbolt = Attack(
    ...     name="Thunderbolt",
    ...     cost=[EnergyType.ELECTRIC, EnergyType.ELECTRIC],
    ...     damage=90,
    ...     effects=[Effect("discard_energy", amount=1, target=TargetType.SELF)]
    ... )
    """
    
    name: str
    cost: List[EnergyType]
    damage: int
    effects: List[Effect] = None
    description: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.effects is None:
            object.__setattr__(self, 'effects', [])


@dataclass(frozen=True)
class Ability:
    """Represents a Pokemon ability.
    
    Parameters
    ----------
    name : str
        The ability name
    ability_type : AbilityType
        Type of ability (static, activated, triggered)
    effects : List[Effect]
        The effects this ability provides
    cost : List[EnergyType], optional
        Energy cost for activated abilities
    usage_limit : str, optional
        Usage restrictions ("once_per_turn", "once_per_game", etc.)
    trigger : str, optional
        What triggers this ability (for triggered abilities)
    description : str, optional
        Human-readable ability description
        
    Examples
    --------
    >>> static_ability = Ability(
    ...     name="Lightning Rod",
    ...     ability_type=AbilityType.STATIC, 
    ...     effects=[Effect("resistance", amount=20, target=TargetType.SELF)],
    ...     description="This Pokemon takes 20 less damage from Water attacks"
    ... )
    """
    
    name: str
    ability_type: AbilityType  # Fixed: Use AbilityType enum instead of string
    effects: List[Effect]
    cost: List[EnergyType] = None
    usage_limit: Optional[str] = None
    trigger: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.cost is None:
            object.__setattr__(self, 'cost', [])


@dataclass
class Card:
    """Base class for all cards."""
    id: str
    name: str
    set_code: Optional[str] = None
    rarity: Optional[str] = None


@dataclass
class PokemonCard:
    """Represents a Pokemon card."""
    # Required fields first
    id: str
    name: str
    hp: int
    pokemon_type: EnergyType
    stage: Stage
    
    # Optional fields with defaults
    set_code: Optional[str] = None
    rarity: Optional[str] = None
    evolves_from: Optional[str] = None
    attacks: List[Attack] = None
    ability: Optional[Ability] = None
    retreat_cost: int = 0
    weakness: Optional[EnergyType] = None
    is_ex: bool = False
    attached_energies: List[EnergyType] = None
    damage_counters: int = 0
    energy_attached: int = 0
    status_condition: Optional[StatusCondition] = None
    
    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.attacks is None:
            object.__setattr__(self, 'attacks', [])
        if self.attached_energies is None:
            object.__setattr__(self, 'attached_energies', [])


@dataclass
class ItemCard:
    """Represents an Item card.
    
    Item cards can be played multiple times per turn and have immediate effects.
    Examples: Potion, Switch, Energy Retrieval
    """
    id: str
    name: str
    effects: List[Effect]
    set_code: Optional[str] = None
    rarity: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ToolCard:
    """Represents a Tool card.
    
    Tool cards attach to Pokemon and provide ongoing effects.
    Only 1 Tool can be attached to each Pokemon at a time.
    Examples: Exp. Share, Rocky Helmet, Choice Band
    """
    id: str
    name: str
    effects: List[Effect]
    attached_to: Optional[PokemonCard] = None  # Which Pokemon this tool is attached to
    set_code: Optional[str] = None
    rarity: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SupporterCard:
    """Represents a Supporter card.
    
    Supporter cards can only be played once per turn and have powerful effects.
    Examples: Professor's Research, Marnie, Boss's Orders
    """
    id: str
    name: str
    effects: List[Effect]
    set_code: Optional[str] = None
    rarity: Optional[str] = None
    description: Optional[str] = None


@dataclass
class EnergyCard(Card):
    """Represents an Energy card."""
    energy_type: EnergyType = None  # Give it a default value
    provides: List[EnergyType] = None  # For special energy cards
    
    def __post_init__(self):
        if self.provides is None:
            self.provides = []


# Type aliases for convenience
AnyCard = Union[PokemonCard, ItemCard, ToolCard, SupporterCard]
TrainerCard = Union[ItemCard, ToolCard, SupporterCard]  # New alias for all trainer types 