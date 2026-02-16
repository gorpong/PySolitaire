"""Save state functionality for Solitaire."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pysolitaire.model import Card, GameState, Rank, Suit

MAX_SAVE_SLOTS = 10


def _serialize_card(card: Card) -> Dict[str, Any]:
    """Serialize a Card to a dict."""
    return {
        'rank': card.rank.value,
        'suit': card.suit.value,
        'face_up': card.face_up,
    }


def _deserialize_card(data: Dict[str, Any]) -> Card:
    """Deserialize a Card from a dict."""
    return Card(
        rank=Rank(data['rank']),
        suit=Suit(data['suit']),
        face_up=data['face_up'],
    )


def serialize_game_state(state: GameState) -> Dict[str, Any]:
    """Serialize GameState to a dict."""
    return {
        'stock': [_serialize_card(card) for card in state.stock],
        'waste': [_serialize_card(card) for card in state.waste],
        'foundations': [
            [_serialize_card(card) for card in pile]
            for pile in state.foundations
        ],
        'tableau': [
            [_serialize_card(card) for card in pile]
            for pile in state.tableau
        ],
    }


def deserialize_game_state(data: Dict[str, Any]) -> GameState:
    """Deserialize GameState from a dict."""
    return GameState(
        stock=[_deserialize_card(card) for card in data['stock']],
        waste=[_deserialize_card(card) for card in data['waste']],
        foundations=[
            [_deserialize_card(card) for card in pile]
            for pile in data['foundations']
        ],
        tableau=[
            [_deserialize_card(card) for card in pile]
            for pile in data['tableau']
        ],
    )


def _is_old_format(data: Dict[str, Any]) -> bool:
    """Return True if data looks like the pre-slot single-game format.

    The old format has a top-level 'state' key but no 'slots' key.
    """
    return 'state' in data and 'slots' not in data


def _migrate_old_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old single-game save dict to the new slots format.

    The old game is placed in slot 1.  Missing fields are given safe
    defaults so that the resume path never triggers a false stall loss.
    """
    slot_entry = {
        'state': data['state'],
        'move_count': data['move_count'],
        'elapsed_time': data['elapsed_time'],
        'draw_count': data['draw_count'],
        'made_progress_since_last_recycle': data.get(
            'made_progress_since_last_recycle', True
        ),
        'consecutive_burials': data.get('consecutive_burials', 0),
        'saved_at': datetime.now().isoformat(timespec='seconds'),
    }
    return {'slots': {'1': slot_entry}}


