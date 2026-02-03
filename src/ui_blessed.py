"""Blessed terminal UI for Solitaire."""

import sys
import time
from contextlib import nullcontext
from typing import Optional, List, Set, Tuple, Dict, Any
from dataclasses import dataclass
from blessed import Terminal

from src.config import GameConfig
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
    bury_top_of_stock,
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
    LAYOUT_LARGE,
    LAYOUT_COMPACT,
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
from src.mouse import (
    ClickableRegion,
    calculate_clickable_regions,
    find_clicked_region,
    parse_mouse_event,
    is_mouse_event,
    translate_mouse_coords,
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

    def __init__(self, config: GameConfig):
        self.term = Terminal()
        self.config = config
        self.layout = LAYOUT_COMPACT if config.compact else LAYOUT_LARGE
        self.state = deal_game(self.config.seed)
        self.cursor = Cursor()
        self.selection: Optional[Selection] = None
        self.message = "Welcome to Solitaire! Use arrows to move, Enter to select."
        self.move_count = 0
        self.running = True
        self.show_help = False
        self.undo_stack = UndoStack()
        # True until the next recycle; any successful move flips it back to True
        # so we only trigger stall detection after a full pass with zero progress.
        self.made_progress_since_last_recycle = True
        # Counts consecutive Draw-3 burials with no real move in between;
        # auto-loss fires when this reaches 2 so the bury loop cannot repeat forever.
        self.consecutive_burials = 0
        self.needs_redraw = True  # Track if redraw is needed
        self.highlighted: Optional[HighlightedDestinations] = None  # Valid destinations to show
        # Timer tracking
        self.start_time = time.time()
        self.elapsed_time = 0.0  # Total elapsed game time
        self.paused = False
        self.pause_start = 0.0
        # Gates idle redraws to 10 s so the timer tick doesn't flicker the screen.
        self.last_timer_render = time.time()
        # Leaderboard and save state
        self.leaderboard = Leaderboard()
        self.save_manager = SaveStateManager()
        self.show_leaderboard = False
        # Mouse support
        self.mouse_enabled = config.mouse_enabled
        self.pad_left = 0  # Will be calculated in _render()
        # Drag state tracking
        self.drag_start: Optional[Tuple[int, int]] = None  # (x, y) terminal coords of mouse down
        self.drag_start_region: Optional[ClickableRegion] = None  # Region where drag started

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
        self.made_progress_since_last_recycle = saved_data['made_progress_since_last_recycle']
        self.consecutive_burials = saved_data['consecutive_burials']
        # Restore timer so the elapsed count continues from where it was
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

    def _get_mouse_context(self):
        """Get the appropriate mouse context manager.

        Returns mouse_enabled context if mouse is enabled, otherwise nullcontext.
        """
        if self.mouse_enabled:
            return self.term.mouse_enabled(clicks=True)
        return nullcontext()

    def run(self) -> None:
        """Main game loop."""
        if not self._check_terminal_size():
            sys.exit(1)

        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor(), \
             self._get_mouse_context():

            if self.save_manager.has_save():
                saved_data = self.save_manager.load_game()
                if saved_data:
                    if self._prompt_resume_game(saved_data['move_count'], saved_data['elapsed_time']):
                        self._load_saved_game(saved_data)
                        self.message = "Game resumed!"
                        # Remove the on-disk copy so it does not re-prompt on the next launch
                        self.save_manager.delete_save()
                    else:
                        # Player declined resume; clean up so the stale file does not reappear
                        self.save_manager.delete_save()
                        self.message = "New game started!"
                    self.needs_redraw = True

            while self.running:
                if self.needs_redraw:
                    self._render()
                    self.needs_redraw = False
                    # Reset so an input-driven render doesn't trigger a redundant idle redraw shortly after.
                    self.last_timer_render = time.time()
                else:
                    # 10 s idle tick; input-driven redraws already paint the clock.
                    if time.time() - self.last_timer_render >= 10.0:
                        self._render()
                        self.last_timer_render = time.time()
                self._handle_input()

    def _render(self) -> None:
        """Render the game board."""
        # Accumulate into a single string so the terminal sees one write, avoiding flicker
        output_lines = []

        highlighted_tableau = self.highlighted.tableau_piles if self.highlighted else None
        highlighted_foundations = self.highlighted.foundation_piles if self.highlighted else None
        canvas = render_board(
            self.state,
            cursor_zone=self.cursor.zone.value,
            cursor_index=self.cursor.pile_index,
            cursor_card_index=self.cursor.card_index,
            highlighted_tableau=highlighted_tableau,
            highlighted_foundations=highlighted_foundations,
            layout=self.layout,
        )

        for row in canvas:
            line = ''.join(row)
            line = self._colorize_line(line)
            output_lines.append(line)

        term_width = self.term.width or BOARD_WIDTH
        self.pad_left = max(0, (term_width - BOARD_WIDTH) // 2)
        padding = ' ' * self.pad_left

        frame = self.term.home + self.term.clear

        for y, line in enumerate(output_lines):
            frame += self.term.move_xy(0, y) + padding + line

        status_y = BOARD_HEIGHT
        elapsed = self._get_elapsed_time()
        time_text = self._format_time(elapsed)
        move_text = f"Moves: {self.move_count}"
        timer_text = f"Time: {time_text}"
        status_line = f"{move_text}    {timer_text}"
        frame += self.term.move_xy(self.pad_left + 2, status_y - 4) + self.term.bright_white(status_line)

        msg_color = self.term.bright_yellow if "!" in self.message or "Invalid" in self.message else self.term.bright_cyan
        # Overwrite with spaces before writing new text so stale characters do not bleed through
        frame += self.term.move_xy(self.pad_left + 2, status_y - 2) + ' ' * (BOARD_WIDTH - 4)
        frame += self.term.move_xy(self.pad_left + 2, status_y - 2) + msg_color(self.message[:BOARD_WIDTH - 4])

        frame += self.term.move_xy(self.pad_left + 2, status_y - 1) + ' ' * (BOARD_WIDTH - 4)
        if self.selection:
            sel_text = f"Selected: {self._describe_selection()}"
            frame += self.term.move_xy(self.pad_left + 2, status_y - 1) + self.term.bright_green(sel_text)

        if self.show_help:
            frame += self._render_help_str(self.pad_left)

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
        """Handle keyboard and mouse input."""
        key = self.term.inkey(timeout=1)  # Wait up to 1 second for input

        if not key:
            return

        # Check for mouse event first
        if self.mouse_enabled and is_mouse_event(key):
            # Skip mouse during overlays
            if self.show_help or self.show_leaderboard:
                return
            mouse_event = parse_mouse_event(key)
            if mouse_event:
                if mouse_event.button == 'left':
                    if mouse_event.action == 'pressed':
                        self._handle_mouse_down(mouse_event.x, mouse_event.y)
                    elif mouse_event.action == 'released':
                        self._handle_mouse_up(mouse_event.x, mouse_event.y)
                elif mouse_event.button == 'right' and mouse_event.action == 'pressed':
                    self._cancel_selection()
                    self.needs_redraw = True
            return

        # Highlights are ephemeral; any keypress dismisses them so the player does not see stale markers
        if self.highlighted:
            self.highlighted = None
            self.needs_redraw = True

        # Errors stay visible until the next action; informational messages vanish immediately
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

    def _handle_mouse_down(self, terminal_x: int, terminal_y: int) -> None:
        """Handle mouse button press - start potential drag."""
        # Clear highlights on mouse down
        if self.highlighted:
            self.highlighted = None

        # Clear non-error messages
        if "Invalid" not in self.message and "Cannot" not in self.message:
            self.message = ""

        # Convert terminal coords to canvas coords
        canvas_x, canvas_y = translate_mouse_coords(terminal_x, terminal_y, self.pad_left)

        # Find what was clicked
        regions = calculate_clickable_regions(self.state, self.layout)
        region = find_clicked_region(canvas_x, canvas_y, regions)

        # Record drag start position and region
        self.drag_start = (terminal_x, terminal_y)
        self.drag_start_region = region

    def _handle_mouse_up(self, terminal_x: int, terminal_y: int) -> None:
        """Handle mouse button release - complete click or drag."""
        if self.drag_start_region is None:
            # No drag in progress (mouse down was outside all regions)
            self.drag_start = None
            return

        # Find release region
        canvas_x, canvas_y = translate_mouse_coords(terminal_x, terminal_y, self.pad_left)
        regions = calculate_clickable_regions(self.state, self.layout)
        release_region = find_clicked_region(canvas_x, canvas_y, regions)

        start_region = self.drag_start_region
        self.drag_start = None
        self.drag_start_region = None

        if release_region is None:
            # Released outside any region - treat as cancelled drag
            self.needs_redraw = True
            return

        # Check if same region (click) or different region (drag)
        same_region = (
            release_region.zone == start_region.zone and
            release_region.pile_index == start_region.pile_index and
            release_region.card_index == start_region.card_index
        )

        if same_region:
            # Same region - treat as click
            self._handle_mouse_click(terminal_x, terminal_y)
        else:
            # Different region - treat as drag
            self._handle_drag(start_region, release_region)

    def _handle_drag(self, source: ClickableRegion, dest: ClickableRegion) -> None:
        """Execute a drag from source region to destination region."""
        # Clear any existing selection first
        self.selection = None

        # Set cursor to source and select
        self.cursor.zone = source.zone
        self.cursor.pile_index = source.pile_index
        self.cursor.card_index = source.card_index

        # Handle stock specially - can't drag from stock, just do stock action
        if source.zone == CursorZone.STOCK:
            self._handle_space()
            self.needs_redraw = True
            return

        # Try to select the source
        self._try_select()

        if self.selection is None:
            # Selection failed (e.g., face-down card, empty pile)
            self.needs_redraw = True
            return

        # Move cursor to destination and place
        self.cursor.zone = dest.zone
        self.cursor.pile_index = dest.pile_index
        self.cursor.card_index = dest.card_index

        self._try_place()
        self.needs_redraw = True

    def _handle_mouse_click(self, terminal_x: int, terminal_y: int) -> None:
        """Handle a mouse click at terminal coordinates."""
        # Convert terminal coords to canvas coords
        canvas_x, canvas_y = translate_mouse_coords(terminal_x, terminal_y, self.pad_left)

        # Find what was clicked
        regions = calculate_clickable_regions(self.state, self.layout)
        region = find_clicked_region(canvas_x, canvas_y, regions)

        if region is None:
            # Clicked empty space - cancel selection if any
            if self.selection:
                self._cancel_selection()
            self.needs_redraw = True
            return

        # Update cursor to clicked location
        self.cursor.zone = region.zone
        self.cursor.pile_index = region.pile_index
        self.cursor.card_index = region.card_index

        # Handle the click based on zone and current state
        if region.zone == CursorZone.STOCK:
            self._handle_space()
        elif self.selection is None:
            self._try_select()
        else:
            self._try_place()

        self.needs_redraw = True

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
            card = self._get_selected_card()
        else:
            card = self._get_card_under_cursor()

        if card is None:
            self.message = "No card to show placements for!"
            return

        tableau_dests = get_valid_tableau_destinations(card, self.state)
        foundation_dests = get_valid_foundation_destinations(card, self.state)

        # Foundation only accepts single cards; a multi-card run from tableau must stay on tableau
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

        # Re-entering on the same pile is the keyboard equivalent of clicking to deselect
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
            self.made_progress_since_last_recycle = True
            self.consecutive_burials = 0
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
            self.made_progress_since_last_recycle = True
            self.consecutive_burials = 0
            self.message = "Moved!"
            self.selection = None
        else:
            self.undo_stack.pop()
            self.message = f"Invalid move: {result.message}"

    def _handle_space(self) -> None:
        """Handle space bar - draw from stock or recycle waste."""
        if self.state.stock:
            self._save_for_undo()
            result = draw_from_stock(self.state, self.config.draw_count)
            if result.success:
                self.move_count += 1
                drawn = min(self.config.draw_count, len(self.state.waste))
                self.message = f"Drew {drawn} card(s) from stock."
        elif self.state.waste:
            # A full pass through the stock just completed — check whether
            # the player made any moves during that pass before recycling.
            if not self.made_progress_since_last_recycle:
                if self.config.draw_count == 1:
                    self._end_game_loss()
                    return
                else:
                    # Two consecutive burials with no real move in between
                    # means the deck is hopelessly stuck; end the game
                    # automatically rather than prompting a third time.
                    if self.consecutive_burials >= 2:
                        self._end_game_loss()
                        return
                    # Draw-3: offer to bury the top waste card as a last resort
                    should_bury = self._prompt_bury_card()
                    if not should_bury:
                        self._end_game_loss()
                        return
                    # Bury succeeded; track it so we know how deep into the
                    # stall streak we are before the next recycle.
                    self.consecutive_burials += 1

            self._save_for_undo()
            result = recycle_waste_to_stock(self.state)
            if result.success:
                # Reset the progress flag so the *next* pass is tracked cleanly
                self.made_progress_since_last_recycle = False
                self.message = "Recycled waste to stock."
        else:
            self.message = "Both stock and waste are empty!"

    def _prompt_bury_card(self) -> bool:
        """Show a Y/N dialog asking the player to bury the top waste card.

        Pauses the timer while the prompt is visible so idle time during the
        decision does not count against the player.

        Returns True if the player chose to bury, False otherwise.
        """
        self._pause_timer()
        self.message = "No progress this pass. Bury top card? (Y/N)"
        self.needs_redraw = True
        self._render()

        while True:
            key = self.term.inkey()
            if key.lower() == 'y':
                # Execute the bury before the recycle so the next Draw-3
                # cycle starts with a different card sequence.
                bury_top_of_stock(self.state)
                self._resume_timer()
                self.message = "Top card buried. Recycling stock..."
                return True
            elif key.lower() == 'n':
                self._resume_timer()
                return False

    def _end_game_loss(self) -> None:
        """Present the loss screen and end the game.

        Mirrors _check_win's structure: pause the timer, show a dialog, and
        set self.running = False so the main loop exits.
        """
        self._pause_timer()
        self.selection = None
        self.message = "No legal moves remain. Game over."
        self.needs_redraw = True
        self._render()

        # Delete the save file — a lost game should not be resumable
        self.save_manager.delete_save()

        # Block until the player explicitly chooses restart or quit so they can read the result
        term_width = self.term.width or BOARD_WIDTH
        pad_left = max(0, (term_width - BOARD_WIDTH) // 2)
        status_y = BOARD_HEIGHT - 1
        loss_line = "Press R to play again or Q to quit."
        self.needs_redraw = False
        print(
            self.term.move_xy(pad_left + 2, status_y)
            + self.term.bright_red(loss_line),
            end='',
            flush=True,
        )

        while True:
            key = self.term.inkey()
            if key.lower() == 'r':
                # Restart in place so the player can continue the session
                self.start_time = time.time()
                self.paused = False
                self.pause_start = 0.0
                self.state = deal_game()
                self.cursor = Cursor()
                self.selection = None
                self.move_count = 0
                self.undo_stack.clear()
                self.made_progress_since_last_recycle = True
                self.consecutive_burials = 0
                self.message = "New game started!"
                self.needs_redraw = True
                return
            elif key.lower() == 'q':
                self.running = False
                return

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
            # Save game state so the session can be resumed next time
            elapsed = self._get_elapsed_time()
            self.save_manager.save_game(
                self.state,
                self.move_count,
                elapsed,
                self.config.draw_count,
                self.made_progress_since_last_recycle,
                self.consecutive_burials,
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
            # Reset timer and progress tracking on restart
            self.start_time = time.time()
            self.paused = False
            self.pause_start = 0.0
            self.state = deal_game()
            self.cursor = Cursor()
            self.selection = None
            self.move_count = 0
            self.undo_stack.clear()
            self.made_progress_since_last_recycle = True
            self.consecutive_burials = 0
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

            # A completed game should not prompt for resume on the next launch
            self.save_manager.delete_save()

            self.message = f"CONGRATULATIONS! You won in {self.move_count} moves and {self._format_time(elapsed)}!"
            self.needs_redraw = True
            self._render()

            initials = self._prompt_initials()

            position = self.leaderboard.add_entry(initials, self.move_count, elapsed, self.config.draw_count)

            self._show_leaderboard_after_win(position)

            self.running = False

    def _prompt_initials(self) -> str:
        """Prompt user to enter 3-letter initials.

        Returns the initials (3 chars, uppercase), or "N/A" if cancelled.
        """
        initials = ""

        while len(initials) < 3:
            frame = self.term.home + self.term.clear

            highlighted_tableau = self.highlighted.tableau_piles if self.highlighted else None
            highlighted_foundations = self.highlighted.foundation_piles if self.highlighted else None
            canvas = render_board(
                self.state,
                cursor_zone=self.cursor.zone.value,
                cursor_index=self.cursor.pile_index,
                cursor_card_index=self.cursor.card_index,
                highlighted_tableau=highlighted_tableau,
                highlighted_foundations=highlighted_foundations,
                layout=self.layout,
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

            status_y = BOARD_HEIGHT
            prompt_display = render_initials_prompt(initials)
            frame += self.term.move_xy(pad_left + 2, status_y - 2) + self.term.bright_cyan(prompt_display)

            print(frame, end='', flush=True)

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
        lines = self.leaderboard.format_leaderboard(self.config.draw_count)

        if position > 0:
            msg = f"You placed #{position} on the leaderboard!"
        else:
            msg = "You didn't make the top 20, but great job!"

        frame = self.term.home + self.term.clear

        term_width = self.term.width or BOARD_WIDTH
        start_x = max(0, (term_width - 40) // 2)
        start_y = 5

        for i, line in enumerate(lines):
            frame += self.term.move_xy(start_x, start_y + i) + self.term.bright_white(line)

        frame += self.term.move_xy(start_x, start_y + len(lines) + 2) + self.term.bright_yellow(msg)
        frame += self.term.move_xy(start_x, start_y + len(lines) + 4) + self.term.bright_cyan("Press any key to exit.")

        print(frame, end='', flush=True)
        self.term.inkey()

    def _show_leaderboard_ingame(self) -> None:
        """Show leaderboard overlay during game (L key)."""
        self._pause_timer()

        lines = self.leaderboard.format_leaderboard(self.config.draw_count)

        frame = self.term.home + self.term.clear

        # Paint the board behind the overlay so it remains visible as context
        highlighted_tableau = self.highlighted.tableau_piles if self.highlighted else None
        highlighted_foundations = self.highlighted.foundation_piles if self.highlighted else None
        canvas = render_board(
            self.state,
            cursor_zone=self.cursor.zone.value,
            cursor_index=self.cursor.pile_index,
            cursor_card_index=self.cursor.card_index,
            highlighted_tableau=highlighted_tableau,
            highlighted_foundations=highlighted_foundations,
            layout=self.layout,
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

        start_x = pad_left + (BOARD_WIDTH - 40) // 2
        start_y = 8

        for i, line in enumerate(lines):
            frame += self.term.move_xy(start_x, start_y + i) + self.term.black_on_bright_white(line)

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
    compact = False
    mouse_enabled = True

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--seed" and i + 1 < len(args):
            try:
                seed = int(args[i + 1])
                i += 1
            except ValueError:
                pass
        elif arg == "--draw3":
            draw_count = 3
        elif arg == "--compact":
            compact = True
        elif arg == "--no-mouse":
            mouse_enabled = False
        elif arg in ("--help", "-h"):
            print("PySolitaire - Terminal Klondike Solitaire")
            print()
            print("Usage: pysolitaire [options]")
            print()
            print("Options:")
            print("  --seed NUM   Use specific random seed for reproducible games")
            print("  --draw3      Draw 3 cards from stock (default: draw 1)")
            print("  --compact    Use smaller 5×3 cards (default: 7×5)")
            print("  --no-mouse   Disable mouse input support")
            print("  --help, -h   Show this help message")
            print()
            print(f"Requires terminal size of at least {MIN_TERM_WIDTH}x{MIN_TERM_HEIGHT}")
            sys.exit(0)
        i += 1

    config = GameConfig(seed=seed, draw_count=draw_count, compact=compact, mouse_enabled=mouse_enabled)
    ui = SolitaireUI(config)
    ui.run()


if __name__ == "__main__":
    main()
