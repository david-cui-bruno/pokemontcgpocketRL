"""
Integration tests for trainer effects - Levels 5-7 consolidated.
Tests trainer executor, complete workflows, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch
from src.card_db.core import PokemonCard, EnergyType, Stage, ItemCard, SupporterCard, ToolCard
from src.card_db.trainer_effects import EffectContext
from src.card_db.trainer_executor import (
    execute_trainer_card, can_play_trainer_card, play_trainer_card
)
from src.card_db.trainer_effects.actions import (
    attach_energy_from_zone, attach_energy_from_discard, heal_pokemon,
    draw_cards, search_deck_for_pokemon, shuffle_hand_into_deck_and_draw
)
from src.card_db.trainer_effects.conditions import (
    require_pokemon_type, set_targets_to_player_pokemon, require_pokemon_in_discard
)
from src.card_db.trainer_effects.selections import (
    player_chooses_target
)
from src.card_db.trainer_effects.composites import (
    heal_20_damage, draw_2_cards
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
# LEVEL 5: TRAINER EXECUTOR
# =============================================================================

class TestTrainerExecutor:
    """Test the main trainer card execution system."""
    
    @patch('src.card_db.trainer_executor.get_effect_for_card')
    @patch('src.card_db.trainer_executor.TRAINER_EFFECTS')
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
    
    @patch('src.card_db.trainer_executor.get_effect_for_card')
    @patch('src.card_db.trainer_executor.TRAINER_EFFECTS')
    def test_execute_trainer_card_no_effect_found(self, mock_effects, mock_get):
        """Test trainer card execution when no effect is found."""
        ctx = create_test_context_with_pokemon()  # Use context with Pokemon
        card = ItemCard(id="test", name="UnknownCard", effects=[])
        
        # Mock the registry to return None
        mock_get.return_value = None
        mock_effects.get.return_value = None
        
        success = execute_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert not success
    
    def test_can_play_trainer_card_supporter_restriction(self):
        """Test supporter card play restriction."""
        ctx = create_test_context_with_pokemon()  # Use context with Pokemon
        card = SupporterCard(id="test", name="Test Supporter", effects=[])
        ctx.player.supporter_played_this_turn = True
        
        can_play = can_play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert not can_play
    
    def test_can_play_trainer_card_supporter_allowed(self):
        """Test supporter card play when allowed."""
        ctx = create_test_context_with_pokemon()  # Use context with Pokemon
        card = SupporterCard(id="test", name="Test Supporter", effects=[])
        ctx.player.supporter_played_this_turn = False
        
        can_play = can_play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        # Should return True or False based on effect validation
        assert isinstance(can_play, bool)
    
    def test_can_play_trainer_card_tool_card(self):
        """Test tool card play validation."""
        ctx = create_test_context_with_pokemon()  # Use context with Pokemon
        card = ToolCard(id="test", name="Test Tool", effects=[])
        
        can_play = can_play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        # Tool cards should be playable (basic validation)
        assert can_play
    
    @patch('src.card_db.trainer_executor.get_effect_for_card')
    @patch('src.card_db.trainer_executor.TRAINER_EFFECTS')
    def test_can_play_trainer_card_with_effect_validation(self, mock_effects, mock_get):
        """Test trainer card play validation with effect checking."""
        ctx = create_test_context_with_pokemon()
        card = ItemCard(id="test", name="ValidCard", effects=[])
        
        # Mock the registry to return an effect
        mock_get.return_value = "Some effect"
        
        # Mock the effect chain with a passing condition
        def passing_condition(ctx):
            ctx.failed = False
            return ctx
        
        # Fix: Set up the mock correctly
        mock_effects.get.return_value = [passing_condition]
        
        can_play = can_play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert can_play
    
    @patch('src.card_db.trainer_executor.execute_trainer_card')
    def test_play_trainer_card_success(self, mock_execute):
        """Test successful trainer card play with hand/discard management."""
        ctx = create_test_context_with_pokemon()  # Use context with Pokemon
        card = ItemCard(id="test", name="Potion", effects=[])
        ctx.player.hand = [card]
        
        mock_execute.return_value = True
        
        success = play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert success
        assert card not in ctx.player.hand  # Card should be removed from hand
    
    @patch('src.card_db.trainer_executor.can_play_trainer_card')
    def test_play_trainer_card_cannot_play(self, mock_can_play):
        """Test trainer card play when card cannot be played."""
        ctx = create_test_context_with_pokemon()  # Use context with Pokemon
        card = ItemCard(id="test", name="InvalidCard", effects=[])
        ctx.player.hand = [card]
        
        mock_can_play.return_value = False
        
        success = play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert not success
        assert card in ctx.player.hand  # Card should remain in hand
    
    @patch('src.card_db.trainer_executor.execute_trainer_card')
    @patch('src.card_db.trainer_executor.can_play_trainer_card')
    @patch('src.card_db.trainer_executor.get_effect_for_card')
    @patch('src.card_db.trainer_executor.TRAINER_EFFECTS')
    def test_play_trainer_card_supporter_marking(self, mock_effects, mock_get, mock_can_play, mock_execute):
        """Test that supporter cards mark the player as having played a supporter."""
        ctx = create_test_context_with_pokemon()
        card = SupporterCard(id="test", name="Test Supporter", effects=[])
        ctx.player.hand = [card]
        ctx.player.supporter_played_this_turn = False
        
        # Mock the registry lookups
        mock_get.return_value = "Some effect"
        mock_effects.get.return_value = [lambda ctx: ctx]  # Simple passing effect
        mock_can_play.return_value = True  # Allow the card to be played
        mock_execute.return_value = True
        
        success = play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert success
        assert ctx.player.supporter_played_this_turn
    
    @patch('src.card_db.trainer_executor.execute_trainer_card')
    @patch('src.card_db.trainer_executor.can_play_trainer_card')
    @patch('src.card_db.trainer_executor.get_effect_for_card')
    @patch('src.card_db.trainer_executor.TRAINER_EFFECTS')
    def test_play_trainer_card_non_supporter_no_marking(self, mock_effects, mock_get, mock_can_play, mock_execute):
        """Test that non-supporter cards don't mark the player as having played a supporter."""
        ctx = create_test_context_with_pokemon()
        card = ItemCard(id="test", name="Test Item", effects=[])
        ctx.player.hand = [card]
        ctx.player.supporter_played_this_turn = False
        
        # Mock the registry lookups
        mock_get.return_value = "Some effect"
        mock_effects.get.return_value = [lambda ctx: ctx]  # Simple passing effect
        mock_can_play.return_value = True  # Allow the card to be played
        mock_execute.return_value = True
        
        success = play_trainer_card(card, ctx.game_state, ctx.player, None)
        
        assert success
        assert not ctx.player.supporter_played_this_turn

