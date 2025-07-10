"""Tests for PokemonTCGEnv integration with GameEngine."""

import pytest
import numpy as np
from typing import List
import copy

from src.env.pokemon_env import PokemonTCGEnv
from src.rules.game_state import GamePhase
from src.card_db.core import (
    PokemonCard, ItemCard, SupporterCard, Attack, Effect, 
    EnergyType, Stage, TargetType,
)
from src.rules.actions import ActionType, Action


@pytest.fixture
def test_decks():
    """Create test decks for integration testing."""
    # Create unique cards for each position to avoid any reference issues
    player_deck = []
    opponent_deck = []
    
    # Create player deck with unique cards
    for i in range(10):
        basic_pokemon = PokemonCard(
            id=f"TEST-001-{i}",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[
                Attack(
                    name="Test Attack",
                    cost=[EnergyType.COLORLESS],
                    damage=30
                )
            ]
        )
        player_deck.append(basic_pokemon)
    
    for i in range(5):
        fire_pokemon = PokemonCard(
            id=f"TEST-002-{i}",
            name="Fire Pokemon",
            hp=80,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[
                Attack(
                    name="Fire Attack",
                    cost=[EnergyType.FIRE],
                    damage=40
                )
            ]
        )
        player_deck.append(fire_pokemon)
    
    for i in range(5):
        grass_pokemon = PokemonCard(
            id=f"TEST-003-{i}",
            name="Grass Pokemon",
            hp=90,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            weakness=EnergyType.FIRE,
            attacks=[
                Attack(
                    name="Grass Attack",
                    cost=[EnergyType.GRASS],
                    damage=35
                )
            ]
        )
        player_deck.append(grass_pokemon)
    
    # Create opponent deck with unique cards
    for i in range(10):
        grass_pokemon = PokemonCard(
            id=f"OPP-GRASS-{i}",
            name="Grass Pokemon",
            hp=90,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            weakness=EnergyType.FIRE,
            attacks=[
                Attack(
                    name="Grass Attack",
                    cost=[EnergyType.GRASS],
                    damage=35
                )
            ]
        )
        opponent_deck.append(grass_pokemon)
    
    for i in range(5):
        basic_pokemon = PokemonCard(
            id=f"OPP-BASIC-{i}",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[
                Attack(
                    name="Test Attack",
                    cost=[EnergyType.COLORLESS],
                    damage=30
                )
            ]
        )
        opponent_deck.append(basic_pokemon)
    
    for i in range(5):
        fire_pokemon = PokemonCard(
            id=f"OPP-FIRE-{i}",
            name="Fire Pokemon",
            hp=80,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[
                Attack(
                    name="Fire Attack",
                    cost=[EnergyType.FIRE],
                    damage=40
                )
            ]
        )
        opponent_deck.append(fire_pokemon)
    
    return player_deck, opponent_deck


