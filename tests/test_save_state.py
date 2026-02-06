"""Tests for save state functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from pysolitaire.dealing import deal_game
from pysolitaire.model import Card, Rank, Suit
from pysolitaire.save_state import (
    SaveStateManager,
    deserialize_game_state,
    serialize_game_state,
)


class TestSerialization:
    """Tests for game state serialization/deserialization."""

    def test_serialize_card(self):
        """Test serializing a card."""
        card = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        from pysolitaire.save_state import _serialize_card
        data = _serialize_card(card)
        assert data['rank'] == 1
        assert data['suit'] == 'hearts'
        assert data['face_up'] is True

    def test_deserialize_card(self):
        """Test deserializing a card."""
        data = {'rank': 1, 'suit': 'hearts', 'face_up': True}
        from pysolitaire.save_state import _deserialize_card
        card = _deserialize_card(data)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.HEARTS
        assert card.face_up is True

    def test_serialize_game_state(self):
        """Test serializing a game state."""
        state = deal_game(seed=42)
        data = serialize_game_state(state)

        assert 'stock' in data
        assert 'waste' in data
        assert 'foundations' in data
        assert 'tableau' in data
        assert len(data['foundations']) == 4
        assert len(data['tableau']) == 7

    def test_deserialize_game_state(self):
        """Test deserializing a game state."""
        state = deal_game(seed=42)
        data = serialize_game_state(state)
        restored = deserialize_game_state(data)

        assert len(restored.stock) == len(state.stock)
        assert len(restored.waste) == len(state.waste)
        assert len(restored.foundations) == 4
        assert len(restored.tableau) == 7

    def test_roundtrip_serialization(self):
        """Test that serialization->deserialization preserves state."""
        state = deal_game(seed=42)
        data = serialize_game_state(state)
        restored = deserialize_game_state(data)

        # Check stock
        assert len(restored.stock) == len(state.stock)
        for i, card in enumerate(state.stock):
            assert restored.stock[i].rank == card.rank
            assert restored.stock[i].suit == card.suit
            assert restored.stock[i].face_up == card.face_up

        # Check tableau
        for i in range(7):
            assert len(restored.tableau[i]) == len(state.tableau[i])


class TestSaveStateManager:
    """Tests for SaveStateManager class."""

    @pytest.fixture
    def temp_save_file(self):
        """Create a temporary save file path (doesn't create the file)."""
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"test_save_{id(self)}.json"
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_save_state_manager_creation(self, temp_save_file):
        """Test creating a save state manager."""
        manager = SaveStateManager(temp_save_file)
        assert manager.path == temp_save_file

    def test_has_save_false_initially(self, temp_save_file):
        """Test has_save returns False when no save exists."""
        manager = SaveStateManager(temp_save_file)
        assert manager.has_save() is False

    def test_save_game(self, temp_save_file):
        """Test saving a game."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)

        manager.save_game(state, move_count=10, elapsed_time=120.5, draw_count=1, made_progress_since_last_recycle=True)

        assert manager.has_save() is True
        assert temp_save_file.exists()

    def test_load_game(self, temp_save_file):
        """Test loading a game."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)

        manager.save_game(state, move_count=10, elapsed_time=120.5, draw_count=1, made_progress_since_last_recycle=True)

        loaded = manager.load_game()
        assert loaded is not None
        assert loaded['move_count'] == 10
        assert loaded['elapsed_time'] == 120.5
        assert loaded['draw_count'] == 1
        assert loaded['made_progress_since_last_recycle'] is True

    def test_load_nonexistent_returns_none(self, temp_save_file):
        """Test loading when no save exists returns None."""
        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game()
        assert loaded is None

    def test_delete_save(self, temp_save_file):
        """Test deleting a save file."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)

        manager.save_game(state, move_count=10, elapsed_time=120.5, draw_count=1, made_progress_since_last_recycle=True)
        assert manager.has_save() is True

        manager.delete_save()
        assert manager.has_save() is False

    def test_delete_nonexistent_save(self, temp_save_file):
        """Test deleting a save that doesn't exist doesn't crash."""
        manager = SaveStateManager(temp_save_file)
        manager.delete_save()  # Should not raise

    def test_save_preserves_game_state(self, temp_save_file):
        """Test that saving and loading preserves the game state."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)

        # Record initial state
        initial_stock_len = len(state.stock)
        initial_tableau_0_len = len(state.tableau[0])

        manager.save_game(state, move_count=5, elapsed_time=60.0, draw_count=1, made_progress_since_last_recycle=True)
        loaded = manager.load_game()

        assert len(loaded['state'].stock) == initial_stock_len
        assert len(loaded['state'].tableau[0]) == initial_tableau_0_len

    def test_corrupted_save_returns_none(self, temp_save_file):
        """Test that a corrupted save file returns None."""
        manager = SaveStateManager(temp_save_file)

        # Write invalid JSON
        with open(temp_save_file, 'w') as f:
            f.write("invalid json{{{")

        loaded = manager.load_game()
        assert loaded is None

    def test_old_format_save_defaults_progress_flag(self, temp_save_file):
        """Old save files missing made_progress_since_last_recycle default to True.

        Before this refactor the JSON key was stock_pass_count (an int).
        A save written by that version lacks made_progress_since_last_recycle,
        so load_game defaults it to True (benefit of the doubt: we cannot know
        whether the player saved at the start of a fresh pass or in the middle
        of one, so assume progress rather than risk a false loss on resume).
        """
        state = deal_game(seed=42)
        old_format_data = {
            'state': serialize_game_state(state),
            'move_count': 15,
            'elapsed_time': 200.0,
            'draw_count': 1,
            'stock_pass_count': 1,  # old key — made_progress_since_last_recycle is absent
        }

        with open(temp_save_file, 'w') as f:
            json.dump(old_format_data, f)

        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game()

        # Must load successfully, not collapse to None
        assert loaded is not None
        assert loaded['move_count'] == 15
        assert loaded['elapsed_time'] == 200.0
        # Progress flag defaults to True when missing (benefit of the doubt)
        assert loaded['made_progress_since_last_recycle'] is True

    def test_save_and_load_consecutive_burials(self, temp_save_file):
        """consecutive_burials round-trips through save and load.

        This counter tracks how many times in a row the Draw-3 bury
        mechanism fired without the player making a real move in between.
        It must survive a quit/resume cycle so a stall streak is not
        silently reset.
        """
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)

        manager.save_game(
            state,
            move_count=20,
            elapsed_time=300.0,
            draw_count=3,
            made_progress_since_last_recycle=False,
            consecutive_burials=2,
        )

        loaded = manager.load_game()
        assert loaded is not None
        assert loaded['consecutive_burials'] == 2

    def test_old_format_save_defaults_consecutive_burials_to_zero(self, temp_save_file):
        """Save files written before consecutive_burials existed load with zero.

        Zero is the generous default: it means no burials have happened yet
        this stall streak, which gives the player the full two-bury grace
        period on resume rather than falsely collapsing into an auto-loss.
        """
        state = deal_game(seed=42)
        old_format_data = {
            'state': serialize_game_state(state),
            'move_count': 10,
            'elapsed_time': 150.0,
            'draw_count': 3,
            'made_progress_since_last_recycle': False,
            # consecutive_burials key is intentionally absent
        }

        with open(temp_save_file, 'w') as f:
            json.dump(old_format_data, f)

        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game()

        assert loaded is not None
        assert loaded['consecutive_burials'] == 0
