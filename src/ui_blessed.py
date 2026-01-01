"""Blessed terminal UI for Solitaire."""

import sys
import time
from typing import Optional, List, Set, Tuple, Dict, Any
from dataclasses import dataclass
from blessed import Terminal

from src.model import Card, Suit, Rank, GameState
from src.dealing import deal_game
from src.cursor import Cursor, CursorZone
from src.moves import (
    move_tableau_to_tableau,
    move_waste_to_tableau,
    move_waste_to_foundation,
    move_tableau_to_foundation,
    move_foundation_to_tableau,
    draw_from_stock,
    recycle_waste_to_stock,
    MoveResult,
)
from src.rules import (
    can_pick_from_tableau,
    can_pick_from_waste,
    get_valid_tableau_destinations,
    get_valid_foundation_destinations,
)
from src.renderer import (
    render_board,
    BOARD_WIDTH,
    BOARD_HEIGHT,
)
from src.undo import UndoStack, save_state, restore_state
from src.leaderboard import Leaderboard
from src.save_state import SaveStateManager
from src.overlays import (
    format_time,
    render_help_lines,
    render_resume_prompt_lines,
    render_leaderboard_overlay_lines,
    render_win_leaderboard_lines,
    render_initials_prompt,
)


# Minimum terminal size requirements
MIN_TERM_WIDTH = 100
MIN_TERM_HEIGHT = 40


@dataclass
class Selection:
    """Represents currently selected cards."""
    zone: CursorZone
    pile_index: int = 0
    card_index: int = 0  # For tableau: starting card of the run


@dataclass
class HighlightedDestinations:
    """Valid destinations to highlight."""
    tableau_piles: Set[int]  # Set of tableau pile indices (0-6)
    foundation_piles: Set[int]  # Set of foundation pile indices (0-3)


