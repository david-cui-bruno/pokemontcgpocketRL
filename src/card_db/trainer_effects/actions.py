"""Action functions for trainer effects."""

import dataclasses
from typing import List, Callable, Optional, Any, Dict
from .context import EffectContext
from src.card_db.core import EnergyType, PokemonCard, Stage, Attack, Ability, PlayerTag, StatusCondition, Effect
from src.card_db.core import Card
from src.card_db.core import ItemCard, SupporterCard, ToolCard

@dataclasses.dataclass(frozen=True)
class Card:
    """Base class for all cards. Contains only universally required fields."""
    id: str
    name: str

@dataclasses.dataclass(frozen=True)
class PokemonCard(Card):
    """Represents a Pokemon card."""
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
    attached_energies: List[EnergyType] = dataclasses.field(default_factory=list)
    damage_counters: int = 0
    status_condition: Optional[StatusCondition] = None

@dataclasses.dataclass(frozen=True)
class ItemCard(Card):
    """Represents an Item card."""
    effects: List[Effect]
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None

@dataclasses.dataclass(frozen=True)
class SupporterCard(Card):
    """Represents a Supporter card."""
    effects: List[Effect]
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None

@dataclasses.dataclass(frozen=True)
class ToolCard(Card):
    """Represents a Tool card."""
    effects: List[Effect]
    owner: Optional[PlayerTag] = None
    set_code: str = "N/A"
    rarity: Optional[str] = None

def switch_opponent_active(ctx: EffectContext) -> EffectContext:
    """Switch opponent's active Pokemon with a benched one."""
    if not ctx.targets:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    selected = ctx.targets[0]
    if selected not in ctx.opponent.bench:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    # Create new bench without the selected Pokemon
    new_bench = [p for p in ctx.opponent.bench if p != selected]
    
    # Add current active to bench if it exists
    if ctx.opponent.active_pokemon:
        new_bench.append(ctx.opponent.active_pokemon)
    
    # Update opponent state
    new_opponent = dataclasses.replace(ctx.opponent, active_pokemon=selected, bench=new_bench)
    ctx = dataclasses.replace(ctx, opponent=new_opponent)
    ctx = dataclasses.replace(ctx, game_state=dataclasses.replace(ctx.game_state, opponent=new_opponent))
    
    return ctx

def return_to_hand(ctx: EffectContext, target_player: str = "player") -> EffectContext:
    """Return selected Pokemon to hand."""
    selected = ctx.data.get('selected_target')
    target = ctx.opponent if target_player == "opponent" else ctx.player
    
    if not selected:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    # Remove from play and add to hand
    if selected == target.active_pokemon:
        target.active_pokemon = None
    elif selected in target.bench:
        target.bench.remove(selected)
    
    target.hand.append(selected)
    print(f"Returned {selected.name} to {target_player}'s hand")
    return ctx

def heal_pokemon(ctx: EffectContext, amount: int) -> EffectContext:
    """Heal a Pokemon by the specified amount."""
    # Don't heal if the effect has failed
    if ctx.failed:
        return ctx
        
    if not ctx.targets:
        # If no targets, try to use active Pokemon
        ctx = dataclasses.replace(ctx, targets=[ctx.player.active_pokemon])
        if not ctx.targets[0]:
            return ctx
    
    selected = ctx.targets[0]
    new_damage = max(0, selected.damage_counters - amount)
    new_pokemon = dataclasses.replace(selected, damage_counters=new_damage)
    
    # Update the Pokemon in the game state
    new_player = None
    if selected == ctx.player.active_pokemon:
        new_player = dataclasses.replace(ctx.player, active_pokemon=new_pokemon)
    elif selected in ctx.player.bench:
        new_bench = [new_pokemon if p == selected else p for p in ctx.player.bench]
        new_player = dataclasses.replace(ctx.player, bench=new_bench)
    
    if new_player:
        new_game_state = dataclasses.replace(ctx.game_state, player=new_player)
        ctx = dataclasses.replace(ctx, game_state=new_game_state, player=new_player)
    
    return ctx

