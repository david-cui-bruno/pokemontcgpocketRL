"""Unit tests for trainer effect selections."""
import pytest
from src.card_db.trainer_effects.selections import (
    player_chooses_target, opponent_chooses_target,
    all_targets, set_target_to_active, random_target
)
from src.card_db.core import EnergyType
from .test_utils import create_test_context, create_test_pokemon

class TestPlayerChoosesTarget:
    """Test player_chooses_target selection."""
    
    def test_basic_choice(self):
        """Test basic target selection."""
        ctx = create_test_context()
        pokemon1 = create_test_pokemon("Choice1", pokemon_type=EnergyType.FIRE)
        pokemon2 = create_test_pokemon("Choice2", pokemon_type=EnergyType.WATER)
        ctx.player.bench = [pokemon1, pokemon2]
        
        def mock_choose(*args):
            return pokemon1
        ctx.game_engine.choose_pokemon = mock_choose
        
        ctx = player_chooses_target(ctx)
        assert not ctx.failed
        assert ctx.targets == [pokemon1]

    def test_no_valid_targets(self):
        """Test when no valid targets exist."""
        ctx = create_test_context(with_active=False)
        ctx.player.bench = []
        
        ctx = player_chooses_target(ctx)
        assert ctx.failed
        assert not ctx.targets

class TestOpponentChoosesTarget:
    """Test opponent_chooses_target selection."""
    
    def test_basic_choice(self):
        """Test opponent selecting a target."""
        ctx = create_test_context()
        pokemon1 = create_test_pokemon("Choice1")
        pokemon2 = create_test_pokemon("Choice2")
        ctx.opponent.bench = [pokemon1, pokemon2]
        
        def mock_choose(*args):
            return pokemon2
        ctx.game_engine.choose_pokemon = mock_choose
        
        ctx = opponent_chooses_target(ctx)
        assert not ctx.failed
        assert ctx.targets == [pokemon2]

class TestAllTargets:
    """Test all_targets selection."""
    
    def test_all_pokemon(self):
        """Test selecting all Pokemon."""
        ctx = create_test_context()
        bench1 = create_test_pokemon("Bench1")
        bench2 = create_test_pokemon("Bench2")
        ctx.player.bench = [bench1, bench2]
        
        ctx = all_targets(ctx)
        assert not ctx.failed
        assert len(ctx.targets) == 3  # Active + 2 bench
        assert ctx.player.active_pokemon in ctx.targets
        assert bench1 in ctx.targets
        assert bench2 in ctx.targets

    def test_no_pokemon(self):
        """Test when no Pokemon available."""
        ctx = create_test_context(with_active=False)
        ctx.player.bench = []
        
        ctx = all_targets(ctx)
        assert ctx.failed
        assert not ctx.targets

class TestSetTargetToActive:
    """Test set_target_to_active selection."""
    
    def test_with_active(self):
        """Test setting active Pokemon as target."""
        ctx = create_test_context()
        active = ctx.player.active_pokemon
        
        ctx = set_target_to_active(ctx)
        assert not ctx.failed
        assert ctx.targets == [active]

    def test_without_active(self):
        """Test when no active Pokemon."""
        ctx = create_test_context(with_active=False)
        
        ctx = set_target_to_active(ctx)
        assert ctx.failed
        assert not ctx.targets

class TestRandomTarget:
    """Test random_target selection."""
    
    def test_basic_random(self):
        """Test random target selection."""
        ctx = create_test_context()
        pokemon1 = create_test_pokemon("Random1")
        pokemon2 = create_test_pokemon("Random2")
        ctx.player.bench = [pokemon1, pokemon2]
        
        ctx = random_target(ctx)
        assert not ctx.failed
        assert len(ctx.targets) == 1
        assert ctx.targets[0] in [ctx.player.active_pokemon, pokemon1, pokemon2]
