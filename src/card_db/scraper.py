"""Simple scraper to get all TCG Pocket card data."""

from tcgdexsdk import TCGdex, Query
import json
from pathlib import Path
import time

# Initialize SDK
sdk = TCGdex()

# All TCG Pocket sets
sets = ["A1", "A1a", "A2", "A2a", "A2b", "A3", "A3a", "A3b", "PROMO-A"]

def convert_attack_to_dict(attack):
    """Convert a CardAttack object to a dictionary."""
    return {
        "name": attack.name,
        "damage": attack.damage,
        "cost": attack.cost,
        "effect": attack.effect
    }

def convert_ability_to_dict(ability):
    """Convert a CardAbility object to a dictionary."""
    return {
        "name": ability.name,
        "type": ability.type,
        "effect": ability.effect
    }

def convert_weakres_to_dict(weakres):
    """Convert a CardWeakRes object to a dictionary."""
    return {
        "type": weakres.type,
        "value": weakres.value
    }

def fetch_cards():
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Fetch all cards from each set
    for set_id in sets:
        print(f"\nFetching {set_id}...")
        
        # Get list of cards
        cards = sdk.card.listSync(Query().equal("set", set_id))
        print(f"Found {len(cards)} cards in {set_id}")
        
        cards_data = []
        for i, card in enumerate(cards, 1):
            try:
                # Get full card data with retries
                for attempt in range(3):
                    try:
                        full_card = sdk.card.getSync(card.id)
                        # Convert card data to JSON-serializable format
                        card_data = {
                            "id": full_card.id,
                            "name": full_card.name,
                            "localId": full_card.localId,
                            "image": full_card.image,
                            "hp": full_card.hp,
                            "types": full_card.types,
                            "category": full_card.category,
                            "stage": full_card.stage,
                            "attacks": [convert_attack_to_dict(a) for a in (full_card.attacks or [])],
                            "abilities": [convert_ability_to_dict(a) for a in (full_card.abilities or [])],
                            "weaknesses": [convert_weakres_to_dict(w) for w in (full_card.weaknesses or [])],
                            "resistances": [convert_weakres_to_dict(r) for r in (full_card.resistances or [])],
                            "retreat": full_card.retreat,
                            "effect": full_card.effect
                        }
                        cards_data.append(card_data)
                        print(f"  {i}/{len(cards)}: {full_card.name}")
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        time.sleep(1)
                
                # Save progress after each card
                with open(data_dir / f"{set_id}.json", "w") as f:
                    json.dump(cards_data, f, indent=2)
                    
            except Exception as e:
                print(f"Error fetching card {i}: {str(e)}")
                continue
        
        print(f"Saved {len(cards_data)} cards from {set_id}")

if __name__ == "__main__":
    fetch_cards() 