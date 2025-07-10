"""Storage module for Pokemon TCG Pocket card data.

This module handles storing and retrieving card data in a structured format:
/data/
  /sets/
    A3a.json  # Ultra Beast Invasion
    A3b.json  # Eevee Grove
  /cards/
    A3a-001.json
    A3a-002.json
    ...
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from src.card_db.core import Card, PokemonCard, ItemCard

logger = logging.getLogger(__name__)

class CardStorage:
    """Handles storage and retrieval of card data."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.sets_dir = self.data_dir / "sets"
        self.cards_dir = self.data_dir / "cards"
        
        # Create directories if they don't exist
        self.sets_dir.mkdir(parents=True, exist_ok=True)
        self.cards_dir.mkdir(parents=True, exist_ok=True)
    
    def store_set(self, set_id: str, set_data: Dict) -> None:
        """Store set data in JSON format."""
        path = self.sets_dir / f"{set_id}.json"
        with open(path, "w") as f:
            json.dump(set_data, f, indent=2)
    
    def store_card(self, card_id: str, card: Card) -> None:
        """Store individual card data in JSON format."""
        path = self.cards_dir / f"{card_id}.json"
        with open(path, "w") as f:
            json.dump(card.to_dict(), f, indent=2)
    
    def get_set(self, set_id: str) -> Optional[Dict]:
        """Retrieve set data."""
        path = self.sets_dir / f"{set_id}.json"
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in set file: {path}")
                return None
        return None
    
    def get_card(self, card_id: str) -> Optional[Dict]:
        """Retrieve card data."""
        path = self.cards_dir / f"{card_id}.json"
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in card file: {path}")
                return None
        return None
    
    def list_sets(self) -> List[str]:
        """List all available sets."""
        return [p.stem for p in self.sets_dir.glob("*.json")]
    
    def list_cards(self) -> List[str]:
        """List all available cards."""
        return [p.stem for p in self.cards_dir.glob("*.json")] 

    def load_card(self, card_id: str) -> Optional[Card]:
        """Load a card from storage by ID."""
        card_path = self.cards_dir / f"{card_id}.json"
        if not card_path.exists():
            return None
            
        with open(card_path, 'r') as f:
            data = json.load(f)
            # Reconstruct the appropriate card type
            if data.get("card_type") == "Item":
                return ItemCard(**data)
            elif "hp" in data:  # It's a Pokemon card
                return PokemonCard(**data)
            else:
                return Card(**data) 