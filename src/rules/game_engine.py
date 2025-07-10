"""Core game mechanics for Pokemon TCG Pocket.

This module handles the actual game logic including attack resolution,
evolution, retreat, and other core mechanics.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import random
from collections import Counter

from src.card_db.core import (
    PokemonCard, Card, Attack, Effect, EnergyType, Stage, StatusCondition, TargetType, ItemCard, ToolCard, SupporterCard, TrainerCard
)
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.rules.actions import Action, ActionType
# REMOVED: No longer importing trainer_executor at the top level to break the circular dependency.
# from src.card_db.trainer_executor import execute_trainer_card 


class DamageResult(Enum):
    """Possible results of damage calculation."""
    NORMAL = "normal"
    WEAKNESS = "weakness"


class CoinFlipResult(Enum):
    """Results of coin flips."""
    HEADS = "heads"
    TAILS = "tails"


@dataclasses.dataclass
class AttackResult:
    """Result of an attack resolution."""
    damage_dealt: int
    damage_result: DamageResult
    effects_applied: List[Effect]
    target_ko: bool
    attacker_effects: List[Effect]
    energy_discarded: List[EnergyType]
    status_condition_applied: Optional[StatusCondition] = None
    coin_flips: List[CoinFlipResult] = None
    
    @property
    def final_damage(self) -> int:
        """Backward compatibility property for final_damage."""
        return self.damage_dealt


class GameEngine:
    """Handles core game mechanics and rule enforcement."""
    
    def __init__(self):
        self.max_bench_size = 3
        self.max_hand_size = 7
        self.points_to_win = 3
        self.random = random.Random()
    
    def flip_coin(self) -> CoinFlipResult:
        """Flip a coin and return the result."""
        return CoinFlipResult.HEADS if self.random.random() < 0.5 else CoinFlipResult.TAILS
    
    def flip_coins(self, count: int) -> List[CoinFlipResult]:
        """Flip multiple coins and return results."""
        return [self.flip_coin() for _ in range(count)]
    
    def resolve_attack(
        self, 
        attacker: PokemonCard, 
        attack: Attack, 
        target: PokemonCard,
        game_state: GameState
    ) -> AttackResult:
        """Resolve an attack and return the results."""
        # Check if attack can be used
        if not self._can_use_attack(attacker, attack, game_state):
            # Allow attacks with no energy cost even if no energy is attached
            if not (attack.cost == []):
                raise ValueError("Attack cannot be used")
 
        # Pay energy costs
        energy_cost_types = attack.cost
        available_energy = attacker.attached_energies.copy()
        
        for energy_type in energy_cost_types:
            if energy_type in available_energy:
                available_energy.remove(energy_type)
            elif EnergyType.COLORLESS in available_energy:
                available_energy.remove(EnergyType.COLORLESS)
            else:
                return False
        
        # Calculate base damage
        base_damage = attack.damage
        final_damage = base_damage
        damage_result = DamageResult.NORMAL
        effects_applied = []
        coin_flips = []
        status_condition_applied = None
        energy_discarded = []
        
        # Handle effects in attack
        if attack.effects:
            for effect in attack.effects:
                # Handle status condition effects
                if effect.effect_type in ["poison", "burn", "paralyze", "confuse", "sleep"]:
                    status = self._map_effect_type_to_status(effect.effect_type)
                    if status:
                        target.status_condition = status
                        status_condition_applied = status
                        effects_applied.append(effect)
                
                # Handle multi-coin flip effects (must come before single coin flip)
                elif effect.effect_type == "multi_coin_flip":
                    # Use effect.parameters['num_flips'] if present, else default to 2
                    num_flips = 2
                    if effect.parameters and "num_flips" in effect.parameters:
                        num_flips = effect.parameters["num_flips"]
                    coin_results = self.flip_coins(num_flips)
                    coin_flips.extend(coin_results)
                    
                    heads_count = sum(1 for flip in coin_results if flip == CoinFlipResult.HEADS)
                    bonus_damage = (effect.amount or 50) * heads_count
                    final_damage += bonus_damage
                    effects_applied.append(effect)
                
                # Handle single coin flip effects
                elif "coin_flip" in effect.effect_type:
                    coin_result = self.flip_coin()
                    coin_flips.append(coin_result)
                    
                    if coin_result == CoinFlipResult.HEADS:
                        if "damage" in effect.effect_type:
                            # Add damage bonus
                            bonus_damage = effect.amount or 30
                            final_damage += bonus_damage
                        elif "paralyze" in effect.effect_type:
                            target.status_condition = StatusCondition.PARALYZED
                            status_condition_applied = StatusCondition.PARALYZED
                            effects_applied.append(effect)
                
                # Handle healing effects
                elif effect.effect_type == "heal":
                    if effect.target == TargetType.SELF:
                        self.heal_pokemon(attacker, effect.amount or 30)
                        effects_applied.append(effect)
                
                # Handle energy discarding effects
                elif effect.effect_type == "discard_energy":
                    # Create a list of energy types to discard based on amount
                    energy_types_to_discard = []
                    for _ in range(effect.amount or 1):
                        if attacker.attached_energies:
                            energy_types_to_discard.append(attacker.attached_energies[0])
                        else:
                            break
                    discarded = self.discard_energy(attacker, energy_types_to_discard)
                    energy_discarded.extend(discarded)
                    effects_applied.append(effect)
                
                # Handle poison bonus damage
                elif effect.effect_type == "poison_bonus":
                    if target.status_condition == StatusCondition.POISONED:
                        bonus_damage = effect.amount or 50
                        final_damage += bonus_damage
                        effects_applied.append(effect)
                
                # Handle random status condition effects
                elif effect.effect_type == "random_status":
                    import random
                    status_options = [
                        StatusCondition.ASLEEP,
                        StatusCondition.BURNED,
                        StatusCondition.CONFUSED,
                        StatusCondition.PARALYZED,
                        StatusCondition.POISONED
                    ]
                    random_status = random.choice(status_options)
                    target.status_condition = random_status
                    status_condition_applied = random_status
                    effects_applied.append(effect)
        
        # Calculate final damage with modifiers
        final_damage, damage_result = self._calculate_damage(attack, attacker, target)
        
        # Apply damage to target
        target_with_damage = dataclasses.replace(target, damage_counters=target.damage_counters + final_damage)
        target_ko = target_with_damage.damage_counters >= target_with_damage.hp
        
        # This part of the logic is now handled in execute_attack
        # to ensure immutable updates to the game state.
        
        # Apply attack effects
        attacker_effects = self._apply_attacker_effects(attack, attacker, game_state)
        
        # Discard energy for attack cost AFTER resolution
        # Note: This is a simplified model. A real implementation would need to handle this
        # as part of the immutable update loop. For now, we assume cost is checked but not "spent"
        # from the card object in this resolver. The execute_attack function will handle it.
        energy_discarded = attack.cost.copy()
        
        return AttackResult(
            damage_dealt=final_damage,
            damage_result=damage_result,
            effects_applied=effects_applied,
            target_ko=target_ko,
            attacker_effects=attacker_effects,
            energy_discarded=energy_discarded,
            status_condition_applied=status_condition_applied,
            coin_flips=coin_flips,
        )
    
    def process_start_of_turn(self, game_state: GameState) -> GameState:
        """Handles start-of-turn card draw and energy generation. Returns new state."""
        new_state = game_state
        player = new_state.active_player_state
        
        # Rule §4 & §5: No draw or energy generation on the very first turn of the game
        if new_state.is_first_turn:
            return new_state

        # Rule §4: Draw 1 card
        drawn_cards, new_deck = self.draw_cards(player.deck, 1)
        
        # Rule §5: Generate one Energy if the buffer is empty
        new_energy_zone = player.energy_zone
        if player.energy_zone is None:
            # This needs a rule for which energy is generated. For now, we'll skip.
            # This logic should be moved to a more specific "generate energy" action.
            pass

        updated_player = dataclasses.replace(
            player,
            hand=player.hand + drawn_cards,
            deck=new_deck,
            energy_zone=new_energy_zone
        )
        
        return self._update_player_in_state(new_state, updated_player)


    def attach_energy_from_zone(self, player: PlayerState, target_pokemon: PokemonCard) -> Tuple[PlayerState, PokemonCard]:
        """Attaches energy from the zone to a Pokemon, if possible."""
        if not self._can_attach_energy_from_zone(player):
            raise ValueError("Cannot attach energy from zone.")
            
        energy_to_attach = player.energy_zone
        
        new_pokemon = dataclasses.replace(
            target_pokemon,
            attached_energies=target_pokemon.attached_energies + [energy_to_attach]
        )
        
        new_player = dataclasses.replace(
            player,
            energy_zone=None,
            energy_attached_this_turn=True
        )

        return new_player, new_pokemon
    
    def evolve_pokemon(
        self, 
        evolution: PokemonCard, 
        base_pokemon: PokemonCard,
        game_state: GameState
    ) -> GameState:
        """Evolves a Pokemon and returns the new game state."""
        if not self._can_evolve(evolution, base_pokemon, game_state):
            raise ValueError("Evolution is not legal.")

        player = game_state.active_player_state
        
        # Create the evolved Pokemon, keeping energies, damage, etc.
        evolved_pokemon = dataclasses.replace(
            evolution,
            attached_energies=base_pokemon.attached_energies,
            damage_counters=base_pokemon.damage_counters,
            status_condition=base_pokemon.status_condition,
            # Reset "entered play" status for the new evolution
        )
        
        # Remove the evolution card from hand
        new_hand = [card for card in player.hand if card.id != evolution.id]
        
        # Place the base Pokemon in the discard pile (as it's now part of the evolution)
        new_discard = player.discard_pile + [base_pokemon]
        
        # Replace the base Pokemon with the evolved one
        if player.active_pokemon and player.active_pokemon.id == base_pokemon.id:
            new_active = evolved_pokemon
            new_bench = player.bench
        else:
            new_active = player.active_pokemon
            new_bench = [evolved_pokemon if p.id == base_pokemon.id else p for p in player.bench]

        updated_player = dataclasses.replace(
            player,
            hand=new_hand,
            discard_pile=new_discard,
            active_pokemon=new_active,
            bench=new_bench,
        )
        
        return self._update_player_in_state(game_state, updated_player)
    
    def retreat_pokemon(
        self, player: PlayerState, to_bench: PokemonCard, game_state: GameState
    ) -> GameState:
        """Retreats the active Pokemon and returns the new game state."""
        active_pokemon = player.active_pokemon
        if not active_pokemon:
            raise ValueError("No active Pokemon to retreat.")
        if to_bench not in player.bench:
            raise ValueError("Target Pokemon is not on the bench.")

        if not self._can_retreat(active_pokemon, to_bench, game_state):
            raise ValueError("Retreat is not legal.")

        # Discard energy for retreat cost
        energies_to_discard = active_pokemon.attached_energies[:active_pokemon.retreat_cost]
        updated_active, _ = self.discard_energy(active_pokemon, energies_to_discard)

        # Swap places
        new_active_pokemon = to_bench
        new_bench = [p for p in player.bench if p.id != to_bench.id]
        new_bench.append(updated_active) # Old active is now on the bench

        updated_player = dataclasses.replace(
            player,
            active_pokemon=new_active_pokemon,
            bench=new_bench,
            discard_pile=player.discard_pile + energies_to_discard
        )
        
        return self._update_player_in_state(game_state, updated_player)
    
    def attach_energy(
        self, 
        player: PlayerState,
        target_pokemon: PokemonCard,
        game_state: GameState
    ) -> GameState:
        """Attach energy from zone to a Pokemon."""
        if player.energy_zone is None:
            raise ValueError("No energy in zone to attach")
        if player.energy_attached_this_turn:
            raise ValueError("Already attached energy this turn")
            
        new_energies = list(target_pokemon.attached_energies)
        new_energies.append(player.energy_zone)
        
        updated_pokemon = dataclasses.replace(target_pokemon, attached_energies=new_energies)
        updated_player = dataclasses.replace(player,
            energy_zone=None,
            energy_attached_this_turn=True,
            active_pokemon=updated_pokemon if player.active_pokemon == target_pokemon else player.active_pokemon
        )
        
        return dataclasses.replace(game_state,
            player=updated_player if game_state.player == player else game_state.player,
            opponent=updated_player if game_state.opponent == player else game_state.opponent
        )

    def draw_cards(self, deck: List[Card], count: int) -> Tuple[List[Card], List[Card]]:
        """Draws cards from the deck, returning the drawn cards and the new deck."""
        if count > len(deck):
            # As per rules, you draw as many as you can. The loss condition is handled
            # by the game state check at the start of the turn.
            count = len(deck)
        
        drawn_cards = deck[:count]
        new_deck = deck[count:]
        return drawn_cards, new_deck
    
    def _extract_damage_bonus(self, effect_text: str) -> int:
        """Extract damage bonus from effect text."""
        # Simple extraction - look for numbers followed by "more damage"
        import re
        match = re.search(r'(\d+)\s+more\s+damage', effect_text)
        return int(match.group(1)) if match else 0
    
    def _extract_poison_bonus(self, effect_text: str) -> int:
        """Extract poison bonus damage from effect text."""
        import re
        match = re.search(r'(\d+)\s+more\s+damage.*Poisoned', effect_text)
        return int(match.group(1)) if match else 0
    
    def _extract_status_condition(self, effect_text: str) -> Optional[StatusCondition]:
        """Extract status condition from effect text."""
        effect_text = effect_text.lower()
        if "poison" in effect_text:
            return StatusCondition.POISONED
        elif "burn" in effect_text:
            return StatusCondition.BURNED
        elif "paralyze" in effect_text:
            return StatusCondition.PARALYZED
        elif "confuse" in effect_text:
            return StatusCondition.CONFUSED
        elif "sleep" in effect_text:
            return StatusCondition.ASLEEP
        return None
    
    def _extract_status_condition_from_attack(self, attack: Attack) -> Optional[StatusCondition]:
        """Extract status condition from attack description."""
        if attack.description:
            return self._extract_status_condition(attack.description)
        return None
    
    def apply_status_condition_effects(self, pokemon: PokemonCard, game_state: GameState) -> PokemonCard:
        """Apply damage from status conditions."""
        damage = 0
        if pokemon.status_condition == StatusCondition.BURNED:
            damage = 20
        elif pokemon.status_condition == StatusCondition.POISONED:
            damage = 10
            
        return dataclasses.replace(pokemon, damage_counters=pokemon.damage_counters + damage)

    def heal_pokemon(self, pokemon: PokemonCard, amount: int) -> PokemonCard:
        """Heals a Pokemon, returning a new PokemonCard instance."""
        new_damage = max(0, pokemon.damage_counters - amount)
        return dataclasses.replace(pokemon, damage_counters=new_damage)
    
    def discard_energy(self, pokemon: PokemonCard, energy_types: List[EnergyType]) -> Tuple[PokemonCard, List[EnergyType]]:
        """Discards specified energy from a Pokemon, returning the new Pokemon and the discarded energies."""
        remaining_energies = pokemon.attached_energies.copy()
        discarded_energies = []
        
        for energy_type in energy_types:
            if energy_type in remaining_energies:
                remaining_energies.remove(energy_type)
                discarded_energies.append(energy_type)
        
        new_pokemon = dataclasses.replace(pokemon, attached_energies=remaining_energies)
        return new_pokemon, discarded_energies
    
    def _can_use_attack(
        self, 
        attacker: PokemonCard, 
        attack: Attack, 
        game_state: GameState
    ) -> bool:
        """Check if a Pokemon can use a specific attack."""
        # Check if it's the right phase (allow both MAIN and ATTACK phases)
        if game_state.phase not in [GamePhase.MAIN, GamePhase.ATTACK]:
            return False
        
        # Check if Pokemon has required energy
        required_energy = attack.cost
        attached_energy = attacker.attached_energies
        
        # Simple check: count energy types
        for energy_type in required_energy:
            if attached_energy.count(energy_type) < required_energy.count(energy_type):
                return False
                
        # Check status conditions that prevent attacks
        if attacker.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
                return False
        
        return True
    
    def _calculate_damage(
        self, 
        attack: Attack,
        attacker: PokemonCard, 
        target: PokemonCard
    ) -> Tuple[int, DamageResult]:
        """Calculate final damage with modifiers."""
        final_damage = attack.damage
        damage_result = DamageResult.NORMAL
        
        # Fixed: Weakness adds a specified amount of damage
        if target.weakness and isinstance(target.weakness, tuple) and target.weakness[0] == attacker.pokemon_type:
            final_damage += target.weakness[1]
            damage_result = DamageResult.WEAKNESS
        
        # Pocket TCG has no resistance
        return final_damage, damage_result
    
    def _handle_attack_costs(
        self, 
        attacker: PokemonCard, 
        attack: Attack, 
        game_state: GameState
    ) -> List[EnergyType]:
        """Handle energy costs for attacks."""
        # For now, we'll just return the energy types that would be discarded
        # In a full implementation, we'd actually remove them from attached_energies
        return attack.cost.copy()
    
    def _apply_attack_effects(
        self, 
        attack: Attack, 
        target: PokemonCard, 
        game_state: GameState
    ) -> List[Effect]:
        """Apply effects from the attack to the target."""
        effects = []
        for effect in attack.effects or []:
            if effect.target == "opponent_active":
                effects.append(effect)
        return effects
    
    def _apply_attacker_effects(
        self, 
        attack: Attack, 
        attacker: PokemonCard, 
        game_state: GameState
    ) -> List[Effect]:
        """Apply effects from the attack to the attacker."""
        effects = []
        for effect in attack.effects or []:
            if effect.target == "self":
                effects.append(effect)
        return effects
    
    def _can_evolve(
        self, 
        evolution: PokemonCard, 
        base_pokemon: PokemonCard, 
        game_state: GameState
    ) -> bool:
        """Check if evolution is legal."""
        # Check if evolution stage is correct
        if evolution.stage == Stage.STAGE_1 and base_pokemon.stage != Stage.BASIC:
            return False
        if evolution.stage == Stage.STAGE_2 and base_pokemon.stage != Stage.STAGE_1:
            return False
        
        # Check if evolution card is in hand
        if evolution not in game_state.active_player_state.hand:
            return False
        
        # Rulebook §4: Cannot evolve on the turn it entered play
        if base_pokemon.id in game_state.active_player_state.pokemon_entered_play_this_turn:
            return False
        
        return True
    
    def _can_retreat(
        self, 
        active_pokemon: PokemonCard, 
        bench_pokemon: PokemonCard, 
        game_state: GameState
    ) -> bool:
        """Check if a Pokemon can retreat."""
        # Check status conditions that prevent retreat
        if active_pokemon.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
            return False
        
        # Check if there's a valid bench Pokemon to switch to
        if bench_pokemon not in game_state.active_player_state.bench:
            return False
            
        # Check if Pokemon has enough energy to pay retreat cost
        if len(active_pokemon.attached_energies) < active_pokemon.retreat_cost:
                return False
        
        return True
    
    def _can_attach_energy(
        self, 
        player: PlayerState,
        target_pokemon: PokemonCard
    ) -> bool:
        """Check if energy attachment is legal."""
        # This method is for the abstract concept. Use _can_attach_energy_from_zone for TCG Pocket.
        return self._can_attach_energy_from_zone(player)
    
    def _can_attach_energy_from_zone(self, player: PlayerState) -> bool:
        """Checks if the player can attach an energy from their zone."""
        # Rule: Must have an energy in the zone and not have attached yet this turn.
        if player.energy_zone is None:
            return False
        if player.energy_attached_this_turn:
            return False
        return True
    
    def award_points(self, player: PlayerState, points: int) -> PlayerState:
        """Award points to a player."""
        new_points = player.points + points
        if new_points > 3:
            raise ValueError(f"Cannot award {points} points - would exceed maximum of 3")
        return dataclasses.replace(player, points=new_points)

    def _apply_knockout(self, game_state: GameState, ko_pokemon: PokemonCard) -> GameState:
        """Handle Pokemon knockout and point awards."""
        points_to_award = 2 if ko_pokemon.is_ex else 1
        updated_player = self.award_points(game_state.player, points_to_award)
        
        # Remove KO'd Pokemon from opponent's field
        if game_state.opponent.active_pokemon == ko_pokemon:
            updated_opponent = dataclasses.replace(game_state.opponent, 
                active_pokemon=None,
                discard_pile=game_state.opponent.discard_pile + [ko_pokemon]
            )
        else:
            updated_opponent = game_state.opponent
            
        updated_state = dataclasses.replace(game_state,
            player=updated_player,
            opponent=updated_opponent
        )
        
        return self.check_game_over(updated_state)
    
    def check_game_over(self, game_state: GameState) -> Optional[str]:
        """
        Checks if the game is over and returns the winner as a string.
        Returns None if the game is not over.
        """
        # Check point victory
        if game_state.player.points >= self.points_to_win:
            return "player"
        if game_state.opponent.points >= self.points_to_win:
            return "opponent"
        
        # Check if player has no Pokemon in play
        if not game_state.player.pokemon_in_play:
            return "opponent"
        if not game_state.opponent.pokemon_in_play:
            return "player"
        
        # Check deck out condition
        if len(game_state.player.deck) == 0:
                return "opponent"
        if len(game_state.opponent.deck) == 0:
                return "player"
        
        # Game continues
        return None
    
    def _map_effect_type_to_status(self, effect_type: str) -> Optional[StatusCondition]:
        """Maps an effect string to a StatusCondition enum."""
        if effect_type == "poison":
            return StatusCondition.POISONED
        elif effect_type == "burn":
            return StatusCondition.BURNED
        elif effect_type == "paralyze":
            return StatusCondition.PARALYZED
        elif effect_type == "confuse":
            return StatusCondition.CONFUSED
        elif effect_type == "sleep":
            return StatusCondition.ASLEEP
        return None
    
    def play_trainer_card(
        self, 
        player: PlayerState,
        card: TrainerCard, 
        game_state: GameState, 
        target_pokemon: Optional[PokemonCard] = None,
    ) -> GameState:
        # Import locally to prevent circular dependency
        from src.card_db.trainer_executor import execute_trainer_card
        
        if not self.can_play_trainer_card(player, card, game_state):
            raise ValueError(f"Cannot play trainer card {card.name}")
            
        return execute_trainer_card(card, game_state, game_state.active_player)

    def can_play_trainer_card(
        self, player: PlayerState, card: TrainerCard, game_state: GameState
    ) -> bool:
        return True # Simplified for now

    def execute_attack(self, attacker: PokemonCard, defender: PokemonCard, attack: Attack, game_state: GameState) -> GameState:
        """Execute an attack and return the updated game state."""
        if not self._can_use_attack(attacker, attack, game_state):
            raise ValueError("Attack cannot be used")

        # Calculate and apply damage
        damage = self._calculate_attack_damage(attack, attacker, defender)
        updated_defender = defender.apply_damage(damage)
        
        # Check for knockout
        if updated_defender.damage_counters >= updated_defender.hp:
            return self._apply_knockout(game_state, updated_defender)
            
        # Update game state with damaged defender
        if game_state.player.active_pokemon == defender:
            updated_player = dataclasses.replace(game_state.player, active_pokemon=updated_defender)
            return dataclasses.replace(game_state, player=updated_player)
        else:
            updated_opponent = dataclasses.replace(game_state.opponent, active_pokemon=updated_defender)
            return dataclasses.replace(game_state, opponent=updated_opponent)

    def _calculate_attack_damage(self, attack: Attack, attacker: PokemonCard, defender: PokemonCard) -> int:
        """Calculate total damage for an attack including modifiers."""
        base_damage = attack.damage
        
        # Apply status condition bonuses
        if defender.status_condition == StatusCondition.POISONED:
            base_damage += 10
            
        # Apply coin flip effects
        if attack.effects:
            for effect in attack.effects:
                if effect.type == "COIN_FLIP" and random.random() < 0.5:  # Heads
                    base_damage += effect.bonus_damage
                    
        return base_damage

    def _can_use_attack(self, pokemon: PokemonCard, attack: Attack, game_state: GameState) -> bool:
        """Check if the Pokemon can use the given attack."""
        if attack not in pokemon.attacks:
            return False
        if pokemon.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
            return False
        if not self._has_sufficient_energy(pokemon, attack.cost):
            return False
        return True

    def _has_sufficient_energy(self, pokemon: PokemonCard, cost: List[EnergyType]) -> bool:
        """Check if Pokemon has sufficient energy for the cost."""
        available_energy = pokemon.attached_energies.copy()
        for required in cost:
            if required in available_energy:
                available_energy.remove(required)
            else:
                return False
        return True

    def start_turn_energy_generation(self, player: PlayerState) -> PlayerState:
        """Generates one energy into the player's buffer if it's empty."""
        if player.energy_zone is None:
            # Simple rule: generate a COLORLESS energy. This can be expanded.
            return dataclasses.replace(player, energy_zone=[EnergyType.COLORLESS])
        return player

    def start_first_turn(self, game_state: GameState) -> GameState:
        """Applies first turn restrictions."""
        return dataclasses.replace(game_state, is_first_turn=True)

    def checkup_phase(self, game_state: GameState) -> GameState:
        """
        Handles the check-up phase between turns, applying status effects.
        Returns the new game state.
        """
        # Rule §8: Effects applied in order for BOTH players' active Pokemon
        # The player whose turn is about to start is checked first.
    
        new_state = game_state
        next_player_state = new_state.inactive_player_state
        current_player_state = new_state.active_player_state

        if next_player_state.active_pokemon:
            new_state = self._apply_checkup_to_pokemon(next_player_state.active_pokemon, new_state)

        if current_player_state.active_pokemon:
            new_state = self._apply_checkup_to_pokemon(current_player_state.active_pokemon, new_state)
            
        # Check for KOs from status effects
        final_state = self.check_game_over(new_state)

        return final_state
    
    def _apply_checkup_to_pokemon(self, pokemon: PokemonCard, game_state: GameState) -> GameState:
        """Apply status effect damage and resolution for a single Pokemon."""
        new_pokemon, did_resolve = self.apply_status_condition_effects_in_order(pokemon)
        return self._update_pokemon_in_state(game_state, new_pokemon)


    def apply_status_condition_effects_in_order(self, pokemon: PokemonCard) -> Tuple[PokemonCard, bool]:
        """
        Applies status condition effects in the specified order (Poisoned, Burned, Asleep, Paralyzed).
        This is a core part of the check-up phase.
        Returns the updated Pokemon and a boolean indicating if a condition was resolved.
        """
        new_pokemon = pokemon
        
        # 1. Poison
        if new_pokemon.status_condition == StatusCondition.POISONED:
            new_pokemon = dataclasses.replace(new_pokemon, damage_counters=new_pokemon.damage_counters + 10)
            if new_pokemon.damage_counters >= new_pokemon.hp:
                return new_pokemon, True # Knocked out by Poison

        # 2. Burn
        if new_pokemon.status_condition == StatusCondition.BURNED:
            # A coin is flipped. On heads, no damage. On tails, 20 damage.
            if self.flip_coin() == CoinFlipResult.TAILS:
                new_pokemon = dataclasses.replace(new_pokemon, damage_counters=new_pokemon.damage_counters + 20)
                if new_pokemon.damage_counters >= new_pokemon.hp:
                    return new_pokemon, True # Knocked out by Burn
        
        return new_pokemon, False

    def can_attach_tool(self, pokemon: PokemonCard, game_state: GameState) -> bool:
        """Check if a tool can be attached to the Pokemon."""
        # Simplified: a Pokemon can only have one tool.
        # A more complex check might involve specific card abilities.
        return not any(isinstance(card, ToolCard) for card in pokemon.attached_energies) # This is a bug, should check attached cards

    def enforce_hand_limit(self, player: PlayerState) -> PlayerState:
        """Enforce hand limit and return updated player state."""
        if len(player.hand) > self.max_hand_size:
            # Player must discard down to hand limit
            cards_to_discard = len(player.hand) - self.max_hand_size
            # For now, discard from the end (in real game, player chooses)
            new_hand = player.hand[:-cards_to_discard]
            discarded_cards = player.hand[-cards_to_discard:]
            new_discard_pile = player.discard_pile + discarded_cards
            return dataclasses.replace(player, hand=new_hand, discard_pile=new_discard_pile)
        return player

    def load_deck(self):
        # TODO: Implement deck loading from file
        pass

    def log_info(self, message: str) -> None:
        """Log information message (stub implementation)."""
        # This is a stub implementation for testing
        # In a real implementation, this would log to a file or console
        pass

    def attach_tool(
        self, player: PlayerState, pokemon: PokemonCard, tool: Card, game_state: GameState
    ) -> GameState:
        raise NotImplementedError("Attaching tools is not yet implemented.")

    def validate_deck(self, deck: List[Card]) -> bool:
        """Validate deck follows construction rules."""
        # Check deck size
        if len(deck) != 20:
            return False

        # Check card count limits
        card_counts = {}
        for card in deck:
            card_counts[card.id] = card_counts.get(card.id, 0) + 1
            if card_counts[card.id] > 2:  # TCG Pocket limit is 2 copies
                return False
                
        return True

    def _update_player_in_state(self, game_state: GameState, player_state: PlayerState) -> GameState:
        """Helper to update one of the players in the game state."""
        if player_state.player_tag == PlayerTag.PLAYER:
            return dataclasses.replace(game_state, player=player_state)
        else:
            return dataclasses.replace(game_state, opponent=player_state)

    def _update_pokemon_in_state(self, game_state: GameState, pokemon: PokemonCard) -> GameState:
        """Helper to find and update a Pokemon card anywhere in the game state."""
        # Determine owner and update the card in the correct list (active, bench)
        owner_state = game_state.get_player_state(pokemon.owner)
        
        if owner_state.active_pokemon and owner_state.active_pokemon.id == pokemon.id:
            updated_owner = dataclasses.replace(owner_state, active_pokemon=pokemon)
        else:
            new_bench = [pokemon if p.id == pokemon.id else p for p in owner_state.bench]
            updated_owner = dataclasses.replace(owner_state, bench=new_bench)
            
        return self._update_player_in_state(game_state, updated_owner)

    def start_turn(self, game_state: GameState) -> GameState:
        """Handle start of turn effects."""
        if game_state.is_first_turn:
            return dataclasses.replace(game_state, 
                phase=GamePhase.MAIN,
                is_first_turn=False
            )
        
        # Draw phase
        updated_player = self.draw_cards(game_state.player, 1)
        
        # Generate energy if zone is empty
        if updated_player.energy_zone is None:
            energy_type = random.choice(list(EnergyType))
            updated_player = dataclasses.replace(updated_player, energy_zone=energy_type)
        
        return dataclasses.replace(game_state,
            player=updated_player,
            phase=GamePhase.MAIN,
            energy_attached_this_turn=False,
            supporter_played_this_turn=False
        )

    def enforce_hand_limit(self, player: PlayerState) -> List[Card]:
        """Force discard down to 7 cards if over the limit."""
        if len(player.hand) <= 7:
            return []
            
        # For now, just discard the excess from the end
        cards_to_discard = player.hand[7:]
        player.hand = player.hand[:7]
        player.discard_pile.extend(cards_to_discard)
        return cards_to_discard

    def can_retreat(self, pokemon: PokemonCard, player: PlayerState) -> bool:
        """Check if a Pokemon can retreat."""
        if pokemon.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
            return False
        return len(pokemon.attached_energies) >= pokemon.retreat_cost

    def retreat(self, game_state: GameState, bench_position: int) -> GameState:
        """Retreat active Pokemon to bench and promote selected Pokemon."""
        player = game_state.player
        if not player.active_pokemon or len(player.bench) <= bench_position:
            raise ValueError("Invalid retreat")
            
        if not self.can_retreat(player.active_pokemon, player):
            raise ValueError("Cannot retreat this Pokemon")

        # Remove retreat cost energy
        remaining_energy = player.active_pokemon.attached_energies[player.active_pokemon.retreat_cost:]
        retreating_pokemon = dataclasses.replace(player.active_pokemon, attached_energies=remaining_energy)
        
        # Swap Pokemon
        new_active = player.bench[bench_position]
        new_bench = player.bench.copy()
        new_bench[bench_position] = retreating_pokemon
        
        updated_player = dataclasses.replace(player,
            active_pokemon=new_active,
            bench=new_bench
        )
        
        return dataclasses.replace(game_state, player=updated_player)

    def choose_pokemon(self, available_pokemon: List[PokemonCard]) -> Optional[PokemonCard]:
        """Choose a Pokemon from available options."""
        if not available_pokemon:
            return None
        # For testing, just return the first one
        return available_pokemon[0]