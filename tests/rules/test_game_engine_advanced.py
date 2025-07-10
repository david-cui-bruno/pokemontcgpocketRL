"""Advanced tests for the GameEngine with status conditions and complex mechanics."""

import pytest
import dataclasses
from unittest.mock import patch
from typing import List, Dict

from src.rules.game_engine import GameEngine, CoinFlipResult, DamageResult
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import (
    PokemonCard, Attack, Effect, EnergyType, Stage, StatusCondition,
    TargetType
)


@pytest.fixture
def game_engine():
    """Create a GameEngine instance."""
    return GameEngine()


@pytest.fixture
def basic_player_state():
    """Create a basic player state for testing."""
    return PlayerState(player_tag=PlayerTag.PLAYER)


@pytest.fixture
def basic_game_state(basic_player_state):
    """Create a basic game state for testing."""
    opponent_state = PlayerState(player_tag=PlayerTag.OPPONENT)
    return GameState(player=basic_player_state, opponent=opponent_state, phase=GamePhase.MAIN)


class TestStatusConditions:
    """Test status condition mechanics."""
    
    def test_poison_status_application(self, game_engine, basic_game_state):
        """Test that poison status is correctly applied."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Poison Pokemon",
            hp=100,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.GRASS]
        )
        
        target = PokemonCard(
            id="TEST-002", 
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Create attack with poison effect
        poison_effect = Effect(
            effect_type="poison",
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Poison Attack",
            cost=[EnergyType.GRASS],
            damage=30,
            effects=[poison_effect]
        )
        
        state = dataclasses.replace(
            basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target),
            phase=GamePhase.ATTACK
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, state)
        
        assert result.status_condition_applied == StatusCondition.POISONED
        assert target.status_condition == StatusCondition.POISONED
    
    def test_poison_damage(self, game_engine, basic_game_state):
        """Test poison status condition damage."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.POISONED
        )
        
        updated_pokemon, was_ko = game_engine.apply_status_condition_effects_in_order(poisoned_pokemon)
        
        # TCG Pocket poison damage is 10
        assert updated_pokemon.damage_counters == 10
    
    def test_burn_status_application(self, game_engine, basic_game_state):
        """Test burn status application and effects."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.FIRE]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon", 
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        burn_effect = Effect(
            effect_type="burn",
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Burn Attack",
            cost=[EnergyType.FIRE],
            damage=40,
            effects=[burn_effect]
        )

        state = dataclasses.replace(
            basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target),
            phase=GamePhase.ATTACK
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, state)
        
        assert result.status_condition_applied == StatusCondition.BURNED
        
        # Test burn damage between turns
        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.TAILS):
            updated_target, was_ko = game_engine.apply_status_condition_effects_in_order(target)
            assert updated_target.damage_counters == 20
        
        # Burn should be cured on a heads flip
        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.HEADS):
            updated_target, was_ko = game_engine.apply_status_condition_effects_in_order(target)
            assert updated_target.status_condition is None
    
    def test_sleep_status_prevents_attack(self, game_engine, basic_game_state):
        """Test that sleep prevents attacking."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        attack = asleep_pokemon.attacks[0]
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        state = dataclasses.replace(basic_game_state, 
            player=dataclasses.replace(basic_game_state.player, active_pokemon=asleep_pokemon),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )

        # Should not be able to attack while asleep
        with pytest.raises(ValueError, match="Cannot attack when Asleep"):
            game_engine.execute_attack(state)
    
    def test_paralysis_prevents_attack(self, game_engine, basic_game_state):
        """Test that paralysis prevents attacking."""
        paralyzed_pokemon = PokemonCard(
            id="TEST-001",
            name="Paralyzed Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.PARALYZED,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        attack = paralyzed_pokemon.attacks[0]
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        state = dataclasses.replace(basic_game_state, 
            player=dataclasses.replace(basic_game_state.player, active_pokemon=paralyzed_pokemon),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )

        # Should not be able to attack while paralyzed
        with pytest.raises(ValueError, match="Cannot attack when Paralyzed"):
            game_engine.execute_attack(state)


class TestCoinFlipMechanics:
    """Test coin flip mechanics."""
    
    def test_basic_coin_flip(self, game_engine):
        """Test basic coin flip functionality."""
        result = game_engine.flip_coin()
        assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
    
    def test_multiple_coin_flips(self, game_engine):
        """Test multiple coin flips."""
        results = game_engine.flip_coins(3)
        assert len(results) == 3
        for result in results:
            assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
    
    def test_coin_flip_damage_bonus(self, game_engine, basic_game_state):
        """Test coin flip for damage bonus."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        coin_effect = Effect(
            effect_type="coin_flip_damage",
            amount=30,
            target=TargetType.SELF
        )
        
        attack = Attack(
            name="Coin Flip Attack",
            cost=[EnergyType.COLORLESS],
            damage=30,
            effects=[coin_effect]
        )
        
        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )

        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.HEADS):
            result = game_engine.resolve_attack(attacker, attack, target, state)
            assert result.damage_dealt == 60  # 30 (base) + 30 (bonus)
        
        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.TAILS):
            result = game_engine.resolve_attack(attacker, attack, target, state)
            assert result.damage_dealt == 30 # 30 (base) + 0 (bonus)
    
    def test_coin_flip_status_condition(self, game_engine, basic_game_state):
        """Test coin flip for status condition application."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        paralyze_effect = Effect(
            effect_type="coin_flip_paralyze",
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Coin Flip Status Attack",
            cost=[EnergyType.COLORLESS],
            damage=10,
            effects=[paralyze_effect]
        )
        
        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )

        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.HEADS):
            result = game_engine.resolve_attack(attacker, attack, target, state)
            assert result.status_condition_applied == StatusCondition.PARALYZED
            
        with patch.object(game_engine, 'flip_coin', return_value=CoinFlipResult.TAILS):
            result = game_engine.resolve_attack(attacker, attack, target, state)
            assert result.status_condition_applied is None