class SolitaireUI:
    """Main UI class for terminal Solitaire game."""

    def __init__(self, seed: Optional[int] = None, draw_count: int = 1):
        self.term = Terminal()
        self.state = deal_game(seed)
        self.cursor = Cursor()
        self.selection: Optional[Selection] = None
        self.draw_count = draw_count
        self.message = "Welcome to Solitaire! Use arrows to move, Enter to select."
        self.move_count = 0
        self.running = True
        self.show_help = False
        self.undo_stack = UndoStack()
        self.stock_pass_count = 0
        self.needs_redraw = True  # Track if redraw is needed
        self.highlighted: Optional[HighlightedDestinations] = None  # Valid destinations to show
        # Timer tracking
        self.start_time = time.time()
        self.elapsed_time = 0.0  # Total elapsed game time
        self.paused = False
        self.pause_start = 0.0
        # Leaderboard and save state
        self.leaderboard = Leaderboard()
        self.save_manager = SaveStateManager()
        self.show_leaderboard = False

    def _check_terminal_size(self) -> bool:
        """Check if terminal is large enough. Returns True if OK."""
        width = self.term.width or 80
        height = self.term.height or 24
        if width < MIN_TERM_WIDTH or height < MIN_TERM_HEIGHT:
            print(f"\nError: Terminal too small!")
            print(f"  Current size: {width}x{height}")
            print(f"  Required minimum: {MIN_TERM_WIDTH}x{MIN_TERM_HEIGHT}")
            print(f"\nPlease resize your terminal and try again.")
            return False
        return True

    def _pause_timer(self) -> None:
        """Pause the game timer."""
        if not self.paused:
            self.paused = True
            self.pause_start = time.time()

    def _resume_timer(self) -> None:
        """Resume the game timer."""
        if self.paused:
            self.paused = False
            # Add paused duration to start time to maintain accurate elapsed time
            pause_duration = time.time() - self.pause_start
            self.start_time += pause_duration

    def _get_elapsed_time(self) -> float:
        """Get current elapsed time in seconds."""
        if self.paused:
            return self.pause_start - self.start_time
        return time.time() - self.start_time

    def _format_time(self, seconds: float) -> str:
        """Format elapsed time as MM:SS."""
        return format_time(seconds)

    def _load_saved_game(self, saved_data: Dict[str, Any]) -> None:
        """Load saved game data into current game state."""
        self.state = saved_data['state']
        self.move_count = saved_data['move_count']
        self.stock_pass_count = saved_data['stock_pass_count']
        # Restore timer
        saved_elapsed = saved_data['elapsed_time']
        self.start_time = time.time() - saved_elapsed
        self.paused = False
        self.pause_start = 0.0

    def _prompt_resume_game(self, move_count: int, elapsed_time: float) -> bool:
        """Prompt user to resume saved game or start new.

        Args:
            move_count: Number of moves in the saved game.
            elapsed_time: Elapsed time in seconds in the saved game.

        Returns True to resume, False to start new.
        """
        frame = self.term.home + self.term.clear
        term_width = self.term.width or BOARD_WIDTH
        start_x = max(0, (term_width - 60) // 2)
        start_y = 10

        prompt_lines = render_resume_prompt_lines(move_count, elapsed_time)

        for i, line in enumerate(prompt_lines):
            frame += self.term.move_xy(start_x, start_y + i) + self.term.bright_white(line)

        print(frame, end='', flush=True)

        while True:
            key = self.term.inkey()
            if key.lower() == 'r':
                return True
            elif key.lower() == 'n':
                return False

    def run(self) -> None:
        """Main game loop."""
        if not self._check_terminal_size():
            sys.exit(1)

        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            # Check for saved game
            if self.save_manager.has_save():
                saved_data = self.save_manager.load_game()
                if saved_data:
                    if self._prompt_resume_game(saved_data['move_count'], saved_data['elapsed_time']):
                        self._load_saved_game(saved_data)
                        self.message = "Game resumed!"
                        # Delete save file after loading
                        self.save_manager.delete_save()
                    else:
                        # Start new game, delete save
                        self.save_manager.delete_save()
                        self.message = "New game started!"
                    self.needs_redraw = True

            while self.running:
                if self.needs_redraw:
                    self._render()
                    self.needs_redraw = False
                else:
                    # Periodically update to refresh timer even without input
                    self._render()
                self._handle_input()

    def _render(self) -> None:
        """Render the game board."""
        # Build output buffer instead of printing directly
        output_lines = []

        # Render the board
        highlighted_tableau = self.highlighted.tableau_piles if self.highlighted else None
        highlighted_foundations = self.highlighted.foundation_piles if self.highlighted else None
        canvas = render_board(
            self.state,
            cursor_zone=self.cursor.zone.value,
            cursor_index=self.cursor.pile_index,
            cursor_card_index=self.cursor.card_index,
            highlighted_tableau=highlighted_tableau,
            highlighted_foundations=highlighted_foundations,
        )

        # Apply colors to canvas
        for row in canvas:
            line = ''.join(row)
            line = self._colorize_line(line)
            output_lines.append(line)

        # Center the board
        term_width = self.term.width or BOARD_WIDTH
        pad_left = max(0, (term_width - BOARD_WIDTH) // 2)
        padding = ' ' * pad_left

        # Build complete frame
        frame = self.term.home + self.term.clear

        for y, line in enumerate(output_lines):
            frame += self.term.move_xy(0, y) + padding + line

        # Draw status bar
        status_y = BOARD_HEIGHT
        elapsed = self._get_elapsed_time()
        time_text = self._format_time(elapsed)
        move_text = f"Moves: {self.move_count}"
        timer_text = f"Time: {time_text}"
        # Display moves and timer on same line
        status_line = f"{move_text}    {timer_text}"
        frame += self.term.move_xy(pad_left + 2, status_y - 4) + self.term.bright_white(status_line)

        # Message line
        msg_color = self.term.bright_yellow if "!" in self.message or "Invalid" in self.message else self.term.bright_cyan
        # Clear the message line first
        frame += self.term.move_xy(pad_left + 2, status_y - 2) + ' ' * (BOARD_WIDTH - 4)
        frame += self.term.move_xy(pad_left + 2, status_y - 2) + msg_color(self.message[:BOARD_WIDTH - 4])

        # Selection indicator
        frame += self.term.move_xy(pad_left + 2, status_y - 1) + ' ' * (BOARD_WIDTH - 4)
        if self.selection:
            sel_text = f"Selected: {self._describe_selection()}"
            frame += self.term.move_xy(pad_left + 2, status_y - 1) + self.term.bright_green(sel_text)

        # Help overlay
        if self.show_help:
            frame += self._render_help_str(pad_left)

        # Output entire frame at once
        print(frame, end='', flush=True)

    def _colorize_line(self, line: str) -> str:
        """Add color to a line including suit symbols and cursor."""
        result = ""
        i = 0
        while i < len(line):
            char = line[i]
            if char in "♥♦":
                result += self.term.bright_red(char)
            elif char in "♣♠":
                result += self.term.white(char)
            elif char == "[":
                result += self.term.bright_cyan_on_blue(char)
            elif char == "]":
                result += self.term.bright_cyan_on_blue(char)
            elif char == "*":
                # Highlight marker for valid destinations
                result += self.term.bright_yellow_on_green(char)
            elif char == "░":
                result += self.term.blue(char)
            else:
                result += char
            i += 1
        return result

    def _render_help_str(self, pad_left: int) -> str:
        """Build help overlay string."""
        help_lines = render_help_lines()
        start_y = 8
        start_x = pad_left + (BOARD_WIDTH - 40) // 2
        result = ""
        for i, help_line in enumerate(help_lines):
            result += self.term.move_xy(start_x, start_y + i) + self.term.black_on_bright_white(help_line)
        return result

    def _handle_input(self) -> None:
        """Handle keyboard input."""
        key = self.term.inkey(timeout=1)  # Wait up to 1 second for input

        if not key:
            return

        # Clear highlighting on any input
        if self.highlighted:
            self.highlighted = None
            self.needs_redraw = True

        # Clear previous non-error message
        if "Invalid" not in self.message and "Cannot" not in self.message:
            self.message = ""

        if key.name == 'KEY_UP':
            self.cursor.move_up(self.state)
            self.needs_redraw = True
        elif key.name == 'KEY_DOWN':
            self.cursor.move_down(self.state)
            self.needs_redraw = True
        elif key.name == 'KEY_LEFT':
            self.cursor.move_left(self.state)
            self.needs_redraw = True
        elif key.name == 'KEY_RIGHT':
            self.cursor.move_right(self.state)
            self.needs_redraw = True
        elif key.name == 'KEY_ENTER' or key == '\n':
            self._handle_enter()
            self.needs_redraw = True
        elif key.name == 'KEY_TAB' or key == '\t':
            self._handle_tab()
            self.needs_redraw = True
        elif key == ' ':
            self._handle_space()
            self.needs_redraw = True
        elif key.name == 'KEY_ESCAPE':
            self._cancel_selection()
            self.needs_redraw = True
        elif key.lower() == 'q':
            self._handle_quit()
        elif key.lower() == 'h' or key == '?':
            if self.show_help:
                self._resume_timer()
            else:
                self._pause_timer()
            self.show_help = not self.show_help
            self.needs_redraw = True
        elif key.lower() == 'r':
            self._handle_restart()
        elif key.lower() == 'u':
            self._handle_undo()
            self.needs_redraw = True
        elif key.lower() == 'l':
            self._show_leaderboard_ingame()

    def _handle_enter(self) -> None:
        """Handle Enter key - select or place."""
        if self.selection is None:
            self._try_select()
        else:
            self._try_place()

    def _handle_tab(self) -> None:
        """Handle Tab key - show valid placements."""
        card = None

        if self.selection:
            # Show placements for selected card
            card = self._get_selected_card()
        else:
            # Show placements for card under cursor
            card = self._get_card_under_cursor()

        if card is None:
            self.message = "No card to show placements for!"
            return

        # Find valid destinations
        tableau_dests = get_valid_tableau_destinations(card, self.state)
        foundation_dests = get_valid_foundation_destinations(card, self.state)

        # For runs (multiple cards), can't go to foundation
        if self.selection and self.selection.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.selection.pile_index]
            if len(pile) - self.selection.card_index > 1:
                foundation_dests = []

        if not tableau_dests and not foundation_dests:
            self.message = "No valid placements for this card!"
            return

        self.highlighted = HighlightedDestinations(
            tableau_piles=set(tableau_dests),
            foundation_piles=set(foundation_dests),
        )

        dest_count = len(tableau_dests) + len(foundation_dests)
        self.message = f"{dest_count} valid placement(s) highlighted."

    def _get_card_under_cursor(self) -> Optional[Card]:
        """Get the card currently under the cursor."""
        if self.cursor.zone == CursorZone.STOCK:
            return None  # Stock cards aren't visible
        elif self.cursor.zone == CursorZone.WASTE:
            return self.state.waste[-1] if self.state.waste else None
        elif self.cursor.zone == CursorZone.FOUNDATION:
            pile = self.state.foundations[self.cursor.pile_index]
            return pile[-1] if pile else None
        elif self.cursor.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.cursor.pile_index]
            if pile and self.cursor.card_index < len(pile):
                card = pile[self.cursor.card_index]
                return card if card.face_up else None
        return None

    def _try_select(self) -> None:
        """Try to select card(s) at cursor position."""
        if self.cursor.zone == CursorZone.STOCK:
            self._handle_space()
            return

        if self.cursor.zone == CursorZone.WASTE:
            if can_pick_from_waste(self.state):
                self.selection = Selection(
                    zone=CursorZone.WASTE,
                    pile_index=0,
                    card_index=0,
                )
                self.message = "Card selected. Press Tab to see placements, or move and Enter to place."
            else:
                self.message = "Waste is empty!"
            return

        if self.cursor.zone == CursorZone.FOUNDATION:
            pile = self.state.foundations[self.cursor.pile_index]
            if pile:
                self.selection = Selection(
                    zone=CursorZone.FOUNDATION,
                    pile_index=self.cursor.pile_index,
                    card_index=0,
                )
                self.message = "Foundation card selected. Press Tab to see placements."
            else:
                self.message = "Foundation is empty!"
            return

        if self.cursor.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.cursor.pile_index]
            if not pile:
                self.message = "Tableau pile is empty!"
                return

            if can_pick_from_tableau(pile, self.cursor.card_index):
                self.selection = Selection(
                    zone=CursorZone.TABLEAU,
                    pile_index=self.cursor.pile_index,
                    card_index=self.cursor.card_index,
                )
                num_cards = len(pile) - self.cursor.card_index
                if num_cards > 1:
                    self.message = f"{num_cards} cards selected. Press Tab to see placements."
                else:
                    self.message = "Card selected. Press Tab to see placements."
            else:
                self.message = "Cannot select face-down card!"

    def _try_place(self) -> None:
        """Try to place selected card(s) at cursor position."""
        if self.selection is None:
            return

        # Cancel if selecting same location
        if (self.cursor.zone == self.selection.zone and
            self.cursor.pile_index == self.selection.pile_index):
            self._cancel_selection()
            return

        if self.cursor.zone == CursorZone.STOCK:
            self.message = "Cannot place cards on stock!"
            return

        if self.cursor.zone == CursorZone.WASTE:
            self.message = "Cannot place cards on waste!"
            return

        if self.cursor.zone == CursorZone.FOUNDATION:
            self._move_to_foundation(self.cursor.pile_index)
            return

        if self.cursor.zone == CursorZone.TABLEAU:
            self._move_to_tableau(self.cursor.pile_index)
            return

    def _save_for_undo(self) -> None:
        """Save current state for undo."""
        self.undo_stack.push(save_state(self.state))

    def _handle_undo(self) -> None:
        """Handle undo request."""
        if not self.undo_stack.can_undo():
            self.message = "Nothing to undo!"
            return

        saved = self.undo_stack.pop()
        if saved:
            restore_state(self.state, saved)
            self.move_count = max(0, self.move_count - 1)
            self.selection = None
            self.message = "Undone!"

    def _move_to_foundation(self, dest_foundation: int) -> None:
        """Move selected card to foundation."""
        result: MoveResult

        self._save_for_undo()

        if self.selection.zone == CursorZone.WASTE:
            result = move_waste_to_foundation(self.state, dest_foundation)
        elif self.selection.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.selection.pile_index]
            if len(pile) - self.selection.card_index > 1:
                self.undo_stack.pop()
                self.message = "Can only move single card to foundation!"
                return
            result = move_tableau_to_foundation(self.state, self.selection.pile_index, dest_foundation)
        elif self.selection.zone == CursorZone.FOUNDATION:
            self.undo_stack.pop()
            self.message = "Cannot move foundation to foundation!"
            return
        else:
            result = MoveResult(False, "Invalid source")

        if result.success:
            self.move_count += 1
            self.stock_pass_count = 0
            self.message = "Moved to foundation!"
            self.selection = None
            self._check_win()
        else:
            self.undo_stack.pop()
            self.message = f"Invalid move: {result.message}"

    def _move_to_tableau(self, dest_pile: int) -> None:
        """Move selected card(s) to tableau."""
        result: MoveResult

        self._save_for_undo()

        if self.selection.zone == CursorZone.WASTE:
            result = move_waste_to_tableau(self.state, dest_pile)
        elif self.selection.zone == CursorZone.TABLEAU:
            result = move_tableau_to_tableau(
                self.state,
                self.selection.pile_index,
                self.selection.card_index,
                dest_pile
            )
        elif self.selection.zone == CursorZone.FOUNDATION:
            result = move_foundation_to_tableau(self.state, self.selection.pile_index, dest_pile)
        else:
            result = MoveResult(False, "Invalid source")

        if result.success:
            self.move_count += 1
            self.stock_pass_count = 0
            self.message = "Moved!"
            self.selection = None
        else:
            self.undo_stack.pop()
            self.message = f"Invalid move: {result.message}"

    def _handle_space(self) -> None:
        """Handle space bar - draw from stock."""
        if self.state.stock:
            self._save_for_undo()
            result = draw_from_stock(self.state, self.draw_count)
            if result.success:
                self.move_count += 1
                drawn = min(self.draw_count, len(self.state.waste))
                self.message = f"Drew {drawn} card(s) from stock."
        elif self.state.waste:
            self._save_for_undo()
            result = recycle_waste_to_stock(self.state)
            if result.success:
                self.stock_pass_count += 1
                self.message = "Recycled waste to stock."
                if self.draw_count == 1 and self.stock_pass_count >= 2:
                    self._check_loss()
        else:
            self.message = "Both stock and waste are empty!"

    def _check_loss(self) -> None:
        """Check if player has lost (Draw-1 mode: no moves after full pass)."""
        self.message = "No progress made. Game may be unwinnable. Press R to restart or keep trying."

    def _cancel_selection(self) -> None:
        """Cancel current selection."""
        if self.selection:
            self.selection = None
            self.message = "Selection cancelled."
        else:
            self.message = ""

    def _handle_quit(self) -> None:
        """Handle quit request."""
        self._pause_timer()
        self.message = "Press Q again to confirm quit, any other key to cancel."
        self.needs_redraw = True
        self._render()
        key = self.term.inkey()
        if key.lower() == 'q':
            # Save game state before quitting
            elapsed = self._get_elapsed_time()
            self.save_manager.save_game(
                self.state,
                self.move_count,
                elapsed,
                self.draw_count,
                self.stock_pass_count,
            )
            self.running = False
        else:
            self._resume_timer()
            self.message = "Quit cancelled."
            self.needs_redraw = True

    def _handle_restart(self) -> None:
        """Handle restart request."""
        self._pause_timer()
        self.message = "Press R again to restart, any other key to cancel."
        self.needs_redraw = True
        self._render()
        key = self.term.inkey()
        if key.lower() == 'r':
            # Reset timer on restart
            self.start_time = time.time()
            self.paused = False
            self.pause_start = 0.0
            self.state = deal_game()
            self.cursor = Cursor()
            self.selection = None
            self.move_count = 0
            self.undo_stack.clear()
            self.stock_pass_count = 0
            self.message = "New game started!"
        else:
            self._resume_timer()
            self.message = "Restart cancelled."
        self.needs_redraw = True

    def _check_win(self) -> None:
        """Check if the player has won."""
        total_in_foundations = sum(len(pile) for pile in self.state.foundations)
        if total_in_foundations == 52:
            self._pause_timer()
            elapsed = int(self._get_elapsed_time())

            # Delete save file since game is complete
            self.save_manager.delete_save()

            # Show win message
            self.message = f"CONGRATULATIONS! You won in {self.move_count} moves and {self._format_time(elapsed)}!"
            self.needs_redraw = True
            self._render()

            # Prompt for initials
            initials = self._prompt_initials()

            # Add to leaderboard
            position = self.leaderboard.add_entry(initials, self.move_count, elapsed, self.draw_count)

            # Show leaderboard with their entry
            self._show_leaderboard_after_win(position)

            self.running = False

    def _prompt_initials(self) -> str:
        """Prompt user to enter 3-letter initials.

        Returns the initials (3 chars, uppercase), or "N/A" if cancelled.
        """
        initials = ""

        while len(initials) < 3:
            # Render current state
            frame = self.term.home + self.term.clear

            # Draw the board
            highlighted_tableau = self.highlighted.tableau_piles if self.highlighted else None
            highlighted_foundations = self.highlighted.foundation_piles if self.highlighted else None
            canvas = render_board(
                self.state,
                cursor_zone=self.cursor.zone.value,
                cursor_index=self.cursor.pile_index,
                cursor_card_index=self.cursor.card_index,
                highlighted_tableau=highlighted_tableau,
                highlighted_foundations=highlighted_foundations,
            )

            output_lines = []
            for row in canvas:
                line = ''.join(row)
                line = self._colorize_line(line)
                output_lines.append(line)

            term_width = self.term.width or BOARD_WIDTH
            pad_left = max(0, (term_width - BOARD_WIDTH) // 2)
            padding = ' ' * pad_left

            for y, line in enumerate(output_lines):
                frame += self.term.move_xy(0, y) + padding + line

            # Draw initials prompt
            status_y = BOARD_HEIGHT
            prompt_display = render_initials_prompt(initials)
            frame += self.term.move_xy(pad_left + 2, status_y - 2) + self.term.bright_cyan(prompt_display)

            print(frame, end='', flush=True)

            # Get input
            key = self.term.inkey()

            if key.name == 'KEY_ESCAPE':
                return "N/A"
            elif key.name == 'KEY_BACKSPACE' or key.name == 'KEY_DELETE':
                if initials:
                    initials = initials[:-1]
            elif key.isalpha() and len(key) == 1:
                initials += key.upper()

        return initials

    def _show_leaderboard_after_win(self, position: int) -> None:
        """Show leaderboard after winning, highlighting the player's position."""
        lines = self.leaderboard.format_leaderboard(self.draw_count)

        # Add position message if in top 20
        if position > 0:
            msg = f"You placed #{position} on the leaderboard!"
        else:
            msg = "You didn't make the top 20, but great job!"

        # Render leaderboard
        frame = self.term.home + self.term.clear

        term_width = self.term.width or BOARD_WIDTH
        start_x = max(0, (term_width - 40) // 2)
        start_y = 5

        for i, line in enumerate(lines):
            frame += self.term.move_xy(start_x, start_y + i) + self.term.bright_white(line)

        # Show message
        frame += self.term.move_xy(start_x, start_y + len(lines) + 2) + self.term.bright_yellow(msg)
        frame += self.term.move_xy(start_x, start_y + len(lines) + 4) + self.term.bright_cyan("Press any key to exit.")

        print(frame, end='', flush=True)
        self.term.inkey()

    def _show_leaderboard_ingame(self) -> None:
        """Show leaderboard overlay during game (L key)."""
        self._pause_timer()

        lines = self.leaderboard.format_leaderboard(self.draw_count)

        # Render overlay
        frame = self.term.home + self.term.clear

        # First render the game board in background
        highlighted_tableau = self.highlighted.tableau_piles if self.highlighted else None
        highlighted_foundations = self.highlighted.foundation_piles if self.highlighted else None
        canvas = render_board(
            self.state,
            cursor_zone=self.cursor.zone.value,
            cursor_index=self.cursor.pile_index,
            cursor_card_index=self.cursor.card_index,
            highlighted_tableau=highlighted_tableau,
            highlighted_foundations=highlighted_foundations,
        )

        output_lines = []
        for row in canvas:
            line = ''.join(row)
            line = self._colorize_line(line)
            output_lines.append(line)

        term_width = self.term.width or BOARD_WIDTH
        pad_left = max(0, (term_width - BOARD_WIDTH) // 2)
        padding = ' ' * pad_left

        for y, line in enumerate(output_lines):
            frame += self.term.move_xy(0, y) + padding + line

        # Draw leaderboard overlay
        start_x = pad_left + (BOARD_WIDTH - 40) // 2
        start_y = 8

        for i, line in enumerate(lines):
            frame += self.term.move_xy(start_x, start_y + i) + self.term.black_on_bright_white(line)

        # Show close instruction
        frame += self.term.move_xy(start_x, start_y + len(lines) + 1) + self.term.bright_cyan("Press any key to continue")

        print(frame, end='', flush=True)
        self.term.inkey()

        self._resume_timer()
        self.needs_redraw = True

    def _get_selected_card(self) -> Optional[Card]:
        """Get the top card of current selection."""
        if self.selection is None:
            return None

        if self.selection.zone == CursorZone.WASTE:
            return self.state.waste[-1] if self.state.waste else None
        elif self.selection.zone == CursorZone.FOUNDATION:
            pile = self.state.foundations[self.selection.pile_index]
            return pile[-1] if pile else None
        elif self.selection.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.selection.pile_index]
            if pile and self.selection.card_index < len(pile):
                return pile[self.selection.card_index]
        return None

    def _describe_selection(self) -> str:
        """Describe the current selection for status bar."""
        if self.selection is None:
            return ""

        card = self._get_selected_card()
        if card is None:
            return "?"

        if self.selection.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.selection.pile_index]
            num_cards = len(pile) - self.selection.card_index
            if num_cards > 1:
                return f"{card} + {num_cards - 1} more"

        return str(card)


def main():
    """Entry point for the game."""
    seed = None
    draw_count = 1

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--seed" and i + 1 < len(args):
            try:
                seed = int(args[i + 1])
            except ValueError:
                pass
        elif arg == "--draw3":
            draw_count = 3
        elif arg in ("--help", "-h"):
            print("PySolitaire - Terminal Klondike Solitaire")
            print()
            print("Usage: pysolitaire [options]")
            print()
            print("Options:")
            print("  --seed NUM   Use specific random seed for reproducible games")
            print("  --draw3      Draw 3 cards from stock (default: draw 1)")
            print("  --help, -h   Show this help message")
            print()
            print(f"Requires terminal size of at least {MIN_TERM_WIDTH}x{MIN_TERM_HEIGHT}")
            sys.exit(0)

    ui = SolitaireUI(seed=seed, draw_count=draw_count)
    ui.run()


if __name__ == "__main__":
    main()
