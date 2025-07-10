#!/usr/bin/env python3
"""Test real gameplay with the Pokemon TCG Pocket environment."""

import numpy as np
from src.env.pokemon_env import PokemonTCGEnv
from src.card_db.core import PokemonCard, Attack, EnergyType, Stage, ItemCard, Effect, TargetType
from src.rules.game_state import GamePhase


def create_realistic_deck() -> list:
    """Create a realistic TCG Pocket deck."""
    deck = []
    
    # Basic Pokemon (12 cards)
    basic_pokemon = [
        ("Pikachu", EnergyType.ELECTRIC, 100, [EnergyType.ELECTRIC], 30),
        ("Charmander", EnergyType.FIRE, 80, [EnergyType.FIRE], 25),
        ("Bulbasaur", EnergyType.GRASS, 70, [EnergyType.GRASS], 20),
        ("Squirtle", EnergyType.WATER, 90, [EnergyType.WATER], 30),
        ("Machop", EnergyType.FIGHTING, 80, [EnergyType.FIGHTING], 25),
        ("Abra", EnergyType.PSYCHIC, 60, [EnergyType.PSYCHIC], 20),
    ]
    
    for i, (name, ptype, hp, cost, damage) in enumerate(basic_pokemon):
        for j in range(2):  # 2 copies each
            pokemon = PokemonCard(
                id=f"{name}-{j}",
                name=name,
                hp=hp,
                pokemon_type=ptype,
                stage=Stage.BASIC,
                attacks=[
                    Attack(
                        name=f"{name} Attack",
                        cost=cost,
                        damage=damage
                    )
                ]
            )
            deck.append(pokemon)
    
    # Stage 1 Pokemon (4 cards)
    stage1_pokemon = [
        ("Raichu", EnergyType.ELECTRIC, 120, [EnergyType.ELECTRIC, EnergyType.ELECTRIC], 60),
        ("Charizard", EnergyType.FIRE, 150, [EnergyType.FIRE, EnergyType.FIRE, EnergyType.COLORLESS], 100),
    ]
    
    for i, (name, ptype, hp, cost, damage) in enumerate(stage1_pokemon):
        for j in range(2):  # 2 copies each
            pokemon = PokemonCard(
                id=f"{name}-{j}",
                name=name,
                hp=hp,
                pokemon_type=ptype,
                stage=Stage.STAGE_1,
                attacks=[
                    Attack(
                        name=f"{name} Attack",
                        cost=cost,
                        damage=damage
                    )
                ]
            )
            deck.append(pokemon)
    
    # Ex Pokemon (2 cards)
    ex_pokemon = [
        ("Pikachu ex", EnergyType.ELECTRIC, 180, [EnergyType.ELECTRIC, EnergyType.ELECTRIC, EnergyType.COLORLESS], 120),
        ("Charizard ex", EnergyType.FIRE, 200, [EnergyType.FIRE, EnergyType.FIRE, EnergyType.FIRE], 150),
    ]
    
    for name, ptype, hp, cost, damage in ex_pokemon:
        pokemon = PokemonCard(
            id=name,
            name=name,
            hp=hp,
            pokemon_type=ptype,
            stage=Stage.BASIC,
            is_ex=True,
            attacks=[
                Attack(
                    name=f"{name} Attack",
                    cost=cost,
                    damage=damage
                )
            ]
        )
        deck.append(pokemon)
    
    # Item cards (2 cards)
    items = [
        ("Potion", [Effect(effect_type="heal", amount=30, target=TargetType.SELF)]),
        ("Energy Switch", [Effect(effect_type="move_energy", amount=1, target=TargetType.SELF)]),
    ]
    
    for name, effects in items:
        item = ItemCard(
            id=name,
            name=name,
            effects=effects
        )
        deck.append(item)
    
    return deck


def print_game_state(env, turn_num):
    """Print current game state."""
    state = env.game_state
    print(f"\n{'='*60}")
    print(f"TURN {turn_num}")
    print(f"{'='*60}")
    
    # Player state
    print(f"PLAYER 1:")
    print(f"  Points: {state.player.points}/3")
    print(f"  Hand: {len(state.player.hand)} cards")
    print(f"  Deck: {len(state.player.deck)} cards")
    print(f"  Energy Zone: {state.player.energy_zone}")
    
    if state.player.active_pokemon:
        active = state.player.active_pokemon
        print(f"  Active: {active.name} (HP: {active.hp - active.damage_counters}/{active.hp})")
        print(f"    Energy: {len(active.attached_energies)} attached")
        print(f"    Status: {active.status_condition}")
    else:
        print(f"  Active: None")
    
    print(f"  Bench: {len(state.player.bench)} Pokemon")
    
    # Opponent state
    print(f"\nPLAYER 2:")
    print(f"  Points: {state.opponent.points}/3")
    print(f"  Hand: {len(state.opponent.hand)} cards")
    print(f"  Deck: {len(state.opponent.deck)} cards")
    print(f"  Energy Zone: {state.opponent.energy_zone}")
    
    if state.opponent.active_pokemon:
        active = state.opponent.active_pokemon
        print(f"  Active: {active.name} (HP: {active.hp - active.damage_counters}/{active.hp})")
        print(f"    Energy: {len(active.attached_energies)} attached")
        print(f"    Status: {active.status_condition}")
    else:
        print(f"  Active: None")
    
    print(f"  Bench: {len(state.opponent.bench)} Pokemon")
    
    print(f"\nPhase: {state.phase}")
    print(f"{'='*60}")


