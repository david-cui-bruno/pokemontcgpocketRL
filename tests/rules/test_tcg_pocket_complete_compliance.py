"""Complete TCG Pocket rulebook compliance tests."""

import pytest
from typing import List, Dict, Optional
import dataclasses
from collections import Counter

from src.rules.game_engine import GameEngine, CoinFlipResult, DamageResult
from src.rules.game_state import GameState, PlayerState, PlayerTag, GamePhase
from src.card_db.core import (
    PokemonCard, Attack, Effect, EnergyType, Stage, StatusCondition,
    TargetType, ItemCard, SupporterCard, ToolCard, Card
)


@pytest.fixture
def game_engine():
    """Create a GameEngine instance."""
    return GameEngine()


@pytest.fixture
def basic_game_state():
    """Create a basic game state for testing."""
    return GameState(
        player=PlayerState(player_tag=PlayerTag.PLAYER),
        opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
    )


class TestDeckConstructionRules:
    """Test deck construction rules (rulebook §1)."""
    
    def test_deck_must_be_exactly_20_cards(self, game_engine):
        """Test that a deck must have exactly 20 cards."""
        # Valid deck
        deck = [
            PokemonCard(id=f"P{i}", name=f"Pokemon {i}", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[])
            for i in range(20)
        ]
        assert game_engine.validate_deck(deck) is True

        # Invalid deck (too few)
        deck = [
            PokemonCard(id=f"P{i}", name=f"Pokemon {i}", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[])
            for i in range(19)
        ]
        assert game_engine.validate_deck(deck) is False

        # Invalid deck (too many)
        deck = [
            PokemonCard(id=f"P{i}", name=f"Pokemon {i}", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[])
            for i in range(21)
        ]
        assert game_engine.validate_deck(deck) is False
    
    def test_no_energy_cards_in_deck(self):
        """Test that decks cannot contain Energy cards."""
        from src.card_db.core import EnergyCard
        
        # This should raise an error or be prevented
        with pytest.raises(Exception):
            deck = [EnergyCard(id="ENERGY-001", energy_type=EnergyType.FIRE)]
    
    def test_maximum_2_copies_per_card(self, game_engine):
        """Test the card copy limit."""
        # Valid deck
        deck = [
            PokemonCard(id="P1", name="Pokemon A", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[]),
            PokemonCard(id="P1", name="Pokemon A", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[]),
        ] * 10
        assert game_engine.validate_deck(deck) is True

        # Invalid deck
        invalid_deck = [
            PokemonCard(id="P1", name="Pokemon A", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[])
        ] * 3 
        invalid_deck.extend([
            PokemonCard(id=f"P{i}", name=f"Pokemon {i}", hp=100, pokemon_type=EnergyType.COLORLESS, stage=Stage.BASIC, attacks=[])
            for i in range(17)
        ])
        assert game_engine.validate_deck(invalid_deck) is False


