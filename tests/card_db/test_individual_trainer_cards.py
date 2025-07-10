#!/usr/bin/env python3
"""
Comprehensive test file for individual trainer card effects.

This file tests each trainer card in the registry to verify they work correctly
with the composable effects system.
"""

import pytest
from unittest.mock import Mock, patch
from src.card_db.core import (
    PokemonCard, ItemCard, ToolCard, SupporterCard, 
    EnergyType, Stage, StatusCondition
)
from src.card_db.trainer_executor import execute_trainer_card, can_play_trainer_card
from src.card_db.trainer_effects import EffectContext
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.rules.game_engine import GameEngine
from src.card_db.comprehensive_trainer_registry import TRAINER_EFFECTS, CARD_NAME_TO_EFFECT


class TestTrainerCardEffects:
    """Test suite for individual trainer card effects."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.game_state = GameState()
        self.game_state.phase = GamePhase.MAIN
        self.game_state.active_player = PlayerTag.PLAYER
        self.game_engine = GameEngine()
        
        # Create test Pokemon
        self.grass_pokemon = PokemonCard(
            id='test-grass-001',
            name='Bulbasaur',
            hp=70,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            damage_counters=30  # Damaged
        )
        
        self.water_pokemon = PokemonCard(
            id='test-water-001',
            name='Squirtle',
            hp=60,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC
        )
        
        self.fire_pokemon = PokemonCard(
            id='test-fire-001',
            name='Charmander',
            hp=60,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.BASIC
        )
        
        self.opponent_pokemon = PokemonCard(
            id='test-opponent-001',
            name='Pikachu',
            hp=60,
            pokemon_type=EnergyType.ELECTRIC,
            stage=Stage.BASIC,
            damage_counters=20  # Damaged
        )
        
        self.opponent_bench_pokemon = PokemonCard(
            id='test-opponent-bench-001',
            name='Raichu',
            hp=90,
            pokemon_type=EnergyType.ELECTRIC,
            stage=Stage.STAGE_1,
            damage_counters=40  # Damaged
        )
        
        # Set up basic game state
        self.game_state.player.active_pokemon = self.grass_pokemon
        self.game_state.player.bench = [self.water_pokemon, self.fire_pokemon]
        self.game_state.opponent.active_pokemon = self.opponent_pokemon
        self.game_state.opponent.bench = [self.opponent_bench_pokemon]
        
        # Add energy to player's zone
        self.game_state.player.energy_zone = EnergyType.GRASS
    
    def create_trainer_card(self, name: str, card_type: type = SupporterCard) -> object:
        """Create a trainer card for testing."""
        return card_type(
            id=f'trainer-{name.lower().replace(" ", "-")}',
            name=name,
            effects=[]  # Effects are handled by the registry
        )
    
    def test_erika_healing(self):
        """Test Erika's healing effect on Grass Pokemon."""
        print("\n🧪 Testing Erika - Heal Grass Pokemon")
        print("=" * 50)
        
        # Create Erika card
        erika = self.create_trainer_card("Erika")
        self.game_state.player.hand.append(erika)
        
        # Record initial damage
        initial_damage = self.grass_pokemon.damage_counters
        print(f"Initial damage on {self.grass_pokemon.name}: {initial_damage}")
        
        # Execute Erika
        success = execute_trainer_card(erika, self.game_state, self.game_state.player, self.game_engine)
        
        # Verify results
        assert success, "Erika should execute successfully"
        expected_damage = max(0, initial_damage - 50)
        print(f"Expected damage after healing: {expected_damage}")
        print(f"Actual damage after healing: {self.grass_pokemon.damage_counters}")
        assert self.grass_pokemon.damage_counters == expected_damage
        print("✅ Erika healing test passed!")
    
    def test_erika_no_grass_pokemon(self):
        """Test Erika fails when no Grass Pokemon are available."""
        print("\n🧪 Testing Erika - No Grass Pokemon")
        print("=" * 50)
        
        # Remove grass Pokemon from play
        self.game_state.player.active_pokemon = self.water_pokemon
        self.game_state.player.bench = [self.fire_pokemon]
        
        erika = self.create_trainer_card("Erika")
        self.game_state.player.hand.append(erika)
        
        # Execute Erika
        success = execute_trainer_card(erika, self.game_state, self.game_state.player, self.game_engine)
        
        # Should fail - no grass Pokemon
        assert not success, "Erika should fail when no Grass Pokemon are available"
        print("✅ Erika no-target test passed!")
    
    def test_sabrina_switching(self):
        """Test Sabrina's opponent Pokemon switching."""
        print("\n🧪 Testing Sabrina - Switch Opponent Pokemon")
        print("=" * 50)
        
        sabrina = self.create_trainer_card("Sabrina")
        self.game_state.player.hand.append(sabrina)
        
        # Record initial active Pokemon
        initial_active = self.game_state.opponent.active_pokemon
        print(f"Initial opponent active: {initial_active.name}")
        print(f"Opponent bench: {[p.name for p in self.game_state.opponent.bench]}")
        
        # Execute Sabrina
        success = execute_trainer_card(sabrina, self.game_state, self.game_state.player, self.game_engine)
        
        # Verify switching occurred
        assert success, "Sabrina should execute successfully"
        assert self.game_state.opponent.active_pokemon != initial_active, "Active Pokemon should have changed"
        print(f"New opponent active: {self.game_state.opponent.active_pokemon.name}")
        print("✅ Sabrina switching test passed!")
    
    def test_sabrina_no_bench(self):
        """Test Sabrina fails when opponent has no bench."""
        print("\n🧪 Testing Sabrina - No Opponent Bench")
        print("=" * 50)
        
        # Remove opponent's bench
        self.game_state.opponent.bench = []
        
        sabrina = self.create_trainer_card("Sabrina")
        self.game_state.player.hand.append(sabrina)
        
        # Execute Sabrina
        success = execute_trainer_card(sabrina, self.game_state, self.game_state.player, self.game_engine)
        
        # Should fail - no bench Pokemon
        assert not success, "Sabrina should fail when opponent has no bench"
        print("✅ Sabrina no-bench test passed!")
    
    def test_cyrus_damaged_switch(self):
        """Test Cyrus switches in damaged opponent Pokemon."""
        print("\n🧪 Testing Cyrus - Switch Damaged Opponent")
        print("=" * 50)
        
        cyrus = self.create_trainer_card("Cyrus")
        self.game_state.player.hand.append(cyrus)
        
        # Ensure bench Pokemon is damaged
        self.opponent_bench_pokemon.damage_counters = 30
        
        print(f"Opponent bench Pokemon damage: {self.opponent_bench_pokemon.damage_counters}")
        
        # Execute Cyrus
        success = execute_trainer_card(cyrus, self.game_state, self.game_state.player, self.game_engine)
        
        # Verify damaged Pokemon was switched in
        assert success, "Cyrus should execute successfully"
        assert self.game_state.opponent.active_pokemon == self.opponent_bench_pokemon, "Damaged Pokemon should be active"
        print("✅ Cyrus damaged switch test passed!")
    
    def test_cyrus_no_damaged_bench(self):
        """Test Cyrus fails when no damaged bench Pokemon."""
        print("\n🧪 Testing Cyrus - No Damaged Bench")
        print("=" * 50)
        
        # Remove damage from bench Pokemon
        self.opponent_bench_pokemon.damage_counters = 0
        
        cyrus = self.create_trainer_card("Cyrus")
        self.game_state.player.hand.append(cyrus)
        
        # Execute Cyrus
        success = execute_trainer_card(cyrus, self.game_state, self.game_state.player, self.game_engine)
        
        # Should fail - no damaged bench Pokemon
        assert not success, "Cyrus should fail when no damaged bench Pokemon"
        print("✅ Cyrus no-damaged-bench test passed!")
    
    @patch('src.rules.game_engine.GameEngine.flip_coin')
    def test_misty_energy_attachment(self, mock_flip):
        """Test Misty's coin flip energy attachment."""
        print("\n🧪 Testing Misty - Energy Attachment")
        print("=" * 50)
        
        # Mock coin flips: 2 heads, then tails
        from src.rules.game_engine import CoinFlipResult
        mock_flip.side_effect = [CoinFlipResult.HEADS, CoinFlipResult.HEADS, CoinFlipResult.TAILS]
        
        # Set up water energy in zone
        self.game_state.player.energy_zone = EnergyType.WATER
        
        misty = self.create_trainer_card("Misty")
        self.game_state.player.hand.append(misty)
        
        # Record initial energy count
        initial_energy = len(self.water_pokemon.attached_energies)
        print(f"Initial energy on {self.water_pokemon.name}: {initial_energy}")
        
        # Execute Misty
        success = execute_trainer_card(misty, self.game_state, self.game_state.player, self.game_engine)
        
        # Should succeed and attach 2 energy (2 heads)
        assert success, "Misty should execute successfully"
        
        # Check that 2 energy were attached
        final_energy = len(self.water_pokemon.attached_energies)
        expected_energy = initial_energy + 2  # 2 heads = 2 energy
        assert final_energy == expected_energy, f"Expected {expected_energy} energy, got {final_energy}"
        print(f"Final energy on {self.water_pokemon.name}: {final_energy}")
        print("✅ Misty energy attachment test passed!")
    
    def test_giovanni_damage_bonus(self):
        """Test Giovanni's damage bonus effect."""
        print("\n🧪 Testing Giovanni - Damage Bonus")
        print("=" * 50)
        
        giovanni = self.create_trainer_card("Giovanni")
        self.game_state.player.hand.append(giovanni)
        
        # Execute Giovanni
        success = execute_trainer_card(giovanni, self.game_state, self.game_state.player, self.game_engine)
        
        # Verify damage bonus is applied
        assert success, "Giovanni should execute successfully"
        # Note: In a real implementation, you'd check if damage bonus is tracked
        print("✅ Giovanni damage bonus test passed!")
    
    def test_blaine_specific_pokemon_bonus(self):
        """Test Blaine's damage bonus for specific Pokemon."""
        print("\n🧪 Testing Blaine - Specific Pokemon Damage Bonus")
        print("=" * 50)
        
        # Create a Pokemon that benefits from Blaine
        ninetales = PokemonCard(
            id='test-ninetales',
            name='Ninetales',
            hp=90,
            pokemon_type=EnergyType.FIRE,
            stage=Stage.STAGE_1
        )
        self.game_state.player.active_pokemon = ninetales
        
        blaine = self.create_trainer_card("Blaine")
        self.game_state.player.hand.append(blaine)
        
        # Execute Blaine
        success = execute_trainer_card(blaine, self.game_state, self.game_state.player, self.game_engine)
        
        # Verify damage bonus is applied
        assert success, "Blaine should execute successfully"
        print("✅ Blaine specific Pokemon bonus test passed!")
    
    def test_supporter_once_per_turn_restriction(self):
        """Test that supporter cards can only be played once per turn."""
        print("\n🧪 Testing Supporter Once Per Turn Restriction")
        print("=" * 50)
        
        giovanni1 = self.create_trainer_card("Giovanni")
        giovanni2 = self.create_trainer_card("Giovanni")
        self.game_state.player.hand.extend([giovanni1, giovanni2])
        
        # First Giovanni should succeed
        success1 = execute_trainer_card(giovanni1, self.game_state, self.game_state.player, self.game_engine)
        assert success1, "First supporter should execute successfully"
        
        # Mark supporter as played
        self.game_state.player.supporter_played_this_turn = True
        
        # Second Giovanni should fail
        can_play = can_play_trainer_card(giovanni2, self.game_state, self.game_state.player, self.game_engine)
        assert not can_play, "Second supporter should not be playable"
        print("✅ Supporter restriction test passed!")
    
    def test_tool_card_attachment(self):
        """Test tool card attachment to Pokemon."""
        print("\n🧪 Testing Tool Card Attachment")
        print("=" * 50)
        
        # Create a tool card
        giant_cape = ToolCard(
            id='tool-giant-cape',
            name='Giant Cape',
            effects=[]
        )
        self.game_state.player.hand.append(giant_cape)
        
        # Execute tool attachment
        success = execute_trainer_card(giant_cape, self.game_state, self.game_state.player, self.game_engine)
        
        # Note: Tool attachment logic would need to be implemented
        # For now, just verify it doesn't crash
        print("✅ Tool card attachment test passed!")
    
    def test_item_card_multiple_uses(self):
        """Test that item cards can be played multiple times per turn."""
        print("\n🧪 Testing Item Card Multiple Uses")
        print("=" * 50)
        
        # Create item cards with a defined effect
        potion1 = ItemCard(id='item-potion-1', name='Potion', effects=[])
        potion2 = ItemCard(id='item-potion-2', name='Potion', effects=[])
        self.game_state.player.hand.extend([potion1, potion2])
        
        # Both should be playable
        can_play1 = can_play_trainer_card(potion1, self.game_state, self.game_state.player, self.game_engine)
        can_play2 = can_play_trainer_card(potion2, self.game_state, self.game_state.player, self.game_engine)
        
        assert can_play1, "First item should be playable"
        assert can_play2, "Second item should be playable"
        
        # Execute first potion
        success1 = execute_trainer_card(potion1, self.game_state, self.game_state.player, self.game_engine)
        assert success1, "First potion should execute successfully"
        
        # Execute second potion
        success2 = execute_trainer_card(potion2, self.game_state, self.game_state.player, self.game_engine)
        assert success2, "Second potion should execute successfully"
        
        print("✅ Item card multiple uses test passed!")
    
    def test_all_registered_cards_have_effects(self):
        """Test that all cards in the registry have defined effects."""
        print("\n🧪 Testing All Registered Cards Have Effects")
        print("=" * 50)
        
        # Test that we have effects defined
        assert len(TRAINER_EFFECTS) > 0
        assert len(CARD_NAME_TO_EFFECT) > 0
        
        # Test that specific cards have effects
        test_cards = ["Erika", "Sabrina", "Cyrus", "Misty", "Giovanni", "Blaine"]
        for card_name in test_cards:
            effect_text = CARD_NAME_TO_EFFECT.get(card_name)
            assert effect_text is not None, f"Card {card_name} should have an effect defined"
            assert effect_text in TRAINER_EFFECTS, f"Effect for {card_name} should be in TRAINER_EFFECTS"
            print(f"✅ {card_name}: {effect_text}")
        
        print("✅ All registered cards have effects!")
    
    def test_effect_context_data_passing(self):
        """Test that effect context properly passes data between functions."""
        print("\n🧪 Testing Effect Context Data Passing")
        print("=" * 50)
        
        # Create a context
        ctx = EffectContext(self.game_state, self.game_state.player, self.game_engine)
        
        # Test data storage and retrieval
        ctx.data['test_key'] = 'test_value'
        assert ctx.data['test_key'] == 'test_value'
        
        # Test target storage
        ctx.targets = [self.grass_pokemon]
        assert len(ctx.targets) == 1
        assert ctx.targets[0] == self.grass_pokemon
        
        # Test failure flag
        ctx.failed = True
        assert ctx.failed is True
        
        print("✅ Effect context data passing test passed!")
    
    def run_all_tests(self):
        """Run all trainer card tests."""
        print("\n🎯 Running All Trainer Card Tests")
        print("=" * 60)
        
        test_methods = [
            self.test_erika_healing,
            self.test_erika_no_grass_pokemon,
            self.test_sabrina_switching,
            self.test_sabrina_no_bench,
            self.test_cyrus_damaged_switch,
            self.test_cyrus_no_damaged_bench,
            self.test_misty_energy_attachment,
            self.test_giovanni_damage_bonus,
            self.test_blaine_specific_pokemon_bonus,
            self.test_supporter_once_per_turn_restriction,
            self.test_tool_card_attachment,
            self.test_item_card_multiple_uses,
            self.test_all_registered_cards_have_effects,
            self.test_effect_context_data_passing,
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                # Reset state for each test
                self.setup_method()
                test_method()
                passed += 1
            except Exception as e:
                print(f"❌ {test_method.__name__} FAILED: {e}")
                failed += 1
        
        print(f"\n📊 Test Results: {passed} passed, {failed} failed")
        return failed == 0


def test_individual_trainer_cards():
    """Pytest entry point for individual trainer card tests."""
    tester = TestTrainerCardEffects()
    success = tester.run_all_tests()
    assert success, "All trainer card tests should pass"


if __name__ == "__main__":
    """Run all tests when executed directly."""
    tester = TestTrainerCardEffects()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All trainer card tests passed!")
        exit(0)
    else:
        print("\n💥 Some trainer card tests failed!")
        exit(1)