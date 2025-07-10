#!/usr/bin/env python3
"""
Comprehensive composite functions for all TCG Pocket trainer effects.

This module provides composable functions for every unique trainer effect
found in the game, organized by effect type.
"""

from functools import partial
from typing import List, Callable
from .context import EffectContext
from .conditions import *
from .selections import *
from .actions import *
from src.card_db.core import EnergyType

# =============================================================================
# HEALING EFFECTS
# =============================================================================

def heal_20_damage():
    """Heal 20 damage from 1 of your Pokémon."""
    return [
        set_targets_to_player_pokemon,
        player_chooses_target,
        lambda ctx: heal_pokemon(ctx, 20)
    ]

def heal_10_damage_remove_condition():
    """Heal 10 damage and remove a random Special Condition from your Active Pokémon."""
    return [
        lambda ctx: require_active_pokemon(ctx, "player"),
        lambda ctx: set_target_to_active(ctx, "player"),
        lambda ctx: heal_pokemon(ctx, 10),
        lambda ctx: remove_special_condition(ctx)
    ]

def heal_30_damage_remove_all_conditions():
    """Heal 30 damage from 1 of your Pokémon, and it recovers from all Special Conditions."""
    return [
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: heal_pokemon(ctx, 30),
        lambda ctx: remove_all_special_conditions(ctx)
    ]

def heal_50_grass_pokemon() -> List[Callable[[EffectContext], EffectContext]]:
    """Heal 50 damage from a Grass Pokemon."""
    return [
        player_chooses_target,
        partial(require_pokemon_type, pokemon_type=EnergyType.GRASS),
        partial(heal_pokemon, amount=50)
    ]

