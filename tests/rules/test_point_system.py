"""Tests for the TCG Pocket point system."""

import pytest
import dataclasses
from unittest.mock import patch
from src.rules.game_engine import GameEngine, CoinFlipResult
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import (
    PokemonCard, Attack, EnergyType, Stage, StatusCondition
)


@pytest.fixture
def game_engine():
    return GameEngine()


@pytest.fixture
def basic_game_state():
    player = PlayerState(player_tag=PlayerTag.PLAYER)
    opponent = PlayerState(player_tag=PlayerTag.OPPONENT)
    return GameState(player=player, opponent=opponent, phase=GamePhase.MAIN)


class TestPointSystem:
    """Test the TCG Pocket point system."""
    
    def test_basic_point_awarding(self, game_engine):
        """Test basic point awarding."""
        player = PlayerState(player_tag=PlayerTag.PLAYER)
        
        # Award 1 point
        player = game_engine.award_points(player, 1)
        assert player.points == 1
        
        # Award 2 points
        player = game_engine.award_points(player, 2)
        assert player.points == 3
        
        # Try to award more points (should not exceed 3)
        with pytest.raises(ValueError):
            game_engine.award_points(player, 1)
    
    def test_ko_awards_points(self, game_engine, basic_game_state):
        """Test that KOing a regular Pokemon awards 1 point."""
        attacker = PokemonCard(
            id="TEST-001", name="Attacker", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC,
            attacks=[Attack(name="Strong Attack", cost=[EnergyType.COLORLESS], damage=40)],
            attached_energies=[EnergyType.COLORLESS]
        )
        target = PokemonCard(
            id="TEST-002", name="Target", hp=30, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[]
        )
        
        player_state = dataclasses.replace(basic_game_state.player, active_pokemon=target)
        opponent_state = dataclasses.replace(basic_game_state.opponent, active_pokemon=attacker)
        game_state = GameState(player=player_state, opponent=opponent_state, active_player=PlayerTag.OPPONENT, phase=GamePhase.ATTACK)
        
        # Execute attack
        final_state = game_engine.execute_attack(game_state, attacker.attacks[0])
        
        assert final_state.opponent.points == 1
        assert final_state.player.active_pokemon is None # Target should be knocked out
    
    def test_ex_pokemon_awards_2_points(self, game_engine, basic_game_state):
        """Test that KOing an ex Pokemon awards 2 points."""
        attacker = PokemonCard(
            id="TEST-001", name="Attacker", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC,
            attacks=[Attack(name="Strong Attack", cost=[EnergyType.COLORLESS], damage=40)],
            attached_energies=[EnergyType.COLORLESS]
        )
        target = PokemonCard(
            id="TEST-002", name="Ex Target", hp=30, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, is_ex=True, attacks=[]
        )
        
        player_state = dataclasses.replace(basic_game_state.player, active_pokemon=target)
        opponent_state = dataclasses.replace(basic_game_state.opponent, active_pokemon=attacker)
        game_state = GameState(player=player_state, opponent=opponent_state, active_player=PlayerTag.OPPONENT, phase=GamePhase.ATTACK)
        
        final_state = game_engine.execute_attack(game_state, attacker.attacks[0])
        
        assert final_state.opponent.points == 2
    
    def test_game_over_at_3_points(self, game_engine, basic_game_state):
        """Test that the game ends when a player reaches 3 points."""
        player = dataclasses.replace(basic_game_state.player, points=2)
        ko_pokemon = PokemonCard(id="p1", name="KO Pokemon", hp=10, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[])
        
        # Set opponent to have the KO'd pokemon
        opponent_state = dataclasses.replace(basic_game_state.opponent, active_pokemon=ko_pokemon)
        
        # Knock out the pokemon, awarding the final point
        game_state = dataclasses.replace(basic_game_state, player=player, opponent=opponent_state)
        final_state = game_engine._apply_knockout(game_state, ko_pokemon)
        
        final_state_after_check = game_engine.check_game_over(final_state)

        assert final_state_after_check.winner == PlayerTag.PLAYER
        assert final_state_after_check.is_finished is True


class TestTCGPocketCompliance:
    """Test compliance with TCG Pocket rules."""
    
    def test_weakness_adds_20_damage(self, game_engine, basic_game_state):
        """Test that weakness adds exactly 20 damage."""
        attacker = PokemonCard(
            id="TEST-001", name="Fire Pokemon", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC,
            attacks=[Attack(name="Test", cost=[], damage=30)], attached_energies=[EnergyType.FIRE]
        )
        defender = PokemonCard(
            id="TEST-002", name="Grass Pokemon", hp=100, pokemon_type=EnergyType.GRASS, stage=Stage.BASIC,
            attacks=[], weakness=(EnergyType.FIRE, 20)
        )

        damage, _ = game_engine._calculate_damage(attacker.attacks[0], attacker, defender)
        assert damage == 50
    
    def test_no_resistance_mechanics(self, game_engine, basic_game_state):
        """Test that resistance does not reduce damage."""
        attacker = PokemonCard(
            id="TEST-001", name="Fire Pokemon", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC,
            attacks=[Attack(name="Test", cost=[], damage=30)], attached_energies=[EnergyType.FIRE]
        )
        defender = PokemonCard(
            id="TEST-002", name="Water Pokemon", hp=100, pokemon_type=EnergyType.WATER, stage=Stage.BASIC, attacks=[]
        )

        damage, _ = game_engine._calculate_damage(attacker.attacks[0], attacker, defender)
        assert damage == 30
    
    def test_bench_limit_3(self, game_engine):
        """Test that bench limit is 3 Pokemon."""
        assert game_engine.max_bench_size == 3
    
    def test_poison_damage_10(self, game_engine, basic_game_state):
        """Test poison damage is 10 in TCG Pocket (rulebook §7)."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001", name="Poisoned Pokemon", hp=100, pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC, attacks=[], status_condition=StatusCondition.POISONED
        )
        updated_pokemon, was_ko = game_engine.apply_status_condition_effects_in_order(poisoned_pokemon)

        assert updated_pokemon.damage_counters == 10

    def test_burn_damage_20(self, game_engine, basic_game_state):
        """Test that burn does exactly 20 damage on a TAILS flip."""
        burned_pokemon = PokemonCard(
            id="TEST-001", name="Burned Pokemon", hp=100, pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC, attacks=[], status_condition=StatusCondition.BURNED
        )

        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.TAILS):
            updated_pokemon, was_ko = game_engine.apply_status_condition_effects_in_order(burned_pokemon)
            assert updated_pokemon.damage_counters == 20 