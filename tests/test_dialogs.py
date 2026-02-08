"""Tests for dialog management and modal interactions."""

from pysolitaire.dialogs import DialogManager, DialogResult, InitialsResult


class FakeKey:
    """A fake key for testing.
    
    Attributes:
        name: Key name like 'KEY_ESCAPE', 'KEY_BACKSPACE', etc.
        char: Character value for regular keys.
    """
    
    def __init__(self, char: str = '', name: str = None):
        self._char = char
        self.name = name
    
    def __bool__(self) -> bool:
        return bool(self._char or self.name)
    
    def __str__(self) -> str:
        return self._char
    
    def __eq__(self, other) -> bool:
        return self._char == other
    
    def lower(self) -> str:
        return self._char.lower() if self._char else ''
    
    def upper(self) -> str:
        return self._char.upper() if self._char else ''
    
    def isalpha(self) -> bool:
        return self._char.isalpha() if self._char else False
    
    def __len__(self) -> int:
        if self.name:
            return 1
        return len(self._char)


class FakeTerminal:
    """A fake Terminal for testing dialog interactions.
    
    Attributes:
        keys: List of keys to return from inkey() calls. Each element can be
              a string (character key) or a tuple of (char, name) for special keys.
        width: Terminal width.
        height: Terminal height.
    """
    
    def __init__(self, keys: list = None, width: int = 120, height: int = 50):
        self.keys = keys or []
        self._key_index = 0
        self.width = width
        self.height = height
    
    def inkey(self, timeout: float = None) -> FakeKey:
        if self._key_index < len(self.keys):
            key_data = self.keys[self._key_index]
            self._key_index += 1
            if isinstance(key_data, tuple):
                return FakeKey(char=key_data[0], name=key_data[1])
            return FakeKey(char=key_data)
        return FakeKey()
    
    def move_xy(self, x: int, y: int) -> str:
        return f"[MOVE:{x},{y}]"
    
    @property
    def home(self) -> str:
        return "[HOME]"
    
    @property
    def clear(self) -> str:
        return "[CLEAR]"
    
    def bright_white(self, text: str) -> str:
        return text
    
    def bright_yellow(self, text: str) -> str:
        return text
    
    def bright_cyan(self, text: str) -> str:
        return text
    
    def bright_red(self, text: str) -> str:
        return text
    
    def black_on_bright_white(self, text: str) -> str:
        return text


class TestDialogResult:
    """Tests for DialogResult enum."""

    def test_confirmed_exists(self):
        assert DialogResult.CONFIRMED is not None

    def test_cancelled_exists(self):
        assert DialogResult.CANCELLED is not None

    def test_confirmed_not_equal_cancelled(self):
        assert DialogResult.CONFIRMED != DialogResult.CANCELLED


class TestInitialsResult:
    """Tests for InitialsResult data class."""

    def test_initials_result_creation(self):
        result = InitialsResult(initials="ABC", cancelled=False)
        assert result.initials == "ABC"
        assert result.cancelled is False

    def test_initials_result_cancelled(self):
        result = InitialsResult(initials="N/A", cancelled=True)
        assert result.initials == "N/A"
        assert result.cancelled is True


class TestDialogManagerCreation:
    """Tests for DialogManager initialization."""

    def test_creates_with_terminal(self):
        term = FakeTerminal()
        manager = DialogManager(term)
        assert manager.term is term


class TestConfirmQuit:
    """Tests for quit confirmation dialog."""

    def test_confirm_quit_returns_confirmed_on_q(self):
        term = FakeTerminal(keys=['q'])
        manager = DialogManager(term)

        result = manager.confirm_quit()

        assert result == DialogResult.CONFIRMED

    def test_confirm_quit_returns_confirmed_on_Q(self):
        term = FakeTerminal(keys=['Q'])
        manager = DialogManager(term)

        result = manager.confirm_quit()

        assert result == DialogResult.CONFIRMED

    def test_confirm_quit_returns_cancelled_on_other_key(self):
        term = FakeTerminal(keys=['n'])
        manager = DialogManager(term)

        result = manager.confirm_quit()

        assert result == DialogResult.CANCELLED

    def test_confirm_quit_returns_cancelled_on_escape(self):
        term = FakeTerminal(keys=[('', 'KEY_ESCAPE')])
        manager = DialogManager(term)

        result = manager.confirm_quit()

        assert result == DialogResult.CANCELLED


class TestConfirmRestart:
    """Tests for restart confirmation dialog."""

    def test_confirm_restart_returns_confirmed_on_r(self):
        term = FakeTerminal(keys=['r'])
        manager = DialogManager(term)

        result = manager.confirm_restart()

        assert result == DialogResult.CONFIRMED

    def test_confirm_restart_returns_confirmed_on_R(self):
        term = FakeTerminal(keys=['R'])
        manager = DialogManager(term)

        result = manager.confirm_restart()

        assert result == DialogResult.CONFIRMED

    def test_confirm_restart_returns_cancelled_on_other_key(self):
        term = FakeTerminal(keys=['x'])
        manager = DialogManager(term)

        result = manager.confirm_restart()

        assert result == DialogResult.CANCELLED


