"""Card loading functionality for Pokemon TCG Pocket.

This module handles loading card data from various sources and converting
them into the appropriate card objects.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.card_db.core import (
    Card, PokemonCard, ItemCard, ToolCard, SupporterCard, Attack, Effect, Ability,
    EnergyType, Stage, AbilityType, TargetType
)


class CardLoader:
    """Loads card data from JSON files."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
    
    def load_all_cards(self) -> List[Card]:
        """Load all cards from the data directory."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
        
        all_cards = []
        
        # Load Pokemon cards
        pokemon_file = self.data_dir / "all_pokemon_cards.json"
        if pokemon_file.exists():
            try:
                cards = self.load_cards_from_file(pokemon_file)
                all_cards.extend(cards)
                print(f"Loaded {len(cards)} cards from {pokemon_file.name}")
            except Exception as e:
                print(f"Error loading {pokemon_file.name}: {e}")
        
        # Load Trainer cards
        trainer_file = self.data_dir / "all_trainer_cards.json"
        if trainer_file.exists():
            try:
                cards = self.load_cards_from_file(trainer_file)
                all_cards.extend(cards)
                print(f"Loaded {len(cards)} cards from {trainer_file.name}")
            except Exception as e:
                print(f"Error loading {trainer_file.name}: {e}")
        
        # Load consolidated cards if no specific files found
        if not all_cards:
            consolidated_file = self.data_dir / "consolidated_cards_moves.json"
            if consolidated_file.exists():
                try:
                    cards = self.load_cards_from_file(consolidated_file)
                    all_cards.extend(cards)
                    print(f"Loaded {len(cards)} cards from {consolidated_file.name}")
                except Exception as e:
                    print(f"Error loading {consolidated_file.name}: {e}")
        
        return all_cards
    
    def load_cards_from_file(self, file_path: Path) -> List[Card]:
        """Load cards from a single JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cards = []
        
        # Handle array of cards (new format)
        if isinstance(data, list):
            for card_data in data:
                try:
                    card = self._parse_card(card_data)
                    if card:
                        cards.append(card)
                except Exception as e:
                    print(f"Error parsing card {card_data.get('id', 'unknown')}: {e}")
        
        # Handle single card object (old format)
        elif isinstance(data, dict):
            try:
                card = self._parse_card(data)
                if card:
                    cards.append(card)
            except Exception as e:
                print(f"Error parsing card {data.get('id', 'unknown')}: {e}")
        
        return cards
    
    def _parse_card(self, card_data: Dict[str, Any]) -> Optional[Card]:
        """Parse a single card from JSON data."""
        try:
            category = card_data.get("category", "").lower()
            
            # Validate required fields for Pokemon cards
            if category == "pokemon":
                required_fields = ["id", "name", "hp", "types", "stage"]
                missing_fields = [field for field in required_fields if not card_data.get(field)]
                if missing_fields:
                    print(f"Warning: Pokemon card missing required fields: {missing_fields}")
                    return None
                return self._parse_pokemon_card(card_data)
            
            # Validate required fields for Trainer cards
            elif category == "trainer":
                required_fields = ["id", "name"]
                missing_fields = [field for field in required_fields if not card_data.get(field)]
                if missing_fields:
                    print(f"Warning: Trainer card missing required fields: {missing_fields}")
                    return None
                return self._parse_trainer_card(card_data)
            else:
                print(f"Warning: Unknown card category '{category}' for card {card_data.get('name', 'Unknown')}")
                return None
        except Exception as e:
            print(f"Warning: Failed to parse card {card_data.get('name', 'Unknown')}: {e}")
            return None
    
    def _parse_pokemon_card(self, data: Dict[str, Any]) -> PokemonCard:
        """Parse a Pokemon card."""
        # Parse attacks
        attacks = []
        for attack_data in data.get("attacks", []):
            attack = Attack(
                name=attack_data.get("name", ""),
                cost=[self._parse_energy_type(cost) for cost in attack_data.get("cost", [])],
                damage=self._parse_damage(attack_data.get("damage")),
                effects=self._parse_effects(attack_data.get("effect"))
            )
            attacks.append(attack)
        
        # Parse ability
        ability = None
        abilities_data = data.get("abilities", [])
        if abilities_data:
            ability_data = abilities_data[0]  # Take first ability
            # Create effect from ability text with required text parameter
            ability_effect = Effect(
                text=ability_data.get("effect", ""),  # Add required text parameter
                effect_type="text",
                parameters={}
            )
            ability = Ability(
                name=ability_data.get("name", ""),
                ability_type=AbilityType.ACTIVATED,
                effects=[ability_effect]
            )
        
        # TCG Pocket has no resistance (rulebook §1) - ignore resistance data
        
        # Extract set_code from ID or use "set" field
        set_code = data.get("set")  # Use "set" field from test data
        if not set_code:
            card_id = data.get("id", "")
            if "-" in card_id:
                set_code = card_id.split("-")[0]
        
        # Parse weakness - handle both old and new formats
        weakness = None
        if "weakness" in data:
            # New format: {"type": "Fighting"}
            weakness = self._parse_energy_type(data["weakness"].get("type"))
        elif "weaknesses" in data:
            # Old format: [{"type": "Fighting", "value": "×2"}]
            weaknesses = data["weaknesses"]
            if weaknesses:
                weakness = self._parse_energy_type(weaknesses[0].get("type"))
        
        # Basic Pokemon attributes
        card_id = data.get("id")
        name = data.get("name")
        hp = data.get("hp")

        # The 'ability' field does not exist on the PokemonCard dataclass.
        # We should ignore it during parsing.
        # ability_data = data.get("ability")

        # Super type and sub type
        super_type = data.get("supertype")
        sub_types = data.get("subtypes", [])

        return PokemonCard(
            id=data.get("id", ""),
            name=data.get("name", ""),
            hp=self._parse_damage(data.get("hp")),
            pokemon_type=self._parse_energy_type(data.get("types", [None])[0] if data.get("types") else None),
            stage=self._parse_stage(data.get("stage", "basic")),
            set_code=set_code,
            rarity=data.get("rarity"),  # Add rarity parsing
            attacks=attacks,
            ability=ability,
            # Removed resistance - TCG Pocket has no resistance
            weakness=weakness,
            retreat_cost=data.get("retreat", 0) or data.get("retreat_cost", 0),  # Handle both field names
            is_ex="ex" in data.get("stage", "").lower() or data.get("is_ex", False)
        )
    
    def _parse_trainer_card(self, data: Dict[str, Any]) -> Card:
        """Parse a Trainer card into the appropriate subtype."""
        try:
            # Ensure category is set to "Trainer" for proper parsing
            if "category" not in data:
                data["category"] = "Trainer"
            
            # Check for explicit subtype first
            subtype = str(data.get("subtype", "")).lower()
            trainer_type = str(data.get("trainer_type", "")).lower()
            
            # Parse effects safely
            effect_data = data.get("effect", [])
            if isinstance(effect_data, str):
                effect_data = [effect_data]
            elif not isinstance(effect_data, list):
                effect_data = []
            effects = [Effect(text=str(e)) for e in effect_data]
            
            # Extract set_code from ID or use "set" field
            set_code = data.get("set")
            if not set_code and "id" in data:
                card_id = data["id"]
                if "-" in card_id:
                    set_code = card_id.split("-")[0]
            
            # Common card attributes
            card_attrs = {
                "id": data.get("id", ""),
                "name": data.get("name", ""),
                "effects": effects,
                "set_code": set_code,
                "rarity": data.get("rarity")
            }
            
            # Determine card type and create appropriate instance
            if subtype == "supporter" or trainer_type == "supporter":
                return SupporterCard(**card_attrs)
            elif subtype == "tool" or trainer_type == "tool":
                return ToolCard(**card_attrs)
            else:
                return ItemCard(**card_attrs)  # Default to Item card
                
        except Exception as e:
            print(f"Warning: Failed to parse trainer card {data.get('name', 'Unknown')}: {e}")
            return None
    
    def _parse_energy_type(self, energy_str: Optional[str]) -> EnergyType:
        """Parse energy type string to enum."""
        if energy_str is None:
            return EnergyType.COLORLESS
        
        energy_map = {
            "fire": EnergyType.FIRE,
            "water": EnergyType.WATER,
            "grass": EnergyType.GRASS,
            "electric": EnergyType.ELECTRIC,
            "lightning": EnergyType.ELECTRIC,  # Add Lightning mapping
            "psychic": EnergyType.PSYCHIC,
            "fighting": EnergyType.FIGHTING,
            "darkness": EnergyType.DARKNESS,
            "metal": EnergyType.METAL,
            "colorless": EnergyType.COLORLESS,
            # Map Dragon-type to appropriate types based on the Pokémon
            "dragon": EnergyType.COLORLESS  # Default to COLORLESS for Dragon-type
        }
        
        if energy_str.lower() not in energy_map:
            raise ValueError(f"Invalid energy type: {energy_str}")
        
        return energy_map.get(energy_str.lower(), EnergyType.COLORLESS)
    
    def _parse_damage(self, damage_value) -> int:
        """Parse damage value to integer."""
        if damage_value is None:
            return 0
        if isinstance(damage_value, str):
            return int(damage_value) if damage_value.isdigit() else 0
        return int(damage_value) if damage_value else 0
    
    def _parse_stage(self, stage_str: str) -> Stage:
        """Parse stage string to enum."""
        stage_map = {
            "basic": Stage.BASIC,
            "stage1": Stage.STAGE_1,
            "stage2": Stage.STAGE_2
        }
        
        if stage_str.lower() not in stage_map:
            raise ValueError(f"Invalid stage: {stage_str}")
        
        return stage_map.get(stage_str.lower(), Stage.BASIC)
    
    def _parse_effects(self, effect_data) -> List[Effect]:
        """Parse effect data into Effect objects."""
        if not effect_data:
            return []
        
        # Handle list effects
        if isinstance(effect_data, list):
            return [Effect(text=str(text)) for text in effect_data if text]
        
        # Handle string effects
        if isinstance(effect_data, str):
            return [Effect(text=effect_data)]
        
        # Handle dict effects
        if isinstance(effect_data, dict):
            # Try to get text from various possible fields
            text = effect_data.get("text", "")
            if not text:
                text = effect_data.get("effect", "")
            if not text:
                text = str(effect_data)  # Use the whole dict as text if no specific field found
            return [Effect(text=text)]
        
        # For any other type, convert to string
        return [Effect(text=str(effect_data))]


