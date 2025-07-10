"""Execute trainer card effect chains."""

from src.card_db.trainer_effects import EffectContext
from src.card_db.comprehensive_trainer_registry import TRAINER_EFFECTS, get_effect_for_card
from src.card_db.core import TrainerCard, ItemCard, ToolCard, SupporterCard
from src.rules.game_state import GameState, PlayerState

def execute_trainer_card(card: TrainerCard, game_state: GameState, player: PlayerState, game_engine=None) -> bool:
    """Execute a trainer card's effects."""
    # First try to get effect by card name
    effect_text = get_effect_for_card(card.name)
    if effect_text:
        effect_chain = TRAINER_EFFECTS.get(effect_text)
    else:
        # Fall back to direct name lookup (for backward compatibility)
        effect_chain = TRAINER_EFFECTS.get(card.name)
    
    if not effect_chain:
        print(f"No effect defined for {card.name}")
        return False
    
    # Create context
    ctx = EffectContext(game_state, player, game_engine)
    
    # Execute each function in the chain
    for effect_fn in effect_chain:
        try:
            ctx = effect_fn(ctx)
            if ctx.failed:
                print(f"Effect chain failed for {card.name}")
                return False
        except Exception as e:
            print(f"Error executing effect for {card.name}: {e}")
            return False
    
    print(f"Successfully executed {card.name}")
    return True

def can_play_trainer_card(card: TrainerCard, game_state: GameState, player: PlayerState, game_engine=None) -> bool:
    """Check if a trainer card can be played (dry run)."""
    # For supporter cards, check if already played this turn
    if isinstance(card, SupporterCard) and player.supporter_played_this_turn:
        return False
    
    # For tool cards, check if target Pokemon already has a tool
    if isinstance(card, ToolCard):
        # This would need additional logic to check tool attachment
        return True
    
    # Try to execute the effect chain without actually applying effects
    effect_text = get_effect_for_card(card.name)
    if effect_text:
        effect_chain = TRAINER_EFFECTS.get(effect_text)
    else:
        effect_chain = TRAINER_EFFECTS.get(card.name)
    
    if not effect_chain:
        return False
    
    # Create a test context (you might want to implement a dry-run mode)
    ctx = EffectContext(game_state, player, game_engine)
    
    # For now, just check the first condition
    if effect_chain:
        try:
            test_ctx = effect_chain[0](ctx)
            return not test_ctx.failed
        except:
            return False
    
    return True

def play_trainer_card(card: TrainerCard, game_state: GameState, player: PlayerState, game_engine=None) -> bool:
    """Play a trainer card."""
    if not can_play_trainer_card(card, game_state, player, game_engine):
        print(f"Cannot play {card.name}")
        return False
    
    success = execute_trainer_card(card, game_state, player, game_engine)
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
