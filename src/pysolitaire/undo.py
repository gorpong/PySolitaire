"""Undo functionality using command pattern with state snapshots."""

from copy import deepcopy
from typing import List, Optional

from pysolitaire.model import GameState


class UndoStack:
    """Stack of game states for undo functionality."""

    def __init__(self, max_size: int = 100):
        self._stack: List[GameState] = []
        self._max_size = max_size

    def push(self, state: GameState) -> None:
        """Push a state onto the stack."""
        # Deep copy to ensure independence
        self._stack.append(deepcopy(state))

        # Without a cap the stack would grow unbounded over a long session
        while len(self._stack) > self._max_size:
            self._stack.pop(0)

    def pop(self) -> Optional[GameState]:
        """Pop and return the most recent state, or None if empty."""
        if not self._stack:
            return None
        return self._stack.pop()

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._stack) > 0

    def clear(self) -> None:
        """Clear all saved states."""
        self._stack.clear()

    def __len__(self) -> int:
        return len(self._stack)


def save_state(state: GameState) -> GameState:
    """Create a deep copy of the game state for saving."""
    return deepcopy(state)


def restore_state(target: GameState, saved: GameState) -> None:
    """Restore a saved state into target state object."""
    # Deep copy each field to avoid reference issues
    target.stock = deepcopy(saved.stock)
    target.waste = deepcopy(saved.waste)
    target.foundations = deepcopy(saved.foundations)
    target.tableau = deepcopy(saved.tableau)
