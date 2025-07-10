"""Selection functions for trainer effects."""

from typing import List
from .context import EffectContext
from src.card_db.core import PokemonCard

def player_chooses_target(ctx: EffectContext, targets: List[PokemonCard] = None) -> EffectContext:
    """Let player choose from available targets."""
    if targets is None:
        targets = ctx.targets
    
    print(f"DEBUG: Available targets: {[p.name for p in targets] if targets else 'None'}")
    
    if not targets:
        ctx.failed = True
        return ctx
    
    # For now, just pick the first target (in a real game, this would be UI)
    ctx.data['selected_target'] = targets[0]
    print(f"Player selected: {targets[0].name}")
    return ctx

def opponent_chooses_target(ctx: EffectContext, targets: List[PokemonCard] = None) -> EffectContext:
    """Let opponent choose from available targets."""
    if targets is None:
        targets = ctx.targets
    
    if not targets:
        ctx.failed = True
        return ctx
    
    # For now, just pick the first target (in a real game, this would be opponent AI/UI)
    ctx.data['selected_target'] = targets[0]
    print(f"Opponent selected: {targets[0].name}")
    return ctx

def random_target(ctx: EffectContext, targets: List[PokemonCard] = None) -> EffectContext:
    """Randomly select a target."""
    import random
    if targets is None:
        targets = ctx.targets
    
    if not targets:
        ctx.failed = True
        return ctx
    
    selected = random.choice(targets)
    ctx.data['selected_target'] = selected
    print(f"Randomly selected: {selected.name}")
    return ctx

def all_targets(ctx: EffectContext, targets: List[PokemonCard] = None) -> EffectContext:
    """Select all available targets."""
    if targets is None:
        targets = ctx.targets
    
    if not targets:
        ctx.failed = True
        return ctx
    
    ctx.data['selected_targets'] = targets
    print(f"Selected all {len(targets)} targets")
    return ctx

def set_target_to_active(ctx: EffectContext, target_player: str = "player") -> EffectContext:
    """Set the target to the active Pokemon."""
    target = ctx.opponent if target_player == "opponent" else ctx.player
    if not target.active_pokemon:
        ctx.failed = True
        return ctx
    
    ctx.data['selected_target'] = target.active_pokemon
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
