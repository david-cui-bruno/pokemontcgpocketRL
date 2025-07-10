"""Trainer card effect function library."""

from .context import EffectContext
from .conditions import *
from .selections import *
from .actions import *
from .composites import *

__all__ = [
    'EffectContext',
    # Conditions
    'require_bench_pokemon',
    'require_damaged_pokemon',
    'require_energy_in_zone',
    'require_pokemon_type',
    'require_specific_pokemon',
    'require_active_pokemon',
    'require_pokemon_in_discard',
    # Selections
    'player_chooses_target',
    'opponent_chooses_target',
    'random_target',
    'all_targets',
    'set_target_to_active',
    # Actions
    'switch_opponent_active',
    'return_to_hand',
    'heal_pokemon',
    'attach_energy_from_zone',
    'attach_energy_from_discard',
    'move_energy_between_pokemon',
    'coin_flip_repeat',
    'damage_bonus_this_turn',
    'search_deck_for_pokemon',
    'shuffle_hand_into_deck_and_draw',
    'draw_cards',
    'attach_tool_card',
    # Composites
    'heal_grass_pokemon',
    'switch_damaged_opponent',
    'switch_opponent_chooses',
    'misty_energy_attach',
    'brock_energy_attach',
    'lt_surge_energy_move',
    'koga_return_to_hand',
    'giovanni_damage_bonus',
    'blaine_damage_bonus',
    'cynthia_damage_bonus',
    'team_galactic_grunt_search',
    'mars_hand_disruption',
    'dawn_energy_move',
    'volkner_energy_from_discard',
]
