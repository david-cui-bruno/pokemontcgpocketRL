#!/usr/bin/env python3
"""
Comprehensive trainer registry mapping all trainer effects to their functions.

This registry covers every unique trainer effect found in TCG Pocket.
"""

from src.card_db.trainer_effects.composites import *

# Load all trainer effects
import json
from pathlib import Path

def load_trainer_effects():
    """Load all trainer effects from the JSON file."""
    effects_file = Path("data/trainer_effects.json")
    if effects_file.exists():
        with open(effects_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Get all effects
ALL_EFFECTS = load_trainer_effects()

# Comprehensive registry mapping effect text to functions
COMPREHENSIVE_TRAINER_EFFECTS = {
    # Healing effects
    "Heal 20 damage from 1 of your Pokémon.": heal_20_damage(),
    "Heal 10 damage and remove a random Special Condition from your Active Pokémon.": heal_10_damage_remove_condition(),
    "Heal 30 damage from 1 of your Pokémon, and it recovers from all Special Conditions.": heal_30_damage_remove_all_conditions(),
    "Heal 50 damage from 1 of your {G} Pokémon.": heal_50_grass_pokemon(),
    "Heal 60 damage from 1 of your Stage 2 Pokémon.": heal_60_stage2_pokemon(),
    "Heal 40 damage from each of your Pokémon that has any {W} Energy attached.": heal_40_water_pokemon(),
    "Heal all damage from 1 of your Shiinotic or Tsareena. If you do, discard all Energy from that Pokémon.": heal_all_damage_specific_pokemon(),
    
    # Drawing effects
    "Draw 2 cards.": draw_2_cards(),
    "Each player shuffles the cards in their hand into their deck, then draws that many cards.": shuffle_hand_draw_equal(),
    "Your opponent shuffles their hand into their deck and draws 3 cards.": opponent_shuffle_hand_draw_3(),
    "Your opponent shuffles their hand into their deck and draws a card for each of their remaining points needed to win.": opponent_shuffle_hand_draw_points(),
    
    # Searching effects
    "Look at the top 3 cards of your deck.": look_top_3_cards(),
    "Look at the top card of your deck. Then, you may shuffle your deck.": look_top_card_shuffle(),
    "Put a random Basic Pokémon from your deck into your hand.": search_basic_pokemon(),
    "Put 1 random Glameow, Stunky, or Croagunk from your deck into your hand.": search_specific_basic_pokemon(),
    "Put 1 random Type: Null or Silvally from your deck into your hand.": search_type_null_silvally(),
    "Look at the top card of your deck. If that card is a {P} Pokémon, put it into your hand. If it is not a {P} Pokémon, put it on the bottom of your deck.": search_psychic_pokemon(),
    "Put 1 random Basic Pokémon from your discard pile into your hand.": search_discard_basic_pokemon(),
    "Put a random Basic {W} Pokémon from your discard pile into your hand.": search_discard_water_pokemon(),
    "Put a Basic Pokémon from your opponent's discard pile onto their Bench.": put_opponent_pokemon_on_bench(),
    
    # Switching effects
    "Switch in 1 of your opponent's Benched Pokémon that has damage on it to the Active Spot.": switch_damaged_opponent(),
    "Switch out your opponent's Active Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)": switch_opponent_chooses(),
    "Switch out your opponent's Active Basic Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)": switch_opponent_basic(),
    "During this turn, the Retreat Cost of your Active Pokémon is 1 less.": reduce_retreat_cost_1(),
    "During this turn, the Retreat Cost of your Active Pokémon is 2 less.": reduce_retreat_cost_2(),
    
    # Energy manipulation
    "Choose 1 of your {W} Pokémon, and flip a coin until you get tails. For each heads, take a {W} Energy from your Energy Zone and attach it to that Pokémon.": attach_water_energy_coin_flip(),
    "Take 1 {F} Energy from your Energy Zone and attach it to your Golem or Onix.": attach_fighting_energy_specific(),
    "Choose 1 of your Electivire or Luxray. Attach 2 {L} Energy from your discard pile to that Pokémon.": attach_lightning_energy_from_discard(),
    "Move an Energy from 1 of your Benched Pokémon to your Active Pokémon.": move_energy_bench_to_active(),
    "Move all {L} Energy from your Benched Pokémon to your Raichu, Electrode, or Electabuzz in the Active Spot.": move_all_lightning_energy(),
    "Choose 1 of your Alolan Marowak or Turtonator. Take 2 {R} Energy from your Energy Zone and attach it to that Pokémon. Your turn ends.": attach_fire_energy_specific(),
    
    # Damage modification
    "During this turn, attacks used by your Pokémon do +10 damage to your opponent's Active Pokémon.": damage_bonus_10(),
    "During this turn, attacks used by your Pokémon do +20 damage to your opponent's Active Pokémon ex.": damage_bonus_20_ex(),
    "During this turn, attacks used by your Ninetales, Rapidash, or Magmar do +30 damage to your opponent's Active Pokémon.": damage_bonus_30_fire(),
    "During this turn, attacks used by your Decidueye ex, Incineroar ex, or Primarina ex do +30 damage to your opponent's Active Pokémon.": damage_bonus_30_ex_pokemon(),
    "During this turn, attacks used by your Alolan Golem, Vikavolt, or Togedemaru do +30 damage to your opponent's Active Pokémon.": damage_bonus_30_alolan(),
    "During this turn, attacks used by your Garchomp or Togekiss do +50 damage to your opponent's Active Pokémon.": damage_bonus_50_specific(),
    "During this turn, attacks used by your Snorlax, Heracross, and Staraptor cost 2 less {C} Energy.": reduce_energy_cost(),
    "During your opponent's next turn, all of your Pokémon take −10 damage from attacks from your opponent's Pokémon.": reduce_damage_10(),
    "During your opponent's next turn, all of your {M} Pokémon take −20 damage from attacks from your opponent's Pokémon.": reduce_damage_20_metal(),
    "During your opponent's next turn, all of your Ultra Beasts take −20 damage from attacks from your opponent's Pokémon.": reduce_damage_20_ultra_beasts(),
    
    # Hand disruption
    "Your opponent reveals their hand.": reveal_opponent_hand(),
    "Your opponent reveals all of the Supporter cards in their deck.": reveal_all_supporter_cards(),
    "Look at a random Supporter card that's not Penny from your opponent's deck and shuffle it back into their deck. Use the effect of that card as the effect of this card.": look_random_supporter(),
    "Flip a coin until you get tails. For each heads, discard a random Energy from your opponent's Active Pokémon.": coin_flip_discard_energy(),
    
    # Pokemon manipulation
    "Put 1 of your {C} Pokémon that has damage on it into your hand.": return_to_hand_specific(),
    "Put your Mew ex in the Active Spot into your hand.": return_mew_ex_to_hand(),
    "Put your Muk or Weezing in the Active Spot into your hand.": return_muk_weezing_to_hand(),
    "Choose 1 of your Palossand or Mimikyu that has damage on it, and move 40 of its damage to your opponent's Active Pokémon.": move_damage_to_opponent(),
    "Choose a Pokémon in your hand and switch it with a random Pokémon in your deck.": switch_pokemon_in_hand(),
    
    # Evolution effects
    "Choose 1 of your Basic Pokémon in play. If you have a Stage 2 card in your hand that evolves from that Pokémon, put that card onto the Basic Pokémon to evolve it, skipping the Stage 1. You can't use this card during your first turn or on a Basic Pokémon that was put into play this turn.": evolve_skip_stage1(),
    
    # Tool effects
    "Discard all Pokémon Tool cards attached to each of your opponent's Pokémon.": discard_all_tools(),
    "At the end of your turn, if the Pokémon this card is attached to is in the Active Spot, heal 10 damage from that Pokémon.": tool_heal_10_active(),
    "At the end of each turn, if the Pokémon this card is attached to is affected by any Special Conditions, it recovers from all of them, and discard this card.": tool_remove_conditions(),
    "Attacks used by the Ultra Beast this card is attached to do +10 damage to your opponent's Active Pokémon for each point you have gotten.": tool_damage_bonus_ultra_beast(),
    "If the Pokémon this card is attached to is your Active Pokémon and is damaged by an attack from your opponent's Pokémon, the Attacking Pokémon is now Poisoned.": tool_poison_attacker(),
    "If the Pokémon this card is attached to is in the Active Spot and is damaged by an attack from your opponent's Pokémon, do 20 damage to the Attacking Pokémon.": tool_damage_attacker(),
    "If the {L} Pokémon this card is attached to is in the Active Spot and is Knocked Out by damage from an attack from your opponent's Pokémon, move 2 {L} Energy from that Pokémon and attach 1 Energy each to 2 of your Benched Pokémon.": tool_move_energy_when_ko(),
    "The Pokémon this card is attached to gets +20 HP.": tool_plus_20_hp(),
    "The {G} Pokémon this card is attached to gets +30 HP.": tool_plus_30_hp_grass(),
    
    # Fossil cards
    "Play this card as if it were a 40-HP Basic {C} Pokémon. At any time during your turn, you may discard this card from play. This card can't retreat.": play_as_basic_pokemon(),
    "Play this card as if it were a 40-HP Basic {C} Pokémon.\nAt any time during your turn, you may discard this card from play.\nThis card can't retreat.": play_as_basic_pokemon(),
    
    # Conditional effects
    "You can use this card only if your opponent has gotten at least 1 point.\n\nChoose 1 of your Ultra Beasts. Attach 2 random Energy from your discard pile to that Pokémon.": conditional_ultra_beast_energy(),
    "You can use this card only if your opponent hasn't gotten any points.\n\nDuring your opponent's next turn, all of your Ultra Beasts take −20 damage from attacks from your opponent's Pokémon.": conditional_ultra_beast_protection(),
    "You can use this card only if you have Araquanid in play. Switch in 1 of your opponent's Benched Pokémon to the Active Spot.": conditional_araquanid_switch(),
    "Choose 1:\n\nDuring this turn, attacks used by your Pokémon that evolve from Eevee do +10 damage to your opponent's Active Pokémon.\n\nHeal 20 damage from each of your Pokémon that evolves from Eevee.": conditional_eevee_choice(),
}

# Card name to effect text mapping for specific trainer cards
CARD_NAME_TO_EFFECT = {
    "Erika": "Heal 50 damage from 1 of your {G} Pokémon.",
    "Sabrina": "Switch out your opponent's Active Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)",
    "Cyrus": "Switch in 1 of your opponent's Benched Pokémon that has damage on it to the Active Spot.",
    "Misty": "Choose 1 of your {W} Pokémon, and flip a coin until you get tails. For each heads, take a {W} Energy from your Energy Zone and attach it to that Pokémon.",
    "Giovanni": "During this turn, attacks used by your Pokémon do +10 damage to your opponent's Active Pokémon.",
    "Blaine": "During this turn, attacks used by your Ninetales, Rapidash, or Magmar do +30 damage to your opponent's Active Pokémon.",
    "Koga": "Put your Muk or Weezing in the Active Spot into your hand.",
    "Potion": "Heal 20 damage from 1 of your Pokémon.",
}

# Export the registry as TRAINER_EFFECTS for compatibility
TRAINER_EFFECTS = COMPREHENSIVE_TRAINER_EFFECTS

def get_trainer_effect_function(effect_text: str):
    """Get the function for a trainer effect by its text."""
    return COMPREHENSIVE_TRAINER_EFFECTS.get(effect_text)

def get_effect_for_card(card_name: str):
    """Get the effect text for a specific card name."""
    return CARD_NAME_TO_EFFECT.get(card_name)

def get_all_covered_effects():
    """Get all effects that are covered by the registry."""
    return list(COMPREHENSIVE_TRAINER_EFFECTS.keys())

def get_missing_effects():
    """Get effects that are not covered by the registry."""
    covered = set(COMPREHENSIVE_TRAINER_EFFECTS.keys())
    all_effects = set(ALL_EFFECTS)
    return all_effects - covered

def print_coverage_stats():
    """Print statistics about effect coverage."""
    covered = len(COMPREHENSIVE_TRAINER_EFFECTS)
    total = len(ALL_EFFECTS)
    missing = len(get_missing_effects())
    
    print(f"📊 Trainer Effect Coverage:")
    print(f"   Total effects: {total}")
    print(f"   Covered effects: {covered}")
    print(f"   Missing effects: {missing}")
    print(f"   Coverage: {covered/total*100:.1f}%")
    
    if missing > 0:
        print(f"\n❌ Missing effects:")
        for effect in get_missing_effects():
            print(f"   - {effect}")

if __name__ == "__main__":
    print("🎴 Comprehensive Trainer Effect Registry")
    print("=" * 60)
    
    print_coverage_stats() 