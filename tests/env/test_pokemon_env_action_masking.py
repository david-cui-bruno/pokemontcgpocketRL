import pytest
from unittest.mock import MagicMock, patch

from src.env.pokemon_env import PokemonTCGEnv
from src.rules.game_state import GameState, PlayerState, GamePhase
from src.rules.actions import Action, ActionType
from src.card_db.core import PokemonCard, SupporterCard, ItemCard, EnergyType, Stage

# Fixture to create a basic, clean environment for each test
@pytest.fixture
def base_env():
    # Create mock decks with simple cards
    player_deck = [PokemonCard(id=f"p{i}", name=f"P{i}", hp=60, stage=Stage.BASIC) for i in range(20)]
    opponent_deck = [PokemonCard(id=f"o{i}", name=f"O{i}", hp=60, stage=Stage.BASIC) for i in range(20)]
    
    env = PokemonTCGEnv(player_deck=player_deck, opponent_deck=opponent_deck)
    # Reset to a known state before each test
    env.reset()
    return env

def get_action_types(actions: list[Action]) -> set[ActionType]:
    """Helper to extract the types from a list of Action objects."""
    return {a.action_type for a in actions}

# Test 1: Action masking at the start of the game
def test_initial_turn_action_mask(base_env):
    # On the first turn, the player cannot attack but can play supporters, basics, etc.
    # We are assuming the first turn player also cannot draw.
    base_env.state.turn_number = 1
    
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)

    assert ActionType.DRAW_CARD not in action_types, "Should not be able to draw on turn 1"
    assert ActionType.ATTACK not in action_types, "Should not be able to attack on turn 1"
    assert ActionType.PLAY_SUPPORTER_CARD in action_types, "Should be able to play a supporter on turn 1"
    assert ActionType.END_TURN in action_types, "Should always be able to end turn"

# Test 2: Action masking after a supporter has been played
def test_supporter_action_masking(base_env):
    # Set the state to indicate a supporter was already played this turn
    base_env.state.player.supporter_played_this_turn = True
    
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    
    assert ActionType.PLAY_SUPPORTER_CARD not in action_types, "Cannot play a second supporter in one turn"

# Test 3: Attack action is only available with an active Pokemon
def test_attack_action_requires_active_pokemon(base_env):
    # Case 1: No active Pokemon
    base_env.state.player.active_pokemon = None
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    assert ActionType.ATTACK not in action_types, "Cannot attack without an active Pokemon"
    
    # Case 2: Active Pokemon is present
    base_env.state.player.active_pokemon = PokemonCard(id="p_active", name="Active Mon", hp=100)
    # Opponent also needs an active for an attack to be valid
    base_env.state.opponent.active_pokemon = PokemonCard(id="o_active", name="Opponent Mon", hp=100)
    
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    assert ActionType.ATTACK in action_types, "Should be able to attack with an active Pokemon"

# Test 4: Evolution action requires a valid target on the board
@patch('src.rules.actions.ActionValidator.get_valid_evolutions')
def test_evolve_action_masking(mock_get_valid_evolutions, base_env):
    # Case 1: No valid evolution targets exist
    mock_get_valid_evolutions.return_value = []
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    assert ActionType.EVOLVE_POKEMON not in action_types, "Cannot evolve if no valid targets exist"

    # Case 2: Valid evolution targets exist
    # (Mocking that the validator found a valid evolution pair)
    mock_get_valid_evolutions.return_value = [(MagicMock(), MagicMock())]
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    assert ActionType.EVOLVE_POKEMON in action_types, "Should be able to evolve if targets exist"

# Test 5: Draw card action is only available in the DRAW phase
def test_draw_action_phase_locking(base_env):
    # Case 1: In MAIN phase
    base_env.state.phase = GamePhase.MAIN
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    assert ActionType.DRAW_CARD not in action_types

    # Case 2: In DRAW phase
    base_env.state.phase = GamePhase.DRAW
    legal_actions = base_env.get_legal_actions()
    action_types = get_action_types(legal_actions)
    assert ActionType.DRAW_CARD in action_types 