def heal_60_stage2_pokemon():
    """Heal 60 damage from 1 of your Stage 2 Pokémon."""
    return [
        lambda ctx: require_stage_pokemon(ctx, 2, "player"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: heal_pokemon(ctx, 60)
    ]

def heal_40_water_pokemon():
    """Heal 40 damage from each of your Pokémon that has any {W} Energy attached."""
    return [
        lambda ctx: heal_all_water_pokemon(ctx, 40)
    ]

def heal_all_damage_specific_pokemon():
    """Heal all damage from 1 of your Shiinotic or Tsareena. If you do, discard all Energy from that Pokémon."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Shiinotic", "Tsareena"], "player"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: heal_all_damage(ctx),
        lambda ctx: discard_all_energy(ctx)
    ]

# =============================================================================
# DRAWING EFFECTS
# =============================================================================

def draw_2_cards():
    """Draw 2 cards."""
    return [
        lambda ctx: draw_cards(ctx, 2)
    ]

def shuffle_hand_draw_equal():
    """Each player shuffles the cards in their hand into their deck, then draws that many cards."""
    return [
        lambda ctx: shuffle_hand_into_deck_and_draw(ctx, len(ctx.player.hand)),
        lambda ctx: shuffle_hand_into_deck_and_draw(ctx, len(ctx.opponent.hand), "opponent")
    ]

def opponent_shuffle_hand_draw_3():
    """Your opponent shuffles their hand into their deck and draws 3 cards."""
    return [
        lambda ctx: shuffle_hand_into_deck_and_draw(ctx, 3, "opponent")
    ]

def opponent_shuffle_hand_draw_points():
    """Your opponent shuffles their hand into their deck and draws a card for each of their remaining points needed to win."""
    return [
        lambda ctx: shuffle_hand_into_deck_and_draw(ctx, 3 - ctx.opponent.points, "opponent")
    ]

# =============================================================================
# SEARCHING EFFECTS
# =============================================================================

def look_top_3_cards():
    """Look at the top 3 cards of your deck."""
    return [
        lambda ctx: look_at_top_cards(ctx, 3)
    ]

def look_top_card_shuffle():
    """Look at the top card of your deck. Then, you may shuffle your deck."""
    return [
        lambda ctx: look_at_top_card(ctx),
        lambda ctx: optional_shuffle_deck(ctx)
    ]

def search_basic_pokemon():
    """Put a random Basic Pokémon from your deck into your hand."""
    return [
        lambda ctx: search_deck_for_pokemon(ctx, stage=1)
    ]

def search_specific_basic_pokemon():
    """Put 1 random Glameow, Stunky, or Croagunk from your deck into your hand."""
    return [
        lambda ctx: search_deck_for_pokemon(ctx, ["Glameow", "Stunky", "Croagunk"])
    ]

def search_type_null_silvally():
    """Put 1 random Type: Null or Silvally from your deck into your hand."""
    return [
        lambda ctx: search_deck_for_pokemon(ctx, ["Type: Null", "Silvally"])
    ]

def search_psychic_pokemon():
    """Look at the top card of your deck. If that card is a {P} Pokémon, put it into your hand. If it is not a {P} Pokémon, put it on the bottom of your deck."""
    return [
        lambda ctx: search_deck_for_psychic_pokemon(ctx)
    ]

def search_discard_basic_pokemon():
    """Put 1 random Basic Pokémon from your discard pile into your hand."""
    return [
        lambda ctx: search_discard_for_pokemon(ctx, stage=1)
    ]

def search_discard_water_pokemon():
    """Put a random Basic {W} Pokémon from your discard pile into your hand."""
    return [
        lambda ctx: search_discard_for_water_pokemon(ctx)
    ]

def put_opponent_pokemon_on_bench():
    """Put a Basic Pokémon from your opponent's discard pile onto their Bench."""
    return [
        lambda ctx: put_pokemon_from_opponent_discard_to_bench(ctx)
    ]

# =============================================================================
# SWITCHING EFFECTS
# =============================================================================

def switch_damaged_opponent():
    """Switch in 1 of your opponent's Benched Pokémon that has damage on it to the Active Spot."""
    return [
        lambda ctx: require_bench_pokemon(ctx, "opponent"),
        lambda ctx: require_damaged_pokemon(ctx, "opponent"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: switch_opponent_active(ctx)
    ]

def switch_opponent_chooses():
    """Switch out your opponent's Active Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)"""
    return [
        lambda ctx: require_bench_pokemon(ctx, "opponent"),
        lambda ctx: opponent_chooses_target(ctx, ctx.opponent.bench),
        lambda ctx: switch_opponent_active(ctx)
    ]

def switch_opponent_basic():
    """Switch out your opponent's Active Basic Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)"""
    return [
        lambda ctx: require_active_basic_pokemon(ctx, "opponent"),
        lambda ctx: require_bench_pokemon(ctx, "opponent"),
        lambda ctx: opponent_chooses_target(ctx, ctx.opponent.bench),
        lambda ctx: switch_opponent_active(ctx)
    ]

def reduce_retreat_cost_1():
    """During this turn, the Retreat Cost of your Active Pokémon is 1 less."""
    return [
        lambda ctx: reduce_retreat_cost(ctx, 1)
    ]

def reduce_retreat_cost_2():
    """During this turn, the Retreat Cost of your Active Pokémon is 2 less."""
    return [
        lambda ctx: reduce_retreat_cost(ctx, 2)
    ]

# =============================================================================
# ENERGY MANIPULATION
# =============================================================================

def attach_water_energy_coin_flip():
    """Choose 1 of your {W} Pokémon, and flip a coin until you get tails. For each heads, take a {W} Energy from your Energy Zone and attach it to that Pokémon."""
    return [
        lambda ctx: require_pokemon_type(ctx, EnergyType.WATER, "player"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: attach_energy_from_zone_coin_flip(ctx, EnergyType.WATER)
    ]

def attach_fighting_energy_specific():
    """Take 1 {F} Energy from your Energy Zone and attach it to your Golem or Onix."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Golem", "Onix"], "player"),
        lambda ctx: require_energy_in_zone(ctx, EnergyType.FIGHTING),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: attach_energy_from_zone(ctx, EnergyType.FIGHTING)
    ]

def attach_lightning_energy_from_discard():
    """Choose 1 of your Electivire or Luxray. Attach 2 {L} Energy from your discard pile to that Pokémon."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Electivire", "Luxray"], "player"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: attach_energy_from_discard(ctx, EnergyType.ELECTRIC, 2)
    ]

def move_energy_bench_to_active():
    """Move an Energy from 1 of your Benched Pokémon to your Active Pokémon."""
    return [
        lambda ctx: require_bench_pokemon(ctx, "player"),
        lambda ctx: require_active_pokemon(ctx, "player"),
        lambda ctx: move_energy_from_bench_to_active(ctx)
    ]

def move_all_lightning_energy():
    """Move all {L} Energy from your Benched Pokémon to your Raichu, Electrode, or Electabuzz in the Active Spot."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Raichu", "Electrode", "Electabuzz"], "player"),
        lambda ctx: require_active_pokemon(ctx, "player"),
        lambda ctx: move_all_lightning_energy_to_active(ctx)
    ]

def attach_fire_energy_specific():
    """Choose 1 of your Alolan Marowak or Turtonator. Take 2 {R} Energy from your Energy Zone and attach it to that Pokémon. Your turn ends."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Alolan Marowak", "Turtonator"], "player"),
        lambda ctx: require_energy_in_zone(ctx, EnergyType.FIRE, 2),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: attach_energy_from_zone(ctx, EnergyType.FIRE, 2),
        lambda ctx: end_turn(ctx)
    ]

