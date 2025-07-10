import pytest
from unittest.mock import MagicMock, patch

from src.card_db.trainer_executor import execute_trainer_card, can_play_trainer_card, play_trainer_card
from src.card_db.core import ItemCard, SupporterCard, ToolCard, Card
from src.rules.game_state import GameState, PlayerState
# Corrected import: 'draw_cards' is a function, not a class
from src.card_db.trainer_effects.actions import draw_cards
# Import a condition that actually exists
from src.card_db.trainer_effects.conditions import require_energy_in_zone

# --- Fixtures ---

@pytest.fixture
def mock_player():
    """Provides a mocked PlayerState."""
    player = MagicMock(spec=PlayerState)
    player.hand = []
    player.deck = [Card(id="C-001", name="Card 1"), Card(id="C-002", name="Card 2")]
    player.discard_pile = []
    player.supporter_played_this_turn = False
    player.energy_zone = None
    return player

@pytest.fixture
def mock_game_state(mock_player):
    """Provides a mocked GameState with a player and opponent."""
    state = GameState()
    state.player = mock_player
    state.opponent = MagicMock(spec=PlayerState)
    # Helper to get the right player
    state.get_player_state.return_value = mock_player
    return state

# --- Test Cases ---

def test_execute_simple_draw_effect(mock_game_state, mock_player):
    """Tests executing a simple draw effect, mocking the action."""
    draw_effect = MagicMock(spec=draw_cards)
    card = ItemCard(id="T-001", name="Potion", effects=[(draw_effect, {"amount": 2})])
    
    execute_trainer_card(card, mock_game_state, mock_player)
    
    # Verify the mocked effect was called correctly
    draw_effect.assert_called_once_with(mock_game_state, mock_player, amount=2)

def test_can_play_supporter_card_logic(mock_game_state, mock_player):
    """Tests the logic for when a supporter card can be played."""
    supporter_card = SupporterCard(id="S-001", name="Cynthia", effects=[])
    
    # Can play if flag is False
    mock_player.supporter_played_this_turn = False
    assert can_play_trainer_card(supporter_card, mock_game_state, mock_player) is True
    
    # Cannot play if flag is True
    mock_player.supporter_played_this_turn = True
    assert can_play_trainer_card(supporter_card, mock_game_state, mock_player) is False

def test_play_supporter_sets_flag(mock_game_state, mock_player):
    """Tests that playing a supporter card correctly sets the once-per-turn flag."""
    supporter_card = SupporterCard(id="S-001", name="Cynthia", effects=[])
    mock_player.supporter_played_this_turn = False
    mock_player.hand = [supporter_card]

    # Mock the actual execution to isolate the play logic
    with patch('src.card_db.trainer_executor.execute_trainer_card') as mock_execute:
        play_trainer_card(supporter_card, mock_game_state, mock_player)
        mock_execute.assert_called_once()

    assert mock_player.supporter_played_this_turn is True

def test_play_trainer_card_moves_card_to_discard(mock_game_state, mock_player):
    """Tests that a played card is moved from hand to discard pile."""
    card = ItemCard(id="I-001", name="Test Item", effects=[])
    mock_player.hand = [card]
    
    with patch('src.card_db.trainer_executor.execute_trainer_card'):
        play_trainer_card(card, mock_game_state, mock_player)

    assert card not in mock_player.hand
    assert card in mock_player.discard_pile

def test_execute_conditional_effect_pass(mock_game_state, mock_player):
    """Tests that an effect with a passing condition is executed."""
    condition = MagicMock(spec=require_energy_in_zone, return_value=True)
    effect = MagicMock()
    # The condition is part of the effect tuple, not the card itself
    card = ItemCard(id="T-002", name="Conditional Item", effects=[(effect, {"condition": condition})])

    execute_trainer_card(card, mock_game_state, mock_player)
    
    condition.assert_called_once_with(mock_game_state, mock_player)
    effect.assert_called_once_with(mock_game_state, mock_player)

def test_execute_conditional_effect_fail(mock_game_state, mock_player):
    """Tests that an effect with a failing condition is NOT executed."""
    condition = MagicMock(spec=require_energy_in_zone, return_value=False)
    effect = MagicMock()
    # The condition is part of the effect tuple
    card = ItemCard(id="T-003", name="Conditional Item", effects=[(effect, {"condition": condition})])

    execute_trainer_card(card, mock_game_state, mock_player)

    condition.assert_called_once_with(mock_game_state, mock_player)
    effect.assert_not_called()

def test_execute_undefined_effect(mock_game_state, mock_player):
    """Tests that the system handles a card with no defined effect gracefully."""
    # A card with an empty effects list should not crash the system.
    card = ItemCard(id="T-004", name="Blank Item", effects=[])
    try:
        execute_trainer_card(card, mock_game_state, mock_player)
    except Exception as e:
        pytest.fail(f"Executing a card with no effects raised an exception: {e}") 