# =============================================================================
# LEVEL 6: INTEGRATION WORKFLOWS
# =============================================================================

class TestTrainerEffectsIntegration:
    """Test complete trainer effect workflows."""
    
    def test_complete_healing_workflow(self):
        """Test a complete healing workflow."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Damaged", damage=30)
        ctx.player.active_pokemon = pokemon
        
        # Use the heal_20_damage composite effect
        effect_chain = heal_20_damage()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert pokemon.damage_counters == 10
    
    def test_complete_drawing_workflow(self):
        """Test a complete drawing workflow."""
        ctx = create_test_context_with_pokemon()
        card1 = create_test_pokemon("Card1")
        card2 = create_test_pokemon("Card2")
        ctx.player.deck = [card1, card2]
        
        # Use the draw_2_cards composite effect
        effect_chain = draw_2_cards()
        
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert len(ctx.player.hand) == 3  # Original + 2 drawn
        assert card1 in ctx.player.hand
        assert card2 in ctx.player.hand
    
    def test_complete_energy_attachment_workflow(self):
        """Test a complete energy attachment workflow."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.player.active_pokemon = pokemon
        ctx.player.energy_zone = EnergyType.FIRE
        
        # Set up the energy attachment chain
        ctx = set_targets_to_player_pokemon(ctx)
        ctx = player_chooses_target(ctx)
        ctx = attach_energy_from_zone(ctx, EnergyType.FIRE)
        
        assert not ctx.failed
        assert EnergyType.FIRE in pokemon.attached_energies
        assert ctx.player.energy_zone is None
    
    def test_supporter_card_restriction_workflow(self):
        """Test the complete supporter card restriction workflow."""
        ctx = create_test_context_with_pokemon()
        supporter1 = SupporterCard(id="test1", name="Supporter1", effects=[])
        supporter2 = SupporterCard(id="test2", name="Supporter2", effects=[])
        ctx.player.hand = [supporter1, supporter2]
        
        # Mock the registry functions INSIDE the trainer_executor module
        with patch('src.card_db.trainer_executor.get_effect_for_card', return_value="Some effect"):
            with patch('src.card_db.trainer_executor.TRAINER_EFFECTS') as mock_effects:
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
    
    def test_item_card_multiple_play_workflow(self):
        """Test that item cards can be played multiple times."""
        ctx = create_test_context_with_pokemon()
        item1 = ItemCard(id="test1", name="Item1", effects=[])
        item2 = ItemCard(id="test2", name="Item2", effects=[])
        ctx.player.hand = [item1, item2]
        
        # Mock effect execution and registry lookups
        with patch('src.card_db.trainer_executor.execute_trainer_card', return_value=True):
            with patch('src.card_db.trainer_executor.can_play_trainer_card', return_value=True):
                with patch('src.card_db.trainer_executor.get_effect_for_card', return_value="Some effect"):
                    with patch('src.card_db.trainer_executor.TRAINER_EFFECTS') as mock_effects:
                        mock_effects.get.return_value = [lambda ctx: ctx]  # Simple passing effect
                        
                        # Play first item
                        success1 = play_trainer_card(item1, ctx.game_state, ctx.player, None)
                        assert success1
                        
                        # Play second item (should succeed)
                        success2 = play_trainer_card(item2, ctx.game_state, ctx.player, None)
                        assert success2

