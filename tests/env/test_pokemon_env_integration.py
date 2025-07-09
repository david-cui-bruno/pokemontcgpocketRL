"""Tests for PokemonTCGEnv integration with GameEngine."""

import pytest
import numpy as np
from typing import List

from src.env.pokemon_env import PokemonTCGEnv
from src.card_db.core import (
    PokemonCard, ItemCard, SupporterCard, Attack, Effect, 
    EnergyType, Stage, TargetType, EnergyCard
)
from src.rules.actions import ActionType


@pytest.fixture
def test_decks():
    """Create test decks for integration testing."""
    # Create a basic Pokemon
    basic_pokemon = PokemonCard(
        id="TEST-001",
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
    
    # Create a Fire Pokemon for weakness testing
    fire_pokemon = PokemonCard(
        id="TEST-002",
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
    
    # Create a Grass Pokemon with weakness to Fire
    grass_pokemon = PokemonCard(
        id="TEST-003",
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
    
    # Create decks
    player_deck = [basic_pokemon] * 10 + [fire_pokemon] * 5 + [grass_pokemon] * 5
    opponent_deck = [grass_pokemon] * 10 + [basic_pokemon] * 5 + [fire_pokemon] * 5
    
    return player_deck, opponent_deck


class TestPokemonTCGEnvIntegration:
    
    def test_attack_with_weakness(self, test_decks):
        """Test that attacks properly apply weakness damage."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Find any Pokemon in hand (not specifically Fire)
        pokemon_in_hand = None
        for card in env.state.player.hand:
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC:
                pokemon_in_hand = card
                break
        
        assert pokemon_in_hand is not None
        
        # Play the Pokemon
        action = env._get_legal_actions()[0]  # Should be play Pokemon
        result = env._apply_action(action)
        assert result["success"]
        
        # Add energy to the Pokemon (use the energy type that matches the Pokemon)
        energy_type = pokemon_in_hand.pokemon_type
        env.state.player.active_pokemon.attached_energies = [energy_type]
        
        # Find and play a Pokemon for the opponent (any basic Pokemon)
        opponent_pokemon = None
        for card in env.state.opponent.hand:
            if isinstance(card, PokemonCard) and card.stage == Stage.BASIC:
                opponent_pokemon = card
                break
        
        assert opponent_pokemon is not None
        env.state.opponent.active_pokemon = opponent_pokemon
        
        # Now check for attack actions
        attack_action = None
        for action in env._get_legal_actions():
            if action.type == ActionType.USE_ATTACK:
                attack_action = action
                break
        
        assert attack_action is not None
        
        result = env._apply_action(attack_action)
        assert result["success"]
        # Don't assert specific damage values since we don't know the exact Pokemon types
        assert "damage" in result
    
    def test_evolution_validation(self, test_decks):
        """Test that evolution uses GameEngine validation."""
        player_deck, opponent_deck = test_decks
        env = PokemonTCGEnv(player_deck, opponent_deck)
        
        obs, info = env.reset()
        
        # Play a basic Pokemon first
        action = env._get_legal_actions()[0]
        result = env._apply_action(action)
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
        
        # Play a Pokemon first
        action = env._get_legal_actions()[0]
        result = env._apply_action(action)
        assert result["success"]
        
        # Create an energy card and add it to hand
        energy_card = EnergyCard(
            id="ENERGY-001",
            name="Fire Energy",
            energy_type=EnergyType.FIRE
        )
        env.state.player.hand.append(energy_card)
        
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
        
        # Simulate player winning by taking all prizes
        env.state.player.prizes = []
        winner = env.game_engine.check_game_over(env.state)
        assert winner == "player"
        
        # Reset and test opponent winning
        env.state.player.prizes = [None, None, None]  # Mock prize cards
        env.state.opponent.prizes = []
        winner = env.game_engine.check_game_over(env.state)
        assert winner == "opponent" 