# =============================================================================
# DAMAGE MODIFICATION
# =============================================================================

def damage_bonus_10():
    """During this turn, attacks used by your Pokémon do +10 damage to your opponent's Active Pokémon."""
    return [
        lambda ctx: damage_bonus_this_turn(ctx, 10)
    ]

def damage_bonus_20_ex():
    """During this turn, attacks used by your Pokémon do +20 damage to your opponent's Active Pokémon ex."""
    return [
        lambda ctx: damage_bonus_this_turn(ctx, 20, target_type="ex")
    ]

def damage_bonus_30_fire():
    """During this turn, attacks used by your Ninetales, Rapidash, or Magmar do +30 damage to your opponent's Active Pokémon."""
    return [
        lambda ctx: damage_bonus_this_turn(ctx, 30, ["Ninetales", "Rapidash", "Magmar"])
    ]

def damage_bonus_30_ex_pokemon():
    """During this turn, attacks used by your Decidueye ex, Incineroar ex, or Primarina ex do +30 damage to your opponent's Active Pokémon."""
    return [
        lambda ctx: damage_bonus_this_turn(ctx, 30, ["Decidueye ex", "Incineroar ex", "Primarina ex"])
    ]

def damage_bonus_30_alolan():
    """During this turn, attacks used by your Alolan Golem, Vikavolt, or Togedemaru do +30 damage to your opponent's Active Pokémon."""
    return [
        lambda ctx: damage_bonus_this_turn(ctx, 30, ["Alolan Golem", "Vikavolt", "Togedemaru"])
    ]

def damage_bonus_50_specific():
    """During this turn, attacks used by your Garchomp or Togekiss do +50 damage to your opponent's Active Pokémon."""
    return [
        lambda ctx: damage_bonus_this_turn(ctx, 50, ["Garchomp", "Togekiss"])
    ]

def reduce_energy_cost():
    """During this turn, attacks used by your Snorlax, Heracross, and Staraptor cost 2 less {C} Energy."""
    return [
        lambda ctx: reduce_energy_cost_this_turn(ctx, 2, ["Snorlax", "Heracross", "Staraptor"])
    ]

def reduce_damage_10():
    """During your opponent's next turn, all of your Pokémon take −10 damage from attacks from your opponent's Pokémon."""
    return [
        lambda ctx: reduce_damage_next_turn(ctx, 10)
    ]

def reduce_damage_20_metal():
    """During your opponent's next turn, all of your {M} Pokémon take −20 damage from attacks from your opponent's Pokémon."""
    return [
        lambda ctx: reduce_damage_next_turn(ctx, 20, EnergyType.METAL)
    ]

def reduce_damage_20_ultra_beasts():
    """During your opponent's next turn, all of your Ultra Beasts take −20 damage from attacks from your opponent's Pokémon."""
    return [
        lambda ctx: reduce_damage_next_turn(ctx, 20, pokemon_type="ultra_beast")
    ]

