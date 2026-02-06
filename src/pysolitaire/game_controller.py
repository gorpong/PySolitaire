"""Game controller and session management for Solitaire.

This module contains the core game logic, coordinating between
the game state, cursor, selection, and move validation without
any UI concerns.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from pysolitaire.config import GameConfig
from pysolitaire.cursor import Cursor, CursorZone
from pysolitaire.dealing import deal_game
from pysolitaire.model import Card, GameState
from pysolitaire.moves import (
    MoveResult,
    bury_top_of_stock,
    draw_from_stock,
    move_foundation_to_tableau,
    move_tableau_to_foundation,
    move_tableau_to_tableau,
    move_waste_to_foundation,
    move_waste_to_tableau,
    recycle_waste_to_stock,
)
from pysolitaire.rules import (
    can_pick_from_tableau,
    can_pick_from_waste,
    get_valid_foundation_destinations,
    get_valid_tableau_destinations,
)
from pysolitaire.selection import HighlightedDestinations, Selection
from pysolitaire.timer import GameTimer
from pysolitaire.undo import UndoStack, restore_state, save_state


@dataclass
class GameSession:
    """All mutable state for a game session.
    
    Attributes:
        state: The current game state (cards in all piles).
        cursor: Current cursor position on the board.
        selection: Currently selected cards, if any.
        move_count: Number of moves made this game.
        message: Status message to display to the user.
        highlighted: Valid destinations to highlight, if any.
        made_progress_since_last_recycle: Tracks whether any move was made
            since the last stock recycle, for stall detection.
        consecutive_burials: Count of consecutive bury operations in Draw-3,
            used to limit stall recovery attempts.
    """
    state: GameState
    cursor: Cursor
    selection: Optional[Selection] = None
    move_count: int = 0
    message: str = ""
    highlighted: Optional[HighlightedDestinations] = None
    made_progress_since_last_recycle: bool = True
    consecutive_burials: int = 0


class GameController:
    """Coordinates game logic without UI concerns.
    
    Manages the game session, processes player actions, and tracks
    game state for undo, win detection, and stall detection.
    
    Attributes:
        config: Game configuration settings.
        session: Current game session state.
        timer: Game timer for tracking elapsed time.
    """

    def __init__(self, config: GameConfig):
        self.config = config
        self._undo_stack = UndoStack()
        self.timer = GameTimer()
        self._init_session()

    def _init_session(self) -> None:
        """Initialize a new game session."""
        self.session = GameSession(
            state=deal_game(self.config.seed),
            cursor=Cursor(),
            message="Welcome to Solitaire! Use arrows to move, Enter to select.",
        )

    @property
    def _state(self) -> GameState:
        """Shortcut to session state."""
        return self.session.state

    @property
    def _cursor(self) -> Cursor:
        """Shortcut to session cursor."""
        return self.session.cursor

    def start_game(self) -> None:
        """Start the game timer."""
        self.timer.start()

    def pause_timer(self) -> None:
        """Pause the game timer."""
        self.timer.pause()

    def resume_timer(self) -> None:
        """Resume the game timer."""
        self.timer.resume()

    def get_elapsed_time(self) -> float:
        """Get elapsed game time in seconds."""
        return self.timer.get_elapsed()

    def new_game(self, seed: Optional[int] = None) -> None:
        """Start a new game, resetting all state."""
        self.timer.reset()
        self._undo_stack.clear()
        self.session = GameSession(
            state=deal_game(seed),
            cursor=Cursor(),
            message="New game started!",
        )

    def try_select(self) -> bool:
        """Try to select card(s) at cursor position.
        
        Returns True if selection succeeded or stock action was triggered.
        """
        if self._cursor.zone == CursorZone.STOCK:
            result = self.handle_stock_action()
            return result.success

        if self._cursor.zone == CursorZone.WASTE:
            if can_pick_from_waste(self._state):
                self.session.selection = Selection(
                    zone=CursorZone.WASTE,
                    pile_index=0,
                    card_index=0,
                )
                self.session.message = "Card selected. Press Tab to see placements, or move and Enter to place."
                return True
            else:
                self.session.message = "Waste is empty!"
                return False

        if self._cursor.zone == CursorZone.FOUNDATION:
            pile = self._state.foundations[self._cursor.pile_index]
            if pile:
                self.session.selection = Selection(
                    zone=CursorZone.FOUNDATION,
                    pile_index=self._cursor.pile_index,
                    card_index=0,
                )
                self.session.message = "Foundation card selected. Press Tab to see placements."
                return True
            else:
                self.session.message = "Foundation is empty!"
                return False

        if self._cursor.zone == CursorZone.TABLEAU:
            pile = self._state.tableau[self._cursor.pile_index]
            if not pile:
                self.session.message = "Tableau pile is empty!"
                return False

            if can_pick_from_tableau(pile, self._cursor.card_index):
                self.session.selection = Selection(
                    zone=CursorZone.TABLEAU,
                    pile_index=self._cursor.pile_index,
                    card_index=self._cursor.card_index,
                )
                num_cards = len(pile) - self._cursor.card_index
                if num_cards > 1:
                    self.session.message = f"{num_cards} cards selected. Press Tab to see placements."
                else:
                    self.session.message = "Card selected. Press Tab to see placements."
                return True
            else:
                self.session.message = "Cannot select face-down card!"
                return False

        return False

    def cancel_selection(self) -> None:
        """Cancel the current selection."""
        if self.session.selection:
            self.session.selection = None
            self.session.message = "Selection cancelled."
        else:
            self.session.message = ""

    def try_place(self) -> bool:
        """Try to place selected card(s) at cursor position.
        
        Returns True if placement succeeded, False otherwise.
        Placing on the same pile cancels selection and returns False.
        """
        if self.session.selection is None:
            return False

        if (self._cursor.zone == self.session.selection.zone and
            self._cursor.pile_index == self.session.selection.pile_index):
            self.cancel_selection()
            return False

        if self._cursor.zone == CursorZone.STOCK:
            self.session.message = "Cannot place cards on stock!"
            return False

        if self._cursor.zone == CursorZone.WASTE:
            self.session.message = "Cannot place cards on waste!"
            return False

        if self._cursor.zone == CursorZone.FOUNDATION:
            return self._move_to_foundation(self._cursor.pile_index)

        if self._cursor.zone == CursorZone.TABLEAU:
            return self._move_to_tableau(self._cursor.pile_index)

        return False

    def _save_for_undo(self) -> None:
        """Save current state for undo."""
        self._undo_stack.push(save_state(self._state))

    def _move_to_foundation(self, dest_foundation: int) -> bool:
        """Move selected card to foundation."""
        self._save_for_undo()

        if self.session.selection is None:
            result = MoveResult(False, "Invalid source")
        elif self.session.selection.zone == CursorZone.WASTE:
            result = move_waste_to_foundation(self._state, dest_foundation)
        elif self.session.selection.zone == CursorZone.TABLEAU:
            pile = self._state.tableau[self.session.selection.pile_index]
            if len(pile) - self.session.selection.card_index > 1:
                self._undo_stack.pop()
                self.session.message = "Can only move single card to foundation!"
                return False
            result = move_tableau_to_foundation(
                self._state, self.session.selection.pile_index, dest_foundation
            )
        elif self.session.selection.zone == CursorZone.FOUNDATION:
            self._undo_stack.pop()
            self.session.message = "Cannot move foundation to foundation!"
            return False

        if result.success:
            self._record_successful_move()
            self.session.message = "Moved to foundation!"
            self.session.selection = None
            return True
        else:
            self._undo_stack.pop()
            self.session.message = f"Invalid move: {result.message}"
            return False

    def _move_to_tableau(self, dest_pile: int) -> bool:
        """Move selected card(s) to tableau."""
        self._save_for_undo()

        if self.session.selection is None:
            result = MoveResult(False, "Invalid source")
        elif self.session.selection.zone == CursorZone.WASTE:
            result = move_waste_to_tableau(self._state, dest_pile)
        elif self.session.selection.zone == CursorZone.TABLEAU:
            result = move_tableau_to_tableau(
                self._state,
                self.session.selection.pile_index,
                self.session.selection.card_index,
                dest_pile,
            )
        elif self.session.selection.zone == CursorZone.FOUNDATION:
            result = move_foundation_to_tableau(
                self._state, self.session.selection.pile_index, dest_pile
            )
        else:
            result = MoveResult(False, "Invalid source")

        if result.success:
            self._record_successful_move()
            self.session.message = "Moved!"
            self.session.selection = None
            return True
        else:
            self._undo_stack.pop()
            self.session.message = f"Invalid move: {result.message}"
            return False

    def _record_successful_move(self) -> None:
        """Update session state after a successful move."""
        self.session.move_count += 1
        self.session.made_progress_since_last_recycle = True
        self.session.consecutive_burials = 0

    def handle_stock_action(self) -> MoveResult:
        """Handle drawing from stock or recycling waste.
        
        Returns MoveResult indicating success/failure.
        Does not handle stall detection prompts - caller should check
        needs_bury_prompt() and is_stalled() separately.
        """
        if self._state.stock:
            self._save_for_undo()
            result = draw_from_stock(self._state, self.config.draw_count)
            if result.success:
                self.session.move_count += 1
                drawn = min(self.config.draw_count, len(self._state.waste))
                self.session.message = f"Drew {drawn} card(s) from stock."
            return result
        elif self._state.waste:
            self._save_for_undo()
            result = recycle_waste_to_stock(self._state)
            if result.success:
                self.session.made_progress_since_last_recycle = False
                self.session.message = "Recycled waste to stock."
            return result
        else:
            self.session.message = "Both stock and waste are empty!"
            return MoveResult(False, "Both stock and waste are empty")

    def needs_bury_prompt(self) -> bool:
        """Check if player should be prompted to bury a card.
        
        Only applies to Draw-3 mode when no progress was made.
        """
        if self.config.draw_count != 3:
            return False
        if self.session.made_progress_since_last_recycle:
            return False
        if not self._state.waste or self._state.stock:
            return False
        if self.session.consecutive_burials >= 2:
            return False
        return True

    def is_stalled(self) -> bool:
        """Check if the game is stalled with no legal moves.
        
        Returns True if player has cycled through stock with no progress.
        """
        if self.session.made_progress_since_last_recycle:
            return False
        if self._state.stock:
            return False
        if not self._state.waste:
            return False
        
        if self.config.draw_count == 1:
            return True
        
        return self.session.consecutive_burials >= 2

    def execute_bury(self) -> None:
        """Bury the top stock card and increment burial counter."""
        bury_top_of_stock(self._state)
        self.session.consecutive_burials += 1

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._undo_stack.can_undo()

    def undo(self) -> bool:
        """Undo the last move.
        
        Returns True if undo succeeded.
        """
        if not self._undo_stack.can_undo():
            self.session.message = "Nothing to undo!"
            return False

        saved = self._undo_stack.pop()
        if saved:
            restore_state(self._state, saved)
            self.session.move_count = max(0, self.session.move_count - 1)
            self.session.selection = None
            self.session.message = "Undone!"
            return True

        return False

    def check_win(self) -> bool:
        """Check if the player has won."""
        total_in_foundations = sum(len(pile) for pile in self._state.foundations)
        return total_in_foundations == 52

    def compute_valid_destinations(self) -> Optional[HighlightedDestinations]:
        """Compute valid placement destinations for current card.
        
        Uses selection if present, otherwise card under cursor.
        Returns None if no card or no valid destinations.
        """
        if self.session.selection:
            card = self.get_selected_card()
        else:
            card = self.get_card_under_cursor()

        if card is None:
            self.session.message = "No card to show placements for!"
            return None

        tableau_dests = get_valid_tableau_destinations(card, self._state)
        foundation_dests = get_valid_foundation_destinations(card, self._state)

        if self.session.selection and self.session.selection.zone == CursorZone.TABLEAU:
            pile = self._state.tableau[self.session.selection.pile_index]
            if len(pile) - self.session.selection.card_index > 1:
                foundation_dests = []

        if not tableau_dests and not foundation_dests:
            self.session.message = "No valid placements for this card!"
            return None

        highlights = HighlightedDestinations(
            tableau_piles=set(tableau_dests),
            foundation_piles=set(foundation_dests),
        )
        self.session.message = f"{highlights.count()} valid placement(s) highlighted."
        return highlights

    def get_card_under_cursor(self) -> Optional[Card]:
        """Get the card currently under the cursor."""
        if self._cursor.zone == CursorZone.STOCK:
            return None
        elif self._cursor.zone == CursorZone.WASTE:
            return self._state.waste[-1] if self._state.waste else None
        elif self._cursor.zone == CursorZone.FOUNDATION:
            pile = self._state.foundations[self._cursor.pile_index]
            return pile[-1] if pile else None
        elif self._cursor.zone == CursorZone.TABLEAU:
            pile = self._state.tableau[self._cursor.pile_index]
            if pile and self._cursor.card_index < len(pile):
                card = pile[self._cursor.card_index]
                return card if card.face_up else None
        return None

    def get_selected_card(self) -> Optional[Card]:
        """Get the top card of current selection."""
        if self.session.selection is None:
            return None

        if self.session.selection.zone == CursorZone.WASTE:
            return self._state.waste[-1] if self._state.waste else None
        elif self.session.selection.zone == CursorZone.FOUNDATION:
            pile = self._state.foundations[self.session.selection.pile_index]
            return pile[-1] if pile else None
        elif self.session.selection.zone == CursorZone.TABLEAU:
            pile = self._state.tableau[self.session.selection.pile_index]
            if pile and self.session.selection.card_index < len(pile):
                return pile[self.session.selection.card_index]
        return None

    def describe_selection(self) -> str:
        """Describe the current selection for display."""
        if self.session.selection is None:
            return ""

        card = self.get_selected_card()
        if card is None:
            return "?"

        if self.session.selection.zone == CursorZone.TABLEAU:
            pile = self._state.tableau[self.session.selection.pile_index]
            num_cards = len(pile) - self.session.selection.card_index
            if num_cards > 1:
                return f"{card} + {num_cards - 1} more"

        return str(card)

    def save_to_dict(self) -> Dict[str, Any]:
        """Save game state to a dictionary for persistence."""
        return {
            'state': self._state,
            'move_count': self.session.move_count,
            'elapsed_time': self.timer.get_elapsed(),
            'made_progress_since_last_recycle': self.session.made_progress_since_last_recycle,
            'consecutive_burials': self.session.consecutive_burials,
        }

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Load game state from a dictionary."""
        self.session.state = data['state']
        self.session.move_count = data['move_count']
        self.session.made_progress_since_last_recycle = data['made_progress_since_last_recycle']
        self.session.consecutive_burials = data['consecutive_burials']
        self.timer.set_elapsed(data['elapsed_time'])
