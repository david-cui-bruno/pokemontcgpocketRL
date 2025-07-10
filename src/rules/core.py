from dataclasses import dataclass, field
from typing import List, Optional

from src.models.card import Card
from src.models.energy_type import EnergyType
from src.models.stage import Stage
from src.models.attack import Attack
from src.models.ability import Ability
from src.models.player_tag import PlayerTag
from src.models.status_condition import StatusCondition

@dataclass(frozen=False)
class PokemonCard(Card):
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

    def apply_damage(self, amount: int) -> 'PokemonCard':
        return dataclasses.replace(self, damage_counters=self.damage_counters + amount)

    def apply_status(self, condition: StatusCondition) -> 'PokemonCard':
        return dataclasses.replace(self, status_condition=condition)