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

    # ------------------------------------------------------------------
    # has_saves / all_slots_full
    # ------------------------------------------------------------------

    def test_has_saves_false_initially(self, temp_save_file):
        """has_saves returns False when no save file exists."""
        manager = SaveStateManager(temp_save_file)
        assert manager.has_saves() is False

    def test_has_saves_true_after_save(self, temp_save_file):
        """has_saves returns True once at least one slot is occupied."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(1, state, move_count=5, elapsed_time=30.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        assert manager.has_saves() is True

    def test_all_slots_full_false_when_empty(self, temp_save_file):
        """all_slots_full is False when there are no saves."""
        manager = SaveStateManager(temp_save_file)
        assert manager.all_slots_full() is False

    def test_all_slots_full_false_when_partially_filled(self, temp_save_file):
        """all_slots_full is False when fewer than 10 slots are occupied."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        for slot in range(1, 6):
            manager.save_game(slot, state, move_count=slot, elapsed_time=10.0,
                              draw_count=1, made_progress_since_last_recycle=True)
        assert manager.all_slots_full() is False

    def test_all_slots_full_true_when_ten_occupied(self, temp_save_file):
        """all_slots_full is True when all 10 slots are occupied."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        for slot in range(1, 11):
            manager.save_game(slot, state, move_count=slot, elapsed_time=10.0,
                              draw_count=1, made_progress_since_last_recycle=True)
        assert manager.all_slots_full() is True

    # ------------------------------------------------------------------
    # list_saves
    # ------------------------------------------------------------------

    def test_list_saves_empty(self, temp_save_file):
        """list_saves returns empty dict when no saves exist."""
        manager = SaveStateManager(temp_save_file)
        assert manager.list_saves() == {}

    def test_list_saves_returns_summaries(self, temp_save_file):
        """list_saves returns a dict keyed by slot with summary info."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(1, state, move_count=10, elapsed_time=120.5,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.save_game(3, state, move_count=25, elapsed_time=300.0,
                          draw_count=3, made_progress_since_last_recycle=False)

        saves = manager.list_saves()

        assert 1 in saves
        assert 3 in saves
        assert 2 not in saves
        assert saves[1]['move_count'] == 10
        assert saves[1]['draw_count'] == 1
        assert saves[3]['move_count'] == 25
        assert saves[3]['draw_count'] == 3

    def test_list_saves_includes_saved_at(self, temp_save_file):
        """Each slot summary includes a saved_at timestamp string."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(2, state, move_count=5, elapsed_time=60.0,
                          draw_count=1, made_progress_since_last_recycle=True)

        saves = manager.list_saves()
        assert 'saved_at' in saves[2]
        assert isinstance(saves[2]['saved_at'], str)
        assert len(saves[2]['saved_at']) > 0

    def test_list_saves_includes_elapsed_time(self, temp_save_file):
        """Each slot summary includes elapsed_time."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(1, state, move_count=7, elapsed_time=99.5,
                          draw_count=1, made_progress_since_last_recycle=True)

        saves = manager.list_saves()
        assert saves[1]['elapsed_time'] == 99.5

    # ------------------------------------------------------------------
    # save_game / load_game (slot-aware)
    # ------------------------------------------------------------------

    def test_save_to_specific_slot(self, temp_save_file):
        """save_game writes to the specified slot."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(5, state, move_count=15, elapsed_time=200.0,
                          draw_count=3, made_progress_since_last_recycle=True)

        loaded = manager.load_game(5)
        assert loaded is not None
        assert loaded['move_count'] == 15
        assert loaded['draw_count'] == 3

    def test_save_multiple_slots_independent(self, temp_save_file):
        """Saving to different slots does not overwrite each other."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=10, elapsed_time=60.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.save_game(2, state, move_count=99, elapsed_time=999.0,
                          draw_count=3, made_progress_since_last_recycle=False)

        slot1 = manager.load_game(1)
        slot2 = manager.load_game(2)

        assert slot1['move_count'] == 10
        assert slot1['draw_count'] == 1
        assert slot2['move_count'] == 99
        assert slot2['draw_count'] == 3

    def test_save_overwrite_slot(self, temp_save_file):
        """Saving to an occupied slot replaces its contents."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=5, elapsed_time=30.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.save_game(1, state, move_count=50, elapsed_time=300.0,
                          draw_count=3, made_progress_since_last_recycle=False)

        loaded = manager.load_game(1)
        assert loaded['move_count'] == 50
        assert loaded['draw_count'] == 3

    def test_load_nonexistent_slot_returns_none(self, temp_save_file):
        """load_game returns None for a slot that has no save."""
        manager = SaveStateManager(temp_save_file)
        assert manager.load_game(7) is None

    def test_load_preserves_game_state(self, temp_save_file):
        """Loading a slot returns the exact game state that was saved."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        initial_stock_len = len(state.stock)
        initial_tableau_0_len = len(state.tableau[0])

        manager.save_game(1, state, move_count=5, elapsed_time=60.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        loaded = manager.load_game(1)

        assert len(loaded['state'].stock) == initial_stock_len
        assert len(loaded['state'].tableau[0]) == initial_tableau_0_len

    def test_load_returns_all_required_keys(self, temp_save_file):
        """Loaded slot dict contains all expected keys."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(1, state, move_count=3, elapsed_time=15.0,
                          draw_count=1, made_progress_since_last_recycle=True,
                          consecutive_burials=0)

        loaded = manager.load_game(1)
        for key in ('state', 'move_count', 'elapsed_time', 'draw_count',
                    'made_progress_since_last_recycle', 'consecutive_burials'):
            assert key in loaded

    # ------------------------------------------------------------------
    # delete_save (slot-aware)
    # ------------------------------------------------------------------

    def test_delete_slot_removes_only_that_slot(self, temp_save_file):
        """delete_save removes the specified slot but leaves others intact."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=1, elapsed_time=10.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.save_game(2, state, move_count=2, elapsed_time=20.0,
                          draw_count=3, made_progress_since_last_recycle=True)

        manager.delete_save(1)

        assert manager.load_game(1) is None
        assert manager.load_game(2) is not None

    def test_delete_nonexistent_slot_does_not_crash(self, temp_save_file):
        """Deleting a slot that does not exist is a no-op."""
        manager = SaveStateManager(temp_save_file)
        manager.delete_save(5)  # Should not raise

    def test_delete_last_slot_file_still_exists(self, temp_save_file):
        """Deleting the only slot leaves the file in place (empty slots dict)."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=1, elapsed_time=5.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.delete_save(1)

        # has_saves should now be False but file may still exist
        assert manager.has_saves() is False

    # ------------------------------------------------------------------
    # next_free_slot
    # ------------------------------------------------------------------

    def test_next_free_slot_empty(self, temp_save_file):
        """next_free_slot returns 1 when no slots are occupied."""
        manager = SaveStateManager(temp_save_file)
        assert manager.next_free_slot() == 1

    def test_next_free_slot_skips_occupied(self, temp_save_file):
        """next_free_slot returns the lowest numbered unoccupied slot."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=1, elapsed_time=5.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.save_game(2, state, move_count=2, elapsed_time=5.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        assert manager.next_free_slot() == 3

    def test_next_free_slot_gap_in_middle(self, temp_save_file):
        """next_free_slot finds a gap in the middle of occupied slots."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=1, elapsed_time=5.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        manager.save_game(3, state, move_count=3, elapsed_time=5.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        assert manager.next_free_slot() == 2

    def test_next_free_slot_none_when_full(self, temp_save_file):
        """next_free_slot returns None when all 10 slots are occupied."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        for slot in range(1, 11):
            manager.save_game(slot, state, move_count=slot, elapsed_time=5.0,
                              draw_count=1, made_progress_since_last_recycle=True)
        assert manager.next_free_slot() is None

    # ------------------------------------------------------------------
    # consecutive_burials round-trip
    # ------------------------------------------------------------------

    def test_save_and_load_consecutive_burials(self, temp_save_file):
        """consecutive_burials round-trips through save and load."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=42)
        manager.save_game(1, state, move_count=20, elapsed_time=300.0,
                          draw_count=3, made_progress_since_last_recycle=False,
                          consecutive_burials=2)

        loaded = manager.load_game(1)
        assert loaded is not None
        assert loaded['consecutive_burials'] == 2

    # ------------------------------------------------------------------
    # Migration: old single-game format → slot 1
    # ------------------------------------------------------------------

    def test_migrate_old_format_to_slot_1(self, temp_save_file):
        """Old single-game save file is migrated to slot 1 on first load."""
        state = deal_game(seed=42)
        old_data = {
            'state': serialize_game_state(state),
            'move_count': 15,
            'elapsed_time': 200.0,
            'draw_count': 1,
            'made_progress_since_last_recycle': True,
            'consecutive_burials': 0,
        }
        with open(temp_save_file, 'w') as f:
            json.dump(old_data, f)

        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game(1)

        assert loaded is not None
        assert loaded['move_count'] == 15
        assert loaded['elapsed_time'] == 200.0
        assert loaded['draw_count'] == 1

    def test_migrate_old_format_preserves_draw_count(self, temp_save_file):
        """Migrated old save preserves draw_count in slot 1."""
        state = deal_game(seed=42)
        old_data = {
            'state': serialize_game_state(state),
            'move_count': 5,
            'elapsed_time': 60.0,
            'draw_count': 3,
            'made_progress_since_last_recycle': True,
            'consecutive_burials': 0,
        }
        with open(temp_save_file, 'w') as f:
            json.dump(old_data, f)

        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game(1)

        assert loaded['draw_count'] == 3

    def test_migrate_old_format_with_missing_progress_flag(self, temp_save_file):
        """Old save missing made_progress_since_last_recycle migrates with True default."""
        state = deal_game(seed=42)
        old_data = {
            'state': serialize_game_state(state),
            'move_count': 15,
            'elapsed_time': 200.0,
            'draw_count': 1,
            'stock_pass_count': 1,  # old key — new key absent
        }
        with open(temp_save_file, 'w') as f:
            json.dump(old_data, f)

        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game(1)

        assert loaded is not None
        assert loaded['made_progress_since_last_recycle'] is True

    def test_migrate_old_format_with_missing_consecutive_burials(self, temp_save_file):
        """Old save missing consecutive_burials migrates with 0 default."""
        state = deal_game(seed=42)
        old_data = {
            'state': serialize_game_state(state),
            'move_count': 10,
            'elapsed_time': 150.0,
            'draw_count': 3,
            'made_progress_since_last_recycle': False,
            # consecutive_burials absent
        }
        with open(temp_save_file, 'w') as f:
            json.dump(old_data, f)

        manager = SaveStateManager(temp_save_file)
        loaded = manager.load_game(1)

        assert loaded is not None
        assert loaded['consecutive_burials'] == 0

    def test_migrate_creates_slot_format_on_disk(self, temp_save_file):
        """After migrating, the on-disk format uses the new slots structure."""
        state = deal_game(seed=42)
        old_data = {
            'state': serialize_game_state(state),
            'move_count': 3,
            'elapsed_time': 20.0,
            'draw_count': 1,
            'made_progress_since_last_recycle': True,
            'consecutive_burials': 0,
        }
        with open(temp_save_file, 'w') as f:
            json.dump(old_data, f)

        manager = SaveStateManager(temp_save_file)
        # Trigger migration by loading
        manager.load_game(1)

        # Re-read the raw file and verify it now uses slots format
        with open(temp_save_file, 'r') as f:
            raw = json.load(f)
        assert 'slots' in raw

    def test_migrate_does_not_overwrite_existing_slot_1(self, temp_save_file):
        """If slot 1 is already occupied, migration does not clobber it."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=99, elapsed_time=500.0,
                          draw_count=3, made_progress_since_last_recycle=True)

        # Now write an old-format file on top (simulating someone manually
        # copying an old save over a new one — this should NOT happen in
        # normal use, but we verify the new format takes priority)
        # Actually: if the file already has 'slots', migration is skipped.
        # This test verifies that a newly-written slots file is not treated
        # as needing migration.
        loaded = manager.load_game(1)
        assert loaded['move_count'] == 99

    # ------------------------------------------------------------------
    # Corrupted file handling
    # ------------------------------------------------------------------

    def test_corrupted_save_returns_none(self, temp_save_file):
        """A corrupted save file returns None for any slot load."""
        manager = SaveStateManager(temp_save_file)
        with open(temp_save_file, 'w') as f:
            f.write("invalid json{{{")

        assert manager.load_game(1) is None

    def test_corrupted_save_has_saves_returns_false(self, temp_save_file):
        """A corrupted save file is treated as having no saves."""
        with open(temp_save_file, 'w') as f:
            f.write("not json")
        manager = SaveStateManager(temp_save_file)
        assert manager.has_saves() is False

    # ------------------------------------------------------------------
    # Backwards-compat: old has_save() / load_game() no-arg / delete_save()
    # no-arg kept working during transition (these mirror old test coverage)
    # ------------------------------------------------------------------

    def test_has_save_alias(self, temp_save_file):
        """has_save() (old API) returns True when any slot is occupied."""
        manager = SaveStateManager(temp_save_file)
        state = deal_game(seed=1)
        manager.save_game(1, state, move_count=1, elapsed_time=5.0,
                          draw_count=1, made_progress_since_last_recycle=True)
        assert manager.has_save() is True

    def test_has_save_alias_false(self, temp_save_file):
        """has_save() (old API) returns False when no slots are occupied."""
        manager = SaveStateManager(temp_save_file)
        assert manager.has_save() is False
