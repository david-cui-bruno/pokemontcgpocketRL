"""Tests for core card data structures."""

import pytest
from src.card_db.core import (
    Attack,
    Ability,
    Card,
    PokemonCard,
    ItemCard,
    SupporterCard,
    Effect,
    EnergyType,
    Stage,
    TargetType,
)


class TestEffect:
    """Test Effect dataclass."""
    
    def test_basic_effect_creation(self) -> None:
        """Test creating a basic effect."""
        effect = Effect(effect_type="damage", amount=30)
        assert effect.effect_type == "damage"
        assert effect.amount == 30
        assert effect.conditions == []
        assert effect.parameters == {}
    
    def test_effect_with_target(self) -> None:
        """Test effect with target specification."""
        effect = Effect(
            effect_type="heal",
            amount=20,
            target=TargetType.SELF
        )
        assert effect.target == TargetType.SELF


class TestAttack:
    """Test Attack dataclass."""
    
    def test_basic_attack_creation(self) -> None:
        """Test creating a basic attack."""
        attack = Attack(
            name="Quick Attack",
            cost=[EnergyType.COLORLESS],
            damage=10
        )
        assert attack.name == "Quick Attack"
        assert attack.cost == [EnergyType.COLORLESS]
        assert attack.damage == 10
        assert attack.effects == []
    
    def test_attack_with_effects(self) -> None:
        """Test attack with additional effects."""
        effect = Effect(effect_type="flip_coin")
        attack = Attack(
            name="Thunder",
            cost=[EnergyType.ELECTRIC, EnergyType.ELECTRIC],
            damage=60,
            effects=[effect]
        )
        assert len(attack.effects) == 1
        assert attack.effects[0].effect_type == "flip_coin"


class TestPokemonCard:
    """Test PokemonCard dataclass."""
    
    def test_basic_pokemon_creation(self) -> None:
        """Test creating a basic Pokemon card."""
        pikachu = PokemonCard(
            id="pikachu_001",
            name="Pikachu",
            hp=60,
            pokemon_type=EnergyType.ELECTRIC,
            stage=Stage.BASIC,
            retreat_cost=1
        )
        assert pikachu.name == "Pikachu"
        assert pikachu.hp == 60
        assert pikachu.pokemon_type == EnergyType.ELECTRIC
        assert pikachu.stage == Stage.BASIC
        assert pikachu.retreat_cost == 1
        assert not pikachu.is_ex
        assert pikachu.attacks == []
    
    def test_ex_pokemon_creation(self) -> None:
        """Test creating an ex Pokemon card."""
        pikachu_ex = PokemonCard(
            id="pikachu_ex_001",
            name="Pikachu ex",
            hp=120,
            pokemon_type=EnergyType.ELECTRIC,
            stage=Stage.BASIC,
            retreat_cost=1,
            is_ex=True
        )
        assert pikachu_ex.is_ex
        assert pikachu_ex.hp == 120


class TestItemCard:
    """Test ItemCard dataclass."""
    
    def test_item_card_creation(self) -> None:
        """Test creating an item card."""
        potion = ItemCard(
            id="potion_001",
            name="Potion",
            effects=[Effect("heal", amount=20, target=TargetType.ANY_POKEMON)]
        )
        assert potion.name == "Potion"
        assert len(potion.effects) == 1
        assert potion.effects[0].effect_type == "heal"


class TestSupporterCard:
    """Test SupporterCard dataclass."""
    
    def test_supporter_card_creation(self) -> None:
        """Test creating a supporter card."""
        oak = SupporterCard(
            id="oak_001",
            name="Professor Oak",
            effects=[Effect("draw_cards", amount=2)]
        )
        assert oak.name == "Professor Oak"
        assert len(oak.effects) == 1
        assert oak.effects[0].effect_type == "draw_cards" 