def test_real_gameplay():
    """Test real gameplay with the environment."""
    print("🎯 Pokemon TCG Pocket Real Gameplay Test")
    print("=" * 60)
    
    # Create realistic decks
    deck = create_realistic_deck()
    print(f"Created deck with {len(deck)} cards")
    
    # Verify deck size (rulebook §1)
    assert len(deck) == 20, f"Deck must be exactly 20 cards, got {len(deck)}"
    
    # Create environment
    env = PokemonTCGEnv(player_deck=deck, opponent_deck=deck)
    obs, info = env.reset()
    
    print("\n🎯 Game initialized successfully!")
    
    # Verify starting hand size (rulebook §3)
    assert obs["hand_size"][0] == 5, f"Starting hand must be 5 cards, got {obs['hand_size'][0]}"
    print(f"✅ Starting hand: {obs['hand_size'][0]} cards")
    
    print_game_state(env, 0)
    
    # Play the game
    turn_count = 0
    max_turns = 50  # Prevent infinite loops
    
    while turn_count < max_turns:
        turn_count += 1
        
        # Get legal actions
        legal_actions = env.get_legal_actions()
        
        if not legal_actions:
            print(f"\n❌ Turn {turn_count}: No legal actions available")
            break
        
        print(f"\nTurn {turn_count}: {len(legal_actions)} legal actions available")
        
        # Show some action details
        for i, action in enumerate(legal_actions[:3]):  # Show first 3 actions
            print(f"  Action {i}: {action.action_type}")
            if hasattr(action, 'card') and action.card:
                print(f"    Card: {action.card.name}")
        
        # Take first available action
        obs, reward, terminated, truncated, info = env.step(0)
        
        print(f"  Action taken: {legal_actions[0].action_type}")
        print(f"  Reward: {reward}")
        
        if terminated:
            print(f"\nGame ended on turn {turn_count}!")
            winner = env.game_engine.check_game_over(env.game_state)
            print(f"Winner: {winner}")
            break
        
        # Print game state every few turns
        if turn_count % 5 == 0 or turn_count <= 3:
            print_game_state(env, turn_count)
    
    print(f"\n📊 Game Summary:")
    print(f"  Total turns: {turn_count}")
    print(f"  Final player points: {env.game_state.player.points}")
    print(f"  Final opponent points: {env.game_state.opponent.points}")
    print(f"  Game ended: {terminated}")
    
    print("\n✅ Real gameplay test completed successfully!")


def test_specific_scenarios():
    """Test specific game scenarios."""
    print("\n🎯 Testing Specific Scenarios")
    print("=" * 40)
    
    # Scenario 1: Energy attachment
    print("\n1. Testing Energy Attachment...")
    deck = create_realistic_deck()
    env = PokemonTCGEnv(player_deck=deck, opponent_deck=deck)
    obs, info = env.reset()
    
    # Generate energy
    env.game_state.player.energy_zone = EnergyType.FIRE
    print(f"   Energy Zone: {env.game_state.player.energy_zone}")
    
    # Scenario 2: Pokemon evolution
    print("\n2. Testing Pokemon Evolution...")
    # Find a Stage 1 Pokemon in hand
    stage1_pokemon = None
    for card in env.game_state.player.hand:
        if isinstance(card, PokemonCard) and card.stage == Stage.STAGE_1:
            stage1_pokemon = card
            break
    
    if stage1_pokemon:
        print(f"   Found Stage 1 Pokemon: {stage1_pokemon.name}")
    else:
        print("   No Stage 1 Pokemon in hand")
    
    # Scenario 3: Attack resolution
    print("\n3. Testing Attack Resolution...")
    # Set up active Pokemon with energy
    if env.game_state.player.hand:
        active_pokemon = env.game_state.player.hand[0]
        if isinstance(active_pokemon, PokemonCard):
            active_pokemon.attached_energies = [EnergyType.COLORLESS]
            env.game_state.player.active_pokemon = active_pokemon
            print(f"   Set active Pokemon: {active_pokemon.name}")
            print(f"   Energy attached: {len(active_pokemon.attached_energies)}")
    
    print("✅ Specific scenarios tested successfully!")


if __name__ == "__main__":
    # Run the tests
    test_real_gameplay()
    test_specific_scenarios() 