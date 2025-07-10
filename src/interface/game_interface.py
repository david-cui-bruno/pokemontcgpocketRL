import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import our game modules
try:
    from src.rules.game_engine import GameEngine
    from src.rules.game_state import GameState, PlayerState
    from src.card_db.loader import load_card_db
    from src.card_db.storage import CardStorage
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    # We'll continue anyway for now

class PokemonTCGInterface:
    def __init__(self):
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Pokémon TCG Pocket - Test Interface")
        self.root.geometry("1200x800")
        
        # Initialize game state variables
        self.game_engine = None
        self.game_state = None
        self.current_player = 0
        
        # Try to load card database
        try:
            self.card_storage = CardStorage()
            self.card_db = load_card_db()
            print(f"✅ Loaded {len(self.card_db)} cards")
        except Exception as e:
            print(f"❌ Error loading card database: {e}")
            self.card_db = {}
        
        # Set up the basic UI
        self.setup_basic_ui()
    
    def setup_basic_ui(self):
        """Set up the basic user interface."""
        
        # Create main title
        title_label = ttk.Label(self.root, text="Pokémon TCG Pocket Test Interface", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        
        # Create status frame
        status_frame = ttk.LabelFrame(self.root, text="Status")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status labels
        self.status_label = ttk.Label(status_frame, text="Ready to start")
        self.status_label.pack(pady=5)
        
        # Create button frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        # Test buttons
        ttk.Button(button_frame, text="Test Button", 
                  command=self.test_function).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Load Cards", 
                  command=self.test_load_cards).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Create Game", 
                  command=self.test_create_game).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Debug Cards", 
          command=self.debug_card_database).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Debug Structure", 
          command=self.debug_card_database_structure).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Build Deck", 
          command=self.setup_deck_builder).pack(side=tk.LEFT, padx=5)
        
        # Create info frame
        info_frame = ttk.LabelFrame(self.root, text="Information")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Info text area
        self.info_text = tk.Text(info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for info text
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        # Add initial info
        self.log_info("Interface initialized successfully!")
        self.log_info(f"Loaded {len(self.card_db)} cards from database")
    
    def setup_deck_builder(self):
        """Create deck builder interface."""
        
        # Deck builder window
        self.deck_builder = tk.Toplevel(self.root)
        self.deck_builder.title("Deck Builder")
        self.deck_builder.geometry("1000x600")
        
        # Player deck builder
        player_frame = ttk.LabelFrame(self.deck_builder, text="Player Deck")
        player_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Available cards (left side)
        available_frame = ttk.Frame(player_frame)
        available_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(available_frame, text="Available Cards:").pack()
        
        # Filter controls
        filter_frame = ttk.Frame(available_frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.card_type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(filter_frame, textvariable=self.card_type_var, 
                                 values=["All", "Pokémon", "Item", "Supporter", "Tool"])
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind('<<ComboboxSelected>>', self.filter_cards)
        
        # Available cards listbox
        self.available_listbox = tk.Listbox(available_frame, height=20)
        self.available_listbox.pack(fill=tk.BOTH, expand=True)
        self.available_listbox.bind('<Double-Button-1>', self.add_card)
        
        # Selected cards (right side)
        selected_frame = ttk.Frame(player_frame)
        selected_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(selected_frame, text="Selected Cards:").pack()
        
        # Selected cards listbox
        self.selected_listbox = tk.Listbox(selected_frame, height=20)
        self.selected_listbox.pack(fill=tk.BOTH, expand=True)
        self.selected_listbox.bind('<Double-Button-1>', self.remove_card)
        
        # Deck info
        self.deck_info_label = ttk.Label(selected_frame, text="Cards: 0/20")
        self.deck_info_label.pack()
        
        # Buttons
        button_frame = ttk.Frame(player_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Clear Deck", 
                  command=self.clear_deck).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Load Deck", 
                  command=self.load_deck).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Deck", 
                  command=self.save_deck).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Done", 
                  command=self.finish_deck).pack(side=tk.RIGHT)
        
        # Energy type selection
        energy_frame = ttk.LabelFrame(self.deck_builder, text="Energy Types (1-3)")
        energy_frame.pack(fill=tk.X, padx=5, pady=5)

        self.energy_type_vars = {}
        energy_types = ["Fire", "Water", "Grass", "Electric", "Psychic", "Fighting", "Dark", "Metal", "Fairy"]

        for energy_type in energy_types:
            var = tk.BooleanVar()
            self.energy_type_vars[energy_type] = var
            ttk.Checkbutton(energy_frame, text=energy_type, 
                           variable=var).pack(side=tk.LEFT, padx=2)
        
        # Populate available cards
        self.populate_available_cards()

    def populate_available_cards(self):
        """Populate the available cards listbox."""
        try:
            self.available_listbox.delete(0, tk.END)
            
            cards = self.card_db._cards
            self.log_info(f"Populating {len(cards)} cards")
            
            for card_name, card in cards.items():
                # Apply filter
                if self.card_type_var.get() != "All":
                    if self.card_type_var.get() == "Pokémon" and not hasattr(card, 'hp'):
                        continue
                    elif self.card_type_var.get() in ["Item", "Supporter", "Tool"] and not hasattr(card, 'card_type'):
                        continue
                    elif hasattr(card, 'card_type') and card.card_type != self.card_type_var.get():
                        continue
                
                self.available_listbox.insert(tk.END, f"{card.name} ({card.id})")
            
            self.log_info(f"Added {self.available_listbox.size()} cards to listbox")
            
        except Exception as e:
            self.log_info(f"Error populating available cards: {e}")

    def filter_cards(self, event=None):
        """Filter available cards based on selection."""
        self.populate_available_cards()

    def add_card(self, event=None):
        """Add selected card to deck."""
        try:
            selection = self.available_listbox.curselection()
            if not selection:
                self.log_info("No card selected")
                return
            
            # Get selected card
            card_text = self.available_listbox.get(selection[0])
            self.log_info(f"Selected card text: {card_text}")
            
            # Extract card ID from the text (format: "Card Name (ID)")
            card_id = card_text.split("(")[1].split(")")[0]
            self.log_info(f"Extracted card ID: {card_id}")
            
            # Find the card in the database using the ID
            card = self.card_db._cards.get(card_id)
            
            if not card:
                self.log_info(f"Card not found in database: {card_id}")
                # Try to find by name as fallback
                for db_card_id, db_card in self.card_db._cards.items():
                    if db_card.name == card_text.split(" (")[0]:
                        card = db_card
                        self.log_info(f"Found card by name: {db_card.name}")
                        break
            
            if not card:
                self.log_info(f"Card not found by ID or name")
                return
            
            # Check deck size limit
            current_count = self.selected_listbox.size()
            if current_count >= 20:
                messagebox.showwarning("Deck Full", "Deck cannot exceed 20 cards!")
                return
            
            # Check copy limit
            if not self.check_copy_limit(card.name):
                messagebox.showwarning("Copy Limit", f"Maximum 2 copies of {card.name} allowed!")
                return
            
            # Add card to selected list
            self.selected_listbox.insert(tk.END, f"{card.name} ({card.id})")
            
            # Update deck info
            self.deck_info_label.config(text=f"Cards: {self.selected_listbox.size()}/20")
            
            self.log_info(f"Added card: {card.name}")
            
        except Exception as e:
            self.log_info(f"Error adding card: {e}")
            messagebox.showerror("Error", f"Error adding card: {e}")

    def remove_card(self, event=None):
        """Remove selected card from deck."""
        try:
            selection = self.selected_listbox.curselection()
            if not selection:
                return
            
            self.selected_listbox.delete(selection[0])
            
            # Update deck info
            self.deck_info_label.config(text=f"Cards: {self.selected_listbox.size()}/20")
            
        except Exception as e:
            self.log_info(f"Error removing card: {e}")

    def clear_deck(self):
        """Clear the current deck."""
        self.selected_listbox.delete(0, tk.END)
        self.deck_info_label.config(text="Cards: 0/20")

    def finish_deck(self):
        """Finish deck building and start game."""
        try:
            # Create deck list
            player_deck = []
            for i in range(self.selected_listbox.size()):
                card_text = self.selected_listbox.get(i)
                card_id = card_text.split("(")[1].split(")")[0]
                card = self.card_db._cards.get(card_id)
                if card:
                    player_deck.append(card)
        
            # Validate deck
            from src.rules.game_state import validate_deck
            is_valid, message = validate_deck(player_deck)
            if not is_valid:
                messagebox.showerror("Invalid Deck", message)
                return
            
            # Get selected energy types
            selected_energy_types = []
            for energy_type, var in self.energy_type_vars.items():
                if var.get():
                    selected_energy_types.append(energy_type)
            
            if not selected_energy_types:
                messagebox.showerror("No Energy Types", "Please select 1-3 energy types!")
                return
            
            if len(selected_energy_types) > 3:
                messagebox.showerror("Too Many Energy Types", "Maximum 3 energy types allowed!")
                return
            
            # Initialize game with energy types
            self.game_state = GameState(
                PlayerState(player_deck),
                PlayerState(player_deck.copy())
            )
            
            # Register energy types
            from src.rules.energy_type import EnergyType
            for energy_type in selected_energy_types:
                self.game_state.player.register_energy_type(EnergyType[energy_type.upper()])
                self.game_state.opponent.register_energy_type(EnergyType[energy_type.upper()])
            
            self.game_engine = GameEngine()
            
            # Draw initial hands
            for _ in range(5):
                self.game_state.player.draw_card()
                self.game_state.opponent.draw_card()
            
            # Hide deck builder
            self.deck_builder.withdraw()
            
            # Update display
            self.update_display()
            self.log_info("Game started successfully!")
            
        except Exception as e:
            self.log_info(f"Error starting game: {e}")
            messagebox.showerror("Error", f"Error starting game: {e}")

    def test_function(self):
        """Test function to verify the interface is working."""
        self.log_info("Test button clicked!")
        messagebox.showinfo("Test", "Interface is working correctly!")
    
    def test_load_cards(self):
        """Test loading cards from the database."""
        try:
            if self.card_db:
                # Access cards through the _cards attribute
                cards = self.card_db._cards
                card_names = list(cards.keys())[:5]
                self.log_info(f"Sample cards: {', '.join(card_names)}")
                messagebox.showinfo("Cards Loaded", f"Successfully loaded {len(cards)} cards!")
            else:
                self.log_info("No cards loaded")
                messagebox.showwarning("No Cards", "No cards were loaded from the database")
        except Exception as e:
            self.log_info(f"Error testing cards: {e}")
            messagebox.showerror("Error", f"Error testing cards: {e}")

    def debug_card_database(self):
        """Debug information about the card database."""
        self.log_info("=== Card Database Debug Info ===")
        self.log_info(f"Type: {type(self.card_db)}")
        self.log_info(f"Attributes: {dir(self.card_db)}")
        
        if hasattr(self.card_db, '__dict__'):
            self.log_info(f"__dict__ keys: {list(self.card_db.__dict__.keys())}")
        
        # Try to get some sample data
        try:
            if hasattr(self.card_db, 'keys'):
                self.log_info(f"Has keys() method: {len(list(self.card_db.keys()))} keys")
            if hasattr(self.card_db, 'values'):
                self.log_info(f"Has values() method: {len(list(self.card_db.values()))} values")
            if hasattr(self.card_db, 'get_all_cards'):
                self.log_info("Has get_all_cards() method")
            if hasattr(self.card_db, 'cards'):
                self.log_info(f"Has cards attribute: {len(self.card_db.cards)} cards")
        except Exception as e:
            self.log_info(f"Error checking methods: {e}")
        
        self.log_info("=== End Debug Info ===")

    def debug_card_database_structure(self):
        """Debug the card database structure."""
        self.log_info("=== Card Database Structure Debug ===")
        
        cards = self.card_db._cards
        self.log_info(f"Total cards in database: {len(cards)}")
        
        # Show first few entries
        sample_keys = list(cards.keys())[:5]
        self.log_info(f"Sample keys: {sample_keys}")
        
        for key in sample_keys:
            card = cards[key]
            self.log_info(f"Key '{key}' -> Card: {card.name} (ID: {card.id})")
        
        self.log_info("=== End Structure Debug ===")

    def test_create_game(self):
        """Test creating a basic game state."""
        try:
            # Create a simple game state
            player_deck = []
            opponent_deck = []
            
            # Add some basic cards if available
            if self.card_db:
                cards = self.card_db._cards
                sample_cards = list(cards.values())[:10]
                
                if sample_cards:
                    player_deck = sample_cards[:5]
                    opponent_deck = sample_cards[5:10]
            
            self.game_state = GameState(
                PlayerState(player_deck),
                PlayerState(opponent_deck)
            )
            self.game_engine = GameEngine()
            
            self.log_info("Game state created successfully!")
            self.log_info(f"Player deck: {len(player_deck)} cards")
            self.log_info(f"Opponent deck: {len(opponent_deck)} cards")
            
            messagebox.showinfo("Game Created", "Basic game state created successfully!")
            
        except Exception as e:
            self.log_info(f"Error creating game: {e}")
            messagebox.showerror("Error", f"Error creating game: {e}")

    def get_card_list(self):
        """Get a list of all cards from the database."""
        try:
            if not self.card_db:
                return []
            return list(self.card_db._cards.values())
        except Exception as e:
            self.log_info(f"Error getting card list: {e}")
            return []
    
    def log_info(self, message):
        """Add a message to the info text area."""
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)
    
    def run(self):
        """Run the application."""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Error running application: {e}")

    def check_copy_limit(self, card_name: str) -> bool:
        """Check if adding this card would exceed the 2-copy limit."""
        current_count = 0
        for i in range(self.selected_listbox.size()):
            if self.selected_listbox.get(i).split(" (")[0] == card_name:
                current_count += 1
        
        return current_count < 2

def main():
    """Main function to run the interface."""
    try:
        app = PokemonTCGInterface()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")

if __name__ == "__main__":
    main()
