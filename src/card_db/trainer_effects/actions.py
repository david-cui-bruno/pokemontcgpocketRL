"""Action functions for trainer effects."""

from typing import List, Callable
from .context import EffectContext
from src.card_db.core import EnergyType, PokemonCard

def switch_opponent_active(ctx: EffectContext) -> EffectContext:
    """Switch opponent's active Pokemon with selected benched Pokemon."""
    selected = ctx.data.get('selected_target')
    if not selected or selected not in ctx.opponent.bench:
        ctx.failed = True
        return ctx
    
    # Perform the switch
    old_active = ctx.opponent.active_pokemon
    ctx.opponent.active_pokemon = selected
    ctx.opponent.bench.remove(selected)
    if old_active:
        ctx.opponent.bench.append(old_active)
    
    print(f"Switched opponent's active Pokemon to {selected.name}")
    return ctx

def return_to_hand(ctx: EffectContext, target_player: str = "player") -> EffectContext:
    """Return selected Pokemon to hand."""
    selected = ctx.data.get('selected_target')
    target = ctx.opponent if target_player == "opponent" else ctx.player
    
    if not selected:
        ctx.failed = True
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
    """Heal selected Pokemon by amount."""
    selected = ctx.data.get('selected_target')
    if not selected:
        ctx.failed = True
        return ctx
    
    old_damage = selected.damage_counters
    selected.damage_counters = max(0, selected.damage_counters - amount)
    healed = old_damage - selected.damage_counters
    
    print(f"Healed {healed} damage from {selected.name}")
    return ctx

def attach_energy_from_zone(ctx: EffectContext, energy_type: EnergyType, amount: int = 1) -> EffectContext:
    """Attach energy from energy zone to selected Pokemon."""
    selected = ctx.data.get('selected_target')
    if not selected:
        ctx.failed = True
        return ctx
    
    attached_count = 0
    for _ in range(amount):
        if ctx.player.energy_zone == energy_type:
            selected.attached_energies.append(energy_type)
            ctx.player.energy_zone = None
            attached_count += 1
            print(f"Attached {energy_type.value} energy to {selected.name}")
        else:
            break
    
    if attached_count == 0:
        ctx.failed = True
        print(f"No {energy_type.value} energy available in Energy Zone")
    
    return ctx

def attach_energy_from_discard(ctx: EffectContext, energy_type: EnergyType, amount: int = 1) -> EffectContext:
    """Attach energy from discard pile to selected Pokemon."""
    selected = ctx.data.get('selected_target')
    if not selected:
        ctx.failed = True
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
        ctx.failed = True
        return ctx
    
    if source.attached_energies:
        energy = source.attached_energies.pop(0)
        target.attached_energies.append(energy)
        print(f"Moved {energy.value} energy from {source.name} to {target.name}")
    else:
        ctx.failed = True
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
        ctx.failed = True
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
    """Draw cards from deck."""
    drawn = 0
    for _ in range(min(count, len(ctx.player.deck))):
        if ctx.player.deck:
            ctx.player.hand.append(ctx.player.deck.pop())
            drawn += 1
    
    print(f"Drew {drawn} cards")
    return ctx