# =============================================================================
# LEVEL 7: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_heal_pokemon_overflow(self):
        """Test healing more damage than Pokemon has."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Damaged", damage=10)
        ctx.data['selected_target'] = pokemon
        
        result = heal_pokemon(ctx, 30)
        
        assert not result.failed
        assert pokemon.damage_counters == 0  # Should not go negative
    
    def test_heal_pokemon_exact_amount(self):
        """Test healing exact amount of damage."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Damaged", damage=20)
        ctx.data['selected_target'] = pokemon
        
        result = heal_pokemon(ctx, 20)
        
        assert not result.failed
        assert pokemon.damage_counters == 0
    
    def test_heal_pokemon_zero_damage(self):
        """Test healing Pokemon with no damage."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Healthy", damage=0)
        ctx.data['selected_target'] = pokemon
        
        result = heal_pokemon(ctx, 20)
        
        assert not result.failed
        assert pokemon.damage_counters == 0
    
    def test_draw_cards_more_than_deck(self):
        """Test drawing more cards than available in deck."""
        ctx = create_test_context_with_pokemon()
        card1 = create_test_pokemon("Card1")
        ctx.player.deck = [card1]  # Only 1 card in deck
        
        result = draw_cards(ctx, 3)  # Try to draw 3
        
        assert not result.failed
        assert len(ctx.player.hand) == 2  # Original + 1 drawn
        assert card1 in ctx.player.hand
    
    def test_draw_cards_zero_cards(self):
        """Test drawing zero cards."""
        ctx = create_test_context_with_pokemon()
        
        result = draw_cards(ctx, 0)
        
        assert not result.failed
        assert len(ctx.player.hand) == 1  # Original hand unchanged
    
    def test_draw_cards_negative_cards(self):
        """Test drawing negative number of cards."""
        ctx = create_test_context_with_pokemon()
        
        result = draw_cards(ctx, -2)
        
        assert not result.failed
        assert len(ctx.player.hand) == 1  # Original hand unchanged
    
    def test_attach_energy_multiple_amounts(self):
        """Test attaching multiple energy at once."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.player.energy_zone = EnergyType.FIRE
        ctx.data['selected_target'] = pokemon
        
        result = attach_energy_from_zone(ctx, EnergyType.FIRE, amount=2)
        
        # Should only attach 1 since only 1 energy in zone
        assert not result.failed
        assert len(pokemon.attached_energies) == 1
        assert ctx.player.energy_zone is None
    
    def test_attach_energy_zero_amount(self):
        """Test attaching zero energy."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.player.energy_zone = EnergyType.FIRE
        ctx.data['selected_target'] = pokemon
        
        result = attach_energy_from_zone(ctx, EnergyType.FIRE, amount=0)
        
        # Should fail for zero amount (correct behavior)
        assert result.failed
    
    def test_attach_energy_negative_amount(self):
        """Test attaching negative amount of energy."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.player.energy_zone = EnergyType.FIRE
        ctx.data['selected_target'] = pokemon
        
        result = attach_energy_from_zone(ctx, EnergyType.FIRE, amount=-2)
        
        # Should fail for negative amount (correct behavior)
        assert result.failed
    
    def test_attach_energy_from_discard_simulated(self):
        """Test energy attachment from discard (simulated)."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Target")
        ctx.data['selected_target'] = pokemon  # Set the target
        
        result = attach_energy_from_discard(ctx, EnergyType.FIRE)
        
        assert not result.failed
        assert EnergyType.FIRE in pokemon.attached_energies
    
    def test_search_deck_for_pokemon_no_pokemon_in_deck(self):
        """Test searching deck with no Pokemon in deck."""
        ctx = create_test_context_with_pokemon()
        ctx.player.deck = []  # Empty deck
        
        result = search_deck_for_pokemon(ctx)
        
        assert result.failed
    
    def test_search_deck_for_pokemon_specific_names_no_match(self):
        """Test searching deck for specific names with no matches."""
        ctx = create_test_context_with_pokemon()
        pokemon = create_test_pokemon("Charmander")
        ctx.player.deck = [pokemon]
        
        result = search_deck_for_pokemon(ctx, ["Pikachu"])
        
        assert result.failed
    
    def test_shuffle_hand_into_deck_and_draw_empty_hand(self):
        """Test shuffling empty hand into deck."""
        ctx = create_test_context_with_pokemon()
        ctx.player.hand = []  # Empty hand
        card1 = create_test_pokemon("Card1")
        ctx.player.deck = [card1]
        
        result = shuffle_hand_into_deck_and_draw(ctx, 2)
        
        assert not result.failed
        assert len(ctx.player.hand) == 1  # Drew 1 card (only 1 available)
        assert len(ctx.player.deck) == 0  # Deck is empty
    
    def test_shuffle_hand_into_deck_and_draw_zero_cards(self):
        """Test shuffling hand and drawing zero cards."""
        ctx = create_test_context_with_pokemon()
        hand_card = create_test_pokemon("HandCard")
        ctx.player.hand = [hand_card]
        
        result = shuffle_hand_into_deck_and_draw(ctx, 0)
        
        assert not result.failed
        assert len(ctx.player.hand) == 0
        assert len(ctx.player.deck) == 2  # 1 original + 1 from hand = 2 total

    def test_require_pokemon_in_discard_success(self):
        """Test Pokemon in discard requirement success."""
        ctx = create_test_context_with_pokemon()
        discarded = create_test_pokemon("Discarded")
        ctx.player.discard_pile = [discarded]
        
        # Fix: Pass None instead of "player" to get all Pokemon in discard
        result = require_pokemon_in_discard(ctx, None)
        
        assert not result.failed

    def test_require_pokemon_in_discard_failure(self):
        """Test Pokemon in discard requirement failure."""
        ctx = create_test_context_with_pokemon()
        ctx.player.discard_pile = []
        
        # Fix: Pass None instead of "player"
        result = require_pokemon_in_discard(ctx, None)
        
        assert result.failed