# =============================================================================
# HAND DISRUPTION
# =============================================================================

def reveal_opponent_hand():
    """Your opponent reveals their hand."""
    return [
        lambda ctx: reveal_hand(ctx, "opponent")
    ]

def reveal_all_supporter_cards():
    """Your opponent reveals all of the Supporter cards in their deck."""
    return [
        lambda ctx: reveal_supporter_cards_in_deck(ctx, "opponent")
    ]

def look_random_supporter():
    """Look at a random Supporter card that's not Penny from your opponent's deck and shuffle it back into their deck. Use the effect of that card as the effect of this card."""
    return [
        lambda ctx: look_random_supporter_and_use_effect(ctx)
    ]

def coin_flip_discard_energy():
    """Flip a coin until you get tails. For each heads, discard a random Energy from your opponent's Active Pokémon."""
    return [
        lambda ctx: require_active_pokemon(ctx, "opponent"),
        lambda ctx: coin_flip_repeat(ctx, lambda c: discard_random_energy(c, "opponent"))
    ]

# =============================================================================
# POKEMON MANIPULATION
# =============================================================================

def return_to_hand_specific():
    """Put 1 of your {C} Pokémon that has damage on it into your hand."""
    return [
        lambda ctx: require_pokemon_type(ctx, EnergyType.COLORLESS, "player"),
        lambda ctx: require_damaged_pokemon(ctx, "player"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: return_to_hand(ctx, "player")
    ]

def return_mew_ex_to_hand():
    """Put your Mew ex in the Active Spot into your hand."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Mew ex"], "player"),
        lambda ctx: require_active_pokemon(ctx, "player"),
        lambda ctx: set_target_to_active(ctx, "player"),
        lambda ctx: return_to_hand(ctx, "player")
    ]

def return_muk_weezing_to_hand():
    """Put your Muk or Weezing in the Active Spot into your hand."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Muk", "Weezing"], "player"),
        lambda ctx: require_active_pokemon(ctx, "player"),
        lambda ctx: set_target_to_active(ctx, "player"),
        lambda ctx: return_to_hand(ctx, "player")
    ]

