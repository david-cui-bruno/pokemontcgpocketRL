"""Action functions for trainer effects."""

import dataclasses
from typing import List, Callable, Optional, Any, Dict
from src.card_db.trainer_effects.context import EffectContext  # Fix the import
from src.card_db.core import (
    EnergyType, PokemonCard, Stage, Attack, Ability, PlayerTag, 
    StatusCondition, Effect, Card, ItemCard, SupporterCard, ToolCard
)

def attach_tool_card(ctx: EffectContext) -> EffectContext:
    """Attach a tool card to a Pokemon."""
    if not ctx.targets:
        print("No target Pokemon specified")
        return dataclasses.replace(ctx, failed=True)
    
    tool_card = ctx.data.get('tool_card')
    if not isinstance(tool_card, ToolCard):
        print(f"Not a tool card: {type(tool_card)}")
        return dataclasses.replace(ctx, failed=True)
    
    target_pokemon = ctx.targets[0]
    if target_pokemon.attached_tool:
        print(f"{target_pokemon.name} already has a tool attached")
        return dataclasses.replace(ctx, failed=True)
    
    # Create new Pokemon with tool attached
    new_pokemon = dataclasses.replace(target_pokemon, attached_tool=tool_card)
    
    # Update game state
    if target_pokemon == ctx.player.active_pokemon:
        new_player = dataclasses.replace(ctx.player, active_pokemon=new_pokemon)
    else:
        new_bench = [new_pokemon if p == target_pokemon else p for p in ctx.player.bench]
        new_player = dataclasses.replace(ctx.player, bench=new_bench)
    
    new_game_state = dataclasses.replace(ctx.game_state, player=new_player)
    return dataclasses.replace(ctx, game_state=new_game_state, player=new_player)
