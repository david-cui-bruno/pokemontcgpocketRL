"""
Unit tests for trainer effects - Levels 1-4 consolidated.
Tests individual functions, conditions, selections, and composite effects.
"""

import pytest
from unittest.mock import Mock, patch
from src.card_db.core import PokemonCard, EnergyType, Stage, ItemCard, SupporterCard
from src.card_db.trainer_effects import EffectContext
from src.card_db.trainer_effects.actions import (
    switch_opponent_active, return_to_hand, heal_pokemon, 
    attach_energy_from_zone, attach_energy_from_discard,
    move_energy_between_pokemon, draw_cards, search_deck_for_pokemon,
    shuffle_hand_into_deck_and_draw, damage_bonus_this_turn
)
from src.card_db.trainer_executor import (
    execute_trainer_card, can_play_trainer_card, play_trainer_card
)
from src.card_db.trainer_effects.conditions import (
    require_bench_pokemon, require_damaged_pokemon, require_energy_in_zone,
    require_pokemon_type, require_specific_pokemon, require_active_pokemon,
    require_pokemon_in_discard, set_targets_to_player_pokemon
)
from src.card_db.trainer_effects.selections import (
    player_chooses_target, opponent_chooses_target, random_target,
    all_targets, set_target_to_active
)
from src.card_db.trainer_effects.composites import (
    heal_20_damage, draw_2_cards, heal_50_grass_pokemon,
    switch_damaged_opponent, switch_opponent_chooses, damage_bonus_10
)
from src.rules.game_state import GameState, PlayerState
from src.rules.game_engine import CoinFlipResult

# =============================================================================
# TEST UTILITIES
# =============================================================================

class MockGameEngine:
    """Mock game engine for testing coin flips."""
    def __init__(self, coin_flips=None):
        self.coin_flips = coin_flips or [CoinFlipResult.HEADS]
        self.flip_index = 0
    
    def flip_coin(self):
        if self.flip_index < len(self.coin_flips):
            result = self.coin_flips[self.flip_index]
            self.flip_index += 1
            return result
        return CoinFlipResult.TAILS

def create_test_pokemon(name="Test", hp=60, pokemon_type=EnergyType.FIRE, damage=0):
    """Create a test Pokemon card."""
    pokemon = PokemonCard(
        id=f"test-{name.lower()}",
        name=name,
        hp=hp,
        pokemon_type=pokemon_type,
        stage=Stage.BASIC,
        attacks=[],
        retreat_cost=1,
        weakness=EnergyType.WATER,
        is_ex=False
    )
    pokemon.damage_counters = damage
    pokemon.attached_energies = []
    return pokemon

def create_test_context_with_pokemon():
    """Create a test context with active Pokemon."""
    player = PlayerState()
    opponent = PlayerState()
    game_state = GameState(player, opponent)
    
    # Add active Pokemon
    pokemon = create_test_pokemon("Active")
    player.active_pokemon = pokemon
    
    # Add some cards to hand and deck
    card1 = create_test_pokemon("Card1")
    card2 = create_test_pokemon("Card2")
    player.hand = [card1]
    player.deck = [card2]
    
    # Add energy to zone
    player.energy_zone = EnergyType.FIRE
    
    game_engine = MockGameEngine()
    return EffectContext(game_state, player, game_engine)

def create_test_context():
    """Create a test context with basic game state."""
    player = PlayerState()
    opponent = PlayerState()
    game_state = GameState(player, opponent)
    game_engine = MockGameEngine()
    return EffectContext(game_state, player, game_engine)

# =============================================================================
# LEVEL 1: ACTION FUNCTIONS
# =============================================================================

