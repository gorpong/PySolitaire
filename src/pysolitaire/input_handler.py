"""Input event handling and normalization for Solitaire.

This module translates raw terminal input (keyboard and mouse) into
normalized InputEvent objects that the game controller can process
without knowing about terminal-specific details.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class InputAction(Enum):
    """Normalized game actions triggered by user input.
    
    Attributes:
        MOVE_UP: Navigate cursor upward.
        MOVE_DOWN: Navigate cursor downward.
        MOVE_LEFT: Navigate cursor left.
        MOVE_RIGHT: Navigate cursor right.
        SELECT: Select card(s) or place selection (Enter).
        CANCEL: Cancel current selection (Escape).
        STOCK_ACTION: Draw from stock or recycle waste (Space).
        UNDO: Undo last move.
        RESTART: Restart the game.
        QUIT: Quit the game.
        HELP: Toggle help overlay.
        LEADERBOARD: Show leaderboard.
        SHOW_HINTS: Show valid placement destinations (Tab).
        MOUSE_DOWN: Mouse button pressed.
        MOUSE_UP: Mouse button released.
        NONE: No action (timeout or unrecognized input).
    """
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    SELECT = auto()
    CANCEL = auto()
    STOCK_ACTION = auto()
    UNDO = auto()
    RESTART = auto()
    QUIT = auto()
    HELP = auto()
    LEADERBOARD = auto()
    SHOW_HINTS = auto()
    MOUSE_DOWN = auto()
    MOUSE_UP = auto()
    NONE = auto()


_MOVEMENT_ACTIONS = frozenset({
    InputAction.MOVE_UP,
    InputAction.MOVE_DOWN,
    InputAction.MOVE_LEFT,
    InputAction.MOVE_RIGHT,
})

_MOUSE_ACTIONS = frozenset({
    InputAction.MOUSE_DOWN,
    InputAction.MOUSE_UP,
})


@dataclass
class InputEvent:
    """A normalized input event from keyboard or mouse.
    
    Attributes:
        action: The game action this input represents.
        mouse_x: Terminal X coordinate for mouse events, None otherwise.
        mouse_y: Terminal Y coordinate for mouse events, None otherwise.
    """
    action: InputAction
    mouse_x: Optional[int] = None
    mouse_y: Optional[int] = None

    @property
    def is_movement(self) -> bool:
        """Return True if this is a cursor movement action."""
        return self.action in _MOVEMENT_ACTIONS

    @property
    def is_mouse(self) -> bool:
        """Return True if this is a mouse-related action."""
        return self.action in _MOUSE_ACTIONS


class InputHandler:
    """Translates terminal input into normalized game actions.
    
    Handles keyboard input (arrow keys, letters, special keys) and
    optionally mouse input, converting them to InputEvent objects.
    
    Attributes:
        mouse_enabled: Whether to process mouse events.
    """

    def __init__(self, mouse_enabled: bool = True):
        self.mouse_enabled = mouse_enabled

    def process(self, key: Any) -> InputEvent:
        """Process a terminal key event and return normalized InputEvent.
        
        Args:
            key: A blessed terminal key object, or None for timeout.
            
        Returns:
            InputEvent representing the user's action.
        """
        if key is None or not key:
            return InputEvent(action=InputAction.NONE)

        key_name = getattr(key, 'name', None)

        if key_name == 'KEY_UP':
            return InputEvent(action=InputAction.MOVE_UP)
        elif key_name == 'KEY_DOWN':
            return InputEvent(action=InputAction.MOVE_DOWN)
        elif key_name == 'KEY_LEFT':
            return InputEvent(action=InputAction.MOVE_LEFT)
        elif key_name == 'KEY_RIGHT':
            return InputEvent(action=InputAction.MOVE_RIGHT)
        elif key_name == 'KEY_ENTER' or key == '\n':
            return InputEvent(action=InputAction.SELECT)
        elif key_name == 'KEY_ESCAPE':
            return InputEvent(action=InputAction.CANCEL)
        elif key_name == 'KEY_TAB' or key == '\t':
            return InputEvent(action=InputAction.SHOW_HINTS)
        elif key == ' ':
            return InputEvent(action=InputAction.STOCK_ACTION)

        key_char = str(key) if key else ''
        key_lower = key_char.lower() if key_char else ''

        if key_lower == 'q':
            return InputEvent(action=InputAction.QUIT)
        elif key_lower == 'u':
            return InputEvent(action=InputAction.UNDO)
        elif key_lower == 'r':
            return InputEvent(action=InputAction.RESTART)
        elif key_lower == 'h' or key_char == '?':
            return InputEvent(action=InputAction.HELP)
        elif key_lower == 'l':
            return InputEvent(action=InputAction.LEADERBOARD)

        return InputEvent(action=InputAction.NONE)

    def process_mouse_event(
        self,
        button: str,
        action: str,
        x: int,
        y: int,
    ) -> InputEvent:
        """Process a parsed mouse event.
        
        Args:
            button: Mouse button ('left', 'right', 'middle').
            action: Event type ('pressed', 'released').
            x: Terminal X coordinate.
            y: Terminal Y coordinate.
            
        Returns:
            InputEvent for the mouse action. Returns NONE action with no
            coordinates if mouse support is disabled.
        """
        if not self.mouse_enabled:
            return InputEvent(action=InputAction.NONE)

        if button == 'left':
            if action == 'pressed':
                return InputEvent(
                    action=InputAction.MOUSE_DOWN,
                    mouse_x=x,
                    mouse_y=y,
                )
            elif action == 'released':
                return InputEvent(
                    action=InputAction.MOUSE_UP,
                    mouse_x=x,
                    mouse_y=y,
                )
        elif button == 'right':
            if action == 'pressed':
                return InputEvent(action=InputAction.CANCEL)

        return InputEvent(action=InputAction.NONE)
