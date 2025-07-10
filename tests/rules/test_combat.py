"""Tests for combat mechanics."""

class TestCombat:
    @pytest.fixture
    def combat_ready_state(self, engine, basic_deck):
        """Create a game state ready for combat testing."""
        state = engine.create_game(basic_deck, basic_deck)
        
        # Setup active Pokemon for both players
        state = engine.play_pokemon(state, 0, to_bench=False)
        state = state.advance_phase()
        state = engine.play_pokemon(state, 0, to_bench=False)
        
        return state

    def test_weakness_damage(self, engine):
        """Test weakness damage calculation (+20)."""
        attacker = PokemonCard(
            id="ATK-1",
            name="Attacker",
            pokemon_type=EnergyType.FIRE,
            hp=100,
            attacks=[Attack(name="Test", cost=[], damage=50)]
        )
        
        defender = PokemonCard(
            id="DEF-1",
            name="Defender",
            pokemon_type=EnergyType.GRASS,
            hp=100,
            weakness=EnergyType.FIRE
        )
        
        damage = engine._calculate_damage(attacker.attacks[0], attacker, defender)
        assert damage == 70  # Base 50 + 20 weakness

    def test_status_conditions(self, engine, combat_ready_state):
        """Test status condition effects."""
        state = combat_ready_state
        
        # Apply poison
        pokemon = state.player.active_pokemon
        pokemon = replace(pokemon, status_condition=StatusCondition.POISONED)
        state = engine._update_player_state(
            state,
            replace(state.player, active_pokemon=pokemon)
        )
        
        # Process checkup
        state = engine.process_checkup(state)
        
        # Verify poison damage
        assert state.player.active_pokemon.damage_counters == 10 