"""Tests for the GameEngine class."""

import pytest
import dataclasses
from typing import List

from src.rules.game_engine import GameEngine, DamageResult, CoinFlipResult
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import PokemonCard, Attack, EnergyType, Stage, StatusCondition, Card


@pytest.fixture
def game_engine():
    """Create a GameEngine instance."""
    return GameEngine()


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
        ],
        retreat_cost=1
    )


@pytest.fixture
def fire_pokemon():
    """Create a Fire Pokemon for testing."""
    return PokemonCard(
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


@pytest.fixture
def grass_pokemon():
    """Create a Grass Pokemon for testing."""
    return PokemonCard(
        id="TEST-003",
        name="Grass Pokemon",
        hp=90,
        pokemon_type=EnergyType.GRASS,
        stage=Stage.BASIC,
        attacks=[
            Attack(
                name="Grass Attack",
                cost=[EnergyType.GRASS],
                damage=35
            )
        ],
        weakness=(EnergyType.FIRE, 20)
    )


@pytest.fixture
def basic_game_state(basic_pokemon):
    """Create a basic game state for testing."""
    player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=basic_pokemon)
    opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=dataclasses.replace(basic_pokemon, id="OPPONENT-001"))
    return GameState(player=player, opponent=opponent, phase=GamePhase.MAIN)


@pytest.fixture
def mock_card():
    """Create a mock card for testing."""
    return Card(id="MOCK-001", name="Mock Card")