class TestPokemonTCGEnvIntegration:
    
    def test_attack_with_weakness(self, test_decks):
        """Test that attacks properly apply weakness damage."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Set the phase to MAIN for Pokémon play (not ATTACK)
        env.state.phase = GamePhase.MAIN
        
        # Find the actual card object in hand
        pokemon_in_hand = None
        for card in env.state.player.hand:
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC:
                pokemon_in_hand = card
                break
        
        assert pokemon_in_hand is not None
        
        # Find the legal action that uses this exact card object (use object identity)
        legal_actions = env._get_legal_actions()
        play_action = None
        for action in legal_actions:
            if (action.type == ActionType.PLAY_POKEMON and
                action.source_card is pokemon_in_hand):
                play_action = action
                break
        
        assert play_action is not None, "No legal PLAY_POKEMON action for the card in hand"
        
        result = env._apply_action(play_action)
        assert result["success"]
        
        # Now the active Pokemon should be set correctly
        assert env.state.player.active_pokemon is not None
        assert env.state.player.active_pokemon.id == pokemon_in_hand.id
        
        # Add energy to the Pokemon (use the energy type that matches the Pokemon)
        energy_type = env.state.player.active_pokemon.pokemon_type
        env.state.player.active_pokemon.attached_energies = [energy_type]
        
        # Create a Fire Pokemon for the opponent to test weakness
        fire_pokemon = PokemonCard(
            id="TEST-FIRE-001",
            name="Test Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC
        )
        env.state.opponent.active_pokemon = fire_pokemon
        
        # Set the phase to ATTACK for attack validation
        env.state.phase = GamePhase.ATTACK
        
        # Test attack with weakness
        attack_action = Action(
            type=ActionType.USE_ATTACK,
            source_card=env.state.player.active_pokemon,
            target_card=fire_pokemon,
            attack_index=0
        )
        
        result = env._apply_action(attack_action)
        # Should succeed and apply weakness damage
        assert result["success"]
    
    def test_evolution_validation(self, test_decks):
        """Test that evolution uses GameEngine validation."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Find the actual card object in hand and play it
        pokemon_in_hand = None
        for card in env.state.player.hand:
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC:
                pokemon_in_hand = card
                break
        
        assert pokemon_in_hand is not None
        
        # Find the legal action that uses this exact card object
        legal_actions = env._get_legal_actions()
        play_action = None
        for action in legal_actions:
            if (action.type == ActionType.PLAY_POKEMON and 
                action.source_card is pokemon_in_hand):
                play_action = action
                break
        
        assert play_action is not None, "No legal PLAY_POKEMON action for the card in hand"
        
        result = env._apply_action(play_action)
        assert result["success"]
        
        # Try to evolve with an invalid evolution (should fail)
        invalid_evolution = PokemonCard(
            id="EVOLUTION-001",
            name="Invalid Evolution",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_2,  # Can't evolve from basic to stage 2
            evolves_from="Wrong Pokemon"
        )
        
        env.state.player.hand.append(invalid_evolution)
        
        # Should not be able to evolve
        evolution_actions = [a for a in env._get_legal_actions() if a.type == ActionType.EVOLVE_POKEMON]
        assert len(evolution_actions) == 0
    
    def test_energy_attachment_validation(self, test_decks):
        """Test that energy attachment uses GameEngine validation."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Find the actual card object in hand and play it
        pokemon_in_hand = None
        for card in env.state.player.hand:
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC:
                pokemon_in_hand = card
                break
        
        assert pokemon_in_hand is not None
        
        # Find the legal action that uses this exact card object
        legal_actions = env._get_legal_actions()
        play_action = None
        for action in legal_actions:
            if (action.type == ActionType.PLAY_POKEMON and 
                action.source_card is pokemon_in_hand):
                play_action = action
                break
        
        assert play_action is not None, "No legal PLAY_POKEMON action for the card in hand"
        
        result = env._apply_action(play_action)
        assert result["success"]
        
        # Generate energy in the Energy Zone (TCG Pocket rulebook §5)
        env.state.player.energy_zone = EnergyType.FIRE
        
        # Try to attach energy (should succeed)
        energy_actions = [a for a in env._get_legal_actions() if a.type == ActionType.ATTACH_ENERGY]
        if energy_actions:
            result1 = env._apply_action(energy_actions[0])
            assert result1["success"]
            
            # Second attachment should fail (turn limit)
            energy_actions2 = [a for a in env._get_legal_actions() if a.type == ActionType.ATTACH_ENERGY]
            assert len(energy_actions2) == 0  # No more energy attachment actions available
    
    def test_game_over_detection(self, test_decks):
        """Test that game over detection uses GameEngine."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Add some Pokemon to avoid the "no Pokemon in play" condition
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Ensure both players have active Pokemon
        env.state.player.active_pokemon = basic_pokemon
        env.state.opponent.active_pokemon = basic_pokemon
        
        # Game should not be over initially
        winner = env.game_engine.check_game_over(env.state)
        assert winner is None
        
        # Simulate player winning by reaching 3 points (rulebook §10)
        env.state.player.points = 3
        winner = env.game_engine.check_game_over(env.state)
        assert winner == "player"
        
        # Reset and test opponent winning
        env.state.player.points = 0
        env.state.opponent.points = 3
        winner = env.game_engine.check_game_over(env.state)
        assert winner == "opponent"

    def test_debug_pokemon_play(self, test_decks):
        """Debug test to understand the Pokemon play issue."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Check initial state
        print(f"Initial hand size: {len(env.state.player.hand)}")
        print(f"Initial deck size: {len(env.state.player.deck)}")
        print(f"Hand cards: {[card.name for card in env.state.player.hand]}")
        print(f"Deck cards: {[card.name for card in env.state.player.deck[:5]]}")  # First 5 cards
        
        # Check if we have Pokemon in hand
        pokemon_in_hand = [card for card in env.state.player.hand if isinstance(card, PokemonCard)]
        print(f"Pokemon in hand: {[p.name for p in pokemon_in_hand]}")
        
        # Get legal actions
        legal_actions = env._get_legal_actions()
        print(f"Legal actions: {[a.type for a in legal_actions[:5]]}")  # First 5 actions
        
        # Check if first action is PLAY_POKEMON
        if legal_actions and legal_actions[0].type == ActionType.PLAY_POKEMON:
            print(f"First action is PLAY_POKEMON with card: {legal_actions[0].source_card.name}")
            
            # Apply the action
            result = env._apply_action(legal_actions[0])
            print(f"Action result: {result}")
            print(f"Active Pokemon after action: {env.state.player.active_pokemon}")
            print(f"Bench after action: {[p.name for p in env.state.player.bench]}")
            print(f"Hand after action: {[card.name for card in env.state.player.hand]}")
            
            assert result["success"]
            assert env.state.player.active_pokemon is not None
        else:
            print("First action is not PLAY_POKEMON!")
            print(f"First action type: {legal_actions[0].type if legal_actions else 'No actions'}")

    def test_debug_object_identity(self, test_decks):
        """Debug test to understand object identity issues."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Find Pokemon in hand
        pokemon_in_hand = None
        for card in env.state.player.hand:
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC:
                pokemon_in_hand = card
                break
        
        assert pokemon_in_hand is not None
        
        # Get legal actions
        legal_actions = env._get_legal_actions()
        
        # Debug: Print information about the card and actions
        print(f"Pokemon in hand: {pokemon_in_hand.name} (id: {id(pokemon_in_hand)})")
        print(f"Hand cards: {[(card.name, id(card)) for card in env.state.player.hand if isinstance(card, PokemonCard)]}")
        
        play_actions = [a for a in legal_actions if a.type == ActionType.PLAY_POKEMON]
        print(f"PLAY_POKEMON actions: {[(a.source_card.name, id(a.source_card)) for a in play_actions]}")
        
        # Check if any action uses the same object
        matching_action = None
        for action in play_actions:
            if action.source_card is pokemon_in_hand:
                matching_action = action
                break
        
        if matching_action:
            print(f"Found matching action!")
            result = env._apply_action(matching_action)
            print(f"Action result: {result}")
            print(f"Active Pokemon: {env.state.player.active_pokemon}")
        else:
            print("No matching action found!")
            print("This means the action validator is creating actions with different card objects.") 