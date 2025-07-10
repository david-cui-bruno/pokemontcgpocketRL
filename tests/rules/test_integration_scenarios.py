"""Integration tests for complex game scenarios."""

import pytest
import dataclasses
from unittest.mock import patch
from src.rules.game_engine import GameEngine, CoinFlipResult
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import (
    PokemonCard, ItemCard, SupporterCard, ToolCard, Attack, Effect,
    EnergyType, Stage, StatusCondition, TargetType
)

# ---- Fixtures ----

@pytest.fixture
def engine():
    """Create a game engine with fixed seed."""
    return GameEngine(random_seed=42)

@pytest.fixture
def basic_pokemon():
    """Create a basic Pokemon for testing."""
    return PokemonCard(
        id="TEST-001",
        name="Test Pokemon",
        hp=100,
        pokemon_type=EnergyType.COLORLESS,
        stage=Stage.BASIC,
        attacks=[
            Attack(
                name="Basic Attack",
                cost=[EnergyType.COLORLESS],
                damage=30
            )
        ]
    )

@pytest.fixture
def evolution_chain():
    """Create a complete evolution chain."""
    basic = PokemonCard(
        id="BASIC-001",
        name="Basic Pokemon",
        hp=60,
        pokemon_type=EnergyType.FIRE,
        stage=Stage.BASIC,
        attacks=[Attack(name="Small Flame", cost=[EnergyType.FIRE], damage=20)]
    )
    
    stage1 = PokemonCard(
        id="STAGE1-001",
        name="Stage 1 Pokemon",
        hp=90,
        pokemon_type=EnergyType.FIRE,
        stage=Stage.STAGE_1,
        evolves_from="Basic Pokemon",
        attacks=[Attack(name="Medium Flame", cost=[EnergyType.FIRE, EnergyType.FIRE], damage=50)]
    )
    
    stage2 = PokemonCard(
        id="STAGE2-001",
        name="Stage 2 Pokemon",
        hp=180,
        pokemon_type=EnergyType.FIRE,
        stage=Stage.STAGE_2,
        evolves_from="Stage 1 Pokemon",
        attacks=[Attack(name="Big Flame", cost=[EnergyType.FIRE, EnergyType.FIRE, EnergyType.FIRE], damage=120)]
    )
    
    return [basic, stage1, stage2]

@pytest.fixture
def tool_card():
    """Create a tool card that boosts damage."""
    return ToolCard(
        id="TOOL-001",
        name="Power Tool",
        effects=[Effect(effect_type="boost_damage", amount=20)]
    )

# ---- Test Classes ----

class TestEvolutionScenarios:
    """Test complex evolution scenarios."""
    
    def test_full_evolution_chain(self, engine, evolution_chain):
        """Test evolving through a complete chain with effects."""
        basic, stage1, stage2 = evolution_chain
        
        # Setup initial state with basic Pokemon
        state = GameState(
            player=PlayerState(
                player_tag=PlayerTag.PLAYER,
                active_pokemon=basic,
                hand=[stage1, stage2]
            ),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN
        )
        
        # Evolve to Stage 1
        state = engine.evolve_pokemon(stage1, basic, state)
        assert state.player.active_pokemon.id == stage1.id
        assert state.player.active_pokemon.stage == Stage.STAGE_1
        
        # Evolve to Stage 2
        state = engine.evolve_pokemon(stage2, state.player.active_pokemon, state)
        assert state.player.active_pokemon.id == stage2.id
        assert state.player.active_pokemon.stage == Stage.STAGE_2
        
        # Verify attack power progression
        assert stage1.attacks[0].damage > basic.attacks[0].damage
        assert stage2.attacks[0].damage > stage1.attacks[0].damage