class TestPromptResume:
    """Tests for resume game prompt."""

    def test_prompt_resume_returns_confirmed_on_r(self):
        term = FakeTerminal(keys=['r'])
        manager = DialogManager(term)

        result = manager.prompt_resume(move_count=10, elapsed_time=120.5)

        assert result == DialogResult.CONFIRMED

    def test_prompt_resume_returns_cancelled_on_n(self):
        term = FakeTerminal(keys=['n'])
        manager = DialogManager(term)

        result = manager.prompt_resume(move_count=10, elapsed_time=120.5)

        assert result == DialogResult.CANCELLED

    def test_prompt_resume_ignores_other_keys_until_valid(self):
        term = FakeTerminal(keys=['x', 'y', 'z', 'r'])
        manager = DialogManager(term)

        result = manager.prompt_resume(move_count=5, elapsed_time=60.0)

        assert result == DialogResult.CONFIRMED

    def test_prompt_resume_accepts_uppercase(self):
        term = FakeTerminal(keys=['R'])
        manager = DialogManager(term)

        result = manager.prompt_resume(move_count=5, elapsed_time=60.0)

        assert result == DialogResult.CONFIRMED


class TestPromptBuryCard:
    """Tests for bury card confirmation dialog."""

    def test_prompt_bury_returns_confirmed_on_y(self):
        term = FakeTerminal(keys=['y'])
        manager = DialogManager(term)

        result = manager.prompt_bury_card()

        assert result == DialogResult.CONFIRMED

    def test_prompt_bury_returns_confirmed_on_Y(self):
        term = FakeTerminal(keys=['Y'])
        manager = DialogManager(term)

        result = manager.prompt_bury_card()

        assert result == DialogResult.CONFIRMED

    def test_prompt_bury_returns_cancelled_on_n(self):
        term = FakeTerminal(keys=['n'])
        manager = DialogManager(term)

        result = manager.prompt_bury_card()

        assert result == DialogResult.CANCELLED

    def test_prompt_bury_returns_cancelled_on_N(self):
        term = FakeTerminal(keys=['N'])
        manager = DialogManager(term)

        result = manager.prompt_bury_card()

        assert result == DialogResult.CANCELLED

    def test_prompt_bury_ignores_other_keys(self):
        term = FakeTerminal(keys=['x', 'z', '1', 'y'])
        manager = DialogManager(term)

        result = manager.prompt_bury_card()

        assert result == DialogResult.CONFIRMED


class TestPromptInitials:
    """Tests for initials entry dialog."""

    def test_prompt_initials_accepts_three_letters(self):
        term = FakeTerminal(keys=['A', 'B', 'C'])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "ABC"
        assert result.cancelled is False

    def test_prompt_initials_converts_to_uppercase(self):
        term = FakeTerminal(keys=['a', 'b', 'c'])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "ABC"

    def test_prompt_initials_ignores_non_alpha(self):
        term = FakeTerminal(keys=['1', 'A', '!', 'B', ' ', 'C'])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "ABC"

    def test_prompt_initials_backspace_removes_char(self):
        term = FakeTerminal(keys=['A', 'B', ('', 'KEY_BACKSPACE'), 'C', 'D'])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "ACD"

    def test_prompt_initials_delete_removes_char(self):
        term = FakeTerminal(keys=['A', 'B', ('', 'KEY_DELETE'), 'C', 'D'])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "ACD"

    def test_prompt_initials_escape_cancels(self):
        term = FakeTerminal(keys=['A', ('', 'KEY_ESCAPE')])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "N/A"
        assert result.cancelled is True

    def test_prompt_initials_backspace_on_empty_is_safe(self):
        term = FakeTerminal(keys=[('', 'KEY_BACKSPACE'), 'A', 'B', 'C'])
        manager = DialogManager(term)

        result = manager.prompt_initials(render_callback=lambda i: None)

        assert result.initials == "ABC"

    def test_prompt_initials_calls_render_callback(self):
        term = FakeTerminal(keys=['A', 'B', 'C'])
        render_calls = []
        
        def mock_render(initials: str):
            render_calls.append(initials)
        
        manager = DialogManager(term)
        manager.prompt_initials(render_callback=mock_render)

        assert "" in render_calls
        assert "A" in render_calls
        assert "AB" in render_calls


