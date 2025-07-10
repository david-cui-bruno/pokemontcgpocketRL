import pytest
from src.card_db.loader import load_card_db
from src.card_db.storage import CardStorage
from src.card_db.core import PokemonCard, ItemCard, SupporterCard, ToolCard

def test_card_db_loads_and_has_pokemon_and_trainers():
    db = load_card_db()
    all_cards = list(db._cards.values())
    assert len(all_cards) > 0, "Card database should not be empty"
    pokemon = [c for c in all_cards if isinstance(c, PokemonCard)]
    trainers = [c for c in all_cards if isinstance(c, (ItemCard, SupporterCard, ToolCard))]
    assert len(pokemon) > 0, "Should load at least one Pokémon card"
    assert len(trainers) > 0, "Should load at least one Trainer card"

def test_card_types_are_correct():
    db = load_card_db()
    for card in db._cards.values():
        if isinstance(card, PokemonCard):
            assert hasattr(card, "hp")
            assert hasattr(card, "pokemon_type")
        elif isinstance(card, ItemCard):
            assert getattr(card, "card_type", None) == "Item"
        elif isinstance(card, SupporterCard):
            assert getattr(card, "card_type", None) == "Supporter"
        elif isinstance(card, ToolCard):
            assert getattr(card, "card_type", None) == "Tool"

def test_card_storage_roundtrip():
    db = load_card_db()
    storage = CardStorage()
    # Save and reload a Pokémon card
    pokemon = next((c for c in db._cards.values() if isinstance(c, PokemonCard)), None)
    assert pokemon is not None
    storage.store_card(pokemon.id, pokemon)  # Use store_card instead of save_card
    loaded = storage.load_card(pokemon.id)
    assert loaded is not None
    assert loaded.id == pokemon.id
    assert loaded.name == pokemon.name

def test_no_duplicate_card_ids():
    db = load_card_db()
    ids = [card.id for card in db._cards.values()]
    assert len(ids) == len(set(ids)), "Card IDs should be unique"

def test_trainer_card_types_are_valid():
    db = load_card_db()
    valid_types = {"Item", "Supporter", "Tool"}
    for card in db._cards.values():
        if hasattr(card, "card_type"):
            assert card.card_type in valid_types, f"Invalid trainer card_type: {card.card_type}"

def test_pokemon_card_has_attacks():
    db = load_card_db()
    for card in db._cards.values():
        if isinstance(card, PokemonCard):
            assert hasattr(card, "attacks")
            assert isinstance(card.attacks, list)

def test_card_db_find_and_get_methods():
    db = load_card_db()
    # Test .find
    found = db.find("Pikachu")
    if found:
        assert isinstance(found, list)
        for card in found:
            assert "Pikachu" in card.name
    # Test .get
    for card_id in list(db._cards.keys())[:5]:
        card = db.get(card_id)
        assert card is not None
        assert card.id == card_id

def test_card_db_handles_missing_card():
    db = load_card_db()
    assert db.get("nonexistent-card-id") is None
    assert db.find("nonexistent-card-name") == []