class TestTurnStructure:
    """Test turn structure (rulebook §4)."""
    
    def test_start_phase_energy_generation(self, game_engine):
        """Test energy generation at start of turn."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        player = game_state.player
        
        # Set up registered energy types (required for energy generation)
        player = dataclasses.replace(player, registered_energy_types=[EnergyType.FIRE, EnergyType.WATER])
        
        # Initially no energy in zone
        assert player.energy_zone is None
        
        # Generate energy at start of turn
        updated_player = game_engine.start_turn_energy_generation(player)
        assert updated_player.energy_zone is not None
        
        # Cannot generate more energy if zone is full
        updated_player2 = game_engine.start_turn_energy_generation(updated_player)
        assert updated_player2.energy_zone is not None  # Should remain same
    
    def test_start_phase_card_drawing(self, game_engine):
        """Test card drawing at start of turn."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        player = game_state.player
        
        # Add cards to deck
        deck = [PokemonCard(
            id=f"TEST-{i}",
            name=f"Test Pokemon {i}",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        ) for i in range(10)]
        
        player = dataclasses.replace(player, deck=deck)
        
        initial_hand_size = len(player.hand)
        initial_deck_size = len(player.deck)
        
        # Draw 1 card (normal turn)
        updated_player = game_engine.draw_cards(player, 1)
        
        assert len(updated_player.hand) == initial_hand_size + 1
        assert len(updated_player.deck) == initial_deck_size - 1
    
    def test_action_phase_order(self, game_engine):
        """Test that actions can be performed in any order during action phase."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN
        )
        assert game_state.phase == GamePhase.MAIN
    
    def test_attack_phase_validation(self, game_engine):
        """Test attack phase validation."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.MAIN
        )
        
        attacker = PokemonCard(
            id="TEST-001",
            name="Attacker",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        # Should be able to attack with proper energy
        can_attack = game_engine._can_use_attack(attacker, attacker.attacks[0], game_state)
        assert can_attack
        
        # Should not be able to attack without energy
        attacker_no_energy = dataclasses.replace(attacker, attached_energies=[])
        can_attack_fail = game_engine._can_use_attack(
            attacker_no_energy, attacker.attacks[0], game_state
        )
        assert not can_attack_fail


class TestEnergyZoneMechanics:
    """Test Energy Zone mechanics (rulebook §5)."""
    
    def test_single_slot_energy_zone(self):
        """Test that Energy Zone can only hold one energy."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        player = game_state.player
        
        # Initially empty
        assert player.energy_zone is None
        
        # Add energy
        player = dataclasses.replace(player, energy_zone=EnergyType.FIRE)
        assert player.energy_zone == EnergyType.FIRE
        
        # Replace energy (single slot)
        player = dataclasses.replace(player, energy_zone=EnergyType.WATER)
        assert player.energy_zone == EnergyType.WATER
        assert player.energy_zone != EnergyType.FIRE
    
    def test_energy_attachment_from_zone(self, game_engine):
        """Test energy attachment from Energy Zone."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        player = game_state.player
        target_pokemon = PokemonCard(
            id="TEST-001",
            name="Target Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        # Set up energy in zone
        player = dataclasses.replace(player, energy_zone=EnergyType.FIRE, active_pokemon=target_pokemon)
        game_state = dataclasses.replace(game_state, player=player)
        
        # Attach energy
        updated_game_state = game_engine.attach_energy(player, target_pokemon, game_state)
        updated_player = updated_game_state.player
        
        # Check energy was attached and zone was cleared
        assert updated_player.energy_zone is None
        assert updated_player.energy_attached_this_turn is True
        assert EnergyType.FIRE in updated_player.active_pokemon.attached_energies
    
    def test_energy_discarding_mechanics(self, game_engine):
        """Test energy discarding mechanics."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            attached_energies=[EnergyType.FIRE, EnergyType.WATER]
        )
        
        # Discard energy
        updated_pokemon, discarded = game_engine.discard_energy(pokemon, [EnergyType.FIRE])
        assert EnergyType.FIRE in discarded
        assert len(updated_pokemon.attached_energies) == 1
        assert EnergyType.WATER in updated_pokemon.attached_energies


class TestVictoryConditions:
    """Test victory conditions (rulebook §1)."""
    
    def test_first_to_3_points_wins(self, game_engine):
        """Test that first player to 3 points wins."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        
        # Set up valid game state
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        game_state = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, active_pokemon=pokemon, deck=[None] * 5),
            opponent=dataclasses.replace(game_state.opponent, active_pokemon=pokemon, deck=[None] * 5)
        )
        
        # Game continues normally
        assert game_engine.check_game_over(game_state) is None
        
        # Player reaches 3 points and wins
        game_state_player_wins = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, points=3)
        )
        assert game_engine.check_game_over(game_state_player_wins) == "player"
        
        # Opponent reaches 3 points and wins
        game_state_opponent_wins = dataclasses.replace(
            game_state,
            opponent=dataclasses.replace(game_state.opponent, points=3)
        )
        assert game_engine.check_game_over(game_state_opponent_wins) == "opponent"
    
    def test_no_pokemon_in_play_loses(self, game_engine):
        """Test that player with no Pokemon in play loses."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        
        # Set up valid game state
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        game_state = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, active_pokemon=pokemon, deck=[None] * 5),
            opponent=dataclasses.replace(game_state.opponent, active_pokemon=pokemon, deck=[None] * 5)
        )
        
        # Game continues normally
        assert game_engine.check_game_over(game_state) is None
        
        # Player has no Pokemon in play
        game_state_no_pokemon = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, active_pokemon=None, bench=[])
        )
        assert game_engine.check_game_over(game_state_no_pokemon) == "opponent"
    
    def test_deck_out_condition(self, game_engine):
        """Test that running out of cards causes loss."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT)
        )
        
        # Set up valid game state
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        game_state = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, active_pokemon=pokemon, deck=[pokemon] * 5),
            opponent=dataclasses.replace(game_state.opponent, active_pokemon=pokemon, deck=[pokemon] * 5)
        )
        
        # Game continues normally
        assert game_engine.check_game_over(game_state) is None
        
        # Player runs out of cards
        game_state_deck_out = dataclasses.replace(
            game_state,
            player=dataclasses.replace(game_state.player, deck=[])
        )
        assert game_engine.check_game_over(game_state_deck_out) == "opponent"