class TestHealingMechanics:
    """Test healing mechanics."""
    
    def test_basic_healing(self, game_engine):
        """Test basic healing functionality."""
        damaged_pokemon = PokemonCard(
            id="TEST-001",
            name="Damaged Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            damage_counters=50
        )
        
        success = game_engine.heal_pokemon(damaged_pokemon, 30)
        assert success
        assert damaged_pokemon.damage_counters == 20
    
    def test_healing_attack_effect(self, game_engine, basic_game_state):
        """Test healing from an attack effect."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Healing Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.COLORLESS],
            damage_counters=40
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        healing_effect = Effect(
            effect_type="heal",
            amount=30,
            target=TargetType.SELF
        )
        
        attack = Attack(
            name="Healing Attack",
            cost=[EnergyType.COLORLESS],
            damage=10,
            effects=[healing_effect]
        )

        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )

        new_state = game_engine.execute_attack(state, attack)
        
        healed_attacker = new_state.player.active_pokemon
        assert healed_attacker.damage_counters == 10 # 40 - 30


class TestEnergyDiscarding:
    """Test energy discarding mechanics."""
    
    def test_basic_energy_discard(self, game_engine):
        """Test basic energy discarding."""
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.FIRE, EnergyType.FIRE, EnergyType.COLORLESS]
        )
        
        discarded = game_engine.discard_energy(pokemon, [EnergyType.FIRE])
        assert len(discarded) == 1
        assert discarded[0] == EnergyType.FIRE
        assert len(pokemon.attached_energies) == 2
        assert EnergyType.FIRE in pokemon.attached_energies  # One should remain
        assert EnergyType.COLORLESS in pokemon.attached_energies
    
    def test_attack_energy_discard(self, game_engine, basic_game_state):
        """Test energy discarding as part of an attack cost/effect."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Discarding Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.FIRE, EnergyType.WATER]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )

        discard_effect = Effect(
            effect_type="discard_energy",
            amount=1,
            target=TargetType.SELF
        )

        attack = Attack(
            name="Discard Attack",
            cost=[EnergyType.FIRE],
            damage=50,
            effects=[discard_effect]
        )

        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )
        
        new_state = game_engine.execute_attack(state, attack)
        
        # 1 for cost, 1 for effect
        assert len(new_state.player.active_pokemon.attached_energies) == 0