class TestGameEngine:
    
    def test_attack_resolution_basic(self, game_engine, basic_pokemon):
        """Test basic attack resolution."""
        attack = basic_pokemon.attacks[0]
        target = PokemonCard(
            id="TARGET-001",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Add energy to attacker using immutable replace
        attacker = dataclasses.replace(basic_pokemon, attached_energies=[EnergyType.COLORLESS])
        
        player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=attacker)
        opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=target)
        game_state = GameState(player=player, opponent=opponent, phase=GamePhase.ATTACK)
        
        result = game_engine.resolve_attack(attacker, attack, target, game_state)
        
        assert result.damage_dealt == 30
        assert result.damage_result == DamageResult.NORMAL
        assert not result.target_ko
        assert len(result.energy_discarded) > 0 # Cost should be paid
    
    def test_attack_resolution_weakness(self, game_engine, fire_pokemon, grass_pokemon):
        """Test attack resolution with weakness."""
        attack = fire_pokemon.attacks[0]
        
        # Add energy to attacker using immutable replace
        attacker = dataclasses.replace(fire_pokemon, attached_energies=[EnergyType.FIRE])
        
        # Target starts with no damage implicitly
        target = grass_pokemon
        
        player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=attacker)
        opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=target)
        game_state = GameState(player=player, opponent=opponent, phase=GamePhase.ATTACK)
        
        result = game_engine.resolve_attack(attacker, attack, target, game_state)
        
        # Weakness adds +20 damage
        assert result.damage_dealt == 60  # 40 + 20 for weakness
        assert result.damage_result == DamageResult.WEAKNESS
        assert not result.target_ko  # 60 damage vs 90 HP is not a KO
    
    def test_attack_resolution_no_resistance(self, game_engine, fire_pokemon):
        """Test attack resolution without resistance (TCG Pocket has no resistance)."""
        attack = fire_pokemon.attacks[0]
        target = PokemonCard(
            id="NORMAL-001",
            name="Normal Pokemon",
            hp=100,
            pokemon_type=EnergyType.WATER,
            stage=Stage.BASIC,
            attacks=[]
            # No resistance field in TCG Pocket
        )
        
        # Add energy to attacker using immutable replace
        attacker = dataclasses.replace(fire_pokemon, attached_energies=[EnergyType.FIRE])
        
        player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=attacker)
        opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=target)
        game_state = GameState(player=player, opponent=opponent, phase=GamePhase.ATTACK)
        result = game_engine.resolve_attack(attacker, attack, target, game_state)
        
        # Should be normal damage, no resistance reduction
        assert result.damage_dealt == 40
        assert result.damage_result == DamageResult.NORMAL
        assert not result.target_ko
    
    def test_evolution_mechanics(self, game_engine, basic_pokemon):
        """Test evolution mechanics."""
        evolution_card = PokemonCard(
            id="EVOLUTION-001",
            name="Evolved Pokemon",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            evolves_from="Test Pokemon",
            attacks=[]
        )

        player_state = PlayerState(
            player_tag=PlayerTag.PLAYER,
            active_pokemon=basic_pokemon,
            hand=[evolution_card],
            pokemon_entered_play_this_turn=[] # Can evolve on turn 1
        )
        opponent_state = PlayerState(player_tag=PlayerTag.OPPONENT)
        game_state = GameState(player=player_state, opponent=opponent_state, phase=GamePhase.MAIN, turn_number=2, is_first_turn=False)
        
        # Should be able to evolve
        new_state = game_engine.evolve_pokemon(evolution_card, basic_pokemon, game_state)
        assert new_state.player.active_pokemon.id == "EVOLUTION-001"
        assert evolution_card not in new_state.player.hand
        
    def test_retreat_mechanics(self, game_engine, basic_pokemon):
        """Test retreat mechanics."""
        bench_pokemon = PokemonCard(
            id="BENCH-001",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Test with retreat cost and sufficient energy
        active_with_energy = dataclasses.replace(basic_pokemon, attached_energies=[EnergyType.COLORLESS])
        
        player_state = PlayerState(
            player_tag=PlayerTag.PLAYER,
            active_pokemon=active_with_energy,
            bench=[bench_pokemon]
        )
        opponent_state = PlayerState(player_tag=PlayerTag.OPPONENT)
        game_state = GameState(player=player_state, opponent=opponent_state, phase=GamePhase.MAIN)
        
        # Retreat should succeed
        new_state = game_engine.retreat_pokemon(player_state, bench_pokemon, game_state)
        assert new_state.player.active_pokemon.id == "BENCH-001"
        assert basic_pokemon.id in [p.id for p in new_state.player.bench]
        
    def test_retreat_restrictions_status_conditions(self, game_engine, basic_pokemon):
        """Test that status conditions prevent retreat."""
        bench_pokemon = PokemonCard(
            id="BENCH-001",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        opponent_state = PlayerState(player_tag=PlayerTag.OPPONENT)

        # Test asleep Pokemon cannot retreat
        asleep_pokemon = dataclasses.replace(basic_pokemon, status_condition=StatusCondition.ASLEEP)
        player_asleep = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=asleep_pokemon, bench=[bench_pokemon])
        game_state_asleep = GameState(player=player_asleep, opponent=opponent_state, phase=GamePhase.MAIN)
        
        with pytest.raises(ValueError, match="Cannot retreat when Asleep"):
            game_engine.retreat_pokemon(player_asleep, bench_pokemon, game_state_asleep)
        
        # Test paralyzed Pokemon cannot retreat
        paralyzed_pokemon = dataclasses.replace(basic_pokemon, status_condition=StatusCondition.PARALYZED)
        player_paralyzed = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=paralyzed_pokemon, bench=[bench_pokemon])
        game_state_paralyzed = GameState(player=player_paralyzed, opponent=opponent_state, phase=GamePhase.MAIN)
        
        with pytest.raises(ValueError, match="Cannot retreat when Paralyzed"):
            game_engine.retreat_pokemon(player_paralyzed, bench_pokemon, game_state_paralyzed)

    def test_point_awarding_system(self, game_engine):
        """Test TCG Pocket point awarding system."""
        player = PlayerState(player_tag=PlayerTag.PLAYER)
        
        # Award 1 point for regular Pokemon KO
        updated_player = game_engine.award_points(player, 1)
        assert updated_player.points == 1
        
        # Award 2 points for ex Pokemon KO
        updated_player = game_engine.award_points(updated_player, 2)
        assert updated_player.points == 3
        
        # Try to award more points (should raise error)
        with pytest.raises(ValueError, match="Cannot award"):
            game_engine.award_points(updated_player, 1)
    
    def test_game_over_conditions(self, game_engine):
        """Test game over detection with point system."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.DRAW
        )
        
        # Add some Pokemon to avoid the "no Pokemon in play" condition
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        game_state = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, active_pokemon=basic_pokemon),
            opponent=dataclasses.replace(game_state.opponent, active_pokemon=basic_pokemon)
        )
        
        # Add some deck cards
        game_state = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, deck=[None, None, None]),
            opponent=dataclasses.replace(game_state.opponent, deck=[None, None, None])
        )
        
        # Game should continue normally
        result = game_engine.check_game_over(game_state)
        assert result is None
        
        # Player wins by reaching 3 points
        game_state_player_wins = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, points=3)
        )
        assert game_engine.check_game_over(game_state_player_wins) == "player"
        
        # Opponent wins by reaching 3 points
        game_state_opponent_wins = dataclasses.replace(
            game_state,
            opponent=dataclasses.replace(game_state.opponent, points=3)
        )
        assert game_engine.check_game_over(game_state_opponent_wins) == "opponent"
        
        # Test deck depletion (only in DRAW phase)
        game_state_deck_out = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, deck=[]),
            phase=GamePhase.DRAW,
            active_player=PlayerTag.PLAYER
        )
        assert game_engine.check_game_over(game_state_deck_out) == "opponent"
    
    def test_draw_cards(self, game_engine):
        """Test drawing cards."""
        player = PlayerState(
            player_tag=PlayerTag.PLAYER,
            deck=[None, None, None, None, None]  # Mock cards
        )
        
        updated_player, drawn = game_engine.draw_cards(player, 3)
        assert len(drawn) == 3
        assert len(updated_player.deck) == 2
        
        # Test drawing more cards than available
        updated_player2, drawn2 = game_engine.draw_cards(updated_player, 5)
        assert len(drawn2) == 2  # Only 2 cards left
        assert len(updated_player2.deck) == 0
    
    def test_attack_resolution_ko(self, game_engine, fire_pokemon):
        """Test attack resolution that results in KO."""
        attack = fire_pokemon.attacks[0]
        target = PokemonCard(
            id="WEAK-001",
            name="Weak Pokemon",
            hp=30,  # Low HP
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Add energy to attacker
        attacker = dataclasses.replace(fire_pokemon, attached_energies=[EnergyType.FIRE])
        
        player = PlayerState(player_tag=PlayerTag.PLAYER, active_pokemon=attacker)
        opponent = PlayerState(player_tag=PlayerTag.OPPONENT, active_pokemon=target)
        game_state = GameState(player=player, opponent=opponent, phase=GamePhase.MAIN)
        
        result = game_engine.resolve_attack(attacker, attack, target, game_state)
        
        assert result.damage_dealt == 40
        assert result.target_ko  # 40 damage vs 30 HP should KO
    
    def test_status_condition_prevents_attack(self, game_engine, basic_game_state):
        """Test that status conditions prevent attacking."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            status_condition=StatusCondition.ASLEEP,
            attached_energies=[EnergyType.COLORLESS]
        )
        
        attack = Attack(
            name="Test Attack",
            cost=[EnergyType.COLORLESS],
            damage=30
        )
        
        # Should not be able to attack while asleep
        can_attack = game_engine._can_use_attack(asleep_pokemon, attack, basic_game_state)
        assert not can_attack
        
        # Should not be able to attack while paralyzed
        paralyzed_pokemon = dataclasses.replace(asleep_pokemon, status_condition=StatusCondition.PARALYZED)
        can_attack = game_engine._can_use_attack(paralyzed_pokemon, attack, basic_game_state)
        assert not can_attack
        
        # Should be able to attack when normal
        normal_pokemon = dataclasses.replace(asleep_pokemon, status_condition=None)
        can_attack = game_engine._can_use_attack(normal_pokemon, attack, basic_game_state)
        assert can_attack
    
    def test_coin_flip_mechanics(self, game_engine):
        """Test coin flip mechanics."""
        # Test single coin flip
        result = game_engine.flip_coin()
        assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
        
        # Test multiple coin flips
        results = game_engine.flip_coins(3)
        assert len(results) == 3
        for result in results:
            assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]
    
    def test_healing_mechanics(self, game_engine):
        """Test healing mechanics."""
        pokemon = PokemonCard(
            id="TEST-001",
            name="Damaged Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            damage_counters=50
        )
        
        # Test healing
        healed_pokemon = game_engine.heal_pokemon(pokemon, 30)
        assert healed_pokemon.damage_counters == 20  # 50 - 30 = 20
        
        # Test healing to full
        healed_pokemon2 = game_engine.heal_pokemon(healed_pokemon, 30)
        assert healed_pokemon2.damage_counters == 0  # Cannot go below 0
        
        # Test healing with no damage
        healed_pokemon3 = game_engine.heal_pokemon(healed_pokemon2, 10)
        assert healed_pokemon3.damage_counters == 0