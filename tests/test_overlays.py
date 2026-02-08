"""Tests for UI overlay rendering functions."""


from pysolitaire.overlays import (
    format_time,
    render_help_lines,
    render_leaderboard_overlay_lines,
    render_resume_prompt_lines,
    render_save_slot_list,
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


class TestRenderSaveSlotList:
    """Tests for save slot list rendering."""

    def test_render_empty_slots_resume_mode(self):
        """Empty slot dict shows a 'no saved games' message in resume mode."""
        lines = render_save_slot_list({}, mode="resume")
        assert len(lines) > 0
        text = ''.join(lines)
        assert "No saved" in text or "no saved" in text.lower()

    def test_render_empty_slots_overwrite_mode(self):
        """Empty slot dict in overwrite mode still renders without error."""
        lines = render_save_slot_list({}, mode="overwrite")
        assert len(lines) > 0

    def test_render_shows_slot_numbers(self):
        """Slot numbers are visible in the output."""
        slots = {
            1: {'draw_count': 1, 'move_count': 10, 'elapsed_time': 60.0,
                'saved_at': '2026-02-07T14:00:00'},
            3: {'draw_count': 3, 'move_count': 25, 'elapsed_time': 300.0,
                'saved_at': '2026-02-07T15:30:00'},
        }
        lines = render_save_slot_list(slots, mode="resume")
        text = ''.join(lines)
        assert '1' in text
        assert '3' in text

    def test_render_shows_draw_type(self):
        """Draw mode (Draw-1 / Draw-3) is shown for each occupied slot."""
        slots = {
            1: {'draw_count': 1, 'move_count': 5, 'elapsed_time': 30.0,
                'saved_at': '2026-02-07T10:00:00'},
            2: {'draw_count': 3, 'move_count': 50, 'elapsed_time': 600.0,
                'saved_at': '2026-02-07T11:00:00'},
        }
        lines = render_save_slot_list(slots, mode="resume")
        text = ''.join(lines)
        assert 'Draw-1' in text or 'D1' in text
        assert 'Draw-3' in text or 'D3' in text

    def test_render_shows_move_count(self):
        """Move count is shown for each occupied slot."""
        slots = {
            2: {'draw_count': 1, 'move_count': 42, 'elapsed_time': 120.0,
                'saved_at': '2026-02-07T12:00:00'},
        }
        lines = render_save_slot_list(slots, mode="resume")
        text = ''.join(lines)
        assert '42' in text

    def test_render_shows_elapsed_time(self):
        """Elapsed time is shown formatted as MM:SS."""
        slots = {
            1: {'draw_count': 1, 'move_count': 7, 'elapsed_time': 125.0,
                'saved_at': '2026-02-07T09:00:00'},
        }
        lines = render_save_slot_list(slots, mode="resume")
        text = ''.join(lines)
        assert '02:05' in text

    def test_render_shows_saved_at(self):
        """Saved-at timestamp is shown for each occupied slot."""
        slots = {
            1: {'draw_count': 1, 'move_count': 3, 'elapsed_time': 20.0,
                'saved_at': '2026-02-07T08:30:00'},
        }
        lines = render_save_slot_list(slots, mode="resume")
        text = ''.join(lines)
        # At minimum the date portion should be visible
        assert '2026-02-07' in text or '08:30' in text

    def test_render_shows_empty_slots_available(self):
        """Unoccupied slot numbers are shown as available in resume mode."""
        slots = {
            1: {'draw_count': 1, 'move_count': 5, 'elapsed_time': 30.0,
                'saved_at': '2026-02-07T10:00:00'},
        }
        lines = render_save_slot_list(slots, mode="resume")
        text = ''.join(lines)
        # Slots 2-10 should be shown as empty
        assert 'empty' in text.lower() or '---' in text or '(empty)' in text

    def test_render_overwrite_mode_has_prompt_text(self):
        """Overwrite mode includes text indicating the player must pick a slot."""
        slots = {}
        for i in range(1, 11):
            slots[i] = {'draw_count': 1, 'move_count': i, 'elapsed_time': 10.0,
                        'saved_at': '2026-02-07T10:00:00'}
        lines = render_save_slot_list(slots, mode="overwrite")
        text = ''.join(lines)
        assert 'overwrite' in text.lower() or 'replace' in text.lower()

    def test_render_returns_list_of_strings(self):
        """Return type is always a list of strings."""
        result = render_save_slot_list({}, mode="resume")
        assert isinstance(result, list)
        assert all(isinstance(line, str) for line in result)

    def test_render_has_box_border(self):
        """Output has the standard box-drawing border."""
        lines = render_save_slot_list({}, mode="resume")
        assert lines[0].startswith("╔")
        assert lines[-1].startswith("╚")
