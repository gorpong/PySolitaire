"""Blessed terminal UI for Solitaire."""

import sys
import time
from contextlib import nullcontext
from typing import Optional, Tuple

from blessed import Terminal

from pysolitaire.config import GameConfig
from pysolitaire.cursor import CursorZone
from pysolitaire.dialogs import DialogManager, DialogResult
from pysolitaire.game_controller import GameController
from pysolitaire.input_handler import InputAction, InputEvent, InputHandler
from pysolitaire.leaderboard import Leaderboard
from pysolitaire.mouse import (
    ClickableRegion,
    calculate_clickable_regions,
    find_clicked_region,
    is_mouse_event,
    parse_mouse_event,
    translate_mouse_coords,
)
from pysolitaire.overlays import (
    format_time,
    render_help_lines,
    render_initials_prompt,
)
from pysolitaire.renderer import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    LAYOUT_COMPACT,
    LAYOUT_LARGE,
    render_board,
)
from pysolitaire.save_state import SaveStateManager

MIN_TERM_WIDTH = 100
MIN_TERM_HEIGHT = 40


class SolitaireUI:
    """Terminal UI for Solitaire game.
    
    Orchestrates rendering and input handling, delegating game logic
    to the GameController and modal interactions to the DialogManager.
    
    Attributes:
        term: Blessed Terminal instance for screen control.
        config: Game configuration settings.
        layout: Card layout dimensions (large or compact).
        controller: Game controller managing state and logic.
        input_handler: Keyboard and mouse input processor.
        dialogs: Dialog manager for modal interactions.
        leaderboard: Leaderboard manager for high scores.
        save_manager: Save/load game state manager.
        running: Whether the game loop should continue.
        show_help: Whether the help overlay is visible.
        needs_redraw: Whether the screen needs to be redrawn.
        pad_left: Left padding for centering the board.
        drag_start: Terminal coordinates where mouse drag began.
        drag_start_region: Clickable region where drag began.
    """

    def __init__(self, config: GameConfig):
        self.term = Terminal()
        self.config = config
        self.layout = LAYOUT_COMPACT if config.compact else LAYOUT_LARGE
        self.controller = GameController(config)
        self.input_handler = InputHandler(mouse_enabled=config.mouse_enabled)
        self.dialogs = DialogManager(self.term)
        self.leaderboard = Leaderboard()
        self.save_manager = SaveStateManager()
        self.running = True
        self.show_help = False
        self.needs_redraw = True
        self.last_timer_render = time.time()
        self.pad_left = 0
        self.drag_start: Optional[Tuple[int, int]] = None
        self.drag_start_region: Optional[ClickableRegion] = None
        self.current_slot: Optional[int] = None

    @property
    def _session(self):
        """Shortcut to controller session."""
        return self.controller.session

    def _assign_new_slot(self) -> None:
        """Assign the next free save slot to current_slot.

        If all slots are full this sets current_slot to None; the quit
        handler will prompt for an overwrite slot in that case.
        """
        self.current_slot = self.save_manager.next_free_slot()

    def _save_current_game(self) -> None:
        """Persist the current game to current_slot."""
        if self.current_slot is None:
            return
        data = self.controller.save_to_dict()
        self.save_manager.save_game(
            self.current_slot,
            data['state'],
            data['move_count'],
            data['elapsed_time'],
            data['draw_count'],
            data['made_progress_since_last_recycle'],
            data['consecutive_burials'],
        )

    def _clear_current_slot(self) -> None:
        """Delete the save slot for the current game."""
        if self.current_slot is not None:
            self.save_manager.delete_save(self.current_slot)
            self.current_slot = None

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

    def _get_mouse_context(self):
        """Get the appropriate mouse context manager."""
        if self.input_handler.mouse_enabled:
            return self.term.mouse_enabled(clicks=True)
        return nullcontext()

    def run(self) -> None:
        """Main game loop."""
        if not self._check_terminal_size():
            sys.exit(1)

        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor(), \
             self._get_mouse_context():

            if self.save_manager.has_saves():
                slot = self.dialogs.prompt_slot_select(
                    self.save_manager.list_saves(), self.pad_left
                )
                if slot is None:
                    # Escape — player wants to quit without playing
                    return
                elif slot == -1:
                    # N — start a new game
                    self._assign_new_slot()
                    self._session.message = "New game started!"
                    self.controller.start_game()
                else:
                    # Numeric slot — resume that save
                    saved_data = self.save_manager.load_game(slot)
                    if saved_data:
                        self.controller.load_from_dict(saved_data)
                        self.current_slot = slot
                        self._session.message = f"Game resumed from slot {slot}!"
                        self.controller.start_game()
                    else:
                        self._session.message = "Save data corrupted — starting new game."
                        self._assign_new_slot()
                        self.controller.start_game()
                self.needs_redraw = True
            else:
                self._assign_new_slot()
                self.controller.start_game()

            while self.running:
                if self.needs_redraw:
                    self._render()
                    self.needs_redraw = False
                    self.last_timer_render = time.time()
                else:
                    if time.time() - self.last_timer_render >= 10.0:
                        self._render()
                        self.last_timer_render = time.time()
                self._handle_input()

    def _render(self) -> None:
        """Render the game board."""
        output_lines = []

        highlighted = self._session.highlighted
        highlighted_tableau = highlighted.tableau_piles if highlighted else None
        highlighted_foundations = highlighted.foundation_piles if highlighted else None
        
        canvas = render_board(
            self._session.state,
            cursor_zone=self._session.cursor.zone.value,
            cursor_index=self._session.cursor.pile_index,
            cursor_card_index=self._session.cursor.card_index,
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
        elapsed = self.controller.get_elapsed_time()
        time_text = format_time(elapsed)
        move_text = f"Moves: {self._session.move_count}"
        timer_text = f"Time: {time_text}"
        status_line = f"{move_text}    {timer_text}"
        frame += self.term.move_xy(self.pad_left + 2, status_y - 4) + self.term.bright_white(status_line)

        msg_color = self.term.bright_yellow if "!" in self._session.message or "Invalid" in self._session.message else self.term.bright_cyan
        frame += self.term.move_xy(self.pad_left + 2, status_y - 2) + ' ' * (BOARD_WIDTH - 4)
        frame += self.term.move_xy(self.pad_left + 2, status_y - 2) + msg_color(self._session.message[:BOARD_WIDTH - 4])

        frame += self.term.move_xy(self.pad_left + 2, status_y - 1) + ' ' * (BOARD_WIDTH - 4)
        if self._session.selection:
            sel_text = f"Selected: {self.controller.describe_selection()}"
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
        key = self.term.inkey(timeout=1)

        if not key:
            return

        if self.input_handler.mouse_enabled and is_mouse_event(key):
            if self.show_help:
                return
            mouse_event = parse_mouse_event(key)
            if mouse_event:
                event = self.input_handler.process_mouse_event(
                    mouse_event.button,
                    mouse_event.action,
                    mouse_event.x,
                    mouse_event.y,
                )
                self._dispatch_event(event)
            return

        event = self.input_handler.process(key)
        self._dispatch_event(event)

    def _dispatch_event(self, event: InputEvent) -> None:
        """Dispatch an input event to the appropriate handler."""
        if event.action == InputAction.NONE:
            return

        if event.is_mouse:
            self._handle_mouse_event(event)
            return

        if self._session.highlighted:
            self._session.highlighted = None
            self.needs_redraw = True

        if "Invalid" not in self._session.message and "Cannot" not in self._session.message:
            self._session.message = ""

        if event.action == InputAction.MOVE_UP:
            self._session.cursor.move_up(self._session.state)
            self.needs_redraw = True
        elif event.action == InputAction.MOVE_DOWN:
            self._session.cursor.move_down(self._session.state)
            self.needs_redraw = True
        elif event.action == InputAction.MOVE_LEFT:
            self._session.cursor.move_left(self._session.state)
            self.needs_redraw = True
        elif event.action == InputAction.MOVE_RIGHT:
            self._session.cursor.move_right(self._session.state)
            self.needs_redraw = True
        elif event.action == InputAction.SELECT:
            self._handle_select()
            self.needs_redraw = True
        elif event.action == InputAction.SHOW_HINTS:
            self._handle_hints()
            self.needs_redraw = True
        elif event.action == InputAction.STOCK_ACTION:
            self._handle_stock_action()
            self.needs_redraw = True
        elif event.action == InputAction.CANCEL:
            self.controller.cancel_selection()
            self.needs_redraw = True
        elif event.action == InputAction.QUIT:
            self._handle_quit()
        elif event.action == InputAction.HELP:
            if self.show_help:
                self.controller.resume_timer()
            else:
                self.controller.pause_timer()
            self.show_help = not self.show_help
            self.needs_redraw = True
        elif event.action == InputAction.RESTART:
            self._handle_restart()
        elif event.action == InputAction.UNDO:
            self.controller.undo()
            self.needs_redraw = True
        elif event.action == InputAction.LEADERBOARD:
            self._show_leaderboard_ingame()

    def _handle_mouse_event(self, event: InputEvent) -> None:
        """Handle mouse-specific events."""
        if event.action == InputAction.MOUSE_DOWN:
            self._handle_mouse_down(event.mouse_x, event.mouse_y)
        elif event.action == InputAction.MOUSE_UP:
            self._handle_mouse_up(event.mouse_x, event.mouse_y)
        elif event.action == InputAction.CANCEL:
            self.controller.cancel_selection()
            self.needs_redraw = True

    def _handle_mouse_down(self, terminal_x: int, terminal_y: int) -> None:
        """Handle mouse button press - start potential drag."""
        if self._session.highlighted:
            self._session.highlighted = None

        if "Invalid" not in self._session.message and "Cannot" not in self._session.message:
            self._session.message = ""

        canvas_x, canvas_y = translate_mouse_coords(terminal_x, terminal_y, self.pad_left)

        regions = calculate_clickable_regions(self._session.state, self.layout)
        region = find_clicked_region(canvas_x, canvas_y, regions)

        self.drag_start = (terminal_x, terminal_y)
        self.drag_start_region = region

    def _handle_mouse_up(self, terminal_x: int, terminal_y: int) -> None:
        """Handle mouse button release - complete click or drag."""
        if self.drag_start_region is None:
            self.drag_start = None
            return

        canvas_x, canvas_y = translate_mouse_coords(terminal_x, terminal_y, self.pad_left)
        regions = calculate_clickable_regions(self._session.state, self.layout)
        release_region = find_clicked_region(canvas_x, canvas_y, regions)

        start_region = self.drag_start_region
        self.drag_start = None
        self.drag_start_region = None

        if release_region is None:
            self.needs_redraw = True
            return

        same_region = (
            release_region.zone == start_region.zone and
            release_region.pile_index == start_region.pile_index and
            release_region.card_index == start_region.card_index
        )

        if same_region:
            self._handle_mouse_click(terminal_x, terminal_y)
        else:
            self._handle_drag(start_region, release_region)

    def _handle_drag(self, source: ClickableRegion, dest: ClickableRegion) -> None:
        """Execute a drag from source region to destination region."""
        self._session.selection = None

        self._session.cursor.zone = source.zone
        self._session.cursor.pile_index = source.pile_index
        self._session.cursor.card_index = source.card_index

        if source.zone == CursorZone.STOCK:
            self._handle_stock_action()
            self.needs_redraw = True
            return

        self.controller.try_select()

        if self._session.selection is None:
            self.needs_redraw = True
            return

        self._session.cursor.zone = dest.zone
        self._session.cursor.pile_index = dest.pile_index
        self._session.cursor.card_index = dest.card_index

        self.controller.try_place()
        self._check_win()
        self.needs_redraw = True

    def _handle_mouse_click(self, terminal_x: int, terminal_y: int) -> None:
        """Handle a mouse click at terminal coordinates."""
        canvas_x, canvas_y = translate_mouse_coords(terminal_x, terminal_y, self.pad_left)

        regions = calculate_clickable_regions(self._session.state, self.layout)
        region = find_clicked_region(canvas_x, canvas_y, regions)

        if region is None:
            if self._session.selection:
                self.controller.cancel_selection()
            self.needs_redraw = True
            return

        self._session.cursor.zone = region.zone
        self._session.cursor.pile_index = region.pile_index
        self._session.cursor.card_index = region.card_index

        if region.zone == CursorZone.STOCK:
            self._handle_stock_action()
        elif self._session.selection is None:
            self.controller.try_select()
        else:
            self.controller.try_place()
            self._check_win()

        self.needs_redraw = True

    def _handle_select(self) -> None:
        """Handle select action (Enter key)."""
        if self._session.selection is None:
            self.controller.try_select()
        else:
            self.controller.try_place()
            self._check_win()

    def _handle_hints(self) -> None:
        """Handle show hints action (Tab key)."""
        highlights = self.controller.compute_valid_destinations()
        self._session.highlighted = highlights

    def _handle_stock_action(self) -> None:
        """Handle stock draw/recycle with stall detection."""
        if self._session.state.stock:
            self.controller.handle_stock_action()
            return

        if self._session.state.waste:
            if self.controller.is_stalled():
                self._end_game_loss()
                return

            if self.controller.needs_bury_prompt():
                self.controller.pause_timer()
                self._session.message = "No progress this pass. Bury top card? (Y/N)"
                self.needs_redraw = True
                self._render()

                result = self.dialogs.prompt_bury_card()
                self.controller.resume_timer()

                if result == DialogResult.CANCELLED:
                    self._end_game_loss()
                    return
                self.controller.execute_bury()
                self._session.message = "Top card buried. Recycling stock..."

            self.controller.handle_stock_action()
        else:
            self._session.message = "Both stock and waste are empty!"

    def _end_game_loss(self) -> None:
        """Present the loss screen and end the game."""
        self.controller.pause_timer()
        self._session.selection = None
        self._session.message = "No legal moves remain. Game over."
        self.needs_redraw = True
        self._render()

        self._clear_current_slot()

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

        result = self.dialogs.show_loss_screen()
        if result == DialogResult.CONFIRMED:
            self._assign_new_slot()
            self.controller.new_game()
            self.controller.start_game()
            self.needs_redraw = True
        else:
            self.running = False

    def _handle_quit(self) -> None:
        """Handle quit request."""
        self.controller.pause_timer()
        self._session.message = "Press Q again to confirm quit, any other key to cancel."
        self.needs_redraw = True
        self._render()

        result = self.dialogs.confirm_quit()
        if result == DialogResult.CONFIRMED:
            # If we don't have a slot yet (all full), prompt for overwrite
            if self.current_slot is None:
                overwrite = self.dialogs.prompt_overwrite_slot(
                    self.save_manager.list_saves(), self.pad_left
                )
                if overwrite is None or overwrite == -1:
                    # Player cancelled overwrite — don't quit
                    self.controller.resume_timer()
                    self._session.message = "Quit cancelled."
                    self.needs_redraw = True
                    return
                self.current_slot = overwrite
            self._save_current_game()
            self.running = False
        else:
            self.controller.resume_timer()
            self._session.message = "Quit cancelled."
            self.needs_redraw = True

    def _handle_restart(self) -> None:
        """Handle restart request."""
        self.controller.pause_timer()
        self._session.message = "Press R again to restart, any other key to cancel."
        self.needs_redraw = True
        self._render()

        result = self.dialogs.confirm_restart()
        if result == DialogResult.CONFIRMED:
            self._clear_current_slot()
            self._assign_new_slot()
            self.controller.new_game()
            self.controller.start_game()
        else:
            self.controller.resume_timer()
            self._session.message = "Restart cancelled."
        self.needs_redraw = True

    def _check_win(self) -> None:
        """Check if the player has won and handle win state."""
        if not self.controller.check_win():
            return

        self.controller.pause_timer()
        elapsed = int(self.controller.get_elapsed_time())

        self._clear_current_slot()

        self._session.message = f"CONGRATULATIONS! You won in {self._session.move_count} moves and {format_time(elapsed)}!"
        self.needs_redraw = True
        self._render()

        initials_result = self.dialogs.prompt_initials(
            render_callback=lambda initials: self._render_initials_prompt(initials)
        )

        position = self.leaderboard.add_entry(
            initials_result.initials, 
            self._session.move_count, 
            elapsed, 
            self.config.draw_count
        )

        self._show_leaderboard_after_win(position)

        self.running = False

    def _render_initials_prompt(self, initials: str) -> None:
        """Render the initials prompt screen."""
        frame = self.term.home + self.term.clear

        highlighted = self._session.highlighted
        highlighted_tableau = highlighted.tableau_piles if highlighted else None
        highlighted_foundations = highlighted.foundation_piles if highlighted else None
        
        canvas = render_board(
            self._session.state,
            cursor_zone=self._session.cursor.zone.value,
            cursor_index=self._session.cursor.pile_index,
            cursor_card_index=self._session.cursor.card_index,
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
        
        self.dialogs.show_win_screen(lines, position, self.pad_left)

    def _show_leaderboard_ingame(self) -> None:
        """Show leaderboard overlay during game (L key)."""
        self.controller.pause_timer()

        lines = self.leaderboard.format_leaderboard(self.config.draw_count)

        frame = self.term.home + self.term.clear

        highlighted = self._session.highlighted
        highlighted_tableau = highlighted.tableau_piles if highlighted else None
        highlighted_foundations = highlighted.foundation_piles if highlighted else None
        
        canvas = render_board(
            self._session.state,
            cursor_zone=self._session.cursor.zone.value,
            cursor_index=self._session.cursor.pile_index,
            cursor_card_index=self._session.cursor.card_index,
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
        
        self.dialogs.show_leaderboard(lines, pad_left)

        self.controller.resume_timer()
        self.needs_redraw = True


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
