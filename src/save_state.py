"""Save state functionality for Solitaire."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from src.model import GameState, Card, Suit, Rank


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


class SaveStateManager:
    """Manages saving and loading game state."""

    def __init__(self, save_path: Optional[Path] = None):
        """Initialize save state manager.

        Args:
            save_path: Path to save file. If None, uses default in home dir.
        """
        if save_path is None:
            home = Path.home()
            config_dir = home / ".config" / "pysolitaire"
            config_dir.mkdir(parents=True, exist_ok=True)
            save_path = config_dir / "save.json"

        self.path = save_path

    def save_game(
        self,
        state: GameState,
        move_count: int,
        elapsed_time: float,
        draw_count: int,
        made_progress_since_last_recycle: bool,
        consecutive_burials: int = 0,
    ) -> None:
        """Save game state to disk."""
        data = {
            'state': serialize_game_state(state),
            'move_count': move_count,
            'elapsed_time': elapsed_time,
            'draw_count': draw_count,
            'made_progress_since_last_recycle': made_progress_since_last_recycle,
            'consecutive_burials': consecutive_burials,
        }

        with open(self.path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_game(self) -> Optional[Dict[str, Any]]:
        """Load game state from disk.

        Returns dict with keys: state, move_count, elapsed_time, draw_count,
        made_progress_since_last_recycle, consecutive_burials — or None if the
        file does not exist or is structurally corrupted (missing core keys
        like state/move_count).

        made_progress_since_last_recycle defaults to True when missing so that
        a resumed game is not falsely treated as stalled; we cannot know whether
        the player saved at the start of a fresh pass or mid-pass, so the
        benefit of the doubt avoids an unjust loss on resume.

        consecutive_burials defaults to 0 when missing, granting the player the
        full two-bury grace period on resume rather than collapsing a stall
        streak that may never have started.
        """
        if not self.path.exists():
            return None

        try:
            with open(self.path, 'r') as f:
                data = json.load(f)

            return {
                'state': deserialize_game_state(data['state']),
                'move_count': data['move_count'],
                'elapsed_time': data['elapsed_time'],
                'draw_count': data['draw_count'],
                'made_progress_since_last_recycle': data.get(
                    'made_progress_since_last_recycle', True
                ),
                'consecutive_burials': data.get('consecutive_burials', 0),
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            # Covers corrupted JSON and saves missing core structural keys
            return None

    def delete_save(self) -> None:
        """Delete the save file."""
        if self.path.exists():
            self.path.unlink()

    def has_save(self) -> bool:
        """Check if a save file exists."""
        return self.path.exists()
