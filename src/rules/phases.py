"""Game phase definitions for Pokemon TCG Pocket."""

from enum import Enum, auto

class GamePhase(Enum):
    """Game phases in order of execution."""
    DRAW = "draw"
    START_OF_TURN = "start_of_turn"
    MAIN = "main"
    ATTACK = "attack"
    END_OF_TURN = "end_of_turn"

    @classmethod
    def next_phase(cls, current: 'GamePhase') -> 'GamePhase':
        """Get the next phase in sequence."""
        order = [
            cls.DRAW,
            cls.START_OF_TURN,
            cls.MAIN,
            cls.ATTACK,
            cls.END_OF_TURN
        ]
        current_idx = order.index(current)
        return order[(current_idx + 1) % len(order)]

    @property
    def allows_trainer_cards(self) -> bool:
        """Whether trainer cards can be played in this phase."""
        return self in [self.MAIN]

    @property
    def allows_evolution(self) -> bool:
        """Whether Pokemon can evolve in this phase."""
        return self in [self.MAIN]

    @property
    def allows_energy_attachment(self) -> bool:
        """Whether energy can be attached in this phase."""
        return self in [self.MAIN]
