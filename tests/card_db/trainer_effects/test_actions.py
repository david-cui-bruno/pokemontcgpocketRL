"""Unit tests for trainer effect actions."""
import pytest
from src.card_db.trainer_effects.actions import (
    heal_pokemon, draw_cards, attach_energy_from_zone,
    move_energy_between_pokemon, switch_opponent_active,
    return_to_hand, search_deck_for_pokemon,
    shuffle_hand_into_deck_and_draw
)
from src.card_db.core import PokemonCard, EnergyType, Stage
from .test_utils import create_test_context, create_test_pokemon

class TestHealPokemon:
    """Test heal_pokemon action."""
    
    def test_heal_basic(self):
        """Test basic healing functionality."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test", damage=50)
        ctx.player.active_pokemon = pokemon  # Set as active Pokemon
        ctx.targets = [pokemon]
        
        ctx = heal_pokemon(ctx, amount=20)
        assert not ctx.failed
        # Check the updated Pokemon from the game state
        assert ctx.player.active_pokemon.damage_counters == 30

    def test_heal_no_damage(self):
        """Test healing Pokemon with no damage."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test")
        ctx.targets = [pokemon]
        
        ctx = heal_pokemon(ctx, amount=20)
        assert not ctx.failed
        assert pokemon.damage_counters == 0

    def test_heal_full_heal(self):
        """Test healing all damage."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test", damage=20)
        ctx.player.active_pokemon = pokemon  # Set as active Pokemon
        ctx.targets = [pokemon]
        
        ctx = heal_pokemon(ctx, amount=30)
        assert not ctx.failed
        # Check the updated Pokemon from the game state
        assert ctx.player.active_pokemon.damage_counters == 0

class TestDrawCards:
    """Test draw_cards action."""
    
    def test_draw_basic(self):
        """Test basic card drawing."""
        ctx = create_test_context()
        card1 = create_test_pokemon("Card1")
        card2 = create_test_pokemon("Card2")
        ctx.player.deck = [card1, card2]
        initial_hand = len(ctx.player.hand)
        
        ctx = draw_cards(ctx, count=2)
        assert not ctx.failed
        assert len(ctx.player.hand) == initial_hand + 2
        assert card1 in ctx.player.hand
        assert card2 in ctx.player.hand

    def test_draw_empty_deck(self):
        """Test drawing from empty deck."""
        ctx = create_test_context()
        ctx.player.deck = []
        
        ctx = draw_cards(ctx, count=2)
        assert ctx.failed

    def test_draw_partial_deck(self):
        """Test drawing more cards than in deck."""
        ctx = create_test_context()
        card = create_test_pokemon("Card")
        ctx.player.deck = [card]
        
        ctx = draw_cards(ctx, count=2)
        assert ctx.failed
        assert card not in ctx.player.hand  # Should not draw any cards

class TestAttachEnergy:
    """Test energy attachment actions."""
    
    def test_attach_from_zone(self):
        """Test attaching energy from energy zone."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test")
        ctx.player.active_pokemon = pokemon  # Set as active Pokemon
        ctx.targets = [pokemon]
        ctx.player.energy_zone = EnergyType.FIRE
        
        ctx = attach_energy_from_zone(ctx, energy_type=EnergyType.FIRE)
        assert not ctx.failed
        # Check the updated Pokemon from the game state
        assert EnergyType.FIRE in ctx.player.active_pokemon.attached_energies

    def test_attach_no_energy_zone(self):
        """Test attaching when no energy in zone."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Test")
        ctx.player.energy_zone = None
        ctx.targets = [pokemon]
        
        ctx = attach_energy_from_zone(ctx, energy_type=EnergyType.FIRE)
        assert ctx.failed

class TestSwitchPokemon:
    """Test Pokemon switching actions."""
    
    def test_switch_opponent_active(self):
        """Test switching opponent's active Pokemon."""
        ctx = create_test_context()
        bench_pokemon = create_test_pokemon("Bench")
        ctx.opponent.bench = [bench_pokemon]
        old_active = ctx.opponent.active_pokemon
        
        ctx.targets = [bench_pokemon]
        ctx = switch_opponent_active(ctx)  # Remove the double call
        
        assert not ctx.failed
        assert ctx.opponent.active_pokemon == bench_pokemon
        assert old_active in ctx.opponent.bench 