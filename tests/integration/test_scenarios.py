import pytest
from unittest.mock import MagicMock, patch

from src.rules.game_state import GameState, PlayerState
from src.rules.game_engine import GameEngine
from src.card_db.core import PokemonCard, Attack, Effect, EnergyType, StatusCondition, Stage
from src.card_db.loader import load_card_db
from src.card_db.trainer_executor import play_trainer_card

# --- Fixtures ---

@pytest.fixture
def card_db():
    """Load the card database for easy access in tests."""
    return load_card_db()

@pytest.fixture
def game_engine():
    return GameEngine()

# --- Scenario-Based Tests ---

def test_scenario_rare_candy_evolution(game_engine, card_db):
    """
    Tests the "Rare Candy" Item card scenario.
    A player should be able to evolve a Basic Pokemon directly to its Stage 2 form,
    skipping the Stage 1, by using Rare Candy.
    """
    # 1. Setup the game state
    game_state = GameState(player=PlayerState(), opponent=PlayerState())
    
    # Get actual cards from the database
    base_pokemon = card_db.get("pgo-007") # Charmander
    stage2_evolution = card_db.get("pgo-009") # Charizard
    rare_candy = card_db.get("pgo-069") # Rare Candy
    
    assert base_pokemon is not None and stage2_evolution is not None and rare_candy is not None
    
    # Put the base Pokemon on the bench and the evolution + rare candy in hand
    base_pokemon.turn_played = game_state.turn_number - 1 # Ensure it wasn't played this turn
    game_state.player.bench = [base_pokemon]
    game_state.player.hand = [stage2_evolution, rare_candy]
    
    # 2. Mock the executor to simulate the Rare Candy effect
    # In a real game, this would involve a complex effect chain. Here, we simulate the outcome.
    def mock_rare_candy_effect(card, gs, player, game_engine):
        # Find the base and evolution in play
        base = next((p for p in player.bench if p.id == base_pokemon.id), None)
        evo_in_hand = next((c for c in player.hand if c.id == stage2_evolution.id), None)
        
        if base and evo_in_hand:
            # Perform the evolution
            game_engine.evolve_pokemon(evo_in_hand, base, gs)
            return True
        return False

    with patch('src.card_db.trainer_executor.execute_trainer_card', side_effect=mock_rare_candy_effect):
        # 3. Play the "Rare Candy" card
        play_trainer_card(rare_candy, game_state, game_state.player, game_engine)

    # 4. Assert the outcome
    assert len(game_state.player.bench) == 1
    evolved_pokemon = game_state.player.bench[0]
    assert evolved_pokemon.id == "pgo-009", "The benched Pokemon should now be Charizard"
    assert evolved_pokemon.stage == Stage.STAGE_2, "Pokemon should have evolved to Stage 2"
    assert rare_candy not in game_state.player.hand, "Rare Candy should be moved from hand"

def test_scenario_weakness_and_resistance_calculation(game_engine, card_db):
    """
    Tests that damage calculation correctly applies weakness.
    TCG Pocket only has Weakness (+20 damage), no Resistance.
    """
    # 1. Setup the game state
    game_state = GameState(player=PlayerState(), opponent=PlayerState())
    
    # Attacker: Fire-type
    attacker = card_db.get("pgo-004") # Charmander (Fire)
    # Target: Grass-type with weakness to Fire
    target = card_db.get("pgo-001") # Bulbasaur (Grass, Weakness: Fire)
    
    assert attacker is not None and target is not None
    
    # Set them as active Pokemon
    game_state.player.active_pokemon = attacker
    game_state.opponent.active_pokemon = target
    
    # Define a simple attack
    attack = Attack(name="Ember", damage=30)
    
    # Mock checks that are not part of this test
    game_engine._can_use_attack = MagicMock(return_value=True)

    # 2. Resolve the attack
    result = game_engine.resolve_attack(attacker, attack, target, game_state)
    
    # 3. Assert the outcome
    # Base damage (30) + Weakness (20) = 50
    assert result.damage_dealt == 50, "Damage should be increased due to weakness"
    assert result.damage_result == "weakness", "Damage result should reflect weakness was applied"
    assert target.damage_counters == 50, "Target should have 50 damage counters" 