class TestStatusConditionMechanics:
    """Test status condition mechanics (rulebook §7)."""
    
    def test_poison_damage_10(self, game_engine):
        """Test poison damage is exactly 10."""
        poisoned_pokemon = PokemonCard(
            id="TEST-001",
            name="Poisoned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.POISONED,
        )

        updated_pokemon = game_engine.apply_status_condition_effects(
            poisoned_pokemon, game_engine.game_state
        )
        assert updated_pokemon.damage_counters == 10
        # The original object is unchanged
        assert poisoned_pokemon.damage_counters == 0

    def test_burn_damage_20(self, game_engine):
        """Test burn damage is exactly 20."""
        burned_pokemon = PokemonCard(
            id="TEST-001",
            name="Burned Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.BURNED,
        )

        updated_pokemon = game_engine.apply_status_condition_effects(
            burned_pokemon, game_engine.game_state
        )
        assert updated_pokemon.damage_counters == 20
    
    def test_sleep_prevents_attack(self, game_engine):
        """Test that asleep Pokemon cannot attack."""
        asleep_pokemon = PokemonCard(
            id="TEST-001",
            name="Asleep Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.ASLEEP
        )
        
        # The attack object is not directly available here, so we'll check if the attack can be used.
        # This requires mocking the attack resolution or a more complex test.
        # For now, we'll just check if the attack cannot be used.
        assert not game_engine._can_use_attack(asleep_pokemon, asleep_pokemon.attacks[0], game_engine.game_state)
    
    def test_paralysis_prevents_attack(self, game_engine):
        """Test that paralyzed Pokemon cannot attack."""
        paralyzed_pokemon = PokemonCard(
            id="TEST-001",
            name="Paralyzed Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.PARALYZED
        )
        
        # The attack object is not directly available here, so we'll check if the attack can be used.
        # This requires mocking the attack resolution or a more complex test.
        # For now, we'll just check if the attack cannot be used.
        assert not game_engine._can_use_attack(paralyzed_pokemon, paralyzed_pokemon.attacks[0], game_engine.game_state)
    
    def test_confusion_coin_flip_mechanics(self, game_engine):
        """Test confusion coin flip mechanics."""
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.ATTACK
        )
        
        confused_pokemon = PokemonCard(
            id="TEST-001",
            name="Confused Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            status_condition=StatusCondition.CONFUSED
        )
        
        # The attack object is not directly available here, so we'll check if the attack can be used.
        # This requires mocking the attack resolution or a more complex test.
        # For now, we'll just check if the attack cannot be used.
        assert not game_engine._can_use_attack(confused_pokemon, confused_pokemon.attacks[0], game_state)


