"""Sample card data for Pokemon TCG Pocket prototype.

This module provides sample card data following TCG Pocket's rules:
- 20-card decks
- Energy Zone system (no energy cards)
- Simplified effects for mobile play
- Points system (3 points to win, ex Pokemon worth 2 points)
"""

from typing import Dict, List

SAMPLE_CARDS = {
    "pikachu_001": {
        "id": "pikachu_001",
        "name": "Pikachu",
        "category": "Pokemon",
        "hp": 70,
        "type": "electric",
        "stage": "basic",
        "attacks": [
            {
                "name": "Quick Attack",
                "cost": ["colorless"],  # Energy Zone provides one large energy per turn
                "damage": 20,
                "effect": "Flip a coin. If heads, this attack does 20 more damage."
            }
        ],
        "retreat_cost": 1,
        "weakness": "fighting",
        "is_ex": False,  # Worth 1 point when KO'd
        "set": "starter_deck"
    },
    "charizard_ex_001": {
        "id": "charizard_ex_001",
        "name": "Charizard ex",
        "category": "Pokemon",
        "hp": 220,
        "type": "fire",
        "stage": "basic",
        "attacks": [
            {
                "name": "Flame Burst",
                "cost": ["fire", "fire"],  # Requires 2 turns of Energy Zone attachment
                "damage": 120,
                "effect": "Discard an Energy from this Pokemon."
            }
        ],
        "retreat_cost": 2,
        "weakness": "water",
        "is_ex": True,  # Worth 2 points when KO'd
        "set": "starter_deck"
    },
    "potion_001": {
        "id": "potion_001",
        "name": "Potion",
        "category": "Trainer",
        "subtype": "Item",
        "effect": ["Heal 30 damage from one of your Pokemon."],
        "set": "starter_deck"
    },
    "professor_oak_001": {
        "id": "professor_oak_001",
        "name": "Professor Oak",
        "category": "Trainer",
        "subtype": "Supporter",  # Only one Supporter per turn
        "effect": ["Draw 2 cards."],
        "set": "starter_deck"
    },
    "mewtwo_ex_001": {
        "id": "mewtwo_ex_001",
        "name": "Mewtwo ex",
        "category": "Pokemon",
        "hp": 200,
        "type": "psychic",
        "stage": "basic",
        "attacks": [
            {
                "name": "Psystrike",
                "cost": ["psychic", "psychic"],
                "damage": 130,
                "effect": "This attack's damage isn't affected by any effects on your opponent's Active Pokemon."
            }
        ],
        "retreat_cost": 2,
        "weakness": "darkness",
        "is_ex": True,  # Worth 2 points when KO'd
        "set": "starter_deck"
    },
    "switch_001": {
        "id": "switch_001",
        "name": "Switch",
        "category": "Trainer",
        "subtype": "Item",
        "effect": ["Switch your Active Pokemon with one of your Benched Pokemon."],
        "set": "starter_deck"
    }
} 