"""Unit tests for trainer effect conditions."""
import pytest
from src.card_db.trainer_effects.conditions import (
    require_bench_pokemon, require_damaged_pokemon,
    require_pokemon_type, require_energy_in_zone,
    require_specific_pokemon, require_active_pokemon,
    require_pokemon_in_discard
)
from src.card_db.core import EnergyType
from .test_utils import create_test_context, create_test_pokemon

class TestRequireBenchPokemon:
    """Test require_bench_pokemon condition."""
    
    def test_with_bench(self):
        """Test when bench has Pokemon."""
        ctx = create_test_context()
        bench_pokemon = create_test_pokemon("Bench")
        ctx.player.bench = [bench_pokemon]
        
        # Fix: Call function directly with ctx
        ctx = require_bench_pokemon(ctx)
        assert not ctx.failed

    def test_without_bench(self):
        """Test when bench is empty."""
        ctx = create_test_context()
        ctx.player.bench = []
        
        # Fix: Call function directly with ctx
        ctx = require_bench_pokemon(ctx)
        assert ctx.failed

class TestRequireDamagedPokemon:
    """Test require_damaged_pokemon condition."""
    
    def test_with_damage(self):
        """Test with damaged Pokemon."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Damaged", damage=30)
        ctx.targets = [pokemon]
        
        # Fix: Call function directly with ctx
        ctx = require_damaged_pokemon(ctx)
        assert not ctx.failed

    def test_without_damage(self):
        """Test with undamaged Pokemon."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Healthy")
        ctx.targets = [pokemon]
        
        ctx = require_damaged_pokemon(ctx)  # Remove the double call
        assert ctx.failed

class TestRequirePokemonType:
    """Test require_pokemon_type condition."""
    
    def test_matching_type(self):
        """Test with matching Pokemon type."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Fire", pokemon_type=EnergyType.FIRE)
        ctx.targets = [pokemon]
        
        # Fix: Call function directly with ctx and pokemon_type
        ctx = require_pokemon_type(ctx, pokemon_type=EnergyType.FIRE)
        assert not ctx.failed

    def test_wrong_type(self):
        """Test with wrong Pokemon type."""
        ctx = create_test_context()
        pokemon = create_test_pokemon("Water", pokemon_type=EnergyType.WATER)
        ctx.targets = [pokemon]
        
        ctx = require_pokemon_type(ctx, pokemon_type=EnergyType.FIRE)  # Fix argument order
        assert ctx.failed 