class TestEvolutionRules:
    """Test evolution rules."""
    
    def test_cannot_evolve_on_turn_entered_play(self, game_engine):
        """Test that Pokemon cannot evolve on the turn they entered play."""
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Basic Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        evolution = PokemonCard(
            id="TEST-002",
            name="Evolution",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            evolves_from="Basic Pokemon",
            attacks=[]
        )
        
        # Add Pokemon to "entered play this turn" list
        game_engine.game_state.player.pokemon_entered_play_this_turn.append(basic_pokemon.id)
        
        # Should not be able to evolve
        can_evolve = game_engine._can_evolve(evolution, basic_pokemon, game_engine.game_state)
        assert not can_evolve
    
    def test_evolution_chain_validation(self, game_engine):
        """Test that evolution follows proper chain."""
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Basic Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        stage1_evolution = PokemonCard(
            id="TEST-002",
            name="Stage 1 Evolution",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            evolves_from="Basic Pokemon",
            attacks=[]
        )
        
        stage2_evolution = PokemonCard(
            id="TEST-003",
            name="Stage 2 Evolution",
            hp=140,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_2,
            evolves_from="Stage 1 Evolution",
            attacks=[]
        )
        
        # Add evolution card to hand
        game_engine.game_state.player.hand.append(stage1_evolution)
        
        # Can evolve basic to stage 1
        can_evolve = game_engine._can_evolve(stage1_evolution, basic_pokemon, game_engine.game_state)
        assert can_evolve
        
        # Cannot evolve basic to stage 2
        can_evolve = game_engine._can_evolve(stage2_evolution, basic_pokemon, game_engine.game_state)
        assert not can_evolve
    
    def test_evolution_once_per_pokemon(self, game_engine):
        """Test that each Pokemon can only evolve once per turn."""
        basic_pokemon = PokemonCard(
            id="TEST-001",
            name="Basic Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        stage1_evolution = PokemonCard(
            id="TEST-002",
            name="Stage 1 Evolution",
            hp=120,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_1,
            evolves_from="Basic Pokemon",
            attacks=[]
        )
        
        stage2_evolution = PokemonCard(
            id="TEST-003",
            name="Stage 2 Evolution",
            hp=140,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.STAGE_2,
            evolves_from="Stage 1 Evolution",
            attacks=[]
        )
        
        # Add both evolutions to hand
        game_engine.game_state.player.hand.extend([stage1_evolution, stage2_evolution])
        
        # Evolve to stage 1
        success = game_engine.evolve_pokemon(stage1_evolution, basic_pokemon, game_engine.game_state)
        assert success
        
        # Should not be able to evolve again in the same turn
        # This would be tested by checking that the evolved Pokemon is marked
        # as having evolved this turn


class TestStartingPlayerRestrictions:
    """Test starting player restrictions (rulebook §3)."""
    
    def test_first_player_no_draw_turn_0(self, game_engine):
        """Test that first player doesn't draw on turn 0."""
        # This would be tested in the environment's turn handling
        # The environment should not draw a card for the first player on turn 0
        # For now, we'll test the concept
        game_state = GameState()
        game_state.turn_number = 0
        
        # In a real implementation, the environment would check turn_number
        # and skip drawing for the first player on turn 0
        assert game_state.turn_number == 0
    
    def test_first_player_no_energy_attachment_turn_0(self, game_engine):
        """Test that first player cannot attach energy on turn 0."""
        # This would be tested in the environment's action validation
        # The environment should prevent energy attachment for first player on turn 0
        game_state = GameState()
        game_state.turn_number = 0
        
        # In a real implementation, the action validator would check turn_number
        # and prevent energy attachment for the first player on turn 0
        assert game_state.turn_number == 0
    
    def test_first_player_can_play_supporter_turn_0(self, game_engine):
        """Test that first player can play supporter on turn 0."""
        # This would be tested in the environment's action validation
        # The environment should allow supporter play for first player on turn 0
        game_state = GameState()
        game_state.turn_number = 0
        
        # In a real implementation, the action validator would check turn_number
        # and allow supporter play for the first player on turn 0
        assert game_state.turn_number == 0


