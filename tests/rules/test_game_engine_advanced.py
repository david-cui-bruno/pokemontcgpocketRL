"""Advanced tests for the GameEngine with status conditions and complex mechanics."""

import pytest
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
def basic_game_state():
    """Create a basic game state for testing."""
    state = GameState()
    state.phase = GamePhase.ATTACK
    return state


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
            attached_energies=[EnergyType.GRASS]
        )
        
        target = PokemonCard(
            id="TEST-002", 
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
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
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
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
            status_condition=StatusCondition.POISONED
        )
        
        effects = game_engine.apply_status_condition_effects(poisoned_pokemon, basic_game_state)
        
        # Fixed: TCG Pocket poison damage is 10 (rulebook §7)
        assert effects["poison_damage"] == 10
        assert poisoned_pokemon.damage_counters == 10
    
    def test_burn_status_application(self, game_engine, basic_game_state):
        """Test burn status application and effects."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Fire Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.FIRE]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon", 
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
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
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        assert result.status_condition_applied == StatusCondition.BURNED
        assert target.status_condition == StatusCondition.BURNED
        
        # Test burn damage between turns
        effects = game_engine.apply_status_condition_effects(target, basic_game_state)
        assert effects["burn_damage"] == 20
        assert target.damage_counters == 60  # 40 from attack + 20 from burn
    
    def test_sleep_status_prevents_attack(self, game_engine, basic_game_state):
        """Test that sleep prevents attacking."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        attack = Attack(
            name="Test Attack",
            cost=[EnergyType.COLORLESS],
            damage=30
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Should not be able to attack while asleep
        can_attack = game_engine._can_use_attack(asleep_pokemon, attack, basic_game_state)
        assert not can_attack
    
    def test_paralysis_prevents_attack(self, game_engine, basic_game_state):
        """Test that paralysis prevents attacking."""
        paralyzed_pokemon = PokemonCard(
            id="TEST-001",
            name="Paralyzed Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.PARALYZED,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        attack = Attack(
            name="Test Attack",
            cost=[EnergyType.COLORLESS],
            damage=30
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        # Should not be able to attack while paralyzed
        can_attack = game_engine._can_use_attack(paralyzed_pokemon, attack, basic_game_state)
        assert not can_attack


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
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
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
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        assert len(result.coin_flips) == 1
        assert result.coin_flips[0] in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
        
        # Damage should be either 30 (tails) or 60 (heads)
        assert result.damage_dealt in [30, 60]
    
    def test_coin_flip_status_condition(self, game_engine, basic_game_state):
        """Test coin flip for status condition application."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        paralyze_effect = Effect(
            effect_type="coin_flip_paralyze",
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Paralyze Attack",
            cost=[EnergyType.COLORLESS],
            damage=20,
            effects=[paralyze_effect]
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        assert len(result.coin_flips) == 1
        # Status condition should only be applied on heads
        if result.coin_flips[0] == CoinFlipResult.HEADS:
            assert result.status_condition_applied == StatusCondition.PARALYZED
            assert target.status_condition == StatusCondition.PARALYZED
        else:
            assert result.status_condition_applied is None
            assert target.status_condition is None


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
        """Test healing from attack effects."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Healing Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS],
            damage_counters=40
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        heal_effect = Effect(
            effect_type="heal",
            amount=30,
            target=TargetType.SELF
        )
        
        attack = Attack(
            name="Healing Attack",
            cost=[EnergyType.COLORLESS],
            damage=30,
            effects=[heal_effect]
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # The healing should be applied to the attacker
        assert attacker.damage_counters == 10  # 40 - 30 = 10


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
            attached_energies=[EnergyType.FIRE, EnergyType.FIRE, EnergyType.COLORLESS]
        )
        
        discarded = game_engine.discard_energy(pokemon, [EnergyType.FIRE])
        assert len(discarded) == 1
        assert discarded[0] == EnergyType.FIRE
        assert len(pokemon.attached_energies) == 2
        assert EnergyType.FIRE in pokemon.attached_energies  # One should remain
        assert EnergyType.COLORLESS in pokemon.attached_energies
    
    def test_attack_energy_discard(self, game_engine, basic_game_state):
        """Test energy discarding from attacks."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.FIRE, EnergyType.FIRE]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        discard_effect = Effect(
            effect_type="discard_energy",
            amount=2,
            target=TargetType.SELF
        )
        
        attack = Attack(
            name="Discard Attack",
            cost=[EnergyType.FIRE],
            damage=50,
            effects=[discard_effect]
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        assert len(result.energy_discarded) == 2
        assert all(energy == EnergyType.FIRE for energy in result.energy_discarded)
        assert len(attacker.attached_energies) == 0


class TestConditionalDamageBonuses:
    """Test conditional damage bonuses."""
    
    def test_poison_bonus_damage(self, game_engine, basic_game_state):
        """Test bonus damage against poisoned Pokemon."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Attacker",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        poisoned_target = PokemonCard(
            id="TEST-002",
            name="Poisoned Target",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.POISONED
        )
        
        poison_bonus_effect = Effect(
            effect_type="poison_bonus",
            amount=50,
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Poison Bonus Attack",
            cost=[EnergyType.COLORLESS],
            damage=40,
            effects=[poison_bonus_effect]
        )
        
        result = game_engine.resolve_attack(attacker, attack, poisoned_target, basic_game_state)
        
        # Should do 40 + 50 = 90 damage
        assert result.damage_dealt == 90
        assert poisoned_target.damage_counters == 90


class TestComplexEffects:
    """Test complex attack effects."""
    
    def test_multiple_coin_flips(self, game_engine, basic_game_state):
        """Test attacks with multiple coin flips."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        multi_coin_effect = Effect(
            effect_type="multi_coin_flip",
            amount=50,
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Multi Flip Attack",
            cost=[EnergyType.COLORLESS],
            damage=20,
            effects=[multi_coin_effect]
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        assert len(result.coin_flips) == 2
        heads_count = sum(1 for flip in result.coin_flips if flip == CoinFlipResult.HEADS)
        expected_damage = 20 + (heads_count * 50)
        assert result.damage_dealt == expected_damage
    
    def test_random_status_condition(self, game_engine, basic_game_state):
        """Test random status condition application."""
        attacker = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = PokemonCard(
            id="TEST-002",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC
        )
        
        random_status_effect = Effect(
            effect_type="random_status",
            target=TargetType.OPPONENT_ACTIVE
        )
        
        attack = Attack(
            name="Random Status Attack",
            cost=[EnergyType.COLORLESS],
            damage=30,
            effects=[random_status_effect]
        )
        
        result = game_engine.resolve_attack(attacker, attack, target, basic_game_state)
        
        # Should apply one of the status conditions
        assert result.status_condition_applied is not None
        assert result.status_condition_applied in [
            StatusCondition.ASLEEP,
            StatusCondition.BURNED,
            StatusCondition.CONFUSED,
            StatusCondition.PARALYZED,
            StatusCondition.POISONED
        ]
        assert target.status_condition == result.status_condition_applied


class TestStatusConditionRecovery:
    """Test status condition recovery mechanics."""
    
    def test_status_condition_removal(self, game_engine):
        """Test that status conditions can be removed."""
        # This would typically be done by trainer cards or abilities
        # For now, we'll test the basic mechanics
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            status_condition=StatusCondition.POISONED,
            attached_energies=[EnergyType.COLORLESS]  # Add energy
        )
        
        # Simulate status removal (this would be done by a trainer card)
        poisoned_pokemon.status_condition = None
        
        assert poisoned_pokemon.status_condition is None
        
        # Should be able to attack normally now
        attack = Attack(
            name="Test Attack",
            cost=[EnergyType.COLORLESS],
            damage=30
        )
        
        game_state = GameState()
        game_state.phase = GamePhase.ATTACK
        can_attack = game_engine._can_use_attack(poisoned_pokemon, attack, game_state)
        assert can_attack 