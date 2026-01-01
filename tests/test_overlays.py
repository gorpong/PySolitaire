"""Tests for UI overlay rendering functions."""

import pytest

from src.overlays import (
    render_help_lines,
    render_resume_prompt_lines,
    render_leaderboard_overlay_lines,
    format_time,
)


class TestFormatTime:
    """Tests for time formatting."""

    def test_format_time_zero(self):
        """Test formatting zero seconds."""
        assert format_time(0) == "00:00"

    def test_format_time_seconds_only(self):
        """Test formatting less than a minute."""
        assert format_time(45) == "00:45"

    def test_format_time_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_time(125) == "02:05"

    def test_format_time_large_value(self):
        """Test formatting large values."""
        assert format_time(3661) == "61:01"

    def test_format_time_float(self):
        """Test formatting float values (truncated)."""
        assert format_time(65.7) == "01:05"


class TestRenderHelpLines:
    """Tests for help overlay rendering."""

    def test_help_lines_not_empty(self):
        """Test that help lines are generated."""
        lines = render_help_lines()
        assert len(lines) > 0

    def test_help_lines_have_border(self):
        """Test that help lines have box borders."""
        lines = render_help_lines()
        assert lines[0].startswith("╔")
        assert lines[-1].startswith("╚")

    def test_help_lines_contain_controls(self):
        """Test that help lines include control information."""
        lines = render_help_lines()
        text = ''.join(lines)
        assert "Arrow Keys" in text
        assert "Enter" in text
        assert "Undo" in text
        assert "Quit" in text

    def test_help_lines_contain_leaderboard_key(self):
        """Test that L key for leaderboard is documented."""
        lines = render_help_lines()
        text = ''.join(lines)
        assert "L" in text
        assert "leaderboard" in text.lower()


class TestRenderResumePromptLines:
    """Tests for resume game prompt rendering."""

    def test_resume_prompt_not_empty(self):
        """Test that prompt lines are generated."""
        lines = render_resume_prompt_lines(10, 120.0)
        assert len(lines) > 0

    def test_resume_prompt_shows_moves(self):
        """Test that prompt shows move count."""
        lines = render_resume_prompt_lines(42, 300.0)
        text = ''.join(lines)
        assert "42" in text

    def test_resume_prompt_shows_time(self):
        """Test that prompt shows formatted time."""
        lines = render_resume_prompt_lines(10, 125.0)  # 2:05
        text = ''.join(lines)
        assert "02:05" in text

    def test_resume_prompt_has_options(self):
        """Test that prompt has resume and new game options."""
        lines = render_resume_prompt_lines(10, 120.0)
        text = ''.join(lines)
        assert "RESUME" in text or "Resume" in text
        assert "NEW" in text or "New" in text


class TestRenderLeaderboardOverlayLines:
    """Tests for leaderboard overlay rendering."""

    def test_leaderboard_not_empty(self):
        """Test that leaderboard lines are generated."""
        lines = render_leaderboard_overlay_lines(1, [])
        assert len(lines) > 0

    def test_leaderboard_shows_draw_mode(self):
        """Test that leaderboard shows draw mode."""
        lines = render_leaderboard_overlay_lines(1, [])
        text = ''.join(lines)
        assert "DRAW 1" in text or "Draw 1" in text

        lines3 = render_leaderboard_overlay_lines(3, [])
        text3 = ''.join(lines3)
        assert "DRAW 3" in text3 or "Draw 3" in text3

    def test_leaderboard_empty_message(self):
        """Test that empty leaderboard shows appropriate message."""
        lines = render_leaderboard_overlay_lines(1, [])
        text = ''.join(lines)
        assert "No entries" in text or "empty" in text.lower()

    def test_leaderboard_with_entries(self):
        """Test leaderboard with entry data."""
        entries = [
            {'initials': 'ABC', 'moves': 100, 'time_seconds': 300},
            {'initials': 'XYZ', 'moves': 150, 'time_seconds': 400},
        ]
        lines = render_leaderboard_overlay_lines(1, entries)
        text = ''.join(lines)
        assert "ABC" in text
        assert "100" in text
