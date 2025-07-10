"""Game constants and configuration for Pokemon TCG Pocket."""

from enum import Enum, auto
from dataclasses import dataclass

class EnergyType(Enum):
    """Energy types in Pokemon TCG Pocket."""
    GRASS = "grass"
    FIRE = "fire"
    WATER = "water"
    ELECTRIC = "electric"
    PSYCHIC = "psychic"
    FIGHTING = "fighting"
    DARKNESS = "darkness"
    METAL = "metal"
    COLORLESS = "colorless"

class Stage(Enum):
    """Pokemon evolution stages."""
    BASIC = "basic"
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"

class StatusCondition(Enum):
    """Status conditions that can affect Pokemon."""
    ASLEEP = "asleep"    # Can't attack/retreat; flip coin at checkup
    BURNED = "burned"    # 20 damage at checkup, flip coin to cure
    CONFUSED = "confused"  # Flip coin to attack, tails = fail
    PARALYZED = "paralyzed"  # Can't attack/retreat for one turn
    POISONED = "poisoned"  # 10 damage at checkup

class GamePhase(Enum):
    """Game phases in order of execution."""
    START = "start"      # Draw + Energy generation
    ACTION = "action"    # Main phase for playing cards
    ATTACK = "attack"    # Attack phase
    CHECKUP = "checkup"  # Status effects and KO processing

@dataclass(frozen=True)
class GameConstants:
    """Game-wide constants."""
    DECK_SIZE: int = 20
    MAX_BENCH_SIZE: int = 3
    POINTS_TO_WIN: int = 3
    INITIAL_HAND_SIZE: int = 5
    MAX_HAND_SIZE: int = 10
    MAX_ENERGY_TYPES: int = 3
    WEAKNESS_BONUS: int = 20
    POISON_DAMAGE: int = 10
    BURN_DAMAGE: int = 20
    MAX_COPIES_PER_CARD: int = 2

    # Status condition order for checkup phase
    STATUS_RESOLUTION_ORDER = [
        StatusCondition.POISONED,
        StatusCondition.BURNED,
        StatusCondition.ASLEEP,
        StatusCondition.PARALYZED
    ] 