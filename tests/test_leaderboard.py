"""Tests for leaderboard functionality."""

import tempfile
from pathlib import Path
import pytest

from src.leaderboard import Leaderboard, LeaderboardEntry


class TestLeaderboardEntry:
    """Tests for LeaderboardEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a leaderboard entry."""
        entry = LeaderboardEntry(
            initials="ABC",
            moves=100,
            time_seconds=300,
            draw_mode=1,
        )
        assert entry.initials == "ABC"
        assert entry.moves == 100
        assert entry.time_seconds == 300
        assert entry.draw_mode == 1


class TestLeaderboard:
    """Tests for Leaderboard class."""

    @pytest.fixture
    def temp_leaderboard(self):
        """Create a temporary leaderboard file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_leaderboard_creation(self, temp_leaderboard):
        """Test creating a new leaderboard."""
        lb = Leaderboard(temp_leaderboard)
        assert lb.entries_draw1 == []
        assert lb.entries_draw3 == []

    def test_add_entry_draw1(self, temp_leaderboard):
        """Test adding an entry to Draw-1 leaderboard."""
        lb = Leaderboard(temp_leaderboard)
        position = lb.add_entry("ABC", 100, 300, 1)
        assert position == 1
        assert len(lb.entries_draw1) == 1
        assert lb.entries_draw1[0].initials == "ABC"
        assert lb.entries_draw1[0].moves == 100

    def test_add_entry_draw3(self, temp_leaderboard):
        """Test adding an entry to Draw-3 leaderboard."""
        lb = Leaderboard(temp_leaderboard)
        position = lb.add_entry("XYZ", 150, 400, 3)
        assert position == 1
        assert len(lb.entries_draw3) == 1
        assert lb.entries_draw3[0].initials == "XYZ"

    def test_sorting_by_moves_then_time(self, temp_leaderboard):
        """Test entries are sorted by moves first, then time."""
        lb = Leaderboard(temp_leaderboard)
        lb.add_entry("AAA", 100, 400, 1)  # 100 moves, 400 seconds
        lb.add_entry("BBB", 100, 300, 1)  # 100 moves, 300 seconds (better)
        lb.add_entry("CCC", 90, 500, 1)   # 90 moves (best)

        assert lb.entries_draw1[0].initials == "CCC"  # Fewest moves
        assert lb.entries_draw1[1].initials == "BBB"  # Same moves, less time
        assert lb.entries_draw1[2].initials == "AAA"

    def test_max_entries_limit(self, temp_leaderboard):
        """Test leaderboard keeps only top 20 entries."""
        lb = Leaderboard(temp_leaderboard)
        # Add 25 entries
        for i in range(25):
            lb.add_entry(f"A{i:02d}", 100 + i, 300, 1)

        assert len(lb.entries_draw1) == 20

    def test_persistence(self, temp_leaderboard):
        """Test leaderboard is persisted to disk."""
        lb1 = Leaderboard(temp_leaderboard)
        lb1.add_entry("ABC", 100, 300, 1)

        # Load in new instance
        lb2 = Leaderboard(temp_leaderboard)
        assert len(lb2.entries_draw1) == 1
        assert lb2.entries_draw1[0].initials == "ABC"

    def test_separate_draw1_and_draw3(self, temp_leaderboard):
        """Test Draw-1 and Draw-3 leaderboards are separate."""
        lb = Leaderboard(temp_leaderboard)
        lb.add_entry("AAA", 100, 300, 1)
        lb.add_entry("BBB", 150, 400, 3)

        assert len(lb.entries_draw1) == 1
        assert len(lb.entries_draw3) == 1
        assert lb.entries_draw1[0].initials == "AAA"
        assert lb.entries_draw3[0].initials == "BBB"

    def test_initials_uppercase(self, temp_leaderboard):
        """Test initials are converted to uppercase."""
        lb = Leaderboard(temp_leaderboard)
        lb.add_entry("abc", 100, 300, 1)
        assert lb.entries_draw1[0].initials == "ABC"

    def test_initials_padded(self, temp_leaderboard):
        """Test initials are padded to 3 characters."""
        lb = Leaderboard(temp_leaderboard)
        lb.add_entry("AB", 100, 300, 1)
        assert lb.entries_draw1[0].initials == "AB "

    def test_format_leaderboard_empty(self, temp_leaderboard):
        """Test formatting an empty leaderboard."""
        lb = Leaderboard(temp_leaderboard)
        lines = lb.format_leaderboard(1)
        assert len(lines) > 0
        assert "No entries yet" in ''.join(lines)

    def test_format_leaderboard_with_entries(self, temp_leaderboard):
        """Test formatting leaderboard with entries."""
        lb = Leaderboard(temp_leaderboard)
        lb.add_entry("AAA", 100, 300, 1)
        lb.add_entry("BBB", 150, 400, 1)

        lines = lb.format_leaderboard(1)
        result = ''.join(lines)
        assert "AAA" in result
        assert "BBB" in result
        assert "100" in result
        assert "05:00" in result  # 300 seconds = 5:00

    def test_position_returned_correctly(self, temp_leaderboard):
        """Test add_entry returns correct position."""
        lb = Leaderboard(temp_leaderboard)
        pos1 = lb.add_entry("AAA", 100, 300, 1)
        pos2 = lb.add_entry("BBB", 90, 250, 1)
        pos3 = lb.add_entry("CCC", 95, 270, 1)

        assert pos1 == 1  # First entry
        assert pos2 == 1  # Best score
        assert pos3 == 2  # Second best

    def test_position_outside_top_20(self, temp_leaderboard):
        """Test position returns -1 if outside top 20."""
        lb = Leaderboard(temp_leaderboard)
        # Fill with 20 entries with score 50
        for i in range(20):
            lb.add_entry(f"A{i:02d}", 50, 100, 1)

        # Add worse entry
        pos = lb.add_entry("ZZZ", 200, 500, 1)
        assert pos == -1
