"""Leaderboard functionality for Solitaire."""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class LeaderboardEntry:
    """Single leaderboard entry."""
    initials: str  # 3-letter initials
    moves: int
    time_seconds: int  # Rounded to nearest second
    draw_mode: int  # 1 or 3


class Leaderboard:
    """Manages leaderboard storage and retrieval."""

    MAX_ENTRIES = 20

    def __init__(self, leaderboard_path: Optional[Path] = None):
        """Initialize leaderboard.

        Args:
            leaderboard_path: Path to leaderboard file. If None, uses default in home dir.
        """
        if leaderboard_path is None:
            home = Path.home()
            config_dir = home / ".config" / "pysolitaire"
            config_dir.mkdir(parents=True, exist_ok=True)
            leaderboard_path = config_dir / "leaderboard.json"

        self.path = leaderboard_path
        self.entries_draw1: List[LeaderboardEntry] = []
        self.entries_draw3: List[LeaderboardEntry] = []
        self._load()

    def _load(self) -> None:
        """Load leaderboard from disk."""
        if not self.path.exists():
            return

        try:
            with open(self.path, 'r') as f:
                data = json.load(f)

            self.entries_draw1 = [
                LeaderboardEntry(**entry) for entry in data.get('draw1', [])
            ]
            self.entries_draw3 = [
                LeaderboardEntry(**entry) for entry in data.get('draw3', [])
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted file, start fresh
            self.entries_draw1 = []
            self.entries_draw3 = []

    def _save(self) -> None:
        """Save leaderboard to disk."""
        data = {
            'draw1': [asdict(entry) for entry in self.entries_draw1],
            'draw3': [asdict(entry) for entry in self.entries_draw3],
        }

        with open(self.path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_entry(self, initials: str, moves: int, time_seconds: int, draw_mode: int) -> int:
        """Add a new entry to the leaderboard.

        Returns the 1-based position of the entry (1 = best), or -1 if not in top 20.
        """
        entry = LeaderboardEntry(
            initials=initials.upper()[:3].ljust(3),  # Ensure 3 chars, uppercase
            moves=moves,
            time_seconds=time_seconds,
            draw_mode=draw_mode,
        )

        # Choose the right list
        entries = self.entries_draw1 if draw_mode == 1 else self.entries_draw3

        # Add entry
        entries.append(entry)

        # Sort by moves (primary), then time (secondary)
        entries.sort(key=lambda e: (e.moves, e.time_seconds))

        # Keep only top MAX_ENTRIES
        entries[:] = entries[:self.MAX_ENTRIES]

        # Update the correct list
        if draw_mode == 1:
            self.entries_draw1 = entries
        else:
            self.entries_draw3 = entries

        # Save to disk
        self._save()

        # Find position (1-indexed)
        try:
            position = entries.index(entry) + 1
            return position
        except ValueError:
            return -1  # Not in top 20

    def get_entries(self, draw_mode: int) -> List[LeaderboardEntry]:
        """Get all entries for a specific draw mode."""
        return self.entries_draw1 if draw_mode == 1 else self.entries_draw3

    def format_leaderboard(self, draw_mode: int) -> List[str]:
        """Format leaderboard as strings for display.

        Returns list of strings, one per line.
        """
        entries = self.get_entries(draw_mode)

        if not entries:
            return [
                "╔══════════════════════════════════════╗",
                f"║     LEADERBOARD - DRAW {draw_mode}             ║",
                "╠══════════════════════════════════════╣",
                "║                                      ║",
                "║         No entries yet!              ║",
                "║                                      ║",
                "╚══════════════════════════════════════╝",
            ]

        lines = [
            "╔══════════════════════════════════════╗",
            f"║     LEADERBOARD - DRAW {draw_mode}             ║",
            "╠═══╦═════╦════════╦══════════════════╣",
            "║ # ║ INI ║ MOVES  ║ TIME             ║",
            "╠═══╬═════╬════════╬══════════════════╣",
        ]

        for i, entry in enumerate(entries, 1):
            minutes = entry.time_seconds // 60
            seconds = entry.time_seconds % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            line = f"║{i:2d} ║ {entry.initials} ║  {entry.moves:4d}  ║ {time_str:16s}║"
            lines.append(line)

        lines.append("╚═══╩═════╩════════╩══════════════════╝")

        return lines
