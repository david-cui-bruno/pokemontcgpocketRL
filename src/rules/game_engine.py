"""Core game mechanics for Pokemon TCG Pocket.

This module handles the actual game logic including attack resolution,
evolution, retreat, and other core mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import random

from src.card_db.core import (
    PokemonCard, Card, Attack, Effect, EnergyType, Stage, StatusCondition, TargetType, ItemCard, ToolCard, SupporterCard, TrainerCard
)
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.rules.actions import Action, ActionType


class DamageResult(Enum):
    """Possible results of damage calculation."""
    NORMAL = "normal"
    WEAKNESS = "weakness"


class CoinFlipResult(Enum):
    """Results of coin flips."""
    HEADS = "heads"
    TAILS = "tails"


@dataclass
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
        self.max_bench_size = 3  # Fixed: TCG Pocket has max 3 bench Pokemon
        self.max_hand_size = 7
        self.prize_cards = 3  # TCG Pocket uses 3 prize cards
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
            raise ValueError("Attack cannot be used")
        
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
        final_damage, damage_result = self._calculate_damage(final_damage, attacker, target)
        
        # Apply damage to target
        target.damage_counters += final_damage
        target_ko = target.damage_counters >= target.hp
        
        # Award points if target is KO'd (TCG Pocket rulebook §10)
        if target_ko:
            # Determine which player gets the points
            # If target is player's active Pokemon, opponent gets points
            # If target is opponent's active Pokemon, player gets points
            if target == game_state.player.active_pokemon:
                # Opponent gets points
                points_to_award = 2 if target.is_ex else 1
                self.award_points(game_state.opponent, points_to_award)
            elif target == game_state.opponent.active_pokemon:
                # Player gets points
                points_to_award = 2 if target.is_ex else 1
                self.award_points(game_state.player, points_to_award)
        
        # Apply attack effects
        attacker_effects = self._apply_attacker_effects(attack, attacker, game_state)
        
        return AttackResult(
            damage_dealt=final_damage,
            damage_result=damage_result,
            effects_applied=effects_applied,
            target_ko=target_ko,
            attacker_effects=attacker_effects,
            energy_discarded=energy_discarded,
            status_condition_applied=status_condition_applied,
            coin_flips=coin_flips
        )
    
    def evolve_pokemon(
        self, 
        evolution: PokemonCard, 
        base_pokemon: PokemonCard,
        game_state: GameState
    ) -> bool:
        """Handle Pokemon evolution.
        
        Parameters
        ----------
        evolution : PokemonCard
            The evolution card to play
        base_pokemon : PokemonCard
            The Pokemon to evolve
        game_state : GameState
            Current game state
            
        Returns
        -------
        bool
            True if evolution was successful
        """
        # Check if evolution is legal
        if not self._can_evolve(evolution, base_pokemon, game_state):
            return False
        
        # Evolution is always legal if the base Pokemon exists
        # and the evolution card is in hand
        return True
    
    def retreat_pokemon(
        self, 
        active_pokemon: PokemonCard, 
        bench_pokemon: PokemonCard,
        game_state: GameState
    ) -> bool:
        """Retreat active Pokemon to bench, bringing bench Pokemon to active."""
        if not self._can_retreat(active_pokemon, bench_pokemon, game_state):
            return False
        
        # Remove energy for retreat cost
        retreat_cost = active_pokemon.retreat_cost
        if retreat_cost > 0:
            self.discard_energy(active_pokemon, active_pokemon.attached_energies[:retreat_cost])
        
        # Switch active and bench Pokemon
        game_state.player.active_pokemon = bench_pokemon
        game_state.player.bench.remove(bench_pokemon)
        game_state.player.bench.append(active_pokemon)
        
        return True
    
    def attach_energy(
        self, 
        energy_card: Card, 
        target_pokemon: PokemonCard,
        game_state: GameState
    ) -> bool:
        """Attach energy to a Pokemon.
        
        Parameters
        ----------
        energy_card : Card
            The energy card to attach
        target_pokemon : PokemonCard
            The Pokemon to attach energy to
        game_state : GameState
            Current game state
            
        Returns
        -------
        bool
            True if energy attachment was successful
        """
        # Check if energy attachment is legal
        if not self._can_attach_energy(energy_card, target_pokemon, game_state):
            return False
        
        # Energy attachment is always legal if the energy card exists
        # and the target Pokemon is in play
        return True
    
    def draw_cards(self, player: PlayerState, count: int) -> List[Card]:
        """Draw cards from deck.
        
        Parameters
        ----------
        player : PlayerState
            The player drawing cards
        count : int
            Number of cards to draw
            
        Returns
        -------
        List[Card]
            List of drawn cards
        """
        drawn_cards = []
        for _ in range(min(count, len(player.deck))):
            if player.deck:
                drawn_card = player.deck.pop()
                drawn_cards.append(drawn_card)
                player.hand.append(drawn_card)
        
        return drawn_cards
    
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
    
    def apply_status_condition_effects(self, pokemon: PokemonCard, game_state: GameState) -> Dict[str, Any]:
        """Apply effects of status conditions during Check-up phase (rulebook §7)."""
        effects = {}
        
        if pokemon.status_condition == StatusCondition.POISONED:
            # Poison: 10 damage during each Check-up
            pokemon.damage_counters += 10
            effects["damage"] = 10
            effects["poison_damage"] = 10
        
        elif pokemon.status_condition == StatusCondition.BURNED:
            # Burn: 20 damage, then flip a coin; heads cures Burn
            pokemon.damage_counters += 20
            effects["damage"] = 20
            effects["burn_damage"] = 20
            coin_result = self.flip_coin()
            if coin_result == CoinFlipResult.HEADS:
                pokemon.status_condition = None
                effects["burn_cured"] = True
        
        # Always return these keys (even if 0)
        effects.setdefault("poison_damage", 0)
        effects.setdefault("burn_damage", 0)
        effects.setdefault("damage", 0)
        
        return effects
    
    def heal_pokemon(self, pokemon: PokemonCard, amount: int) -> bool:
        """Heal a Pokemon by the specified amount."""
        if amount > 0:
            pokemon.damage_counters = max(0, pokemon.damage_counters - amount)
            return True
        return False
    
    def discard_energy(self, pokemon: PokemonCard, energy_types: List[EnergyType]) -> List[EnergyType]:
        """Discard energy from a Pokemon."""
        discarded = []
        for energy_type in energy_types:
            if energy_type in pokemon.attached_energies:
                pokemon.attached_energies.remove(energy_type)
                discarded.append(energy_type)
        return discarded
    
    def _can_use_attack(
        self, 
        attacker: PokemonCard, 
        attack: Attack, 
        game_state: GameState
    ) -> bool:
        """Check if an attack can be used."""
        # Check if we're in ATTACK phase
        if game_state.phase != GamePhase.ATTACK:
            return False
        
        # Check if Pokemon is asleep or paralyzed
        if attacker.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
            return False
        
        # Check if attacker has enough energy
        required_energy = attack.cost
        available_energy = attacker.attached_energies.copy()
        
        for energy_type in required_energy:
            if energy_type in available_energy:
                available_energy.remove(energy_type)
            elif EnergyType.COLORLESS in available_energy:
                available_energy.remove(EnergyType.COLORLESS)
            else:
                return False
        
        return True
    
    def _calculate_damage(
        self, 
        base_damage: int, 
        attacker: PokemonCard, 
        target: PokemonCard
    ) -> Tuple[int, DamageResult]:
        """Calculate final damage with modifiers."""
        final_damage = base_damage
        damage_result = DamageResult.NORMAL
        
        # Fixed: Weakness adds +20 damage (not multiplies by 2)
        if target.weakness == attacker.pokemon_type:
            final_damage += 20
            damage_result = DamageResult.WEAKNESS
        
        # Removed resistance mechanics - TCG Pocket has no resistance
        
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
        """Check if retreat is legal."""
        # Check if bench Pokemon exists
        if bench_pokemon not in game_state.player.bench:
            return False
        
        # Fixed: Cannot retreat if asleep or paralyzed
        if active_pokemon.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
            return False
        
        # Check if enough energy is attached for retreat cost
        retreat_cost = active_pokemon.retreat_cost
        if retreat_cost > 0:
            if len(active_pokemon.attached_energies) < retreat_cost:
                return False
        
        return True
    
    def _can_attach_energy(
        self, 
        energy_card: Card, 
        target_pokemon: PokemonCard, 
        game_state: GameState
    ) -> bool:
        """Check if energy attachment is legal."""
        # Check if energy card is in hand
        if energy_card not in game_state.player.hand:
            return False
        
        # Check if target Pokemon is in play
        if (target_pokemon != game_state.player.active_pokemon and 
            target_pokemon not in game_state.player.bench):
            return False
        
        # Check if energy attachment limit is reached (1 per turn)
        if game_state.player.has_attached_energy:
            return False
        
        return True
    
    def award_points(self, player: PlayerState, points: int) -> bool:
        """Award points for KOing Pokemon (TCG Pocket rulebook §10).
        
        Parameters
        ----------
        player : PlayerState
            The player to award points to
        points : int
            Points to award (1 for regular Pokemon, 2 for ex/Tera)
            
        Returns
        -------
        bool
            True if points were awarded, False if player already has 3 points
        """
        if player.points >= 3:
            return False
        
        player.points = min(3, player.points + points)
        return True
    
    def check_game_over(self, game_state: GameState) -> Optional[str]:
        """Check if the game is over and return the winner (rulebook §10)."""
        # Check points (first to 3 points wins)
        if game_state.player.points >= 3:
            return "player"
        if game_state.opponent.points >= 3:
            return "opponent"
        
        # Check if either player has no Pokemon in play
        if (not game_state.player.active_pokemon and 
            not game_state.player.bench):
            return "opponent"
        if (not game_state.opponent.active_pokemon and 
                not game_state.opponent.bench):
            return "player"
        
        # Deck out: Only lose if required to draw and cannot (DRAW phase)
        if game_state.phase == GamePhase.DRAW:
            if game_state.active_player == PlayerTag.PLAYER and not game_state.player.deck:
                return "opponent"
            if game_state.active_player == PlayerTag.OPPONENT and not game_state.opponent.deck:
                return "player"
        
        return None
    
    def _map_effect_type_to_status(self, effect_type: str) -> Optional[StatusCondition]:
        """Map effect type string to StatusCondition enum."""
        mapping = {
            "poison": StatusCondition.POISONED,
            "burn": StatusCondition.BURNED,
            "paralyze": StatusCondition.PARALYZED,
            "confuse": StatusCondition.CONFUSED,
            "sleep": StatusCondition.ASLEEP
        }
        return mapping.get(effect_type)
    
    def play_trainer_card(
        self, 
        card: TrainerCard, 
        game_state: GameState, 
        target_pokemon: Optional[PokemonCard] = None
    ) -> bool:
        """Play a trainer card using the composable effects system."""
        player = game_state.active_player_state
        
        # Import here to avoid circular import
        from src.card_db.trainer_executor import execute_trainer_card, can_play_trainer_card
        
        # Check if the card can be played first
        if not can_play_trainer_card(card, game_state, player, self):
            return False
        
        success = execute_trainer_card(card, game_state, player, self)
        if success:
            # Remove card from hand
            if card in player.hand:
                player.hand.remove(card)
            # Add to discard pile
            player.discard_pile.append(card)
            
            # Mark supporter as played if it's a supporter card
            if isinstance(card, SupporterCard):
                player.supporter_played_this_turn = True
        
        return success
    
    def can_play_trainer_card_engine(
        self, 
        card: TrainerCard, 
        game_state: GameState, 
        target_pokemon: Optional[PokemonCard] = None
    ) -> bool:
        """Check if a trainer card can be played (dry run)."""
        player = game_state.active_player_state  # Fixed: Use active_player_state instead of active_player
        
        # Import here to avoid circular import
        from src.card_db.trainer_executor import can_play_trainer_card
        
        return can_play_trainer_card(card, game_state, player, self)
    
    def start_turn_energy_generation(self, player: PlayerState) -> bool:
        """Generate energy in Energy Zone at start of turn if empty (rulebook §5)."""
        # Only generate if energy zone is empty and player has registered types
        if player.energy_zone is None and player.registered_energy_types:
            import random
            energy_type = random.choice(player.registered_energy_types)
            success = player.generate_energy(energy_type)
            if success:
                # According to rulebook, energy should be immediately attached
                # This might need to be handled in the turn advancement logic
                return True
        return False

    def start_first_turn(self, game_state: GameState) -> None:
        """Handle first turn restrictions (rulebook §3)."""
        if game_state.turn_number == 0:  # Fixed: Check for turn 0
            # First player cannot draw or attach energy on turn 0
            active_state = game_state.active_player_state
            active_state.can_draw_this_turn = False
            active_state.can_attach_energy_this_turn = False

    def apply_status_condition_effects_in_order(self, pokemon: PokemonCard, game_state: GameState) -> Dict[str, Any]:
        """Apply status condition effects in rulebook order: Poison → Burn → Sleep → Paralysis."""
        results = {}
        
        # Apply in fixed order per rulebook §7
        if pokemon.status_condition == StatusCondition.POISONED:
            pokemon.damage_counters += 10
            results['poison_damage'] = 10
        
        if pokemon.status_condition == StatusCondition.BURNED:
            pokemon.damage_counters += 20
            results['burn_damage'] = 20
            # Flip coin for burn cure
            if self.flip_coin() == CoinFlipResult.HEADS:
                pokemon.status_condition = None
                results['burn_cured'] = True
        
        if pokemon.status_condition == StatusCondition.ASLEEP:
            # Flip coin to wake up
            if self.flip_coin() == CoinFlipResult.HEADS:
                pokemon.status_condition = None
                results['woke_up'] = True
        
        if pokemon.status_condition == StatusCondition.PARALYZED:
            # Paralysis wears off after one full turn
            # This should be handled in turn advancement
            pass
        
        return results

    def can_attach_tool(self, pokemon: PokemonCard, game_state: GameState) -> bool:
        """Check if a tool can be attached to a Pokemon (rulebook §9)."""
        # Check if this Pokemon already has a tool attached
        # This would need to track attached tools in the PokemonCard or GameState
        # For now, we'll assume no tool is attached
        return True  # Placeholder - needs proper implementation

    def enforce_hand_limit(self, player: PlayerState) -> List[Card]:
        """Enforce 10-card hand limit (rulebook §11)."""
        if len(player.hand) > 10:
            # In a real implementation, this would need player input
            # For now, we'll discard the oldest cards
            excess = len(player.hand) - 10
            discarded = player.hand[:excess]
            player.hand = player.hand[excess:]
            player.discard_pile.extend(discarded)
            return discarded
        return []

    def load_deck(self):
        # TODO: Implement deck loading from file
        self.log_info("Load deck not yet implemented.")