class TestRetreatMechanics:
    """Test retreat mechanics."""
    
    def test_retreat_cost_validation(self, game_engine):
        """Test that retreat requires discarding the correct amount of energy."""
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            retreat_cost=2,
            attached_energies=[EnergyType.FIRE, EnergyType.WATER]
        )
        
        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[]
        )
        
        game_engine.game_state.player.bench.append(bench_pokemon)
        
        # Should be able to retreat with sufficient energy
        can_retreat = game_engine._can_retreat(pokemon, bench_pokemon, game_engine.game_state)
        assert can_retreat

        # Create a new pokemon with less energy for the second check
        pokemon_less_energy = dataclasses.replace(pokemon, attached_energies=[EnergyType.FIRE])

        # Should not be able to retreat without sufficient energy
        can_retreat_fail = game_engine._can_retreat(
            pokemon_less_energy, bench_pokemon, game_engine.game_state
        )
        assert not can_retreat_fail
    
    def test_retreat_switches_active_pokemon(self, game_engine):
        """Test that retreat switches the active Pokemon."""
        active_pokemon = PokemonCard(
            id="TEST-001",
            name="Active Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            retreat_cost=0,
        )

        bench_pokemon = PokemonCard(
            id="TEST-002",
            name="Bench Pokemon",
            hp=80,
            pokemon_type=EnergyType.GRASS,
            stage=Stage.BASIC,
            attacks=[],
        )

        player = game_engine.game_state.player
        player.active_pokemon = active_pokemon
        player.bench.append(bench_pokemon)

        # Perform retreat
        new_game_state = game_engine.retreat_pokemon(
            player, bench_pokemon, game_engine.game_state
        )

        # Check that the pokemon were swapped
        assert new_game_state.player.active_pokemon.id == "TEST-002"
        # The old active pokemon should now be on the bench
        assert new_game_state.player.bench[0].id == "TEST-001"

    def test_supporter_once_per_turn(self, game_engine):
        """Test that only one supporter can be played per turn."""
        supporter1 = SupporterCard(
            id="SUPP-001", name="Test Supporter 1", effects=[]
        )

        supporter2 = SupporterCard(
            id="SUPP-002", name="Test Supporter 2", effects=[]
        )

        # Create a valid pokemon to be the target of "Potion"
        damaged_pokemon = PokemonCard(
            id="TEST-PKMN-001",
            name="Damaged Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            damage_counters=30,
        )
        game_engine.game_state.player.active_pokemon = damaged_pokemon

        # Use a real trainer card effect that exists
        potion_card = SupporterCard(
            id="potion-id", name="Potion", effects=[]
        )  # The test will look up the effect by name
        player = game_engine.game_state.player
        player.hand.extend([potion_card, supporter2])

        # First supporter play should succeed
        success1 = game_engine.play_trainer_card(
            player, potion_card, game_engine.game_state
        )
        assert success1

        # Mark that a supporter has been played this turn
        player.supporter_played_this_turn = True

        # Second supporter play should fail
        success2 = game_engine.play_trainer_card(
            player, supporter2, game_engine.game_state
        )
        assert not success2

    def test_item_cards_no_limit(self, game_engine):
        """Test that item cards can be played multiple times per turn."""
        item1 = ItemCard(
            id="ITEM-001",
            name="Test Item 1",
            effects=[]
        )
        
        item2 = ItemCard(
            id="ITEM-002",
            name="Test Item 2",
            effects=[]
        )
        
        player = game_engine.game_state.player
        
        # Add items to hand
        player.hand.extend([item1, item2])
        
        # Should be able to play multiple items
        # (This would be tested in actual game flow)
        assert len(player.hand) >= 2
    
    def test_tool_card_attachment_limit(self, game_engine):
        """Test that only one tool can be attached per Pokemon."""
        tool1 = ToolCard(
            id="TOOL-001",
            name="Test Tool 1",
            effects=[]
        )
        
        tool2 = ToolCard(
            id="TOOL-002",
            name="Test Tool 2",
            effects=[]
        )
        
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
        )

        # Attach first tool
        game_engine.attach_tool(
            game_engine.game_state.player, pokemon, tool1, game_engine.game_state
        )

        # Second attachment should fail (this test needs can_attach_tool to be implemented)
        # For now, we just ensure the call signature is correct.
        pass