def heal_all_pokemon(ctx: EffectContext, amount: int) -> EffectContext:
    """Heal all Pokemon by the specified amount."""
    # Get all Pokemon
    all_pokemon = [ctx.player.active_pokemon] + ctx.player.bench if ctx.player.active_pokemon else ctx.player.bench
    
    # Heal each Pokemon
    new_active = None
    new_bench = []
    
    for pokemon in all_pokemon:
        new_damage = max(0, pokemon.damage_counters - amount)
        new_pokemon = dataclasses.replace(pokemon, damage_counters=new_damage)
        
        if pokemon == ctx.player.active_pokemon:
            new_active = new_pokemon
        else:
            new_bench.append(new_pokemon)
    
    # Update game state
    new_player = dataclasses.replace(ctx.player, active_pokemon=new_active, bench=new_bench)
    new_game_state = dataclasses.replace(ctx.game_state, player=new_player)
    return dataclasses.replace(ctx, game_state=new_game_state, player=new_player)  # Add player update

def attach_energy_from_zone(ctx: EffectContext, energy_type: EnergyType) -> EffectContext:
    """Attach energy from energy zone to a Pokemon."""
    if not ctx.targets or ctx.player.energy_zone != energy_type:
        return dataclasses.replace(ctx, failed=True)
    
    selected = ctx.targets[0]
    new_energies = list(selected.attached_energies) + [energy_type]
    new_pokemon = dataclasses.replace(selected, attached_energies=new_energies)
    
    # Update the Pokemon in the game state
    if selected == ctx.player.active_pokemon:
        new_player = dataclasses.replace(ctx.player, active_pokemon=new_pokemon)
        new_game_state = dataclasses.replace(ctx.game_state, player=new_player)
        ctx = dataclasses.replace(ctx, player=new_player, game_state=new_game_state, targets=[new_pokemon])
    elif selected in ctx.player.bench:
        new_bench = list(ctx.player.bench)
        idx = new_bench.index(selected)
        new_bench[idx] = new_pokemon
        new_player = dataclasses.replace(ctx.player, bench=new_bench)
        new_game_state = dataclasses.replace(ctx.game_state, player=new_player)
        ctx = dataclasses.replace(ctx, player=new_player, game_state=new_game_state, targets=[new_pokemon])
    
    return ctx

def attach_energy_from_discard(ctx: EffectContext, energy_type: EnergyType, amount: int = 1) -> EffectContext:
    """Attach energy from discard pile to selected Pokemon."""
    selected = ctx.data.get('selected_target')
    if not selected:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    # Find energy cards in discard pile (in TCG Pocket, energy comes from Energy Zone)
    # This is for special cards like Volkner that attach from discard
    attached_count = 0
    for _ in range(amount):
        # For now, simulate having energy available
        selected.attached_energies.append(energy_type)
        attached_count += 1
        print(f"Attached {energy_type.value} energy from discard to {selected.name}")
    
    return ctx

def move_energy_between_pokemon(ctx: EffectContext) -> EffectContext:
    """Move energy from one Pokemon to another."""
    source = ctx.data.get('source_pokemon')
    target = ctx.data.get('selected_target')
    
    if not source or not target:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    if source.attached_energies:
        energy = source.attached_energies.pop(0)
        target.attached_energies.append(energy)
        print(f"Moved {energy.value} energy from {source.name} to {target.name}")
    else:
        ctx = dataclasses.replace(ctx, failed=True)
        print(f"No energy to move from {source.name}")
    
    return ctx

def coin_flip_repeat(ctx: EffectContext, effect_fn: Callable) -> EffectContext:
    """Repeat an effect for each heads in coin flips until tails."""
    from src.rules.game_engine import CoinFlipResult
    
    flip_count = 0
    while True:
        flip = ctx.game_engine.flip_coin()
        flip_count += 1
        print(f"Coin flip {flip_count}: {flip.value}")
        
        if flip == CoinFlipResult.HEADS:
            effect_fn(ctx)
            if ctx.failed:
                break
        else:
            break
    
    return ctx

def damage_bonus_this_turn(ctx: EffectContext, amount: int, pokemon_names: List[str] = None) -> EffectContext:
    """Give damage bonus to attacks this turn."""
    # Store the bonus in game state (you'd need to add this to GameState)
    if not hasattr(ctx.game_state, 'damage_bonuses'):
        ctx.game_state.damage_bonuses = {}
    
    if pokemon_names:
        for name in pokemon_names:
            ctx.game_state.damage_bonuses[name] = amount
        print(f"Attacks by {', '.join(pokemon_names)} do +{amount} damage this turn")
    else:
        ctx.game_state.damage_bonuses['all'] = amount
        print(f"All attacks do +{amount} damage this turn")
    
    return ctx

