"""Blessed terminal UI for Solitaire."""

from typing import Optional, Tuple, List
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
    FOUNDATION_SUIT_ORDER,
)
from src.renderer import (
    render_board,
    canvas_to_string,
    BOARD_WIDTH,
    BOARD_HEIGHT,
    get_card_color,
)


@dataclass
class Selection:
    """Represents currently selected cards."""
    zone: CursorZone
    pile_index: int = 0
    card_index: int = 0  # For tableau: starting card of the run


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

    def run(self) -> None:
        """Main game loop."""
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            while self.running:
                self._render()
                self._handle_input()

    def _render(self) -> None:
        """Render the game board."""
        # Clear screen
        print(self.term.home + self.term.clear, end='')

        # Render the board
        canvas = render_board(
            self.state,
            cursor_zone=self.cursor.zone.value,
            cursor_index=self.cursor.pile_index,
            cursor_card_index=self.cursor.card_index,
        )

        # Apply colors to canvas and convert to string
        output = self._colorize_board(canvas)

        # Center the board
        term_width = self.term.width or BOARD_WIDTH
        pad_left = max(0, (term_width - BOARD_WIDTH) // 2)

        lines = output.split('\n')
        for y, line in enumerate(lines):
            print(self.term.move_xy(pad_left, y) + line, end='')

        # Draw status bar with message
        status_y = BOARD_HEIGHT + 1
        move_text = f"Moves: {self.move_count}"
        print(self.term.move_xy(pad_left + 2, status_y - 4) + self.term.bright_white(move_text), end='')

        # Message line
        msg_color = self.term.bright_yellow if "!" in self.message or "Invalid" in self.message else self.term.bright_cyan
        print(self.term.move_xy(pad_left + 2, status_y - 2) + msg_color(self.message[:BOARD_WIDTH - 4]), end='')

        # Selection indicator
        if self.selection:
            sel_text = f"Selected: {self._describe_selection()}"
            print(self.term.move_xy(pad_left + 2, status_y - 1) + self.term.bright_green(sel_text), end='')

        # Help overlay
        if self.show_help:
            self._render_help(pad_left)

        # Flush output
        print('', end='', flush=True)

    def _colorize_board(self, canvas: List[List[str]]) -> str:
        """Apply colors to the rendered board."""
        lines = []
        for row in canvas:
            line = ''.join(row)
            # Colorize suit symbols
            line = self._colorize_suits(line)
            lines.append(line)
        return '\n'.join(lines)

    def _colorize_suits(self, line: str) -> str:
        """Add color to suit symbols in a line."""
        result = ""
        i = 0
        while i < len(line):
            char = line[i]
            if char in "♥♦":
                result += self.term.bright_red(char)
            elif char in "♣♠":
                result += self.term.white(char)
            elif char == "[":
                # Cursor bracket - make it very visible
                result += self.term.bright_cyan_on_blue(char)
            elif char == "]":
                result += self.term.bright_cyan_on_blue(char)
            elif char == "░":
                result += self.term.blue(char)
            else:
                result += char
            i += 1
        return result

    def _render_help(self, pad_left: int) -> None:
        """Render help overlay."""
        help_lines = [
            "╔══════════════════════════════════════╗",
            "║           SOLITAIRE HELP             ║",
            "╠══════════════════════════════════════╣",
            "║  Arrow Keys : Navigate the board     ║",
            "║  Enter      : Select / Place card    ║",
            "║  Space      : Draw from stock        ║",
            "║  Escape     : Cancel selection       ║",
            "║  U          : Undo last move         ║",
            "║  R          : Restart game           ║",
            "║  H / ?      : Toggle this help       ║",
            "║  Q          : Quit game              ║",
            "╠══════════════════════════════════════╣",
            "║  Goal: Move all cards to foundations ║",
            "║  Build foundations A→K by suit       ║",
            "║  Build tableau K→A alternating color ║",
            "╚══════════════════════════════════════╝",
        ]
        start_y = 8
        start_x = pad_left + (BOARD_WIDTH - 40) // 2
        for i, help_line in enumerate(help_lines):
            print(self.term.move_xy(start_x, start_y + i) + self.term.black_on_bright_white(help_line), end='')

    def _handle_input(self) -> None:
        """Handle keyboard input."""
        key = self.term.inkey(timeout=0.1)

        if not key:
            return

        # Clear previous non-error message
        if "Invalid" not in self.message and "Cannot" not in self.message:
            self.message = ""

        if key.name == 'KEY_UP':
            self.cursor.move_up(self.state)
        elif key.name == 'KEY_DOWN':
            self.cursor.move_down(self.state)
        elif key.name == 'KEY_LEFT':
            self.cursor.move_left(self.state)
        elif key.name == 'KEY_RIGHT':
            self.cursor.move_right(self.state)
        elif key.name == 'KEY_ENTER' or key == '\n':
            self._handle_enter()
        elif key == ' ':
            self._handle_space()
        elif key.name == 'KEY_ESCAPE':
            self._cancel_selection()
        elif key.lower() == 'q':
            self._handle_quit()
        elif key.lower() == 'h' or key == '?':
            self.show_help = not self.show_help
        elif key.lower() == 'r':
            self._handle_restart()
        elif key.lower() == 'u':
            self.message = "Undo not yet implemented"

    def _handle_enter(self) -> None:
        """Handle Enter key - select or place."""
        if self.selection is None:
            self._try_select()
        else:
            self._try_place()

    def _try_select(self) -> None:
        """Try to select card(s) at cursor position."""
        if self.cursor.zone == CursorZone.STOCK:
            # Stock: draw card(s) instead of selecting
            self._handle_space()
            return

        if self.cursor.zone == CursorZone.WASTE:
            if can_pick_from_waste(self.state):
                self.selection = Selection(
                    zone=CursorZone.WASTE,
                    pile_index=0,
                    card_index=0,
                )
                self.message = "Card selected. Move to destination and press Enter."
                self._check_auto_move()
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
                self.message = "Foundation card selected."
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
                    self.message = f"{num_cards} cards selected."
                else:
                    self.message = "Card selected."
                self._check_auto_move()
            else:
                self.message = "Cannot select face-down card!"

    def _check_auto_move(self) -> None:
        """Check if there's only one valid destination and auto-move."""
        if self.selection is None:
            return

        card = self._get_selected_card()
        if card is None:
            return

        # Find all valid destinations
        tableau_dests = get_valid_tableau_destinations(card, self.state)
        foundation_dests = get_valid_foundation_destinations(card, self.state)

        # For runs (multiple cards), can't go to foundation
        if self.selection.zone == CursorZone.TABLEAU:
            pile = self.state.tableau[self.selection.pile_index]
            if len(pile) - self.selection.card_index > 1:
                foundation_dests = []

        total_dests = len(tableau_dests) + len(foundation_dests)

        if total_dests == 1:
            # Auto-move to the single destination
            if foundation_dests:
                self._move_to_foundation(foundation_dests[0])
            else:
                self._move_to_tableau(tableau_dests[0])

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

    def _move_to_foundation(self, dest_foundation: int) -> None:
        """Move selected card to foundation."""
        result: MoveResult

        if self.selection.zone == CursorZone.WASTE:
            result = move_waste_to_foundation(self.state, dest_foundation)
        elif self.selection.zone == CursorZone.TABLEAU:
            # Can only move single card to foundation
            pile = self.state.tableau[self.selection.pile_index]
            if len(pile) - self.selection.card_index > 1:
                self.message = "Can only move single card to foundation!"
                return
            result = move_tableau_to_foundation(self.state, self.selection.pile_index, dest_foundation)
        elif self.selection.zone == CursorZone.FOUNDATION:
            self.message = "Cannot move foundation to foundation!"
            return
        else:
            result = MoveResult(False, "Invalid source")

        if result.success:
            self.move_count += 1
            self.message = f"Moved to foundation!"
            self.selection = None
            self._check_win()
        else:
            self.message = f"Invalid move: {result.message}"

    def _move_to_tableau(self, dest_pile: int) -> None:
        """Move selected card(s) to tableau."""
        result: MoveResult

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
            self.message = "Moved!"
            self.selection = None
        else:
            self.message = f"Invalid move: {result.message}"

    def _handle_space(self) -> None:
        """Handle space bar - draw from stock."""
        if self.state.stock:
            result = draw_from_stock(self.state, self.draw_count)
            if result.success:
                self.move_count += 1
                drawn = min(self.draw_count, len(self.state.waste))
                self.message = f"Drew {drawn} card(s) from stock."
        elif self.state.waste:
            result = recycle_waste_to_stock(self.state)
            if result.success:
                self.message = "Recycled waste to stock."
        else:
            self.message = "Both stock and waste are empty!"

    def _cancel_selection(self) -> None:
        """Cancel current selection."""
        if self.selection:
            self.selection = None
            self.message = "Selection cancelled."
        else:
            self.message = ""

    def _handle_quit(self) -> None:
        """Handle quit request."""
        self.message = "Press Q again to confirm quit, any other key to cancel."
        self._render()
        key = self.term.inkey()
        if key.lower() == 'q':
            self.running = False
        else:
            self.message = "Quit cancelled."

    def _handle_restart(self) -> None:
        """Handle restart request."""
        self.message = "Press R again to restart, any other key to cancel."
        self._render()
        key = self.term.inkey()
        if key.lower() == 'r':
            self.state = deal_game()
            self.cursor = Cursor()
            self.selection = None
            self.move_count = 0
            self.message = "New game started!"
        else:
            self.message = "Restart cancelled."

    def _check_win(self) -> None:
        """Check if the player has won."""
        total_in_foundations = sum(len(pile) for pile in self.state.foundations)
        if total_in_foundations == 52:
            self.message = "🎉 CONGRATULATIONS! You won! 🎉 Press any key to exit."
            self._render()
            self.term.inkey()
            self.running = False

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
    import sys

    seed = None
    draw_count = 1

    # Simple argument parsing
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--seed" and i + 1 < len(args):
            try:
                seed = int(args[i + 1])
            except ValueError:
                pass
        elif arg == "--draw3":
            draw_count = 3

    ui = SolitaireUI(seed=seed, draw_count=draw_count)
    ui.run()


if __name__ == "__main__":
    main()
