"""Unit tests for trainer effect composites."""
import pytest
from src.card_db.trainer_effects.composites import (
    heal_20_damage, draw_2_cards, heal_50_grass_pokemon,
    switch_damaged_opponent, switch_opponent_chooses,
    damage_bonus_10
)
from src.card_db.core import EnergyType
from .test_utils import create_test_context, create_test_pokemon

class TestHeal20Damage:
    """Test heal_20_damage composite effect."""
    
    def test_basic_healing(self):
        """Test basic healing workflow."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test", damage=30)
        ctx.player.active_pokemon = pokemon
        
        effect_chain = heal_20_damage()
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        # Check the updated Pokemon from the game state
        assert ctx.player.active_pokemon.damage_counters == 10

    def test_no_damage(self):
        """Test healing with no damage."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test")
        ctx.player.active_pokemon = pokemon
        
        effect_chain = heal_20_damage()
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert pokemon.damage_counters == 0

class TestDraw2Cards:
    """Test draw_2_cards composite effect."""
    
    def test_basic_draw(self):
        """Test drawing 2 cards."""
        ctx = create_test_context()
        card1 = create_test_pokemon("Card1")
        card2 = create_test_pokemon("Card2")
        ctx.player.deck = [card1, card2]
        initial_hand = len(ctx.player.hand)
        
        effect_chain = draw_2_cards()
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert len(ctx.player.hand) == initial_hand + 2
        assert card1 in ctx.player.hand
        assert card2 in ctx.player.hand

class TestHeal50GrassPokemon:
    """Test heal_50_grass_pokemon composite effect."""
    
    def test_heal_grass(self):
        """Test healing Grass Pokemon."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Grass", pokemon_type=EnergyType.GRASS, damage=60)
        ctx.player.active_pokemon = pokemon
        ctx.targets = [pokemon]  # Need to set the target explicitly
        
        effect_chain = heal_50_grass_pokemon()
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert not ctx.failed
        assert ctx.player.active_pokemon.damage_counters == 10

    def test_non_grass_fail(self):
        """Test failing on non-Grass Pokemon."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Fire", pokemon_type=EnergyType.FIRE, damage=60)
        ctx.player.active_pokemon = pokemon
        
        effect_chain = heal_50_grass_pokemon()
        for effect_fn in effect_chain:
            ctx = effect_fn(ctx)
            if ctx.failed:
                break
        
        assert ctx.failed
        assert pokemon.damage_counters == 60  # Unchanged