def move_damage_to_opponent():
    """Choose 1 of your Palossand or Mimikyu that has damage on it, and move 40 of its damage to your opponent's Active Pokémon."""
    return [
        lambda ctx: require_specific_pokemon(ctx, ["Palossand", "Mimikyu"], "player"),
        lambda ctx: require_damaged_pokemon(ctx, "player"),
        lambda ctx: require_active_pokemon(ctx, "opponent"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: move_damage_to_opponent(ctx, 40)
    ]

def switch_pokemon_in_hand():
    """Choose a Pokémon in your hand and switch it with a random Pokémon in your deck."""
    return [
        lambda ctx: require_pokemon_in_hand(ctx),
        lambda ctx: switch_pokemon_with_deck(ctx)
    ]

# =============================================================================
# EVOLUTION EFFECTS
# =============================================================================

def evolve_skip_stage1():
    """Choose 1 of your Basic Pokémon in play. If you have a Stage 2 card in your hand that evolves from that Pokémon, put that card onto the Basic Pokémon to evolve it, skipping the Stage 1. You can't use this card during your first turn or on a Basic Pokémon that was put into play this turn."""
    return [
        lambda ctx: require_not_first_turn(ctx),
        lambda ctx: require_basic_pokemon_in_play(ctx),
        lambda ctx: require_stage2_in_hand(ctx),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: evolve_skip_stage1(ctx)
    ]

# =============================================================================
# TOOL EFFECTS
# =============================================================================

def discard_all_tools():
    """Discard all Pokémon Tool cards attached to each of your opponent's Pokémon."""
    return [
        lambda ctx: discard_all_tools_from_opponent(ctx)
    ]

def tool_heal_10_active():
    """At the end of your turn, if the Pokémon this card is attached to is in the Active Spot, heal 10 damage from that Pokémon."""
    return [
        lambda ctx: tool_heal_at_end_of_turn(ctx, 10)
    ]

def tool_remove_conditions():
    """At the end of each turn, if the Pokémon this card is attached to is affected by any Special Conditions, it recovers from all of them, and discard this card."""
    return [
        lambda ctx: tool_remove_conditions_at_end_of_turn(ctx)
    ]

def tool_damage_bonus_ultra_beast():
    """Attacks used by the Ultra Beast this card is attached to do +10 damage to your opponent's Active Pokémon for each point you have gotten."""
    return [
        lambda ctx: tool_damage_bonus_per_point(ctx, 10)
    ]

def tool_poison_attacker():
    """If the Pokémon this card is attached to is your Active Pokémon and is damaged by an attack from your opponent's Pokémon, the Attacking Pokémon is now Poisoned."""
    return [
        lambda ctx: tool_poison_attacker_when_damaged(ctx)
    ]

def tool_damage_attacker():
    """If the Pokémon this card is attached to is in the Active Spot and is damaged by an attack from your opponent's Pokémon, do 20 damage to the Attacking Pokémon."""
    return [
        lambda ctx: tool_damage_attacker_when_damaged(ctx, 20)
    ]

def tool_move_energy_when_ko():
    """If the {L} Pokémon this card is attached to is in the Active Spot and is Knocked Out by damage from an attack from your opponent's Pokémon, move 2 {L} Energy from that Pokémon and attach 1 Energy each to 2 of your Benched Pokémon."""
    return [
        lambda ctx: tool_move_energy_when_ko(ctx, EnergyType.ELECTRIC, 2)
    ]

def tool_plus_20_hp():
    """The Pokémon this card is attached to gets +20 HP."""
    return [
        lambda ctx: tool_add_hp(ctx, 20)
    ]

def tool_plus_30_hp_grass():
    """The {G} Pokémon this card is attached to gets +30 HP."""
    return [
        lambda ctx: tool_add_hp(ctx, 30, EnergyType.GRASS)
    ]

# =============================================================================
# FOSSIL CARDS
# =============================================================================

def play_as_basic_pokemon():
    """Play this card as if it were a 40-HP Basic {C} Pokémon. At any time during your turn, you may discard this card from play. This card can't retreat."""
    return [
        lambda ctx: play_fossil_as_pokemon(ctx, 40, EnergyType.COLORLESS)
    ]

# =============================================================================
# CONDITIONAL EFFECTS
# =============================================================================

def conditional_ultra_beast_energy():
    """You can use this card only if your opponent has gotten at least 1 point. Choose 1 of your Ultra Beasts. Attach 2 random Energy from your discard pile to that Pokémon."""
    return [
        lambda ctx: require_opponent_has_points(ctx, 1),
        lambda ctx: require_ultra_beast(ctx, "player"),
        lambda ctx: player_chooses_target(ctx),
        lambda ctx: attach_random_energy_from_discard(ctx, 2)
    ]

def conditional_ultra_beast_protection():
    """You can use this card only if your opponent hasn't gotten any points. During your opponent's next turn, all of your Ultra Beasts take −20 damage from attacks from your opponent's Pokémon."""
    return [
        lambda ctx: require_opponent_no_points(ctx),
        lambda ctx: reduce_damage_next_turn(ctx, 20, pokemon_type="ultra_beast")
    ]

def conditional_araquanid_switch():
    """You can use this card only if you have Araquanid in play. Switch in 1 of your opponent's Benched Pokémon to the Active Spot."""
    return [
        lambda ctx: require_specific_pokemon_in_play(ctx, ["Araquanid"], "player"),
        lambda ctx: require_bench_pokemon(ctx, "opponent"),
        lambda ctx: player_chooses_target(ctx, ctx.opponent.bench),
        lambda ctx: switch_opponent_active(ctx)
    ]

def conditional_eevee_choice():
    """Choose 1: During this turn, attacks used by your Pokémon that evolve from Eevee do +10 damage to your opponent's Active Pokémon. Heal 20 damage from each of your Pokémon that evolves from Eevee."""
    return [
        lambda ctx: player_chooses_eevee_effect(ctx)
    ] 