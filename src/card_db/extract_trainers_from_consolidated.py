#!/usr/bin/env python3
"""
Extract all trainer cards from the consolidated cards file.

This script separates trainer cards from the consolidated Pokemon data
and saves them to a dedicated trainer cards file.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def extract_trainers_from_consolidated(base_dir: Path = None):
    """Extract all trainer cards from the consolidated file."""
    print(" Extracting trainer cards from consolidated data...")
    print("=" * 60)
    
    # Use provided base directory or default to data/
    base_dir = base_dir or Path("data")
    
    # Load the consolidated card data
    data_file = base_dir / "consolidated_cards_moves.json"
    if not data_file.exists():
        print(f"❌ {data_file} not found!")
        print("Make sure you've run the consolidation script first.")
        return [], {}  # Return empty results on failure
    
    print(f"📖 Loading consolidated card data from {data_file}...")
    with open(data_file, 'r', encoding='utf-8') as f:
        all_cards = json.load(f)
    
    print(f" Total cards loaded: {len(all_cards)}")
    
    # Separate Pokemon and Trainer cards
    pokemon_cards = []
    trainer_cards = []
    
    for card in all_cards:
        if card.get("category") == "Pokemon":
            pokemon_cards.append(card)
        elif card.get("category") == "Trainer":
            trainer_cards.append(card)
    
    print(f" Pokemon cards: {len(pokemon_cards)}")
    print(f" Trainer cards: {len(trainer_cards)}")
    
    # Categorize trainer cards by type
    categorized_trainers = {
        "items": [],
        "supporters": [],
        "tools": [],
        "unknown": []
    }
    
    for card in trainer_cards:
        name = card.get("name", "").lower()
        effect = card.get("effect", "").lower() if card.get("effect") else ""
        trainer_type = card.get("trainer_type", "").lower() if card.get("trainer_type") else ""
        
        # Determine trainer subtype based on name, effect, and trainer_type
        if (trainer_type == "tool" or 
            "tool" in name or 
            "attach" in effect or 
            "equip" in effect or
            any(keyword in name for keyword in ["band", "helmet", "share", "mail", "stone", "cape", "berry"])):
            categorized_trainers["tools"].append(card)
            
        elif (trainer_type == "supporter" or
              any(keyword in name for keyword in ["professor", "marnie", "boss", "cynthia", "n", "juniper"])):
            categorized_trainers["supporters"].append(card)
            
        elif (trainer_type == "item" or
              "ball" in name or  # Add this line to catch Poké Ball variants
              any(keyword in name for keyword in ["potion", "switch", "energy", "retrieval", "communication", "fossil"]) or
              any(keyword in effect for keyword in ["search your deck", "draw", "look at"])):  # Add more item-like effects
            categorized_trainers["items"].append(card)
            
        else:
            categorized_trainers["unknown"].append(card)
    
    # Print categorization summary
    print(f"\n📋 Trainer Card Categorization:")
    print(f"   Items: {len(categorized_trainers['items'])}")
    print(f"   Supporters: {len(categorized_trainers['supporters'])}")
    print(f"   Tools: {len(categorized_trainers['tools'])}")
    print(f"   Unknown: {len(categorized_trainers['unknown'])}")
    
    # Save all trainer cards to a single file
    trainer_file = base_dir / "all_trainer_cards.json"
    with open(trainer_file, 'w', encoding='utf-8') as f:
        json.dump(trainer_cards, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 All trainer cards saved to: {trainer_file}")
    
    # Save categorized trainers
    categorized_file = base_dir / "categorized_trainer_cards.json"
    with open(categorized_file, 'w', encoding='utf-8') as f:
        json.dump(categorized_trainers, f, indent=2, ensure_ascii=False)
    
    print(f"📂 Categorized trainers saved to: {categorized_file}")
    
    # Save Pokemon-only file (without trainers)
    pokemon_file = base_dir / "all_pokemon_cards.json"
    with open(pokemon_file, 'w', encoding='utf-8') as f:
        json.dump(pokemon_cards, f, indent=2, ensure_ascii=False)
    
    print(f" Pokemon cards saved to: {pokemon_file}")
    
    # Create a human-readable summary
    create_trainer_summary(trainer_cards, categorized_trainers, base_dir)
    
    return trainer_cards, categorized_trainers

def create_trainer_summary(trainer_cards, categorized_trainers, base_dir: Path = None):
    """Create a human-readable summary of all trainer cards."""
    print("\n📋 Creating trainer card summary...")
    
    # Use provided base directory or default to data/
    base_dir = base_dir or Path("data")
    
    summary = {
        "total_trainer_cards": len(trainer_cards),
        "categorization": {
            "items": len(categorized_trainers["items"]),
            "supporters": len(categorized_trainers["supporters"]),
            "tools": len(categorized_trainers["tools"]),
            "unknown": len(categorized_trainers["unknown"])
        },
        "items": [{"id": card["id"], "name": card.get("name", "Unknown"), "effect": card.get("effect", "")}
                 for card in categorized_trainers["items"]],
        "supporters": [{"id": card["id"], "name": card.get("name", "Unknown"), "effect": card.get("effect", "")}
                      for card in categorized_trainers["supporters"]],
        "tools": [{"id": card["id"], "name": card.get("name", "Unknown"), "effect": card.get("effect", "")}
                 for card in categorized_trainers["tools"]],
        "unknown": [{"id": card["id"], "name": card.get("name", "Unknown"), "effect": card.get("effect", "")}
                   for card in categorized_trainers["unknown"]]
    }
    
    # Save summary
    summary_file = base_dir / "trainer_cards_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Trainer summary saved to: {summary_file}")
    
    # Print sample cards from each category
    print(f"\n🎯 Sample Trainer Cards by Category:")
    
    for category, cards in categorized_trainers.items():
        if cards:
            print(f"\n{category.upper()}:")
            for card in cards[:5]:  # Show first 5 cards
                name = card.get("name", "Unknown")
                print(f"  {card['id']}: {name}")
                if card.get("effect"):
                    print(f"    Effect: {card['effect']}")
            if len(cards) > 5:
                print(f"  ... and {len(cards) - 5} more")

def print_trainer_descriptions(base_dir: Path = None):
    """Print all trainer card descriptions in a readable format."""
    print("\n📖 All Trainer Card Descriptions:")
    print("=" * 80)
    
    # Use provided base directory or default to data/
    base_dir = base_dir or Path("data")
    
    data_file = base_dir / "all_trainer_cards.json"
    if not data_file.exists():
        print("❌ Run extract_trainers_from_consolidated() first!")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        trainer_cards = json.load(f)
    
    # Sort by ID for consistent ordering
    trainer_cards.sort(key=lambda x: x.get("id", ""))
    
    for card in trainer_cards:
        card_id = card.get("id", "Unknown")
        name = card.get("name", "Unknown")
        effect = card.get("effect", "No effect")
        
        print(f"{card_id:12} | {name:25} | {effect}")
    
    print(f"\n📊 Total trainer cards: {len(trainer_cards)}")

if __name__ == "__main__":
    print("�� TCG Pocket Trainer Card Extractor")
    print("=" * 60)
    
    # Extract trainer cards
    trainer_cards, categorized = extract_trainers_from_consolidated()
    
    # Print descriptions
    print_trainer_descriptions()
    
    print(f"\n✅ Trainer card extraction complete!")
    print(f"Check the following files:")
    print(f"  data/all_trainer_cards.json - All trainer cards")
    print(f"  data/categorized_trainer_cards.json - Categorized by type")
    print(f"  data/trainer_cards_summary.json - Human-readable summary")
    print(f"  data/all_pokemon_cards.json - Pokemon cards only") 