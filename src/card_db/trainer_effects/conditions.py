"""Condition functions for trainer effects."""

from typing import List
from .context import EffectContext
from src.card_db.core import PokemonCard, EnergyType

def require_bench_pokemon(ctx: EffectContext, target_player: str = "opponent") -> EffectContext:
    """Require that target player has Pokemon on bench."""
    target = ctx.opponent if target_player == "opponent" else ctx.player
    if not target.bench:
        ctx.failed = True
        print(f"Cannot play card: {target_player} has no benched Pokemon")
    return ctx

def require_damaged_pokemon(ctx: EffectContext, target_player: str = "opponent") -> EffectContext:
    """Filter targets to only damaged Pokemon."""
    target = ctx.opponent if target_player == "opponent" else ctx.player
    damaged_pokemon = [p for p in target.bench if p.damage_counters > 0]
    if not damaged_pokemon:
        ctx.failed = True
        print(f"Cannot play card: {target_player} has no damaged Pokemon on bench")
    else:
        ctx.targets = damaged_pokemon
    return ctx

def require_energy_in_zone(ctx: EffectContext, energy_type: EnergyType) -> EffectContext:
    """Require specific energy type in player's energy zone."""
    if ctx.player.energy_zone != energy_type:
        ctx.failed = True
        print(f"Cannot play card: No {energy_type.value} energy in Energy Zone")
    return ctx

def require_pokemon_type(ctx: EffectContext, pokemon_type: EnergyType, target_player: str = "player") -> EffectContext:
    """Filter targets to specific Pokemon type."""
    target = ctx.opponent if target_player == "opponent" else ctx.player
    typed_pokemon = [p for p in target.pokemon_in_play if p.pokemon_type == pokemon_type]
    if not typed_pokemon:
        ctx.failed = True
        print(f"Cannot play card: No {pokemon_type.value} Pokemon in play")
    else:
        ctx.targets = typed_pokemon
    return ctx

def require_specific_pokemon(ctx: EffectContext, pokemon_names: List[str], target_player: str = "player") -> EffectContext:
    """Filter targets to specific Pokemon names."""
    target = ctx.opponent if target_player == "opponent" else ctx.player
    specific_pokemon = [p for p in target.pokemon_in_play if p.name in pokemon_names]
    if not specific_pokemon:
        ctx.failed = True
        print(f"Cannot play card: No {', '.join(pokemon_names)} in play")
    else:
        ctx.targets = specific_pokemon
    return ctx

def require_active_pokemon(ctx: EffectContext, target_player: str = "player") -> EffectContext:
    """Require that target player has an active Pokemon."""
    target = ctx.opponent if target_player == "opponent" else ctx.player
    if not target.active_pokemon:
        ctx.failed = True
        print(f"Cannot play card: {target_player} has no active Pokemon")
    else:
        ctx.targets = [target.active_pokemon]
    return ctx

def require_pokemon_in_discard(ctx: EffectContext, pokemon_names: List[str] = None) -> EffectContext:
    """Require specific Pokemon in discard pile."""
    pokemon_in_discard = [card for card in ctx.player.discard_pile 
                         if isinstance(card, PokemonCard)]
    
    if pokemon_names:
        pokemon_in_discard = [p for p in pokemon_in_discard if p.name in pokemon_names]
    
    if not pokemon_in_discard:
        ctx.failed = True
        print(f"Cannot play card: No suitable Pokemon in discard pile")
    else:
        ctx.targets = pokemon_in_discard
    return ctx
