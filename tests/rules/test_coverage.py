# tests/rules/test_game_engine_coverage.py
import pytest
from unittest.mock import MagicMock, patch
import dataclasses
from src.rules.game_engine import GameEngine, DamageResult, CoinFlipResult
from src.rules.game_state import GameState, PlayerState, GamePhase, PlayerTag
from src.card_db.core import PokemonCard, Attack, Effect, EnergyType, StatusCondition, Stage


@pytest.fixture
def game_engine():
    return GameEngine()


@pytest.fixture
def base_player_state():
    return PlayerState(player_tag=PlayerTag.PLAYER)


@pytest.fixture
def base_game_state():
    return GameState(
        player=PlayerState(player_tag=PlayerTag.PLAYER),
        opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
    )


class TestGameEngineCoverage:
    """Tests to improve game engine coverage."""

    def test_flip_coin(self, game_engine):
        """Test coin flip mechanics."""
        result = game_engine.flip_coin()
        assert result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS]

    def test_flip_coins(self, game_engine):
        """Test multiple coin flips."""
        results = game_engine.flip_coins(5)
        assert len(results) == 5
        assert all(result in [CoinFlipResult.HEADS, CoinFlipResult.TAILS] for result in results)

    def test_extract_damage_bonus(self, game_engine):
        """Test damage bonus extraction."""
        text = "Deal 30 more damage"
        result = game_engine._extract_damage_bonus(text)
        assert result == 30

    def test_extract_poison_bonus(self, game_engine):
        """Test poison bonus extraction."""
        text = "Deal 50 more damage if the defending Pokémon is Poisoned"
        result = game_engine._extract_poison_bonus(text)
        assert result == 50

    def test_extract_status_condition(self, game_engine):
        """Test status condition extraction."""
        assert game_engine._extract_status_condition("Poison the defending Pokémon") == StatusCondition.POISONED
        assert game_engine._extract_status_condition("Burn the defending Pokémon") == StatusCondition.BURNED
        assert game_engine._extract_status_condition("Paralyze the defending Pokémon") == StatusCondition.PARALYZED
        assert game_engine._extract_status_condition("Confuse the defending Pokémon") == StatusCondition.CONFUSED
        assert game_engine._extract_status_condition("Put the defending Pokémon to sleep") == StatusCondition.ASLEEP

    def test_extract_status_condition_from_attack(self, game_engine):
        """Test status condition extraction from attack."""
        attack = Attack(name="Test Attack", cost=[], damage=50, description="Poison the defending Pokémon")
        result = game_engine._extract_status_condition_from_attack(attack)
        assert result == StatusCondition.POISONED

    def test_apply_status_condition_effects(self, game_engine, base_game_state):
        """Test status condition effects."""
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[], status_condition=StatusCondition.POISONED)
        updated_pokemon = game_engine.apply_status_condition_effects(pokemon, base_game_state)
        assert updated_pokemon.damage_counters > 0

    def test_heal_pokemon(self, game_engine):
        """Test Pokemon healing."""
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[], damage_counters=30)
        healed_pokemon = game_engine.heal_pokemon(pokemon, 20)
        assert healed_pokemon.damage_counters == 10

    def test_discard_energy(self, game_engine):
        """Test energy discarding."""
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[], attached_energies=[EnergyType.FIRE])
        updated_pokemon, _ = game_engine.discard_energy(pokemon, [EnergyType.FIRE])
        assert len(updated_pokemon.attached_energies) == 0

    def test_can_use_attack(self, game_engine, base_game_state):
        """Test attack usage validation."""
        attack = Attack(name="A", cost=[EnergyType.FIRE], damage=10)
        attacker = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[attack], attached_energies=[EnergyType.FIRE])
        game_state = dataclasses.replace(base_game_state, player=dataclasses.replace(base_game_state.player, active_pokemon=attacker))
        assert game_engine._can_use_attack(attacker, attack, game_state)

    def test_can_evolve(self, game_engine, base_game_state):
        """Test evolution validation."""
        evolution = PokemonCard(id="evolved", name="Evolved", hp=120, pokemon_type=EnergyType.FIRE, stage=Stage.STAGE_1, evolves_from="Basic", attacks=[])
        base_pokemon = PokemonCard(id="basic", name="Basic", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        
        player_state = dataclasses.replace(base_game_state.player, hand=[evolution], active_pokemon=base_pokemon)
        game_state = dataclasses.replace(base_game_state, player=player_state)
        
        assert game_engine._can_evolve(evolution, base_pokemon, game_state) is True

    def test_can_retreat(self, game_engine, base_game_state):
        """Test retreat validation."""
        active_pokemon = PokemonCard(id="active", name="Active", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, retreat_cost=1, attached_energies=[EnergyType.FIRE], attacks=[])
        bench_pokemon = PokemonCard(id="bench", name="Bench", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        
        player_state = dataclasses.replace(base_game_state.player, active_pokemon=active_pokemon, bench=[bench_pokemon])
        game_state = dataclasses.replace(base_game_state, player=player_state)

        assert game_engine._can_retreat(active_pokemon, bench_pokemon, game_state) is True

    def test_can_attach_energy(self):
        """Test energy attachment validation (now deprecated logic)."""
        pass # This logic is now handled by can_attach_energy_from_zone

    def test_apply_status_condition_effects_in_order(self, game_engine):
        """Test status condition effects in order."""
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[], damage_counters=0, status_condition=StatusCondition.POISONED)
        
        new_pokemon, resolved = game_engine.apply_status_condition_effects_in_order(pokemon)
        assert new_pokemon.damage_counters == 10
        assert not resolved

    def test_can_attach_tool(self, game_engine, base_game_state):
        """Test tool attachment validation."""
        pokemon = PokemonCard(id="test", name="Test", hp=100, pokemon_type=EnergyType.FIRE, stage=Stage.BASIC, attacks=[])
        assert game_engine.can_attach_tool(pokemon, base_game_state) is True

    def test_award_points(self, game_engine, base_player_state):
        """Test point awarding."""
        player = game_engine.award_points(base_player_state, 1)
        assert player.points == 1
        
        player = game_engine.award_points(player, 3)
        assert player.points == 3
        
        # Test trying to award more when at max - should cap at 3
        player = game_engine.award_points(player, 1)
        assert player.points == 3
    
    def test_map_effect_type_to_status(self, game_engine):
        """Test effect type to status mapping."""
        assert game_engine._map_effect_type_to_status("poison") == StatusCondition.POISONED
        assert game_engine._map_effect_type_to_status("burn") == StatusCondition.BURNED
        assert game_engine._map_effect_type_to_status("paralyze") == StatusCondition.PARALYZED
        assert game_engine._map_effect_type_to_status("confuse") == StatusCondition.CONFUSED
        assert game_engine._map_effect_type_to_status("sleep") == StatusCondition.ASLEEP
        assert game_engine._map_effect_type_to_status("unknown") is None
    
    def test_start_turn_energy_generation(self, game_engine):
        """Test start turn energy generation."""
        player = PlayerState(player_tag=PlayerTag.PLAYER, energy_zone=None)
        
        player = game_engine.start_turn_energy_generation(player)
        assert player.energy_zone is not None
        
        # Test does not generate if buffer is full
        player_full = dataclasses.replace(player, energy_zone=[EnergyType.FIRE])
        player_full = game_engine.start_turn_energy_generation(player_full)
        assert player_full.energy_zone == [EnergyType.FIRE]
    
    def test_start_first_turn(self, game_engine, base_game_state):
        """Test first turn restrictions."""
        game_state = dataclasses.replace(base_game_state, turn_number=0)
        
        final_state = game_engine.start_first_turn(game_state)
        assert final_state.is_first_turn is True
    
    def test_enforce_hand_limit(self, game_engine):
        """Test hand limit enforcement."""
        player = PlayerState(
            player_tag=PlayerTag.PLAYER,
            hand=[MagicMock() for _ in range(15)]
        )
        
        new_player = game_engine.enforce_hand_limit(player)
        assert len(new_player.hand) == game_engine.max_hand_size
        assert len(new_player.discard_pile) > 0
    
    def test_load_deck(self, game_engine):
        """Test load deck method."""
        # Should not raise any exceptions
        game_engine.load_deck() 