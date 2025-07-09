#!/usr/bin/env python3
"""
Quick test to verify the trainer effects system is working.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all trainer effect modules can be imported."""
    print("🧪 Testing trainer effects system imports...")
    print("=" * 50)
    
    # Test core imports
    print("Testing core imports...")
    from src.card_db.core import PokemonCard, ItemCard, ToolCard, SupporterCard, EnergyType
    print("✅ Core imports successful")
    
    # Test trainer effects imports
    print("Testing trainer effects imports...")
    from src.card_db.trainer_effects import EffectContext
    from src.card_db.trainer_effects.conditions import require_bench_pokemon
    from src.card_db.trainer_effects.actions import heal_pokemon
    from src.card_db.trainer_effects.composites import heal_20_damage
    print("✅ Trainer effects imports successful")
    
    # Test trainer executor
    print("Testing trainer executor...")
    from src.card_db.trainer_executor import execute_trainer_card, can_play_trainer_card
    print("✅ Trainer executor imports successful")
    
    # Test comprehensive registry
    print("Testing comprehensive registry...")
    from src.card_db.comprehensive_trainer_registry import COMPREHENSIVE_TRAINER_EFFECTS
    print("✅ Comprehensive registry imports successful")
    
    # Test game state
    print("Testing game state...")
    from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
    from src.rules.game_engine import GameEngine
    print("✅ Game state imports successful")
    
    print("\n🎉 All imports successful!")

def test_basic_functionality():
    """Test basic trainer effect functionality."""
    print("\n🧪 Testing basic trainer effect functionality...")
    print("=" * 50)
    
    from src.card_db.core import PokemonCard, SupporterCard, EnergyType, Stage
    from src.card_db.trainer_effects import EffectContext
    from src.card_db.trainer_effects.composites import heal_20_damage
    from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
    from src.rules.game_engine import GameEngine
    
    # Create test game state
    game_state = GameState()
    game_state.phase = GamePhase.MAIN
    game_state.active_player = PlayerTag.PLAYER
    
    # Create test Pokemon
    test_pokemon = PokemonCard(
        id='test-001',
        name='Test Pokemon',
        hp=100,
        pokemon_type=EnergyType.GRASS,
        stage=Stage.BASIC,
        damage_counters=50  # Damaged
    )
    
    game_state.player.active_pokemon = test_pokemon
    game_state.player.hand = []
    game_state.player.deck = []
    
    # Create game engine
    game_engine = GameEngine()
    
    # Create effect context
    context = EffectContext(game_state, game_state.player, game_engine)
    context.targets = [test_pokemon]
    
    print(f"Initial damage: {test_pokemon.damage_counters}")
    
    # Test heal effect
    heal_chain = heal_20_damage()
    for effect_func in heal_chain:
        context = effect_func(context)
        if context.failed:
            break
    
    print(f"Damage after healing: {test_pokemon.damage_counters}")
    
    # Verify healing worked
    expected_damage = max(0, 50 - 20)
    assert test_pokemon.damage_counters == expected_damage, f"Expected {expected_damage}, got {test_pokemon.damage_counters}"
    
    print("✅ Basic healing functionality works!")

def test_registry_coverage():
    """Test that the registry covers the trainer effects."""
    print("\n🧪 Testing registry coverage...")
    print("=" * 50)
    
    from src.card_db.comprehensive_trainer_registry import COMPREHENSIVE_TRAINER_EFFECTS, get_all_covered_effects, get_missing_effects
    
    # Load trainer effects
    effects_file = Path("data/trainer_effects.json")
    assert effects_file.exists(), "Trainer effects file not found"
    
    import json
    with open(effects_file, 'r', encoding='utf-8') as f:
        all_effects = json.load(f)
    
    covered = get_all_covered_effects()
    missing = get_missing_effects()
    
    print(f"Total effects: {len(all_effects)}")
    print(f"Covered effects: {len(covered)}")
    print(f"Missing effects: {len(missing)}")
    print(f"Coverage: {len(covered)/len(all_effects)*100:.1f}%")
    
    if missing:
        print(f"\nMissing effects:")
        for effect in missing[:5]:  # Show first 5
            print(f"  - {effect}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")
    
    # Assert that all effects are covered
    assert len(missing) == 0, f"Missing {len(missing)} trainer effects"
    print("✅ All trainer effects are covered!")

if __name__ == "__main__":
    print("🎉 TCG Pocket Trainer Effects System Test")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("Imports", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Registry Coverage", test_registry_coverage)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} | {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Trainer effects system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.") 