class TestActionFunctions:
    """Test individual action functions in isolation."""
    
    def test_switch_opponent_active_success(self):
        """Test successful opponent active Pokemon switch."""
        ctx = create_test_context()
        benched = create_test_pokemon("Bench")
        active = create_test_pokemon("Active")
        
        ctx.opponent.bench = [benched]
        ctx.opponent.active_pokemon = active
        ctx.data['selected_target'] = benched
        
        result = switch_opponent_active(ctx)
        
        assert not result.failed
        assert ctx.opponent.active_pokemon == benched
        assert active in ctx.opponent.bench
    
    def test_switch_opponent_active_failure_no_target(self):
        """Test opponent switch failure when no target selected."""
        ctx = create_test_context()
        ctx.opponent.bench = [create_test_pokemon("Bench")]
        
        result = switch_opponent_active(ctx)
        
        assert result.failed
    
    def test_return_to_hand_active_pokemon(self):
        """Test returning active Pokemon to hand."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Active")
        ctx.player.active_pokemon = pokemon
        ctx.data['selected_target'] = pokemon
        
        result = return_to_hand(ctx, "player")
        
        assert not result.failed
        assert pokemon in ctx.player.hand
        assert ctx.player.active_pokemon is None
    
    def test_heal_pokemon_success(self):
        """Test successful Pokemon healing."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Damaged", damage=30)
        ctx.data['selected_target'] = pokemon
        
        result = heal_pokemon(ctx, 20)
        
        assert not result.failed
        assert pokemon.damage_counters == 10
    
    def test_attach_energy_from_zone_success(self):
        """Test successful energy attachment from zone."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.player.energy_zone = EnergyType.FIRE
        ctx.data['selected_target'] = pokemon
        
        result = attach_energy_from_zone(ctx, EnergyType.FIRE)
        
        assert not result.failed
        assert EnergyType.FIRE in pokemon.attached_energies
        assert ctx.player.energy_zone is None
    
    def test_attach_energy_from_zone_failure_wrong_energy(self):
        """Test energy attachment failure when wrong energy in zone."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.player.energy_zone = EnergyType.WATER
        ctx.data['selected_target'] = pokemon
        
        result = attach_energy_from_zone(ctx, EnergyType.FIRE)
        
        assert result.failed
    
    def test_attach_energy_from_discard_success(self):
        """Test successful energy attachment from discard."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.data['selected_target'] = pokemon
        
        result = attach_energy_from_discard(ctx, EnergyType.FIRE)
        
        assert not result.failed
        assert EnergyType.FIRE in pokemon.attached_energies
    
    def test_move_energy_between_pokemon_success(self):
        """Test successful energy movement between Pokemon."""
        ctx = create_test_context_with_pokemon()
        source = create_test_pokemon("Source")
        target = create_test_pokemon("Target")
        source.attached_energies = [EnergyType.FIRE]
        
        ctx.data['source_pokemon'] = source
        ctx.data['selected_target'] = target
        
        result = move_energy_between_pokemon(ctx)
        
        assert not result.failed
        assert EnergyType.FIRE in target.attached_energies
        assert EnergyType.FIRE not in source.attached_energies
    
    def test_draw_cards_success(self):
        """Test successful card drawing."""
        ctx = create_test_context_with_pokemon()
        card1 = create_test_pokemon("Card1")
        card2 = create_test_pokemon("Card2")
        ctx.player.deck = [card1, card2]
        
        result = draw_cards(ctx, 2)
        
        assert not result.failed
        assert len(ctx.player.hand) == 3  # Original + 2 drawn
        assert card1 in ctx.player.hand
        assert card2 in ctx.player.hand
    
    def test_search_deck_for_pokemon_success(self):
        """Test successful Pokemon search from deck."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Searched")
        ctx.player.deck = [pokemon]
        
        result = search_deck_for_pokemon(ctx)
        
        assert not result.failed
        assert pokemon in ctx.player.hand
        assert pokemon not in ctx.player.deck
    
    def test_shuffle_hand_into_deck_and_draw_success(self):
        """Test successful hand shuffle and draw."""
        ctx = create_test_context_with_pokemon()
        hand_card = create_test_pokemon("HandCard")
        deck_card = create_test_pokemon("DeckCard")
        ctx.player.hand = [hand_card]
        ctx.player.deck = [deck_card]
        
        result = shuffle_hand_into_deck_and_draw(ctx, 1)
        
        assert not result.failed
        assert len(ctx.player.hand) == 1
        assert len(ctx.player.deck) == 1
    
    def test_shuffle_hand_into_deck_and_draw_empty_hand(self):
        """Test shuffling empty hand into deck."""
        ctx = create_test_context_with_pokemon()
        ctx.player.hand = []  # Empty hand
        card1 = create_test_pokemon("Card1")
        ctx.player.deck = [card1]
        
        result = shuffle_hand_into_deck_and_draw(ctx, 2)
        
        assert not result.failed
        # When drawing 2 cards from a deck with 1 card, should draw 1 card
        assert len(ctx.player.hand) == 1  # Drew 1 card (only 1 available)
        assert len(ctx.player.deck) == 0  # Deck is empty
    
    def test_damage_bonus_this_turn_specific_pokemon(self):
        """Test damage bonus for specific Pokemon."""
        ctx = create_test_context_with_pokemon()
        
        result = damage_bonus_this_turn(ctx, 20, ["Active"])
        
        assert not result.failed
        assert hasattr(ctx.game_state, 'damage_bonuses')
        assert ctx.game_state.damage_bonuses["Active"] == 20
    
    def test_damage_bonus_this_turn_all_pokemon(self):
        """Test damage bonus for all Pokemon."""
        ctx = create_test_context_with_pokemon()
        
        result = damage_bonus_this_turn(ctx, 30)
        
        assert not result.failed
        assert hasattr(ctx.game_state, 'damage_bonuses')
        assert ctx.game_state.damage_bonuses['all'] == 30

    @patch('src.card_db.comprehensive_trainer_registry.get_effect_for_card')
    @patch('src.card_db.comprehensive_trainer_registry.TRAINER_EFFECTS')
    def test_execute_trainer_card_success(self, mock_effects, mock_get):
        """Test successful trainer card execution."""
        ctx = create_test_context_with_pokemon()
        card = ItemCard(id="test", name="Potion", effects=[])
        
        # Set up the Pokemon with damage first
        ctx.player.active_pokemon.damage_counters = 30
        
        # Mock the registry to return a known effect
        mock_get.return_value = "Heal 20 damage from 1 of your Pokémon."
        
        # Mock the effect chain - this is the key fix
        def mock_heal_effect(ctx):
            # Set the target to the active Pokemon
            ctx.data['selected_target'] = ctx.player.active_pokemon
            # Then heal it
            ctx.player.active_pokemon.damage_counters = max(0, ctx.player.active_pokemon.damage_counters - 20)
            return ctx
        
        # Fix: Return the actual function, not a list
        mock_effects.get.return_value = [mock_heal_effect]
        
        success = execute_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert success
        assert ctx.player.active_pokemon.damage_counters == 10