class TestStatusConditionInteractions:
    """Test interactions between multiple status conditions."""
    
    def test_status_condition_order(self, engine, basic_pokemon):
        """Test that status conditions are applied in correct order."""
        pokemon = dataclasses.replace(
            basic_pokemon,
            hp=100,
            damage_counters=60,  # 40 HP remaining
            status_condition=StatusCondition.POISONED
        )
        
        state = GameState(
            player=PlayerState(
                player_tag=PlayerTag.PLAYER,
                active_pokemon=pokemon
            ),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.CHECK_UP
        )
        
        # Process status effects
        state = engine.process_checkup(state)
        
        # Pokemon should be KO'd by poison (10 damage to 40 HP)
        assert state.player.active_pokemon is None

class TestToolCardEffects:
    """Test tool card attachment and effect combinations."""
    
    def test_tool_card_damage_boost(self, engine, basic_pokemon, tool_card):
        """Test that tool cards properly boost damage."""
        pokemon_with_tool = dataclasses.replace(
            basic_pokemon,
            attached_tools=[tool_card],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        target = dataclasses.replace(basic_pokemon)
        
        state = GameState(
            player=PlayerState(
                player_tag=PlayerTag.PLAYER,
                active_pokemon=pokemon_with_tool
            ),
            opponent=PlayerState(
                player_tag=PlayerTag.OPPONENT,
                active_pokemon=target
            ),
            phase=GamePhase.ATTACK
        )
        
        # Execute attack with tool boost
        result = engine.resolve_attack(
            pokemon_with_tool,
            pokemon_with_tool.attacks[0],
            target,
            state
        )
        
        # Base damage (30) + Tool boost (20)
        assert result.damage_dealt == 50

class TestComplexGameScenarios:
    """Test complex game scenarios involving multiple mechanics."""
    
    def test_bench_manipulation_with_effects(self, engine, basic_pokemon):
        """Test complex bench manipulation with status effects."""
        active = dataclasses.replace(basic_pokemon, status_condition=StatusCondition.PARALYZED)
        bench = [
            dataclasses.replace(basic_pokemon, id=f"BENCH-{i}")
            for i in range(3)
        ]
        
        state = GameState(
            player=PlayerState(
                player_tag=PlayerTag.PLAYER,
                active_pokemon=active,
                bench=bench
            ),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN
        )
        
        # Try to retreat paralyzed Pokemon (should fail)
        with pytest.raises(ValueError):
            engine.retreat_pokemon(state.player, bench[0], state)
    
    def test_energy_zone_advanced_mechanics(self, engine, basic_pokemon):
        """Test complex energy zone interactions."""
        pokemon = dataclasses.replace(basic_pokemon)
        state = GameState(
            player=PlayerState(
                player_tag=PlayerTag.PLAYER,
                active_pokemon=pokemon,
                registered_energy_types=[EnergyType.FIRE, EnergyType.WATER]
            ),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN
        )
        
        # Generate energy
        state.player.generate_energy(EnergyType.FIRE)
        assert state.player.energy_zone == EnergyType.FIRE
        
        # Attach energy
        state = engine.attach_energy(state, pokemon.id)
        assert len(state.player.active_pokemon.attached_energies) == 1
        assert state.player.energy_zone is None
        
        # Try to attach again (should fail)
        with pytest.raises(ValueError):
            engine.attach_energy(state, pokemon.id)

class TestVictoryConditions:
    """Test various victory conditions and scenarios."""
    
    def test_ex_pokemon_points(self, engine, basic_pokemon):
        """Test point awarding with EX Pokemon knockouts."""
        ex_pokemon = dataclasses.replace(
            basic_pokemon,
            is_ex=True,
            hp=30  # Low HP to ensure KO
        )
        
        attacker = dataclasses.replace(
            basic_pokemon,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        state = GameState(
            player=PlayerState(
                player_tag=PlayerTag.PLAYER,
                active_pokemon=attacker
            ),
            opponent=PlayerState(
                player_tag=PlayerTag.OPPONENT,
                active_pokemon=ex_pokemon
            ),
            phase=GamePhase.ATTACK
        )
        
        # Execute attack that will KO EX Pokemon
        final_state = engine.execute_attack(state, attacker.attacks[0])
        
        # Should award 2 points for EX knockout
        assert final_state.player.points == 2