def search_deck_for_pokemon(ctx: EffectContext, pokemon_names: List[str] = None) -> EffectContext:
    """Search deck for specific Pokemon and put in hand."""
    available_pokemon = [card for card in ctx.player.deck 
                        if isinstance(card, PokemonCard)]
    
    if pokemon_names:
        available_pokemon = [p for p in available_pokemon if p.name in pokemon_names]
    
    if not available_pokemon:
        ctx = dataclasses.replace(ctx, failed=True)
        print(f"No suitable Pokemon found in deck")
        return ctx
    
    # Take the first matching Pokemon
    selected = available_pokemon[0]
    ctx.player.deck.remove(selected)
    ctx.player.hand.append(selected)
    print(f"Added {selected.name} from deck to hand")
    
    return ctx

def shuffle_hand_into_deck_and_draw(ctx: EffectContext, draw_count: int) -> EffectContext:
    """Shuffle hand into deck and draw new cards."""
    # Move hand to deck
    ctx.player.deck.extend(ctx.player.hand)
    ctx.player.hand.clear()
    
    # Shuffle deck (simulate)
    import random
    random.shuffle(ctx.player.deck)
    
    # Draw new cards
    for _ in range(min(draw_count, len(ctx.player.deck))):
        if ctx.player.deck:
            ctx.player.hand.append(ctx.player.deck.pop())
    
    print(f"Shuffled hand into deck and drew {len(ctx.player.hand)} cards")
    return ctx

def draw_cards(ctx: EffectContext, count: int) -> EffectContext:
    """Draw specified number of cards."""
    if len(ctx.player.deck) < count:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    for _ in range(count):
        card = ctx.player.deck.pop(0)
        ctx.player.hand.append(card)
    return ctx

def attach_energy_from_zone_coin_flip(ctx: EffectContext, energy_type: EnergyType) -> EffectContext:
    """Attach energy based on coin flips until tails. For each heads, attach one energy."""
    selected = ctx.data.get('selected_target')
    if not selected:
        ctx = dataclasses.replace(ctx, failed=True)
        return ctx
    
    # Count heads first to determine total energy to attach
    from src.rules.game_engine import CoinFlipResult
    
    heads_count = 0
    while True:
        flip = ctx.game_engine.flip_coin()
        print(f"Coin flip {heads_count + 1}: {flip.value}")
        
        if flip == CoinFlipResult.HEADS:
            heads_count += 1
        else:
            break
    
    print(f"Total heads: {heads_count}")
    
    # Attach energy equal to the number of heads
    for _ in range(heads_count):
        selected.attached_energies.append(energy_type)
        print(f"Attached {energy_type.value} energy to {selected.name}")
    
    if heads_count > 0:
        print(f"Attached {heads_count} {energy_type.value} energy to {selected.name}")
    else:
        print(f"No heads - no energy attached to {selected.name}")
    
    return ctx

def attach_tool_card(ctx: EffectContext) -> EffectContext:
    """Attach a tool card to a Pokemon."""
    if not ctx.targets:
        # If no targets, try to use active Pokemon
        ctx = dataclasses.replace(ctx, targets=[ctx.player.active_pokemon])
        if not ctx.targets[0]:
            return dataclasses.replace(ctx, failed=True)
    
    selected = ctx.targets[0]
    tool_card = ctx.data.get('tool_card')
    
    if not tool_card:
        print("No tool card provided")
        return dataclasses.replace(ctx, failed=True)
    
    if not isinstance(tool_card, ToolCard):
        print(f"Not a tool card: {type(tool_card)}")  # Add more debug info
        return dataclasses.replace(ctx, failed=True)
    
    # Check if Pokemon already has a tool
    if hasattr(selected, 'attached_tool') and selected.attached_tool:
        print("Pokemon already has a tool")
        return dataclasses.replace(ctx, failed=True)
        
    # Attach the tool
    new_pokemon = dataclasses.replace(selected, attached_tool=tool_card)
    
    # Update the Pokemon in the game state
    new_player = None
    if selected == ctx.player.active_pokemon:
        new_player = dataclasses.replace(ctx.player, active_pokemon=new_pokemon)
    elif selected in ctx.player.bench:
        new_bench = list(ctx.player.bench)
        idx = new_bench.index(selected)
        new_bench[idx] = new_pokemon
        new_player = dataclasses.replace(ctx.player, bench=new_bench)
    
    if new_player:
        new_game_state = dataclasses.replace(ctx.game_state, player=new_player)
        return dataclasses.replace(ctx, game_state=new_game_state, player=new_player)
    
    return ctx