# =============================================================================
# LEVEL 2: CONDITION FUNCTIONS
# =============================================================================

class TestConditionFunctions:
    """Test condition functions that check game state requirements."""
    
    def test_require_bench_pokemon_success_player(self):
        """Test bench Pokemon requirement success for player."""
        ctx = create_test_context_with_pokemon()
        bench_pokemon = create_test_pokemon("Bench")
        ctx.player.bench = [bench_pokemon]
        
        result = require_bench_pokemon(ctx, "player")
        
        assert not result.failed
    
    def test_require_bench_pokemon_failure_player(self):
        """Test bench Pokemon requirement failure for player."""
        ctx = create_test_context_with_pokemon()
        ctx.player.bench = []
        
        result = require_bench_pokemon(ctx, "player")
        
        assert result.failed
    
    def test_require_damaged_pokemon_success(self):
        """Test damaged Pokemon requirement success."""
        ctx = create_test_context_with_pokemon()
        damaged = create_test_pokemon("Damaged", damage=20)
        ctx.player.bench = [damaged]
        
        result = require_damaged_pokemon(ctx, "player")
        
        assert not result.failed
    
    def test_require_damaged_pokemon_failure(self):
        """Test damaged Pokemon requirement failure."""
        ctx = create_test_context_with_pokemon()
        healthy = create_test_pokemon("Healthy", damage=0)
        ctx.player.bench = [healthy]
        
        result = require_damaged_pokemon(ctx, "player")
        
        assert result.failed
    
    def test_require_energy_in_zone_success(self):
        """Test energy in zone requirement success."""
        ctx = create_test_context_with_pokemon()
        ctx.player.energy_zone = EnergyType.FIRE
        
        result = require_energy_in_zone(ctx, EnergyType.FIRE)
        
        assert not result.failed
    
    def test_require_energy_in_zone_failure(self):
        """Test energy in zone requirement failure."""
        ctx = create_test_context_with_pokemon()
        ctx.player.energy_zone = EnergyType.WATER
        
        result = require_energy_in_zone(ctx, EnergyType.FIRE)
        
        assert result.failed
    
    def test_require_pokemon_type_success(self):
        """Test Pokemon type requirement success."""
        ctx = create_test_context_with_pokemon()
        fire_pokemon = create_test_pokemon("FireMon", pokemon_type=EnergyType.FIRE)
        ctx.player.active_pokemon = fire_pokemon
        
        result = require_pokemon_type(ctx, EnergyType.FIRE, "player")
        
        assert not result.failed
    
    def test_require_pokemon_type_failure(self):
        """Test Pokemon type requirement failure."""
        ctx = create_test_context_with_pokemon()
        water_pokemon = create_test_pokemon("WaterMon", pokemon_type=EnergyType.WATER)
        ctx.player.active_pokemon = water_pokemon
        
        result = require_pokemon_type(ctx, EnergyType.FIRE, "player")
        
        assert result.failed
    
    def test_require_specific_pokemon_success(self):
        """Test specific Pokemon requirement success."""
        ctx = create_test_context_with_pokemon()
        pikachu = create_test_pokemon("Pikachu")
        ctx.player.active_pokemon = pikachu
        
        result = require_specific_pokemon(ctx, ["Pikachu"], "player")
        
        assert not result.failed
    
    def test_require_specific_pokemon_failure(self):
        """Test specific Pokemon requirement failure."""
        ctx = create_test_context_with_pokemon()
        charmander = create_test_pokemon("Charmander")
        ctx.player.active_pokemon = charmander
        
        result = require_specific_pokemon(ctx, ["Pikachu"], "player")
        
        assert result.failed
    
    def test_require_active_pokemon_success_player(self):
        """Test active Pokemon requirement success for player."""
        ctx = create_test_context_with_pokemon()
        
        result = require_active_pokemon(ctx, "player")
        
        assert not result.failed
    
    def test_require_active_pokemon_failure_player(self):
        """Test active Pokemon requirement failure for player."""
        ctx = create_test_context()
        ctx.player.active_pokemon = None
        
        result = require_active_pokemon(ctx, "player")
        
        assert result.failed
    
    def test_require_pokemon_in_discard_success(self):
        """Test Pokemon in discard requirement success."""
        ctx = create_test_context_with_pokemon()
        discarded = create_test_pokemon("Discarded")
        ctx.player.discard_pile = [discarded]
        
        result = require_pokemon_in_discard(ctx, None)
        
        assert not result.failed
    
    def test_require_pokemon_in_discard_failure(self):
        """Test Pokemon in discard requirement failure."""
        ctx = create_test_context_with_pokemon()
        ctx.player.discard_pile = []
        
        result = require_pokemon_in_discard(ctx, None)
        
        assert result.failed
    
    def test_set_targets_to_player_pokemon_success(self):
        """Test setting targets to player Pokemon success."""
        ctx = create_test_context_with_pokemon()
        bench_pokemon = create_test_pokemon("Bench")
        ctx.player.bench = [bench_pokemon]
        
        result = set_targets_to_player_pokemon(ctx)
        
        assert not result.failed
        assert len(ctx.targets) == 2  # Active + bench
    
    def test_set_targets_to_player_pokemon_failure(self):
        """Test setting targets to player Pokemon failure."""
        ctx = create_test_context()
        ctx.player.active_pokemon = None
        ctx.player.bench = []
        
        result = set_targets_to_player_pokemon(ctx)
        
        assert result.failed

