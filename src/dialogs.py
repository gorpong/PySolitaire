"""Dialog management for modal user interactions.

This module handles all modal dialogs that pause the game and wait
for specific user input, such as confirmations, prompts, and
informational displays.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Any

from src.overlays import render_resume_prompt_lines
from src.renderer import BOARD_WIDTH


class DialogResult(Enum):
    """Result of a confirmation dialog.
    
    Attributes:
        CONFIRMED: User confirmed the action.
        CANCELLED: User cancelled the action.
    """
    CONFIRMED = auto()
    CANCELLED = auto()


@dataclass
class InitialsResult:
    """Result of the initials prompt dialog.
    
    Attributes:
        initials: The entered initials (3 characters), or "N/A" if cancelled.
        cancelled: True if the user cancelled entry.
    """
    initials: str
    cancelled: bool


class DialogManager:
    """Manages modal dialog interactions.
    
    Handles displaying dialogs and processing user input for
    confirmations, prompts, and informational screens.
    
    Attributes:
        term: The blessed Terminal instance for display and input.
    """

    def __init__(self, term: Any):
        self.term = term

    def confirm_quit(self) -> DialogResult:
        """Wait for quit confirmation.
        
        Returns CONFIRMED if user presses Q, CANCELLED otherwise.
        """
        key = self.term.inkey()
        if key.lower() == 'q':
            return DialogResult.CONFIRMED
        return DialogResult.CANCELLED

    def confirm_restart(self) -> DialogResult:
        """Wait for restart confirmation.
        
        Returns CONFIRMED if user presses R, CANCELLED otherwise.
        """
        key = self.term.inkey()
        if key.lower() == 'r':
            return DialogResult.CONFIRMED
        return DialogResult.CANCELLED

    def prompt_resume(self, move_count: int, elapsed_time: float) -> DialogResult:
        """Display resume game prompt and wait for response.
        
        Args:
            move_count: Number of moves in saved game.
            elapsed_time: Elapsed time in saved game.
            
        Returns:
            CONFIRMED if user wants to resume, CANCELLED for new game.
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
                return DialogResult.CONFIRMED
            elif key.lower() == 'n':
                return DialogResult.CANCELLED

    def prompt_bury_card(self) -> DialogResult:
        """Prompt user to bury top card in Draw-3 stall recovery.
        
        Returns CONFIRMED if user chooses to bury, CANCELLED otherwise.
        """
        while True:
            key = self.term.inkey()
            if key.lower() == 'y':
                return DialogResult.CONFIRMED
            elif key.lower() == 'n':
                return DialogResult.CANCELLED

    def prompt_initials(self, render_callback: Callable[[str], None]) -> InitialsResult:
        """Prompt user to enter 3-letter initials.
        
        Args:
            render_callback: Function to call with current initials for display.
                           Called before each keypress is processed.
        
        Returns:
            InitialsResult with the entered initials or cancellation status.
        """
        initials = ""

        while len(initials) < 3:
            render_callback(initials)

            key = self.term.inkey()

            if key.name == 'KEY_ESCAPE':
                return InitialsResult(initials="N/A", cancelled=True)
            elif key.name == 'KEY_BACKSPACE' or key.name == 'KEY_DELETE':
                if initials:
                    initials = initials[:-1]
            elif key.isalpha() and len(key) == 1:
                initials += str(key).upper()

        return InitialsResult(initials=initials, cancelled=False)

    def show_loss_screen(self) -> DialogResult:
        """Wait for user input on loss screen.
        
        Returns CONFIRMED if user wants to restart (R),
        CANCELLED if user wants to quit (Q).
        """
        while True:
            key = self.term.inkey()
            if key.lower() == 'r':
                return DialogResult.CONFIRMED
            elif key.lower() == 'q':
                return DialogResult.CANCELLED

    def show_leaderboard(self, lines: List[str], pad_left: int) -> None:
        """Display leaderboard overlay and wait for any key.
        
        Args:
            lines: Formatted leaderboard lines to display.
            pad_left: Left padding for centering.
        """
        self.term.inkey()

    def show_win_screen(self, lines: List[str], position: int, pad_left: int) -> None:
        """Display win screen with leaderboard and wait for any key.
        
        Args:
            lines: Formatted leaderboard lines to display.
            position: Player's position on leaderboard (0 if not ranked).
            pad_left: Left padding for centering.
        """
        self.term.inkey()
