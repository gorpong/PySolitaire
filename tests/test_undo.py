"""Tests for undo functionality."""

from copy import deepcopy

from pysolitaire.model import Card, GameState, Rank, Suit
from pysolitaire.undo import UndoStack, restore_state, save_state


class TestUndoStack:
    """Tests for undo stack operations."""

    def test_empty_stack_cannot_undo(self):
        stack = UndoStack()
        assert stack.can_undo() is False

    def test_push_enables_undo(self):
        stack = UndoStack()
        state = GameState()
        stack.push(state)
        assert stack.can_undo() is True

    def test_pop_returns_previous_state(self):
        stack = UndoStack()
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS)]
        stack.push(deepcopy(state))

        # Modify state
        state.stock = []

        # Pop should return original
        restored = stack.pop()
        assert len(restored.stock) == 1

    def test_multiple_undos(self):
        stack = UndoStack()

        state1 = GameState()
        state1.move_count = 0  # Using a marker
        stack.push(deepcopy(state1))

        state2 = GameState()
        state2.waste = [Card(Rank.TWO, Suit.HEARTS)]
        stack.push(deepcopy(state2))

        state3 = GameState()
        state3.waste = [Card(Rank.THREE, Suit.HEARTS)]
        stack.push(deepcopy(state3))

        # Pop returns most recent
        popped = stack.pop()
        assert popped.waste[0].rank == Rank.THREE

        popped = stack.pop()
        assert popped.waste[0].rank == Rank.TWO

        popped = stack.pop()
        assert len(popped.waste) == 0

    def test_pop_empty_returns_none(self):
        stack = UndoStack()
        assert stack.pop() is None

    def test_clear_stack(self):
        stack = UndoStack()
        state = GameState()
        stack.push(state)
        stack.push(state)
        stack.clear()
        assert stack.can_undo() is False

    def test_max_size_limit(self):
        stack = UndoStack(max_size=3)
        for i in range(5):
            state = GameState()
            state.stock = [Card(Rank.ACE, Suit.HEARTS)] * i
            stack.push(state)

        # Should only have 3 states (oldest discarded)
        count = 0
        while stack.can_undo():
            stack.pop()
            count += 1
        assert count == 3


class TestSaveRestoreState:
    """Tests for state save/restore helpers."""

    def test_save_creates_deep_copy(self):
        state = GameState()
        state.tableau[0] = [Card(Rank.KING, Suit.HEARTS, face_up=True)]

        saved = save_state(state)

        # Modify original
        state.tableau[0][0] = Card(Rank.QUEEN, Suit.SPADES, face_up=True)

        # Saved should be unchanged
        assert saved.tableau[0][0].rank == Rank.KING

    def test_restore_creates_deep_copy(self):
        saved = GameState()
        saved.foundations[0] = [Card(Rank.ACE, Suit.HEARTS, face_up=True)]

        state = GameState()
        restore_state(state, saved)

        # Modify restored state
        state.foundations[0] = []

        # Saved should be unchanged
        assert len(saved.foundations[0]) == 1

    def test_restore_replaces_all_fields(self):
        saved = GameState()
        saved.stock = [Card(Rank.ACE, Suit.HEARTS)]
        saved.waste = [Card(Rank.TWO, Suit.HEARTS)]
        saved.foundations[0] = [Card(Rank.THREE, Suit.HEARTS)]
        saved.tableau[0] = [Card(Rank.KING, Suit.SPADES)]

        state = GameState()
        restore_state(state, saved)

        assert len(state.stock) == 1
        assert len(state.waste) == 1
        assert len(state.foundations[0]) == 1
        assert len(state.tableau[0]) == 1
