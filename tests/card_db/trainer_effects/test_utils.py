"""Shared test utilities for card database tests."""
from dataclasses import field
from typing import List, Optional
from src.card_db.core import (
    PokemonCard, EnergyType, Stage, Attack, Card,
    ItemCard, SupporterCard, ToolCard, Effect
)
from src.card_db.trainer_effects.context import EffectContext
from src.rules.game_state import GameState, PlayerState, PlayerTag
from src.rules.game_engine import GameEngine, CoinFlipResult

def create_test_pokemon(
    name: str,
    hp: int = 100,
    pokemon_type: EnergyType = EnergyType.COLORLESS,
    damage: int = 0,
    attacks: Optional[List[Attack]] = None
) -> PokemonCard:
    """Create a test Pokemon card."""
    if attacks is None:
        attacks = [Attack(name="Test Attack", cost=[], damage=10)]
    
    return PokemonCard(
        id=f"test-{name.lower()}",
        name=name,
        hp=hp,
        pokemon_type=pokemon_type,
        stage=Stage.BASIC,
        attacks=attacks,
        damage_counters=damage
    )

def create_test_context(with_active: bool = True) -> EffectContext:
    """Create a test effect context with basic setup."""
    player = PlayerState(player_tag=PlayerTag.PLAYER)
    opponent = PlayerState(player_tag=PlayerTag.OPPONENT)
    game_state = GameState(player=player, opponent=opponent)
    game_engine = GameEngine()
    
    if with_active:
        player.active_pokemon = create_test_pokemon("Active")
        opponent.active_pokemon = create_test_pokemon("OpponentActive")
    
    return EffectContext(
        game_state=game_state,
        player=player,
        opponent=opponent,
        game_engine=game_engine
    )

def create_test_item_card(name: str, effects: List[str] = None) -> ItemCard:
    """Create a test item card."""
    return ItemCard(
        id=f"test-item-{name.lower()}",
        name=name,
        effects=effects or []
    )

def create_test_supporter_card(name: str, effects: List[str] = None) -> SupporterCard:
    """Create a test supporter card."""
    return SupporterCard(
        id=f"test-supporter-{name.lower()}",
        name=name,
        effects=effects or []
    )

def create_test_tool_card(name: str, effects: List[str] = None) -> ToolCard:
    """Create a test tool card."""
    if effects is None:
        effects = []
    effects = [Effect(text=effect) for effect in effects]  # Convert string effects to Effect objects
    
    return ToolCard(
        id=f"test-tool-{name.lower()}",
        name=name,
        effects=effects,
        description=None,
        attached_to=None,
        owner=None,
        set_code="N/A",
        rarity=None
    ) 