# =============================================================================
# LEVEL 3: SELECTION FUNCTIONS
# =============================================================================

class TestSelectionFunctions:
    """Test selection functions that choose targets."""
    
    def test_player_chooses_target_success_with_targets(self):
        """Test player target selection with available targets."""
        ctx = create_test_context_with_pokemon()
        pokemon1 = create_test_pokemon("Target1")
        pokemon2 = create_test_pokemon("Target2")
        ctx.targets = [pokemon1, pokemon2]
        
        result = player_chooses_target(ctx)
        
        assert not result.failed
        assert ctx.data['selected_target'] in [pokemon1, pokemon2]
    
    def test_player_chooses_target_failure_no_targets(self):
        """Test player target selection failure with no targets."""
        ctx = create_test_context_with_pokemon()
        ctx.targets = []
        
        result = player_chooses_target(ctx)
        
        assert result.failed
    
    def test_opponent_chooses_target_success_with_targets(self):
        """Test opponent target selection with available targets."""
        ctx = create_test_context_with_pokemon()
        pokemon1 = create_test_pokemon("Target1")
        pokemon2 = create_test_pokemon("Target2")
        ctx.targets = [pokemon1, pokemon2]
        
        result = opponent_chooses_target(ctx)
        
        assert not result.failed
        assert ctx.data['selected_target'] in [pokemon1, pokemon2]
    
    def test_random_target_success_with_targets(self):
        """Test random target selection with available targets."""
        ctx = create_test_context_with_pokemon()
        pokemon1 = create_test_pokemon("Target1")
        pokemon2 = create_test_pokemon("Target2")
        ctx.targets = [pokemon1, pokemon2]
        
        result = random_target(ctx)
        
        assert not result.failed
        assert ctx.data['selected_target'] in [pokemon1, pokemon2]
    
    def test_all_targets_success_with_targets(self):
        """Test all targets selection with available targets."""
        ctx = create_test_context_with_pokemon()
        pokemon1 = create_test_pokemon("Target1")
        pokemon2 = create_test_pokemon("Target2")
        ctx.targets = [pokemon1, pokemon2]
        
        result = all_targets(ctx)
        
        assert not result.failed
        assert ctx.data['selected_targets'] == [pokemon1, pokemon2]
    
    def test_set_target_to_active_success_player(self):
        """Test setting target to active Pokemon for player."""
        ctx = create_test_context_with_pokemon()
        
        result = set_target_to_active(ctx, "player")
        
        assert not result.failed
        assert ctx.data['selected_target'] == ctx.player.active_pokemon
    
    def test_set_target_to_active_failure_player(self):
        """Test setting target to active Pokemon failure for player."""
        ctx = create_test_context()
        ctx.player.active_pokemon = None
        
        result = set_target_to_active(ctx, "player")
        
        assert result.failed