def _load_raw(path: Path) -> Optional[Dict[str, Any]]:
    """Read and JSON-parse the save file.  Returns None on any error."""
    if not path.exists():
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_raw(path: Path, data: Dict[str, Any]) -> None:
    """Write data as JSON to path."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


class SaveStateManager:
    """Manages saving and loading game state across up to 10 save slots.

    Save file format (new)::

        {
          "slots": {
            "1": {
              "state": { ... },
              "move_count": 42,
              "elapsed_time": 183.5,
              "draw_count": 1,
              "made_progress_since_last_recycle": true,
              "consecutive_burials": 0,
              "saved_at": "2026-02-07T14:23:00"
            },
            ...
          }
        }

    Old single-game saves (no ``slots`` key) are automatically migrated
    to slot 1 the first time they are read.
    """

    def __init__(self, save_path: Optional[Path] = None):
        """Initialize save state manager.

        Args:
            save_path: Path to save file.  If None, uses the default
                location ``~/.config/pysolitaire/save.json``.
        """
        if save_path is None:
            home = Path.home()
            config_dir = home / ".config" / "pysolitaire"
            config_dir.mkdir(parents=True, exist_ok=True)
            save_path = config_dir / "save.json"

        self.path = save_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_slots(self) -> Dict[int, Any]:
        """Return the slots dict (keyed by int) from disk, or empty dict.

        Handles migration of old single-game format transparently.
        After a successful migration the new format is written back so
        subsequent loads skip the migration step.
        """
        raw = _load_raw(self.path)
        if raw is None:
            return {}

        if _is_old_format(raw):
            migrated = _migrate_old_format(raw)
            _write_raw(self.path, migrated)
            raw = migrated

        slots_raw = raw.get('slots', {})
        # JSON keys are always strings; convert to int for internal use
        return {int(k): v for k, v in slots_raw.items()}

    def _save_slots(self, slots: Dict[int, Any]) -> None:
        """Persist the slots dict to disk (keys stored as strings)."""
        _write_raw(self.path, {'slots': {str(k): v for k, v in slots.items()}})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_saves(self) -> bool:
        """Return True if at least one save slot is occupied."""
        return bool(self._load_slots())

    def has_save(self) -> bool:
        """Alias for has_saves() — kept for backwards compatibility."""
        return self.has_saves()

    def all_slots_full(self) -> bool:
        """Return True when all MAX_SAVE_SLOTS slots are occupied."""
        return len(self._load_slots()) >= MAX_SAVE_SLOTS

    def next_free_slot(self) -> Optional[int]:
        """Return the lowest-numbered free slot (1–10), or None if full."""
        occupied = set(self._load_slots().keys())
        for slot in range(1, MAX_SAVE_SLOTS + 1):
            if slot not in occupied:
                return slot
        return None

    def list_saves(self) -> Dict[int, Dict[str, Any]]:
        """Return a summary dict for all occupied slots.

        Each entry contains: ``move_count``, ``elapsed_time``,
        ``draw_count``, ``saved_at``.  The full game state is *not*
        included to keep the summary lightweight.

        Returns:
            Dict keyed by slot number (int) → summary dict.
        """
        slots = self._load_slots()
        summaries = {}
        for slot_num, entry in slots.items():
            summaries[slot_num] = {
                'move_count': entry['move_count'],
                'elapsed_time': entry['elapsed_time'],
                'draw_count': entry['draw_count'],
                'saved_at': entry.get('saved_at', ''),
            }
        return summaries

    def save_game(
        self,
        slot: int,
        state: GameState,
        move_count: int,
        elapsed_time: float,
        draw_count: int,
        made_progress_since_last_recycle: bool,
        consecutive_burials: int = 0,
    ) -> None:
        """Save a game to the specified slot.

        Args:
            slot: Slot number (1–10).  Overwrites any existing save in
                that slot.
            state: Current game state.
            move_count: Number of moves made.
            elapsed_time: Elapsed game time in seconds.
            draw_count: Draw mode (1 or 3).
            made_progress_since_last_recycle: Stall-detection flag.
            consecutive_burials: Draw-3 burial counter.
        """
        slots = self._load_slots()
        slots[slot] = {
            'state': serialize_game_state(state),
            'move_count': move_count,
            'elapsed_time': elapsed_time,
            'draw_count': draw_count,
            'made_progress_since_last_recycle': made_progress_since_last_recycle,
            'consecutive_burials': consecutive_burials,
            'saved_at': datetime.now().isoformat(timespec='seconds'),
        }
        self._save_slots(slots)

    def load_game(self, slot: int) -> Optional[Dict[str, Any]]:
        """Load a game from the specified slot.

        Returns a dict with keys: ``state``, ``move_count``,
        ``elapsed_time``, ``draw_count``,
        ``made_progress_since_last_recycle``, ``consecutive_burials`` —
        or ``None`` if the slot is empty or the file is corrupted.

        Missing optional fields are given safe defaults:

        * ``made_progress_since_last_recycle`` → ``True`` (avoids false
          stall loss on resume when history is unknown).
        * ``consecutive_burials`` → ``0`` (grants full two-bury grace
          period on resume).
        """
        slots = self._load_slots()
        entry = slots.get(slot)
        if entry is None:
            return None

        try:
            return {
                'state': deserialize_game_state(entry['state']),
                'move_count': entry['move_count'],
                'elapsed_time': entry['elapsed_time'],
                'draw_count': entry['draw_count'],
                'made_progress_since_last_recycle': entry.get(
                    'made_progress_since_last_recycle', True
                ),
                'consecutive_burials': entry.get('consecutive_burials', 0),
            }
        except (KeyError, TypeError):
            return None

    def delete_save(self, slot: int) -> None:
        """Remove the save in the specified slot.

        No-op if the slot is empty or the file does not exist.
        """
        slots = self._load_slots()
        slots.pop(slot, None)
        self._save_slots(slots)
