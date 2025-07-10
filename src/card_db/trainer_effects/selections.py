"""Selection functions for trainer effects."""

from typing import List
from .context import EffectContext
from src.card_db.core import PokemonCard

def player_chooses_target(ctx: EffectContext) -> EffectContext:
    """Let player choose a target Pokemon."""
    available = [ctx.player.active_pokemon] + ctx.player.bench if ctx.player.active_pokemon else ctx.player.bench
    if not available:
        ctx.failed = True
        return ctx
    
    selected = ctx.game_engine.choose_pokemon(available)
    if selected:
        ctx.targets = [selected]
    else:
        ctx.failed = True
    return ctx

def opponent_chooses_target(ctx: EffectContext) -> EffectContext:
    """Let opponent choose a target Pokemon."""
    available = [ctx.opponent.active_pokemon] + ctx.opponent.bench if ctx.opponent.active_pokemon else ctx.opponent.bench
    if not available:
        ctx.failed = True
        return ctx
    
    selected = ctx.game_engine.choose_pokemon(available)
    if selected:
        ctx.targets = [selected]
    else:
        ctx.failed = True
    return ctx

def random_target(ctx: EffectContext) -> EffectContext:
    """Choose a random target Pokemon."""
    import random
    available = [ctx.player.active_pokemon] + ctx.player.bench if ctx.player.active_pokemon else ctx.player.bench
    if not available:
        ctx.failed = True
        return ctx
    ctx.targets = [random.choice(available)]
    return ctx

def all_targets(ctx: EffectContext) -> EffectContext:
    """Select all Pokemon as targets."""
    targets = []
    if ctx.player.active_pokemon:
        targets.append(ctx.player.active_pokemon)
    targets.extend(ctx.player.bench)
    if not targets:
        ctx.failed = True
    else:
        ctx.targets = targets
    return ctx

def set_target_to_active(ctx: EffectContext) -> EffectContext:
    """Set active Pokemon as target."""
    if not ctx.player.active_pokemon:
        ctx.failed = True
        return ctx
    ctx.targets = [ctx.player.active_pokemon]
    return ctx

def switch_opponent_active(ctx: EffectContext) -> EffectContext:
    """Switch opponent's active Pokemon with selected benched Pokemon."""
    selected = ctx.data.get('selected_target')
    if not selected or selected not in ctx.opponent.bench:
        ctx.failed = True
        return ctx
    
    # Store the current active Pokemon
    current_active = ctx.opponent.active_pokemon
    
    # Move selected Pokemon from bench to active
    ctx.opponent.bench.remove(selected)
    ctx.opponent.active_pokemon = selected
    
    # Move current active to bench (if there was one)
    if current_active:
        ctx.opponent.bench.append(current_active)
    
    print(f"Switched opponent's active Pokemon to {selected.name}")
    return ctx