# =============================================================================
# LEVEL 4: COMPOSITE EFFECTS
# =============================================================================

class TestCompositeEffects:
    """Test pre-built effect chains."""
    
    def test_heal_20_damage_chain_success(self):
        """Test the complete heal 20 damage effect chain."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Damaged", damage=30)
        ctx.player.active_pokemon = pokemon
        
        effect_chain = heal_20_damage()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert pokemon.damage_counters == 10
    
    def test_heal_20_damage_chain_no_pokemon(self):
        """Test heal 20 damage chain with no Pokemon in play."""
        ctx = create_test_context()
        ctx.player.active_pokemon = None
        ctx.player.bench = []
        
        effect_chain = heal_20_damage()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        # Should fail gracefully when no Pokemon to heal
        assert ctx.failed
    
    def test_draw_2_cards_chain_success(self):
        """Test the complete draw 2 cards effect chain."""
        ctx = create_test_context_with_pokemon()
        card1 = create_test_pokemon("Card1")
        card2 = create_test_pokemon("Card2")
        ctx.player.deck = [card1, card2]
        
        effect_chain = draw_2_cards()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert len(ctx.player.hand) == 3  # Original + 2 drawn
        assert card1 in ctx.player.hand
        assert card2 in ctx.player.hand
    
    def test_heal_50_grass_pokemon_chain_success(self):
        """Test the complete heal 50 grass Pokemon effect chain."""
        ctx = create_test_context_with_pokemon()
        grass_pokemon = create_test_pokemon("GrassMon", pokemon_type=EnergyType.GRASS, damage=60)
        fire_pokemon = create_test_pokemon("FireMon", pokemon_type=EnergyType.FIRE, damage=30)
        ctx.player.active_pokemon = grass_pokemon
        ctx.player.bench = [fire_pokemon]
        
        effect_chain = heal_50_grass_pokemon()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert grass_pokemon.damage_counters == 10  # 60 - 50
        assert fire_pokemon.damage_counters == 30  # Should not be healed
    
    def test_switch_damaged_opponent_chain_success(self):
        """Test the complete switch damaged opponent effect chain."""
        ctx = create_test_context_with_pokemon()
        damaged = create_test_pokemon("Damaged", damage=20)
        healthy = create_test_pokemon("Healthy", damage=0)
        active = create_test_pokemon("Active", damage=0)
        ctx.opponent.bench = [damaged, healthy]
        ctx.opponent.active_pokemon = active
        
        effect_chain = switch_damaged_opponent()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert ctx.opponent.active_pokemon == damaged
        assert active in ctx.opponent.bench
    
    def test_damage_bonus_10_chain_success(self):
        """Test the complete damage bonus 10 effect chain."""
        ctx = create_test_context_with_pokemon()
        
        effect_chain = damage_bonus_10()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert hasattr(ctx.game_state, 'damage_bonuses')
        assert ctx.game_state.damage_bonuses['all'] == 10

def test_can_play_trainer_card_with_effect_validation():
    """Test trainer card play validation with effect checking."""
    ctx = create_test_context_with_pokemon()
    card = ItemCard(id="test", name="ValidCard", effects=[])
    
    # Mock the registry functions INSIDE the trainer_executor module
    with patch('src.card_db.trainer_executor.get_effect_for_card', return_value="Some effect"):
        with patch('src.card_db.trainer_executor.TRAINER_EFFECTS') as mock_effects:
            # Mock a passing condition
            def passing_condition(ctx):
                ctx.failed = False
                return ctx
            
            mock_effects.get.return_value = [passing_condition]
            
            can_play = can_play_trainer_card(card, ctx.game_state, ctx.player, None)
            assert can_play

def test_supporter_card_restriction_workflow():
    """Test the complete supporter card restriction workflow."""
    ctx = create_test_context_with_pokemon()
    supporter1 = SupporterCard(id="test1", name="Supporter1", effects=[])
    supporter2 = SupporterCard(id="test2", name="Supporter2", effects=[])
    ctx.player.hand = [supporter1, supporter2]
    
    # Mock the registry functions INSIDE the trainer_executor module
    with patch('src.card_db.trainer_executor.get_effect_for_card', return_value="Some effect"):
        with patch('src.card_db.trainer_executor.TRAINER_EFFECTS') as mock_effects:
            # Mock a passing effect
            def passing_effect(ctx):
                ctx.failed = False
                return ctx
            
            mock_effects.get.return_value = [passing_effect]
            
            # Play first supporter
            success1 = play_trainer_card(supporter1, ctx.game_state, ctx.player, None)
            assert success1
            
            # Try to play second supporter (should fail due to supporter restriction)
            success2 = play_trainer_card(supporter2, ctx.game_state, ctx.player, None)
            assert not success2