class TestShowLossScreen:
    """Tests for loss screen dialog."""

    def test_loss_screen_returns_confirmed_on_r(self):
        term = FakeTerminal(keys=['r'])
        manager = DialogManager(term)

        result = manager.show_loss_screen()

        assert result == DialogResult.CONFIRMED

    def test_loss_screen_returns_cancelled_on_q(self):
        term = FakeTerminal(keys=['q'])
        manager = DialogManager(term)

        result = manager.show_loss_screen()

        assert result == DialogResult.CANCELLED

    def test_loss_screen_ignores_other_keys(self):
        term = FakeTerminal(keys=['x', 'y', '1', 'r'])
        manager = DialogManager(term)

        result = manager.show_loss_screen()

        assert result == DialogResult.CONFIRMED


class TestShowLeaderboard:
    """Tests for leaderboard display."""

    def test_show_leaderboard_waits_for_key(self):
        term = FakeTerminal(keys=['x'])
        manager = DialogManager(term)

        manager.show_leaderboard(lines=["Line 1", "Line 2"], pad_left=10)

        assert term._key_index == 1

    def test_show_leaderboard_accepts_any_key(self):
        term = FakeTerminal(keys=[' '])
        manager = DialogManager(term)

        manager.show_leaderboard(lines=[], pad_left=0)

        assert term._key_index == 1


class TestShowWinScreen:
    """Tests for win screen with leaderboard."""

    def test_win_screen_waits_for_key(self):
        term = FakeTerminal(keys=['x'])
        manager = DialogManager(term)

        manager.show_win_screen(
            lines=["Line 1"],
            position=1,
            pad_left=10,
        )

        assert term._key_index == 1

    def test_win_screen_shows_position_message(self):
        term = FakeTerminal(keys=[' '])
        manager = DialogManager(term)

        manager.show_win_screen(
            lines=["Leaderboard"],
            position=5,
            pad_left=0,
        )

        assert term._key_index == 1


class TestPromptSlotSelect:
    """Tests for save slot selection dialog."""

    def test_prompt_slot_select_returns_slot_number_1_to_9(self):
        """Pressing 1-9 returns that slot number."""
        for digit in '123456789':
            term = FakeTerminal(keys=[digit])
            manager = DialogManager(term)
            result = manager.prompt_slot_select(slots={}, pad_left=0)
            assert result == int(digit)

    def test_prompt_slot_select_0_returns_10(self):
        """Pressing 0 selects slot 10."""
        term = FakeTerminal(keys=['0'])
        manager = DialogManager(term)
        result = manager.prompt_slot_select(slots={}, pad_left=0)
        assert result == 10

    def test_prompt_slot_select_n_returns_negative_one(self):
        """Pressing N means 'new game' and returns -1 (not quit)."""
        term = FakeTerminal(keys=['n'])
        manager = DialogManager(term)
        result = manager.prompt_slot_select(slots={}, pad_left=0)
        assert result == -1

    def test_prompt_slot_select_uppercase_n_returns_negative_one(self):
        """Pressing N (uppercase) also means new game."""
        term = FakeTerminal(keys=['N'])
        manager = DialogManager(term)
        result = manager.prompt_slot_select(slots={}, pad_left=0)
        assert result == -1

    def test_prompt_slot_select_ignores_invalid_keys(self):
        """Non-digit, non-N keys are ignored until a valid key is pressed."""
        term = FakeTerminal(keys=['x', 'q', ' ', '3'])
        manager = DialogManager(term)
        result = manager.prompt_slot_select(slots={}, pad_left=0)
        assert result == 3

    def test_prompt_slot_select_escape_returns_none(self):
        """Escape means quit intent — returns None."""
        term = FakeTerminal(keys=[('', 'KEY_ESCAPE')])
        manager = DialogManager(term)
        result = manager.prompt_slot_select(slots={}, pad_left=0)
        assert result is None


class TestPromptOverwriteSlot:
    """Tests for overwrite slot selection dialog."""

    def test_prompt_overwrite_returns_slot_number(self):
        """Pressing a digit returns that slot number."""
        term = FakeTerminal(keys=['5'])
        manager = DialogManager(term)
        result = manager.prompt_overwrite_slot(slots={}, pad_left=0)
        assert result == 5

    def test_prompt_overwrite_0_returns_10(self):
        """Pressing 0 selects slot 10 for overwrite."""
        term = FakeTerminal(keys=['0'])
        manager = DialogManager(term)
        result = manager.prompt_overwrite_slot(slots={}, pad_left=0)
        assert result == 10

    def test_prompt_overwrite_n_returns_negative_one(self):
        """Pressing N cancels overwrite without quitting — returns -1."""
        term = FakeTerminal(keys=['n'])
        manager = DialogManager(term)
        result = manager.prompt_overwrite_slot(slots={}, pad_left=0)
        assert result == -1

    def test_prompt_overwrite_ignores_invalid_keys(self):
        """Non-digit, non-N keys are ignored."""
        term = FakeTerminal(keys=['a', 'b', '7'])
        manager = DialogManager(term)
        result = manager.prompt_overwrite_slot(slots={}, pad_left=0)
        assert result == 7
