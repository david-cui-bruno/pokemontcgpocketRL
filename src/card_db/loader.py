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
    PokemonCard, ItemCard, ToolCard, SupporterCard, Attack, Effect, Ability,
    EnergyType, Stage, AbilityType, TargetType
)


class CardLoader:
    """Loads card data from JSON files."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
    
    def load_all_cards(self) -> List[Card]:
        """Load all cards from the data directory."""
        all_cards = []
        
        for json_file in self.data_dir.glob("*.json"):
            try:
                cards = self.load_cards_from_file(json_file)
                all_cards.extend(cards)
                print(f"Loaded {len(cards)} cards from {json_file.name}")
            except Exception as e:
                print(f"Error loading {json_file.name}: {e}")
        
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
        card_type = card_data.get("category", "").lower()
        
        if card_type == "pokemon":
            return self._parse_pokemon_card(card_data)
        elif card_type == "trainer":
            return self._parse_trainer_card(card_data)
        else:
            print(f"Unknown card type: {card_type}")
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
        
        # Parse weaknesses (TCG Pocket format)
        weakness = None
        weaknesses = data.get("weaknesses", [])
        if weaknesses:
            weakness_data = weaknesses[0]  # Take first weakness
            weakness = self._parse_energy_type(weakness_data.get("type"))
        
        # Parse stage
        stage_str = data.get("stage", "Basic").lower()
        stage = Stage.BASIC
        if stage_str == "stage1":
            stage = Stage.STAGE_1
        elif stage_str == "stage2":
            stage = Stage.STAGE_2
        
        # Check if it's an ex Pokemon
        is_ex = "ex" in data.get("name", "").lower()
        
        return PokemonCard(
            id=data.get("id", ""),
            name=data.get("name", ""),
            hp=data.get("hp", 0),
            pokemon_type=self._parse_energy_type(data.get("types", [""])[0]),
            stage=stage,
            attacks=attacks,
            retreat_cost=data.get("retreat", 0),
            weakness=weakness,
            # No resistance in TCG Pocket
            is_ex=is_ex
        )
    
    def _parse_trainer_card(self, data: Dict[str, Any]) -> Card:
        """Parse a Trainer card into the appropriate subtype."""
        trainer_type = data.get("trainer_type", "").lower()
        effects = self._parse_effects(data.get("effect"))
        
        # Determine trainer subtype based on name and effect
        name = data.get("name", "").lower()
        effect_text = data.get("effect", "").lower()
        
        # Check for Tool cards (attach to Pokemon)
        if (trainer_type == "tool" or 
            "tool" in name or 
            "attach" in effect_text or 
            "equip" in effect_text or
            any(keyword in name for keyword in ["band", "helmet", "share", "mail", "stone"])):
            return ToolCard(
                id=data.get("id", ""),
                name=data.get("name", ""),
                effects=effects
            )
        
        # Check for Supporter cards (powerful, once per turn)
        elif (trainer_type == "supporter" or
              any(keyword in name for keyword in ["professor", "marnie", "boss", "cynthia", "n", "juniper"]) or
              any(keyword in effect_text for keyword in ["draw", "shuffle", "search", "discard"])):
            return SupporterCard(
                id=data.get("id", ""),
                name=data.get("name", ""),
                effects=effects
            )
        
        # Default to Item cards (can be played multiple times)
        else:
            return ItemCard(
                id=data.get("id", ""),
                name=data.get("name", ""),
                effects=effects
            )
    
    def _parse_energy_type(self, energy_str: Optional[str]) -> EnergyType:
        """Parse energy type string to enum."""
        if energy_str is None:
            return EnergyType.COLORLESS
        
        energy_map = {
            "fire": EnergyType.FIRE,
            "water": EnergyType.WATER,
            "grass": EnergyType.GRASS,
            "electric": EnergyType.ELECTRIC,
            "psychic": EnergyType.PSYCHIC,
            "fighting": EnergyType.FIGHTING,
            "darkness": EnergyType.DARKNESS,
            "metal": EnergyType.METAL,
            "colorless": EnergyType.COLORLESS,
            "fairy": EnergyType.FAIRY
        }
        return energy_map.get(energy_str.lower(), EnergyType.COLORLESS)
    
    def _parse_damage(self, damage_value) -> int:
        """Parse damage value to integer."""
        if damage_value is None:
            return 0
        if isinstance(damage_value, str):
            return int(damage_value) if damage_value.isdigit() else 0
        return int(damage_value) if damage_value else 0
    
    def _parse_effects(self, effect_text: Optional[str]) -> List[Effect]:
        """Parse effect text into Effect objects."""
        if not effect_text:
            return []
        
        # Simple effect parsing - you can expand this
        effects = []
        
        # Check for healing effects
        if "heal" in effect_text.lower():
            effects.append(Effect(
                effect_type="heal",
                amount=30,  # Default heal amount
                target=TargetType.SELF
            ))
        
        # Check for status conditions
        if "poison" in effect_text.lower():
            effects.append(Effect(
                effect_type="poison",
                target=TargetType.OPPONENT_ACTIVE
            ))
        
        return effects 