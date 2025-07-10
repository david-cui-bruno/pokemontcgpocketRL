"""Game engine for Pokemon TCG Pocket.

Handles all game mechanics and rule enforcement following official rules.
"""

from __future__ import annotations
from dataclasses import dataclass, replace, field
from typing import List, Optional, Tuple, Dict, Set
import random

from src.rules.constants import (
    EnergyType, Stage, StatusCondition, GamePhase, GameConstants
)
from src.rules.game_state import (
    GameState, PlayerState, PlayerTag, TurnState, EnergyZone
)
from src.card_db.core import (
    Card, PokemonCard, TrainerCard, ItemCard, SupporterCard, ToolCard,
    Attack, Effect
)

@dataclass
class AttackResult:
    """Result of attack resolution."""
    damage_dealt: int
    effects_applied: List[Effect]
    target_knocked_out: bool
    energy_discarded: List[EnergyType]
    status_applied: Optional[StatusCondition]
    coin_flips: List[bool] = field(default_factory=list)

class GameEngine:
    """Core game logic engine."""
    
    def __init__(self, random_seed: Optional[int] = None):
        """Initialize game engine with optional random seed."""
        self.rng = random.Random(random_seed)
        
    def create_game(self, player_deck: List[Card], opponent_deck: List[Card]) -> GameState:
        """Create a new game state with shuffled decks and initial hands."""
        if not self._validate_deck(player_deck) or not self._validate_deck(opponent_deck):
            raise ValueError("Invalid deck")
            
        # Shuffle decks
        player_deck = player_deck.copy()
        opponent_deck = opponent_deck.copy()
        self.rng.shuffle(player_deck)
        self.rng.shuffle(opponent_deck)
        
        # Draw initial hands (5 cards each)
        player_hand = player_deck[:GameConstants.INITIAL_HAND_SIZE]
        opponent_hand = opponent_deck[:GameConstants.INITIAL_HAND_SIZE]
        
        return GameState(
            player=PlayerState(
                tag=PlayerTag.PLAYER,
                deck=player_deck[GameConstants.INITIAL_HAND_SIZE:],
                hand=player_hand,
                energy_zone=EnergyZone(set())  # Empty until types registered
            ),
            opponent=PlayerState(
                tag=PlayerTag.OPPONENT,
                deck=opponent_deck[GameConstants.INITIAL_HAND_SIZE:],
                hand=opponent_hand,
                energy_zone=EnergyZone(set())
            ),
            phase=GamePhase.START,
            is_first_turn=True
        )

    def start_turn(self, state: GameState) -> GameState:
        """Handle start of turn (draw + energy generation)."""
        if state.phase != GamePhase.START:
            raise ValueError("Can only start turn in START phase")
            
        new_state = state
        
        # Draw card (except first player's first turn)
        if not (state.is_first_turn and state.active_player_tag == PlayerTag.PLAYER):
            new_state = self.draw_cards(new_state, 1)
            
        # Generate energy (except first player's first turn)
        if not (state.is_first_turn and state.active_player_tag == PlayerTag.PLAYER):
            new_state = self._generate_energy(new_state)
            
        return new_state.advance_phase()

    def draw_cards(self, state: GameState, count: int) -> GameState:
        """Draw cards for active player."""
        player = state.active_player
        if len(player.deck) < count:
            # In TCG Pocket, running out of cards doesn't lose the game immediately
            count = len(player.deck)
            
        drawn = player.deck[:count]
        new_deck = player.deck[count:]
        new_hand = player.hand + drawn
        
        # Handle hand size limit
        if len(new_hand) > GameConstants.MAX_HAND_SIZE:
            raise ValueError("Would exceed hand size limit")
            
        new_player = replace(player, deck=new_deck, hand=new_hand)
        return self._update_player_state(state, new_player)

    def play_pokemon(self, state: GameState, card_idx: int, to_bench: bool = True) -> GameState:
        """Play a Pokemon from hand."""
        if state.phase != GamePhase.ACTION:
            raise ValueError("Can only play Pokemon in ACTION phase")
            
        player = state.active_player
        if card_idx >= len(player.hand):
            raise ValueError("Invalid card index")
            
        card = player.hand[card_idx]
        if not isinstance(card, PokemonCard):
            raise ValueError("Not a Pokemon card")
            
        # Handle evolution
        if card.stage != Stage.BASIC:
            raise ValueError("Cannot play evolution directly - use evolve_pokemon instead")
            
        new_hand = player.hand[:card_idx] + player.hand[card_idx + 1:]
        
        if to_bench:
            if not player.can_bench_pokemon:
                raise ValueError("Bench is full")
            new_bench = player.bench + [card]
            new_player = replace(player, hand=new_hand, bench=new_bench)
        else:
            if player.has_active_pokemon:
                raise ValueError("Active slot is occupied")
            new_player = replace(player, hand=new_hand, active_pokemon=card)
            
        # Update turn state
        new_turn_state = replace(
            state.turn_state,
            pokemon_played_this_turn=state.turn_state.pokemon_played_this_turn | {card.id}
        )
        
        new_state = self._update_player_state(state, new_player)
        return replace(new_state, turn_state=new_turn_state)

    def evolve_pokemon(self, state: GameState, card_idx: int, target_id: str) -> GameState:
        """Evolve a Pokemon in play."""
        if state.phase != GamePhase.ACTION:
            raise ValueError("Can only evolve in ACTION phase")
            
        player = state.active_player
        if card_idx >= len(player.hand):
            raise ValueError("Invalid card index")
            
        evolution = player.hand[card_idx]
        if not isinstance(evolution, PokemonCard) or evolution.stage == Stage.BASIC:
            raise ValueError("Not an evolution card")
            
        if not player.can_evolve_pokemon(evolution, target_id):
            raise ValueError("Invalid evolution target")
            
        # Find and update target Pokemon
        new_player = player
        if player.active_pokemon and player.active_pokemon.id == target_id:
            evolved = replace(
                evolution,
                attached_energies=player.active_pokemon.attached_energies,
                damage_counters=player.active_pokemon.damage_counters,
                attached_tool=player.active_pokemon.attached_tool
            )
            new_player = replace(new_player, active_pokemon=evolved)
        else:
            for i, pokemon in enumerate(player.bench):
                if pokemon.id == target_id:
                    evolved = replace(
                        evolution,
                        attached_energies=pokemon.attached_energies,
                        damage_counters=pokemon.damage_counters,
                        attached_tool=pokemon.attached_tool
                    )
                    new_bench = list(player.bench)
                    new_bench[i] = evolved
                    new_player = replace(new_player, bench=new_bench)
                    break
        
        # Remove evolution card from hand
        new_hand = player.hand[:card_idx] + player.hand[card_idx + 1:]
        new_player = replace(new_player, hand=new_hand)
        
        # Update turn state
        new_turn_state = replace(
            state.turn_state,
            pokemon_evolved_this_turn=state.turn_state.pokemon_evolved_this_turn | {evolution.id}
        )
        
        new_state = self._update_player_state(state, new_player)
        return replace(new_state, turn_state=new_turn_state)

    def attach_energy(self, state: GameState, target_id: str) -> GameState:
        """Attach energy from zone to a Pokemon."""
        if state.phase != GamePhase.ACTION:
            raise ValueError("Can only attach energy in ACTION phase")
            
        if state.turn_state.energy_attached:
            raise ValueError("Already attached energy this turn")
            
        player = state.active_player
        if not player.energy_zone.current_energy:
            raise ValueError("No energy in zone")
            
        # Find target Pokemon
        target = None
        new_player = player
        energy = player.energy_zone.current_energy
        
        if player.active_pokemon and player.active_pokemon.id == target_id:
            target = player.active_pokemon
            new_active = replace(
                target,
                attached_energies=target.attached_energies + [energy]
            )
            new_player = replace(new_player, active_pokemon=new_active)
        else:
            for i, pokemon in enumerate(player.bench):
                if pokemon.id == target_id:
                    target = pokemon
                    new_pokemon = replace(
                        target,
                        attached_energies=target.attached_energies + [energy]
                    )
                    new_bench = list(player.bench)
                    new_bench[i] = new_pokemon
                    new_player = replace(new_player, bench=new_bench)
                    break
                    
        if not target:
            raise ValueError("Target Pokemon not found")
            
        # Clear energy zone
        new_zone = replace(player.energy_zone, current_energy=None)
        new_player = replace(new_player, energy_zone=new_zone)
        
        # Update turn state
        new_turn_state = replace(state.turn_state, energy_attached=True)
        
        new_state = self._update_player_state(state, new_player)
        return replace(new_state, turn_state=new_turn_state)

    def play_trainer(self, state: GameState, card_idx: int, 
                    target_id: Optional[str] = None) -> GameState:
        """Play a trainer card."""
        if state.phase != GamePhase.ACTION:
            raise ValueError("Can only play trainers in ACTION phase")
            
        player = state.active_player
        if card_idx >= len(player.hand):
            raise ValueError("Invalid card index")
            
        card = player.hand[card_idx]
        if not isinstance(card, TrainerCard):
            raise ValueError("Not a trainer card")
            
        # Handle different trainer types
        if isinstance(card, SupporterCard):
            if state.turn_state.supporter_played:
                raise ValueError("Already played a supporter this turn")
        elif isinstance(card, ToolCard):
            if not target_id:
                raise ValueError("Tool card requires a target")
                
        # Apply effects and update state
        new_state = self._apply_trainer_effects(state, card, target_id)
        
        # Remove from hand and update discard
        new_hand = player.hand[:card_idx] + player.hand[card_idx + 1:]
        new_discard = player.discard_pile + [card]
        new_player = replace(
            new_state.active_player,
            hand=new_hand,
            discard_pile=new_discard
        )
        
        # Update turn state for supporters
        new_turn_state = state.turn_state
        if isinstance(card, SupporterCard):
            new_turn_state = replace(new_turn_state, supporter_played=True)
            
        new_state = self._update_player_state(new_state, new_player)
        return replace(new_state, turn_state=new_turn_state)

    def execute_attack(self, state: GameState, attack_idx: int) -> GameState:
        """Execute an attack."""
        if state.phase != GamePhase.ATTACK:
            raise ValueError("Can only attack in ATTACK phase")
            
        attacker = state.active_player.active_pokemon
        defender = state.inactive_player.active_pokemon
        
        if not attacker or not defender:
            raise ValueError("Both players must have active Pokemon")
            
        if not attacker.can_attack:
            raise ValueError("Pokemon cannot attack")
            
        if attack_idx >= len(attacker.attacks):
            raise ValueError("Invalid attack index")
            
        attack = attacker.attacks[attack_idx]
        
        # Handle confused Pokemon
        if attacker.status_condition == StatusCondition.CONFUSED:
            if not self.flip_coin():
                # Attack fails, turn ends
                return state.advance_phase()
        
        # Calculate and apply damage
        damage = self._calculate_damage(attack, attacker, defender)
        new_defender = replace(
            defender,
            damage_counters=defender.damage_counters + damage
        )
        
        # Check for knockout
        if new_defender.is_knocked_out:
            points = new_defender.points_when_kod
            new_state = self._handle_knockout(state, new_defender)
            return self._award_points(new_state, state.active_player_tag, points)
        
        # Update defender
        new_opponent = replace(
            state.inactive_player,
            active_pokemon=new_defender
        )
        new_state = self._update_player_state(state, new_opponent)
        
        # Update turn state
        new_turn_state = replace(state.turn_state, attacked=True)
        return replace(new_state, turn_state=new_turn_state)

    def process_checkup(self, state: GameState) -> GameState:
        """Process end-of-turn effects and status conditions."""
        if state.phase != GamePhase.CHECKUP:
            raise ValueError("Can only process checkup in CHECKUP phase")
            
        new_state = state
        
        # Process status conditions in order
        for condition in GameConstants.STATUS_RESOLUTION_ORDER:
            new_state = self._process_status_condition(new_state, condition)
            
        # Check for knockouts from status damage
        new_state = self._check_knockouts(new_state)
        
        return new_state.advance_phase()

    def _validate_deck(self, deck: List[Card]) -> bool:
        """Validate deck according to TCG Pocket rules."""
        if len(deck) != GameConstants.DECK_SIZE:
            return False
        
        # Must have at least one Basic Pokemon
        basic_count = sum(
            1 for card in deck
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC
        )
        if basic_count == 0:
            return False
        
        # Maximum 2 copies of any card
        card_counts: Dict[str, int] = {}
        for card in deck:
            card_counts[card.name] = card_counts.get(card.name, 0) + 1
            if card_counts[card.name] > GameConstants.MAX_COPIES_PER_CARD:
                return False
        
        return True
    
    def _calculate_damage(self, attack: Attack, attacker: PokemonCard, 
                         defender: PokemonCard) -> int:
        """Calculate attack damage including weakness."""
        damage = attack.damage
        
        # Apply weakness
        if defender.weakness == attacker.pokemon_type:
            damage += GameConstants.WEAKNESS_BONUS
            
        return damage

    def _process_status_condition(self, state: GameState, 
                                condition: StatusCondition) -> GameState:
        """Process a specific status condition."""
        player = state.active_player
        if not player.active_pokemon:
            return state
            
        pokemon = player.active_pokemon
        if pokemon.status_condition != condition:
            return state
            
        new_pokemon = pokemon
        new_state = state
        
        if condition == StatusCondition.POISONED:
            new_pokemon = replace(
                pokemon,
                damage_counters=pokemon.damage_counters + GameConstants.POISON_DAMAGE
            )
        elif condition == StatusCondition.BURNED:
            new_pokemon = replace(
                pokemon,
                damage_counters=pokemon.damage_counters + GameConstants.BURN_DAMAGE
            )
            if self.flip_coin():  # Heads cures burn
                new_pokemon = replace(new_pokemon, status_condition=None)
        elif condition == StatusCondition.ASLEEP:
            if self.flip_coin():  # Heads wakes up
                new_pokemon = replace(new_pokemon, status_condition=None)
        elif condition == StatusCondition.PARALYZED:
            # Wears off during checkup
            new_pokemon = replace(new_pokemon, status_condition=None)
            
        if new_pokemon != pokemon:
            new_player = self._update_pokemon_in_player(player, new_pokemon)
            new_state = self._update_player_state(state, new_player)
            
        return new_state

    def flip_coin(self) -> bool:
        """Flip a coin."""
        return self.rng.choice([True, False])

    def _handle_knockout(self, state: GameState, knocked_out: PokemonCard) -> GameState:
        """Handle a Pokemon being knocked out."""
        player = state.inactive_player  # Owner of knocked out Pokemon
        
        # Move to discard pile
        new_discard = player.discard_pile + [knocked_out]
        
        # Clear active slot
        new_player = replace(
            player,
            active_pokemon=None,
            discard_pile=new_discard
        )
                           
        return self._update_player_state(state, new_player)

    def _award_points(self, state: GameState, player_tag: PlayerTag, 
                     points: int) -> GameState:
        """Award points to a player."""
        if player_tag == PlayerTag.PLAYER:
            new_player = replace(
                state.player,
                points=state.player.points + points
            )
            return replace(state, player=new_player)
        else:
            new_opponent = replace(
                state.opponent,
                points=state.opponent.points + points
            )
            return replace(state, opponent=new_opponent)

    def _update_player_state(self, state: GameState, new_player: PlayerState) -> GameState:
        """Update the state with new player state."""
        if new_player.tag == PlayerTag.PLAYER:
            return replace(state, player=new_player)
        return replace(state, opponent=new_player)

    def _generate_energy(self, state: GameState) -> GameState:
        """Generate energy in active player's zone if empty."""
        player = state.active_player
        if not player.energy_zone.can_generate_energy():
            return state
            
        energy = player.energy_zone.generate_energy(self.rng)
        new_zone = replace(player.energy_zone, current_energy=energy)
        new_player = replace(player, energy_zone=new_zone)
        return self._update_player_state(state, new_player)