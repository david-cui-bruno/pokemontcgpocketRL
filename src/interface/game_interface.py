import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import our game modules
try:
    from src.rules.game_engine import GameEngine
    from src.rules.game_state import GameState, PlayerState, GamePhase
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
        """Create deck builder interface with search, filter, and energy selection."""
        # Create or lift the deck builder window
        if hasattr(self, 'deck_builder') and self.deck_builder.winfo_exists():
            self.deck_builder.lift()
            return

        self.deck_builder = tk.Toplevel(self.root)
        self.deck_builder.title("Deck Builder")
        self.deck_builder.geometry("1000x700")

        # Main horizontal frame: left (available), right (selected)
        main_frame = ttk.Frame(self.deck_builder)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- LEFT: Available Cards ---
        available_frame = ttk.Frame(main_frame)
        available_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ttk.Label(available_frame, text="Available Cards:").pack(anchor=tk.W)
        
        # Search and filter controls
        search_filter_frame = ttk.Frame(available_frame)
        search_filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_filter_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.filter_cards)
        search_entry = ttk.Entry(search_filter_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(search_filter_frame, text="Type:").pack(side=tk.LEFT, padx=(10, 0))
        self.card_type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(search_filter_frame, textvariable=self.card_type_var, 
                                  values=["All", "Pokémon", "Item", "Supporter", "Tool"], width=10, state="readonly")
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind('<<ComboboxSelected>>', self.filter_cards)
        
        ttk.Button(search_filter_frame, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=5)
        
        # Listbox with scrollbar for available cards
        listbox_frame = ttk.Frame(available_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.available_listbox = tk.Listbox(listbox_frame, height=20)
        self.available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.available_listbox.bind('<Double-Button-1>', self.add_card)
        available_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.available_listbox.yview)
        available_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.available_listbox.configure(yscrollcommand=available_scrollbar.set)
        
        # --- RIGHT: Selected Cards ---
        selected_frame = ttk.Frame(main_frame)
        selected_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(selected_frame, text="Selected Cards:").pack(anchor=tk.W)
        
        selected_listbox_frame = ttk.Frame(selected_frame)
        selected_listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.selected_listbox = tk.Listbox(selected_listbox_frame, height=20)
        self.selected_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.selected_listbox.bind('<Double-Button-1>', self.remove_card)
        selected_scrollbar = ttk.Scrollbar(selected_listbox_frame, orient=tk.VERTICAL, command=self.selected_listbox.yview)
        selected_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.selected_listbox.configure(yscrollcommand=selected_scrollbar.set)
        
        self.deck_info_label = ttk.Label(selected_frame, text="Cards: 0/20")
        self.deck_info_label.pack(pady=5)
        
        # Deck control buttons
        button_frame = ttk.Frame(selected_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Clear Deck", command=self.clear_deck).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Done", command=self.finish_deck).pack(side=tk.RIGHT)

        # --- ENERGY TYPE SELECTION ---
        energy_frame = ttk.LabelFrame(self.deck_builder, text="Energy Types (Select 1-3)")
        energy_frame.pack(fill=tk.X, padx=10, pady=10)
        self.energy_type_vars = {}
        energy_types = ["Fire", "Water", "Grass", "Electric", "Psychic", "Fighting", "Dark", "Metal", "Fairy"]
        for i, energy_type in enumerate(energy_types):
            var = tk.BooleanVar()
            self.energy_type_vars[energy_type] = var
            ttk.Checkbutton(energy_frame, text=energy_type, variable=var).pack(side=tk.LEFT, padx=5)

        # --- SEARCH HINTS ---
        hints_frame = ttk.LabelFrame(self.deck_builder, text="Search Tips")
        hints_frame.pack(fill=tk.X, padx=10, pady=5)
        hints_text = (
            "• Type card names (e.g., 'Pikachu', 'Professor')\n"
            "• Search by card ID (e.g., 'base1-1')\n"
            "• Search by type (e.g., 'Fire', 'Water')\n"
            "• Use type filter dropdown for specific card types\n"
            "• Double-click cards to add/remove from deck"
        )
        ttk.Label(hints_frame, text=hints_text, justify=tk.LEFT).pack(anchor=tk.W, padx=5, pady=2)

        # Populate available cards
        self.populate_available_cards()

    def clear_search(self):
        self.search_var.set("")
        self.card_type_var.set("All")
        self.filter_cards()

    def filter_cards(self, event=None, *args):
        """Filter available cards based on search text and type selection."""
        self.available_listbox.delete(0, tk.END)
        search_text = self.search_var.get().lower() if hasattr(self, 'search_var') else ""
        card_type_filter = self.card_type_var.get() if hasattr(self, 'card_type_var') else "All"
        cards = self.card_db._cards

        for card in cards.values():
            # Type filter
            if card_type_filter != "All":
                # Pokémon
                if card_type_filter == "Pokémon":
                    if not hasattr(card, 'hp'):
                        continue
                # Trainer subtypes
                elif hasattr(card, 'card_type'):
                    if card.card_type != card_type_filter:
                        continue
                else:
                    continue  # Not a matching type
            # Search filter
            if search_text:
                card_text = f"{card.name} {card.id}".lower()
                if hasattr(card, 'card_type'):
                    card_text += f" {card.card_type}".lower()
                if hasattr(card, 'pokemon_type'):
                    card_text += f" {card.pokemon_type}".lower()
                if search_text not in card_text:
                    continue
            # Display
            display_text = f"{card.name} ({card.id})"
            if hasattr(card, 'card_type'):
                display_text += f" - {card.card_type}"
            elif hasattr(card, 'hp'):
                display_text += f" - Pokémon"
            self.available_listbox.insert(tk.END, display_text)

    def populate_available_cards(self):
        """Populate the available cards listbox."""
        self.filter_cards()

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

    def load_deck(self):
        """Load a deck from file."""
        self.log_info("Load deck functionality not implemented yet")

    def save_deck(self):
        """Save current deck to file."""
        self.log_info("Save deck functionality not implemented yet")

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
            from src.card_db.core import EnergyType
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
            
            # Set up game interface
            self.setup_game_interface()
            
            # Update display
            self.update_display()
            self.log_game_event("Game started successfully!")
            
        except Exception as e:
            self.log_info(f"Error starting game: {e}")
            messagebox.showerror("Error", f"Error starting game: {e}")

    def setup_game_interface(self):
        """Set up the main game interface for playtesting."""
        
        # Clear the main window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create game interface
        self.setup_game_ui()
        
    def setup_game_ui(self):
        """Set up the game UI with board, hands, and controls."""
        
        # Main title
        title_label = ttk.Label(self.root, text="Pokémon TCG Pocket - Playtesting", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Game status frame
        status_frame = ttk.LabelFrame(self.root, text="Game Status")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.turn_label = ttk.Label(status_frame, text="Turn: 1 | Phase: START")
        self.turn_label.pack(side=tk.LEFT, padx=5)
        
        self.points_label = ttk.Label(status_frame, text="Points - Player: 0 | Opponent: 0")
        self.points_label.pack(side=tk.RIGHT, padx=5)
        
        # Main game area
        game_frame = ttk.Frame(self.root)
        game_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Opponent area (top)
        self.setup_opponent_area(game_frame)
        
        # Player area (bottom)
        self.setup_player_area(game_frame)
        
        # Action buttons
        self.setup_action_buttons()
        
        # Energy zone display
        self.setup_energy_zone()
        
        # Log area
        self.setup_log_area()

    def setup_opponent_area(self, parent):
        """Set up the opponent's board area."""
        opponent_frame = ttk.LabelFrame(parent, text="Opponent")
        opponent_frame.pack(fill=tk.X, pady=5)
        
        # Opponent's active Pokémon
        active_frame = ttk.Frame(opponent_frame)
        active_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(active_frame, text="Active:").pack(side=tk.LEFT)
        self.opponent_active_label = ttk.Label(active_frame, text="None")
        self.opponent_active_label.pack(side=tk.LEFT, padx=5)
        
        # Opponent's bench
        bench_frame = ttk.Frame(opponent_frame)
        bench_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(bench_frame, text="Bench:").pack(side=tk.LEFT)
        self.opponent_bench_labels = []
        for i in range(3):
            label = ttk.Label(bench_frame, text="Empty")
            label.pack(side=tk.LEFT, padx=5)
            self.opponent_bench_labels.append(label)
        
        # Opponent's hand count
        hand_frame = ttk.Frame(opponent_frame)
        hand_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(hand_frame, text="Hand:").pack(side=tk.LEFT)
        self.opponent_hand_label = ttk.Label(hand_frame, text="0 cards")
        self.opponent_hand_label.pack(side=tk.LEFT, padx=5)

    def setup_player_area(self, parent):
        """Set up the player's board area."""
        player_frame = ttk.LabelFrame(parent, text="Player")
        player_frame.pack(fill=tk.X, pady=5)
        
        # Player's hand
        hand_frame = ttk.LabelFrame(player_frame, text="Your Hand")
        hand_frame.pack(fill=tk.X, pady=5)
        
        # Hand listbox with scrollbar
        hand_list_frame = ttk.Frame(hand_frame)
        hand_list_frame.pack(fill=tk.X, pady=5)
        
        self.hand_listbox = tk.Listbox(hand_list_frame, height=4)
        self.hand_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.hand_listbox.bind('<Double-Button-1>', self.play_card)
        
        hand_scrollbar = ttk.Scrollbar(hand_list_frame, orient=tk.HORIZONTAL, 
                                       command=self.hand_listbox.xview)
        hand_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.hand_listbox.configure(xscrollcommand=hand_scrollbar.set)
        
        # Player's active Pokémon
        active_frame = ttk.Frame(player_frame)
        active_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(active_frame, text="Active:").pack(side=tk.LEFT)
        self.player_active_label = ttk.Label(active_frame, text="None")
        self.player_active_label.pack(side=tk.LEFT, padx=5)
        
        # Player's bench
        bench_frame = ttk.Frame(player_frame)
        bench_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(bench_frame, text="Bench:").pack(side=tk.LEFT)
        self.player_bench_labels = []
        for i in range(3):
            label = ttk.Label(bench_frame, text="Empty")
            label.pack(side=tk.LEFT, padx=5)
            self.player_bench_labels.append(label)

    def setup_action_buttons(self):
        """Set up action buttons for gameplay."""
        action_frame = ttk.LabelFrame(self.root, text="Actions")
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Turn actions
        turn_frame = ttk.Frame(action_frame)
        turn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(turn_frame, text="Draw Card", 
                   command=self.draw_card).pack(side=tk.LEFT, padx=2)
        ttk.Button(turn_frame, text="End Turn", 
                   command=self.end_turn).pack(side=tk.LEFT, padx=2)
        ttk.Button(turn_frame, text="Attack", 
                   command=self.attack).pack(side=tk.LEFT, padx=2)
        ttk.Button(turn_frame, text="Retreat", 
                   command=self.retreat).pack(side=tk.LEFT, padx=2)
        
        # Card actions
        card_frame = ttk.Frame(action_frame)
        card_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(card_frame, text="Play Pokémon", 
                   command=self.play_pokemon).pack(side=tk.LEFT, padx=2)
        ttk.Button(card_frame, text="Evolve", 
                   command=self.evolve_pokemon).pack(side=tk.LEFT, padx=2)
        ttk.Button(card_frame, text="Play Item", 
                   command=self.play_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(card_frame, text="Play Supporter", 
                   command=self.play_supporter).pack(side=tk.LEFT, padx=2)
        ttk.Button(card_frame, text="Attach Tool", 
                   command=self.attach_tool).pack(side=tk.LEFT, padx=2)

    def setup_energy_zone(self):
        """Set up energy zone display."""
        energy_frame = ttk.LabelFrame(self.root, text="Energy Zone")
        energy_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.energy_zone_label = ttk.Label(energy_frame, text="Empty")
        self.energy_zone_label.pack(pady=5)

    def setup_log_area(self):
        """Set up the log area for game events."""
        log_frame = ttk.LabelFrame(self.root, text="Game Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Log text area with scrollbar
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_text_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL, 
                                      command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

    def update_display(self):
        """Update the game display with current state."""
        if not self.game_state:
            return
        
        # Update turn and phase
        self.turn_label.config(text=f"Turn: {self.game_state.turn_number} | Phase: {self.game_state.phase}")
        
        # Update points
        self.points_label.config(text=f"Points - Player: {self.game_state.player.points} | Opponent: {self.game_state.opponent.points}")
        
        # Update opponent area
        self.update_opponent_display()
        
        # Update player area
        self.update_player_display()
        
        # Update energy zone
        self.update_energy_zone()
        
        # Update hand
        self.update_hand_display()

    def update_opponent_display(self):
        """Update opponent's board display."""
        # Active Pokémon
        if self.game_state.opponent.active_pokemon:
            active_text = f"{self.game_state.opponent.active_pokemon.name} (HP: {self.game_state.opponent.active_pokemon.hp})"
            self.opponent_active_label.config(text=active_text)
        else:
            self.opponent_active_label.config(text="None")
        
        # Bench
        for i, label in enumerate(self.opponent_bench_labels):
            if i < len(self.game_state.opponent.bench):
                pokemon = self.game_state.opponent.bench[i]
                bench_text = f"{pokemon.name} (HP: {pokemon.hp})"
                label.config(text=bench_text)
            else:
                label.config(text="Empty")
        
        # Hand count
        self.opponent_hand_label.config(text=f"{len(self.game_state.opponent.hand)} cards")

    def update_player_display(self):
        """Update player's board display."""
        # Active Pokémon
        if self.game_state.player.active_pokemon:
            active_text = f"{self.game_state.player.active_pokemon.name} (HP: {self.game_state.player.active_pokemon.hp})"
            self.player_active_label.config(text=active_text)
        else:
            self.player_active_label.config(text="None")
        
        # Bench
        for i, label in enumerate(self.player_bench_labels):
            if i < len(self.game_state.player.bench):
                pokemon = self.game_state.player.bench[i]
                bench_text = f"{pokemon.name} (HP: {pokemon.hp})"
                label.config(text=bench_text)
            else:
                label.config(text="Empty")

    def update_energy_zone(self):
        """Update energy zone display."""
        if self.game_state.player.energy_zone:
            energy_text = f"Energy: {self.game_state.player.energy_zone}"
            self.energy_zone_label.config(text=energy_text)
        else:
            self.energy_zone_label.config(text="Empty")

    def update_hand_display(self):
        """Update hand display."""
        self.hand_listbox.delete(0, tk.END)
        
        for card in self.game_state.player.hand:
            card_text = f"{card.name} ({card.id})"
            self.hand_listbox.insert(tk.END, card_text)

    # Game action methods
    def draw_card(self):
        """Draw a card."""
        if self.game_state and self.game_state.phase == GamePhase.START:
            try:
                self.game_engine.draw_card(self.game_state)
                self.update_display()
                self.log_game_event("Drew a card")
            except Exception as e:
                self.log_game_event(f"Error drawing card: {e}")

    def end_turn(self):
        """End the current turn."""
        if self.game_state:
            try:
                self.game_engine.end_turn(self.game_state)
                self.update_display()
                self.log_game_event("Turn ended")
            except Exception as e:
                self.log_game_event(f"Error ending turn: {e}")

    def play_pokemon(self):
        """Play a Pokémon card from hand."""
        selection = self.hand_listbox.curselection()
        if not selection:
            self.log_game_event("No card selected")
            return
        
        card_index = selection[0]
        card = self.game_state.player.hand[card_index]
        
        # Check if it's a Pokémon card
        if not hasattr(card, 'hp'):
            self.log_game_event(f"{card.name} is not a Pokémon card")
            return
        
        # Check if it's a Basic Pokémon
        if hasattr(card, 'stage') and card.stage != 'Basic':
            self.log_game_event(f"{card.name} is not a Basic Pokémon")
            return
        
        try:
            # Play the Pokémon
            if not self.game_state.player.active_pokemon:
                # Set as active Pokémon
                self.game_state.player.active_pokemon = card
                self.game_state.player.hand.pop(card_index)
                self.log_game_event(f"Set {card.name} as active Pokémon")
            elif len(self.game_state.player.bench) < 3:
                # Add to bench
                self.game_state.player.bench.append(card)
                self.game_state.player.hand.pop(card_index)
                self.log_game_event(f"Added {card.name} to bench")
            else:
                self.log_game_event("Bench is full")
            
            self.update_display()
        except Exception as e:
            self.log_game_event(f"Error playing Pokémon: {e}")

    def play_item(self):
        """Play an item card."""
        selection = self.hand_listbox.curselection()
        if not selection:
            self.log_game_event("No card selected")
            return
        
        card_index = selection[0]
        card = self.game_state.player.hand[card_index]
        
        # Check if it's an item card
        if not hasattr(card, 'card_type') or card.card_type != 'Item':
            self.log_game_event(f"{card.name} is not an item card")
            return
        
        try:
            # Play the item (for now, just discard it)
            self.game_state.player.hand.pop(card_index)
            self.game_state.player.discard_pile.append(card)
            self.log_game_event(f"Played item: {card.name}")
            self.update_display()
        except Exception as e:
            self.log_game_event(f"Error playing item: {e}")

    def play_supporter(self):
        """Play a supporter card."""
        selection = self.hand_listbox.curselection()
        if not selection:
            self.log_game_event("No card selected")
            return
        
        card_index = selection[0]
        card = self.game_state.player.hand[card_index]
        
        # Check if it's a supporter card
        if not hasattr(card, 'card_type') or card.card_type != 'Supporter':
            self.log_game_event(f"{card.name} is not a supporter card")
            return
        
        try:
            # Play the supporter (for now, just discard it)
            self.game_state.player.hand.pop(card_index)
            self.game_state.player.discard_pile.append(card)
            self.log_game_event(f"Played supporter: {card.name}")
            self.update_display()
        except Exception as e:
            self.log_game_event(f"Error playing supporter: {e}")

    def attack(self):
        """Perform an attack."""
        if not self.game_state.player.active_pokemon:
            self.log_game_event("No active Pokémon to attack with")
            return
        
        if not self.game_state.opponent.active_pokemon:
            self.log_game_event("No opponent Pokémon to attack")
            return
        
        try:
            # For now, just log the attack
            attacker = self.game_state.player.active_pokemon
            target = self.game_state.opponent.active_pokemon
            self.log_game_event(f"{attacker.name} attacks {target.name}")
            
            # TODO: Implement actual attack logic
            self.log_game_event("Attack logic not fully implemented yet")
        except Exception as e:
            self.log_game_event(f"Error during attack: {e}")

    def retreat(self):
        """Retreat active Pokémon."""
        if not self.game_state.player.active_pokemon:
            self.log_game_event("No active Pokémon to retreat")
            return
        
        if not self.game_state.player.bench:
            self.log_game_event("No bench Pokémon to retreat to")
            return
        
        try:
            # For now, just swap with first bench Pokémon
            active = self.game_state.player.active_pokemon
            bench_pokemon = self.game_state.player.bench[0]
            
            self.game_state.player.active_pokemon = bench_pokemon
            self.game_state.player.bench[0] = active
            
            self.log_game_event(f"Retreated {active.name} for {bench_pokemon.name}")
            self.update_display()
        except Exception as e:
            self.log_game_event(f"Error during retreat: {e}")

    def evolve_pokemon(self):
        """Evolve a Pokémon."""
        self.log_game_event("Evolve action selected (not implemented yet)")

    def attach_tool(self):
        """Attach a tool card."""
        self.log_game_event("Attach Tool action selected (not implemented yet)")

    def play_card(self, event=None):
        """Play a card from hand."""
        selection = self.hand_listbox.curselection()
        if selection:
            card_index = selection[0]
            card = self.game_state.player.hand[card_index]
            self.log_game_event(f"Selected card: {card.name}")

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
    
    def log_game_event(self, message):
        """Log a game event."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
    
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
