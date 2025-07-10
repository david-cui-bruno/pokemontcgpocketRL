"""Action system for Pokemon TCG Pocket.

This module defines all possible actions a player can take during their turn,
along with validation logic for when actions are legal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Dict, Any

from src.card_db.core import Card, PokemonCard, ItemCard, ToolCard, SupporterCard, Ability, Stage, StatusCondition, AbilityType
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag


class ActionType(Enum):
    """All possible action types in the game."""
    
    # Pokemon Actions
    PLAY_POKEMON = auto()      # Play basic Pokemon to bench
    EVOLVE_POKEMON = auto()    # Evolve a Pokemon in play
    RETREAT_POKEMON = auto()   # Switch active with benched Pokemon
    USE_ATTACK = auto()        # Use active Pokemon's attack
    
    # Trainer Actions
    PLAY_ITEM = auto()         # Play an item card
    PLAY_TOOL = auto()         # Play a tool card (attach to Pokemon)
    PLAY_SUPPORTER = auto()    # Play a supporter card (once per turn)
    
    # Energy Actions
    ATTACH_ENERGY = auto()     # Use energy from energy zone (once per turn)
    
    # New ability actions
    USE_ABILITY = auto()       # Use an activated ability
    TRIGGER_ABILITY = auto()   # Acknowledge a triggered ability
    
    # Other Actions
    PASS = auto()              # Do nothing (end phase/turn)


@dataclass
class Action:
    """Represents a single game action with its parameters."""
    
    type: ActionType                          # Required
    source_card: Optional[Card] = None        # Optional
    target_card: Optional[Card] = None        # Optional
    target_player: Optional[str] = None       # Optional
    attack_index: Optional[int] = None        # Optional
    target_cards: Optional[List[Card]] = None # Optional
    additional_params: Optional[Dict[str, Any]] = None  # Optional
    
    @property
    def action_type(self) -> ActionType:
        """Backward compatibility property for action_type."""
        return self.type


@dataclass
class AbilityAction:
    """Specialized action for using abilities."""
    
    type: ActionType                          # Required (from Action)
    ability: Ability                          # Required
    source_pokemon: PokemonCard               # Required
    source_card: Optional[Card] = None        # Optional (from Action)
    target_card: Optional[Card] = None        # Optional (from Action)
    target_player: Optional[str] = None       # Optional (from Action)
    attack_index: Optional[int] = None        # Optional (from Action)
    target_cards: Optional[List[Card]] = None # Optional
    additional_params: Optional[Dict[str, Any]] = None  # Optional


class ActionValidator:
    """Validates whether actions are legal in a given game state."""
    
    @staticmethod
    def can_play_pokemon(state: GameState, card: PokemonCard, target: Optional[PokemonCard] = None) -> bool:
        """Check if a Pokemon card can be played/evolved."""
        player = state.active_player_state
        
        # Basic Pokemon checks (no target provided)
        if target is None:
            if card.stage == Stage.BASIC:
                # You can always play a Pokemon if you don't have an active Pokemon
                if player.active_pokemon is None:
                    return (
                        card in player.hand and
                        state.phase == GamePhase.MAIN
                    )
                # If you have an active Pokemon, you can only play to bench if bench has space
                else:
                    return (
                        card in player.hand and
                        len(player.bench) < 3 and  # Fixed: TCG Pocket has max 3 bench
                        state.phase == GamePhase.MAIN
                    )
            else:
                # Non-basic Pokemon can't be played directly
                return False
        
        # Evolution checks (target provided)
        if card.stage == Stage.BASIC:
            # Basic Pokemon can't evolve other Pokemon
            return False
        
        # Only allow evolution if the evolution card is a higher stage than the target
        stage_order = {Stage.BASIC: 0, Stage.STAGE_1: 1, Stage.STAGE_2: 2}
        if stage_order[card.stage] <= stage_order[target.stage]:
            return False
        
        return (
            card in player.hand and
            target in player.pokemon_in_play and
            card.evolves_from == target.name and
            state.phase == GamePhase.MAIN and
            target.id not in player.pokemon_entered_play_this_turn  # Fixed: Use new tracking system
        )
    
    @staticmethod
    def can_play_item(state: GameState, card: ItemCard) -> bool:
        """Check if an Item card can be played."""
        from src.rules.game_engine import GameEngine
        engine = GameEngine()
        return engine.can_play_trainer_card_engine(card, state)
    
    @staticmethod
    def can_play_tool(state: GameState, card: ToolCard, target_pokemon: PokemonCard) -> bool:
        """Check if a Tool card can be attached."""
        from src.rules.game_engine import GameEngine
        engine = GameEngine()
        return engine.can_play_trainer_card_engine(card, state, target_pokemon)
    
    @staticmethod
    def can_play_supporter(state: GameState, card: SupporterCard) -> bool:
        """Check if a Supporter card can be played."""
        from src.rules.game_engine import GameEngine
        engine = GameEngine()
        return engine.can_play_trainer_card_engine(card, state)
    
    @staticmethod
    def can_retreat(state: GameState) -> bool:
        """Check if active Pokemon can retreat."""
        player = state.active_player_state
        if not player.active_pokemon:
            return False
            
        # Fixed: Cannot retreat if asleep or paralyzed
        if player.active_pokemon.status_condition in [StatusCondition.ASLEEP, StatusCondition.PARALYZED]:
            return False
            
        return (
            len(player.bench) > 0 and
            player.energy_zone is not None and  # Fixed: Use energy zone instead of energy count
            state.phase == GamePhase.MAIN
        )
    
    @staticmethod
    def can_attack(state: GameState, attack_index: int) -> bool:
        """Check if active Pokemon can use the specified attack."""
        player = state.active_player_state
        if not player.active_pokemon or attack_index >= len(player.active_pokemon.attacks):
            return False
            
        attack = player.active_pokemon.attacks[attack_index]
        return (
            state.phase == GamePhase.ATTACK and
            len(player.active_pokemon.attached_energies) >= len(attack.cost)  # Fixed: Check attached energies
        )
    
    @staticmethod
    def can_use_ability(
        state: GameState,
        pokemon: PokemonCard,
        ability: Ability
    ) -> bool:
        """Check if an ability can be used."""
        player = state.active_player_state
        
        # Basic checks
        if pokemon not in player.pokemon_in_play:
            return False
        if not pokemon.ability or pokemon.ability != ability:
            return False
            
        # Check ability type
        if ability.ability_type == AbilityType.STATIC:
            return False  # Static abilities are always active
        
        if ability.ability_type == AbilityType.TRIGGERED:
            return False  # Triggered abilities are handled separately
            
        # Check if we're in a valid phase
        if state.phase not in [GamePhase.MAIN]:
            return False
            
        # Check ability-specific costs and conditions
        if ability.cost and len(pokemon.attached_energies) < len(ability.cost):
            return False
            
        return True
    
    @staticmethod
    def get_legal_actions(state: GameState) -> List[Action]:
        """Get all legal actions in the current game state."""
        actions = []
        player = state.active_player_state
        
        if state.phase == GamePhase.MAIN:
            # Check Pokemon plays
            for card in player.hand:
                if isinstance(card, PokemonCard):
                    if ActionValidator.can_play_pokemon(state, card):
                        actions.append(Action(
                            type=ActionType.PLAY_POKEMON,
                            source_card=card
                        ))
                    
                    # Check evolutions
                    for pokemon in player.pokemon_in_play:
                        if ActionValidator.can_play_pokemon(state, card, pokemon):
                            actions.append(Action(
                                type=ActionType.EVOLVE_POKEMON,
                                source_card=card,
                                target_card=pokemon
                            ))
                
                # Check Trainer cards
                elif isinstance(card, ItemCard):
                    if ActionValidator.can_play_item(state, card):
                        actions.append(Action(
                            type=ActionType.PLAY_ITEM,
                            source_card=card
                        ))
                
                elif isinstance(card, ToolCard):
                    # Check if can attach to any Pokemon in play
                    for pokemon in player.pokemon_in_play:
                        if ActionValidator.can_play_tool(state, card, pokemon):
                            actions.append(Action(
                                type=ActionType.PLAY_TOOL,
                                source_card=card,
                                target_card=pokemon
                            ))
                
                elif isinstance(card, SupporterCard):
                    if ActionValidator.can_play_supporter(state, card):
                        actions.append(Action(
                            type=ActionType.PLAY_SUPPORTER,
                            source_card=card
                        ))
            
            # Check retreat
            if ActionValidator.can_retreat(state):
                actions.append(Action(type=ActionType.RETREAT_POKEMON))
            
            # Check energy attachment
            if player.can_attach_energy():
                actions.append(Action(type=ActionType.ATTACH_ENERGY))
            
            # Check abilities
            for pokemon in player.pokemon_in_play:
                if pokemon.ability and ActionValidator.can_use_ability(state, pokemon, pokemon.ability):
                    actions.append(Action(
                        type=ActionType.USE_ABILITY,
                        source_card=pokemon,
                        additional_params={"ability": pokemon.ability}
                    ))
        
        elif state.phase == GamePhase.ATTACK:
            # Check attacks
            if player.active_pokemon:
                for i, attack in enumerate(player.active_pokemon.attacks):
                    if ActionValidator.can_attack(state, i):
                        actions.append(Action(
                            type=ActionType.USE_ATTACK,
                            attack_index=i
                        ))
        
        # Always allow pass
        actions.append(Action(type=ActionType.PASS))
        
        return actions


class AbilityTriggerChecker:
    """Checks for triggered abilities and creates appropriate actions."""
    
    @staticmethod
    def check_triggers(state: GameState, trigger_type: str) -> List[AbilityAction]:
        """Check for abilities that should trigger on the given event."""
        triggered_abilities = []
        
        for player_tag in [PlayerTag.PLAYER, PlayerTag.OPPONENT]:
            player_state = state.player if player_tag == PlayerTag.PLAYER else state.opponent
            
            for pokemon in player_state.pokemon_in_play:
                if pokemon.ability and pokemon.ability.ability_type == AbilityType.TRIGGERED:
                    if pokemon.ability.trigger == trigger_type:
                        triggered_abilities.append(AbilityAction(
                            type=ActionType.TRIGGER_ABILITY,
                            ability=pokemon.ability,
                            source_pokemon=pokemon
                        ))
        
        return triggered_abilities


@dataclass
class TriggerEvent:
    """Represents an event that might trigger abilities."""
    
    type: str
    source_card: Optional[Card] = None
    target_card: Optional[Card] = None
    additional_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}


class TriggerType:
    """Common trigger types for abilities."""
    
    WHEN_PLAYED = "when_played"
    WHEN_EVOLVED = "when_evolved"
    WHEN_DAMAGED = "when_damaged"
    WHEN_KNOCKED_OUT = "when_knocked_out"
    WHEN_RETREATED = "when_retreated"
    START_OF_TURN = "start_of_turn"
    END_OF_TURN = "end_of_turn" 