class TestConditionalDamageBonuses:
    """Test conditional damage bonuses."""
    
    def test_poison_bonus_damage(self, game_engine, basic_game_state):
        """Test bonus damage against a poisoned Pokemon."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Bonus Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        poisoned_target = PokemonCard(
            id="TEST-002",
            name="Poisoned Target",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.POISONED
        )
        
        poison_bonus_effect = Effect(
            effect_type="poison_bonus",
            amount=40,
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Poison Bonus Attack",
            cost=[EnergyType.COLORLESS],
            damage=20,
            effects=[poison_bonus_effect]
        )

        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=poisoned_target)
        )
        
        result = game_engine.resolve_attack(attacker, attack, poisoned_target, state)
        assert result.damage_dealt == 60  # 20 (base) + 40 (bonus)


class TestComplexEffects:
    """Test complex attack effects."""
    
    def test_multiple_coin_flips(self, game_engine, basic_game_state):
        """Test effects with multiple coin flips."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Multi-Flip Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target",
            hp=200,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        multi_flip_effect = Effect(
            effect_type="multi_coin_flip",
            amount=50,  # 50 damage per heads
            parameters={"num_flips": 3}
        )
        
        attack = Attack(
            name="Multi-Flip Attack",
            cost=[EnergyType.COLORLESS],
            damage=0,
            effects=[multi_flip_effect]
        )

        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )
        
        # Mock 2 heads, 1 tails
        with patch.object(game_engine, 'flip_coins', return_value=[CoinFlipResult.HEADS, CoinFlipResult.HEADS, CoinFlipResult.TAILS]):
            result = game_engine.resolve_attack(attacker, attack, target, state)
            assert result.damage_dealt == 100  # 2 heads * 50 damage
    
    def test_random_status_condition(self, game_engine, basic_game_state):
        """Test applying a random status condition."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Random Pokemon",
            hp=100,
            pokemon_type=EnergyType.PSYCHIC,
            stage=Stage.BASIC,
            attacks=[],
            attached_energies=[EnergyType.PSYCHIC]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        random_status_effect = Effect(effect_type="random_status")
        
        attack = Attack(
            name="Random Status Attack",
            cost=[EnergyType.PSYCHIC],
            damage=10,
            effects=[random_status_effect]
        )

        state = dataclasses.replace(basic_game_state,
            player=dataclasses.replace(basic_game_state.player, active_pokemon=attacker),
            opponent=dataclasses.replace(basic_game_state.opponent, active_pokemon=target)
        )
        
        with patch.object(game_engine.random, 'choice', return_value=StatusCondition.CONFUSED):
            result = game_engine.resolve_attack(attacker, attack, target, state)
            assert result.status_condition_applied == StatusCondition.CONFUSED


class TestStatusConditionRecovery:
    """Tests for recovering from status conditions."""

    def test_status_condition_removal(self, game_engine):
        """Test that status conditions can be removed."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.POISONED,
            attached_energies=[EnergyType.COLORLESS]  # Add energy
        )
        
        # This would typically be done by a trainer card or ability
        healed_pokemon = dataclasses.replace(poisoned_pokemon, status_condition=None)
        
        assert poisoned_pokemon.status_condition == StatusCondition.POISONED
        assert healed_pokemon.status_condition is None


@pytest.mark.skip(reason="Deck loading not implemented")
def test_load_deck_stub():
    """Test deck loading stub."""
    engine = GameEngine()
    engine.load_deck()


def test_enforce_hand_limit():
    """Test hand limit enforcement."""
    engine = GameEngine()
    player = PlayerState(
        player_tag=PlayerTag.PLAYER,
        hand=[PokemonCard(id=f"c{i}", name="c", hp=10, stage=Stage.BASIC, pokemon_type=EnergyType.COLORLESS, attacks=[]) for i in range(10)]
    )
    
    discarded = engine.enforce_hand_limit(player)
    assert len(discarded) == 3