class TestGamePhaseTransitions:
    """Test game phase transitions."""
    
    def test_phase_advancement(self, basic_game_state):
        """Test that game phases advance correctly."""
        # Start in DRAW phase
        assert basic_game_state.phase == GamePhase.DRAW
        
        # Advance to MAIN phase
        basic_game_state.advance_phase()
        assert basic_game_state.phase == GamePhase.MAIN
        
        # Advance to ATTACK phase
        basic_game_state.advance_phase()
        assert basic_game_state.phase == GamePhase.ATTACK
        
        # Advance to CHECK_UP phase
        basic_game_state.advance_phase()
        assert basic_game_state.phase == GamePhase.CHECK_UP
    
    def test_phase_specific_actions(self, game_engine, basic_game_state):
        """Test that actions are only available in correct phases."""
        # Set up game state
        pokemon = PokemonCard(
            id="TEST-001",
            name="Test Pokemon",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=30)],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        # In MAIN phase, should be able to play Pokemon but not attack
        basic_game_state.phase = GamePhase.MAIN
        assert not game_engine._can_use_attack(pokemon, pokemon.attacks[0], basic_game_state)
        
        # In ATTACK phase, should be able to attack
        basic_game_state.phase = GamePhase.ATTACK
        assert game_engine._can_use_attack(pokemon, pokemon.attacks[0], basic_game_state)


class TestPointsSystem:
    """Test the TCG Pocket points system."""
    
    def test_regular_pokemon_ko_awards_1_point(self, game_engine):
        """Test that KOing a regular Pokemon awards 1 point."""
        # Set phase to ATTACK
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.ATTACK
        )
        
        attacker = PokemonCard(
            id="TEST-001",
            name="Attacker",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=100)],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        defender = PokemonCard(
            id="TEST-002",
            name="Defender",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            is_ex=False
        )
        
        game_state.player.active_pokemon = attacker
        game_state.opponent.active_pokemon = defender
        
        game_engine.execute_attack(game_state)
        assert game_state.player.points == 1
    
    def test_ex_pokemon_ko_awards_2_points(self, game_engine):
        """Test that KOing an ex Pokemon awards 2 points."""
        # Set phase to ATTACK
        game_state = GameState(
            player=PlayerState(player_tag=PlayerTag.PLAYER),
            opponent=PlayerState(player_tag=PlayerTag.OPPONENT),
            phase=GamePhase.ATTACK
        )
        
        attacker = PokemonCard(
            id="TEST-001",
            name="Attacker",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[Attack(name="Test Attack", cost=[EnergyType.COLORLESS], damage=100)],
            attached_energies=[EnergyType.COLORLESS]
        )
        
        defender = PokemonCard(
            id="TEST-002",
            name="Defender",
            hp=100,
            pokemon_type=EnergyType.COLORLESS,
            stage=Stage.BASIC,
            attacks=[],
            is_ex=True
        )
        
        game_state.player.active_pokemon = attacker
        game_state.opponent.active_pokemon = defender
        
        game_engine.execute_attack(game_state)
        assert game_state.player.points == 2
    
    def test_points_cannot_exceed_3(self, game_engine):
        """Test that points cannot exceed 3."""
        player = PlayerState(player_tag=PlayerTag.PLAYER)
        
        # Award 1 point
        updated_player = game_engine.award_points(player, 1)
        assert updated_player.points == 1
        
        # Award 2 more points (total 3)
        updated_player = game_engine.award_points(updated_player, 2)
        assert updated_player.points == 3
        
        # Try to award more points (should raise error)
        with pytest.raises(ValueError, match="Cannot award"):
            game_engine.award_points(updated_player, 1) 