class CardDatabase:
    """Simple card database with lookup functionality."""
    
    def __init__(self, cards: Dict[str, Card]):
        self._cards = cards
    
    def __len__(self) -> int:
        return len(self._cards)
    
    def get(self, card_id: str) -> Optional[Card]:
        """Get card by ID."""
        return self._cards.get(card_id)
    
    def find(self, card_name: str) -> List[Card]:
        """Find cards by name. Returns a list of matching cards."""
        matches = []
        for card in self._cards.values():
            if card.name == card_name:
                matches.append(card)
        return matches


# Standalone functions for backward compatibility with tests

def load_card_db(data_dir: str = "data") -> CardDatabase:
    """Load all cards from the data directory and return as a CardDatabase."""
    loader = CardLoader(data_dir)
    cards = loader.load_all_cards()
    
    # Convert to dictionary with card ID as key
    card_dict = {}
    for card in cards:
        card_dict[card.id] = card
    
    return CardDatabase(card_dict)


def _parse_trainer(data: Dict[str, Any]) -> Card:
    """Parse a trainer card (standalone function for tests)."""
    loader = CardLoader()
    return loader._parse_trainer_card(data)


def _parse_pokemon(data: Dict[str, Any]) -> PokemonCard:
    """Parse a Pokemon card (standalone function for tests)."""
    loader = CardLoader()
    return loader._parse_pokemon_card(data)


# Additional helper functions for tests

def _to_energy(energy_str: str) -> EnergyType:
    """Convert energy string to EnergyType enum (for tests)."""
    loader = CardLoader()
    return loader._parse_energy_type(energy_str)


def _to_stage(stage_str: str) -> Stage:
    """Convert stage string to Stage enum (for tests)."""
    loader = CardLoader()
    return loader._parse_stage(stage_str) 