import pytest
import dataclasses
from unittest.mock import patch, MagicMock

from src.rules.game_engine import GameEngine
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import EnergyType, PokemonCard, Stage, Attack

@pytest.fixture
def game_engine():
    return GameEngine()

@pytest.fixture
def base_player_state():
    """A basic player state for reuse."""
    return PlayerState(
        player_tag=PlayerTag.PLAYER,
        registered_energy_types=[EnergyType.FIRE, EnergyType.WATER]
    )

@pytest.fixture
def game_state_turn_2(base_player_state):
    """Provides a game state on Turn 2, where energy generation is legal."""
    player = base_player_state
    opponent = PlayerState(
        player_tag=PlayerTag.OPPONENT,
        registered_energy_types=[EnergyType.GRASS]
    )
    return GameState(player=player, opponent=opponent, turn_number=2, is_first_turn=False)

# --- Test Cases ---

def test_energy_generates_on_turn_start_if_buffer_is_empty(game_engine, game_state_turn_2):
    """Rule §5: At the Start Phase, if the buffer is empty it creates one Basic Energy."""
    state = dataclasses.replace(game_state_turn_2, player=dataclasses.replace(game_state_turn_2.player, energy_zone=None))
    
    with patch.object(game_engine.random, 'choice', return_value=EnergyType.FIRE):
        new_state = game_engine.process_start_of_turn(state)

    player = new_state.active_player_state
    assert player.energy_zone is not None, "Energy should be generated into the empty buffer"
    assert player.energy_zone in player.registered_energy_types, "Generated energy must match a registered type"

def test_energy_does_not_generate_if_buffer_is_full(game_engine, game_state_turn_2):
    """Rule §5: The Zone will not generate a new Energy until the slot is vacant."""
    player = dataclasses.replace(game_state_turn_2.player, energy_zone=EnergyType.FIGHTING)
    state = dataclasses.replace(game_state_turn_2, player=player)

    new_state = game_engine.process_start_of_turn(state)

    assert new_state.player.energy_zone == EnergyType.FIGHTING, "Energy buffer should not change if it's already full"

def test_no_energy_generation_on_very_first_turn(game_engine):
    """Rule §3 & §5: On Turn 0/1 the player who goes first may not attach Energy."""
    player = PlayerState(player_tag=PlayerTag.PLAYER, registered_energy_types=[EnergyType.FIRE])
    opponent = PlayerState(player_tag=PlayerTag.OPPONENT)
    state = GameState(player=player, opponent=opponent, turn_number=1, active_player=PlayerTag.PLAYER, is_first_turn=True)

    new_state = game_engine.process_start_of_turn(state)
    
    assert new_state.player.energy_zone is None, "No energy should be generated on the first player's first turn"

def test_can_attach_energy_from_zone(game_engine, game_state_turn_2):
    """Rule §5: You may attach the energy from the buffer."""
    pokemon = PokemonCard(id="p1", name="TestMon", hp=100, pokemon_type=EnergyType.GRASS, stage=Stage.BASIC, attacks=[])
    player = dataclasses.replace(game_state_turn_2.player, active_pokemon=pokemon, energy_zone=EnergyType.GRASS)
    state = dataclasses.replace(game_state_turn_2, player=player)

    new_state = game_engine.attach_energy(player, pokemon, state)

    updated_pokemon = new_state.player.active_pokemon
    assert updated_pokemon.attached_energies == [EnergyType.GRASS]
    assert new_state.player.energy_zone is None
    assert new_state.player.energy_attached_this_turn is True


def test_cannot_attach_energy_twice_in_one_turn(game_engine, game_state_turn_2):
    """A player can only perform the manual energy attachment once per turn."""
    pokemon = PokemonCard(id="p1", name="TestMon", hp=100, pokemon_type=EnergyType.GRASS, stage=Stage.BASIC, attacks=[])
    player = dataclasses.replace(game_state_turn_2.player, active_pokemon=pokemon, energy_zone=EnergyType.GRASS, energy_attached_this_turn=True)
    state = dataclasses.replace(game_state_turn_2, player=player)

    with pytest.raises(ValueError, match="Energy already attached this turn."):
        game_engine.attach_energy(player, pokemon, state)


def test_cannot_attach_from_empty_buffer(game_engine, game_state_turn_2):
    """Rule §5: Card text that says “attach an Energy” pulls from the buffer; if it is empty, the effect fails."""
    pokemon = PokemonCard(id="p1", name="TestMon", hp=100, pokemon_type=EnergyType.GRASS, stage=Stage.BASIC, attacks=[])
    player = dataclasses.replace(game_state_turn_2.player, active_pokemon=pokemon, energy_zone=None)
    state = dataclasses.replace(game_state_turn_2, player=player)

    with pytest.raises(ValueError, match="No energy in zone to attach."):
        game_engine.attach_energy(player, pokemon, state)


def test_player_state_can_attach_energy():
    """Test the PlayerState.can_attach_energy helper."""
    player = PlayerState(player_tag=PlayerTag.PLAYER)
    assert player.can_attach_energy()
    
    player_blocked = dataclasses.replace(player, energy_attached_this_turn=True)
    assert not player_blocked.can_attach_energy() 