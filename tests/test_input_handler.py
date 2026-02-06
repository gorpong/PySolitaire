"""Tests for input event handling and normalization."""

import pytest

from pysolitaire.input_handler import InputAction, InputEvent, InputHandler


class FakeKey:
    """A fake blessed key object for testing.
    
    Attributes:
        name: Key name like 'KEY_UP', 'KEY_ENTER', etc. None for character keys.
        char: Character value for regular keys.
    """
    
    def __init__(self, name: str = None, char: str = ''):
        self.name = name
        self._char = char
    
    def __bool__(self) -> bool:
        return bool(self.name or self._char)
    
    def __str__(self) -> str:
        return self._char
    
    def __len__(self) -> int:
        if self.name:
            return 1
        return len(self._char)
    
    def __eq__(self, other) -> bool:
        return self._char == other
    
    def lower(self) -> str:
        return self._char.lower() if self._char else ''
    
    def isalpha(self) -> bool:
        return self._char.isalpha() if self._char else False


class TestFakeKey:
    """Tests for FakeKey test helper to ensure it behaves correctly."""

    def test_empty_key_is_falsy(self):
        key = FakeKey()
        assert bool(key) is False

    def test_empty_key_has_zero_length(self):
        key = FakeKey()
        assert len(key) == 0

    def test_named_key_is_truthy(self):
        key = FakeKey(name='KEY_UP')
        assert bool(key) is True

    def test_named_key_has_length_one(self):
        key = FakeKey(name='KEY_UP')
        assert len(key) == 1

    def test_char_key_is_truthy(self):
        key = FakeKey(char='a')
        assert bool(key) is True

    def test_char_key_has_char_length(self):
        key = FakeKey(char='a')
        assert len(key) == 1

    def test_char_key_str_returns_char(self):
        key = FakeKey(char='q')
        assert str(key) == 'q'

    def test_char_key_equality(self):
        key = FakeKey(char='\n')
        assert key == '\n'
        assert key != '\t'


class TestInputAction:
    """Tests for InputAction enum values."""

    def test_movement_actions_exist(self):
        assert InputAction.MOVE_UP is not None
        assert InputAction.MOVE_DOWN is not None
        assert InputAction.MOVE_LEFT is not None
        assert InputAction.MOVE_RIGHT is not None

    def test_game_actions_exist(self):
        assert InputAction.SELECT is not None
        assert InputAction.CANCEL is not None
        assert InputAction.STOCK_ACTION is not None
        assert InputAction.UNDO is not None
        assert InputAction.RESTART is not None
        assert InputAction.QUIT is not None
        assert InputAction.HELP is not None
        assert InputAction.LEADERBOARD is not None
        assert InputAction.SHOW_HINTS is not None

    def test_mouse_actions_exist(self):
        assert InputAction.MOUSE_DOWN is not None
        assert InputAction.MOUSE_UP is not None

    def test_none_action_exists(self):
        assert InputAction.NONE is not None


class TestInputEvent:
    """Tests for InputEvent data structure."""

    def test_event_with_action_only(self):
        event = InputEvent(action=InputAction.MOVE_UP)
        assert event.action == InputAction.MOVE_UP
        assert event.mouse_x is None
        assert event.mouse_y is None

    def test_event_with_mouse_coordinates(self):
        event = InputEvent(
            action=InputAction.MOUSE_DOWN,
            mouse_x=42,
            mouse_y=15,
        )
        assert event.action == InputAction.MOUSE_DOWN
        assert event.mouse_x == 42
        assert event.mouse_y == 15

    def test_event_equality(self):
        event1 = InputEvent(action=InputAction.SELECT)
        event2 = InputEvent(action=InputAction.SELECT)
        assert event1 == event2

    def test_event_inequality(self):
        event1 = InputEvent(action=InputAction.SELECT)
        event2 = InputEvent(action=InputAction.CANCEL)
        assert event1 != event2

    def test_is_movement_true_for_movement_actions(self):
        assert InputEvent(action=InputAction.MOVE_UP).is_movement is True
        assert InputEvent(action=InputAction.MOVE_DOWN).is_movement is True
        assert InputEvent(action=InputAction.MOVE_LEFT).is_movement is True
        assert InputEvent(action=InputAction.MOVE_RIGHT).is_movement is True

    def test_is_movement_false_for_non_movement_actions(self):
        assert InputEvent(action=InputAction.SELECT).is_movement is False
        assert InputEvent(action=InputAction.QUIT).is_movement is False
        assert InputEvent(action=InputAction.MOUSE_DOWN).is_movement is False

    def test_is_mouse_true_for_mouse_actions(self):
        assert InputEvent(action=InputAction.MOUSE_DOWN).is_mouse is True
        assert InputEvent(action=InputAction.MOUSE_UP).is_mouse is True

    def test_is_mouse_false_for_non_mouse_actions(self):
        assert InputEvent(action=InputAction.SELECT).is_mouse is False
        assert InputEvent(action=InputAction.MOVE_UP).is_mouse is False


class TestInputHandlerCreation:
    """Tests for InputHandler initialization."""

    def test_default_mouse_enabled(self):
        handler = InputHandler()
        assert handler.mouse_enabled is True

    def test_mouse_disabled(self):
        handler = InputHandler(mouse_enabled=False)
        assert handler.mouse_enabled is False


class TestInputHandlerArrowKeys:
    """Tests for arrow key processing."""

    @pytest.mark.parametrize("key_name,expected_action", [
        ('KEY_UP', InputAction.MOVE_UP),
        ('KEY_DOWN', InputAction.MOVE_DOWN),
        ('KEY_LEFT', InputAction.MOVE_LEFT),
        ('KEY_RIGHT', InputAction.MOVE_RIGHT),
    ])
    def test_arrow_keys(self, key_name: str, expected_action: InputAction):
        handler = InputHandler()
        key = FakeKey(name=key_name)
        event = handler.process(key)
        assert event.action == expected_action


class TestInputHandlerSpecialKeys:
    """Tests for special key processing."""

    def test_enter_key(self):
        handler = InputHandler()
        key = FakeKey(name='KEY_ENTER')
        event = handler.process(key)
        assert event.action == InputAction.SELECT

    def test_newline_as_enter(self):
        handler = InputHandler()
        key = FakeKey(char='\n')
        event = handler.process(key)
        assert event.action == InputAction.SELECT

    def test_escape_key(self):
        handler = InputHandler()
        key = FakeKey(name='KEY_ESCAPE')
        event = handler.process(key)
        assert event.action == InputAction.CANCEL

    def test_tab_key(self):
        handler = InputHandler()
        key = FakeKey(name='KEY_TAB')
        event = handler.process(key)
        assert event.action == InputAction.SHOW_HINTS

    def test_tab_character(self):
        handler = InputHandler()
        key = FakeKey(char='\t')
        event = handler.process(key)
        assert event.action == InputAction.SHOW_HINTS

    def test_space_key(self):
        handler = InputHandler()
        key = FakeKey(char=' ')
        event = handler.process(key)
        assert event.action == InputAction.STOCK_ACTION


class TestInputHandlerLetterKeys:
    """Tests for letter key processing."""

    @pytest.mark.parametrize("char", ['q', 'Q'])
    def test_quit_key(self, char: str):
        handler = InputHandler()
        key = FakeKey(char=char)
        event = handler.process(key)
        assert event.action == InputAction.QUIT

    @pytest.mark.parametrize("char", ['u', 'U'])
    def test_undo_key(self, char: str):
        handler = InputHandler()
        key = FakeKey(char=char)
        event = handler.process(key)
        assert event.action == InputAction.UNDO

    @pytest.mark.parametrize("char", ['r', 'R'])
    def test_restart_key(self, char: str):
        handler = InputHandler()
        key = FakeKey(char=char)
        event = handler.process(key)
        assert event.action == InputAction.RESTART

    @pytest.mark.parametrize("char", ['h', 'H', '?'])
    def test_help_key(self, char: str):
        handler = InputHandler()
        key = FakeKey(char=char)
        event = handler.process(key)
        assert event.action == InputAction.HELP

    @pytest.mark.parametrize("char", ['l', 'L'])
    def test_leaderboard_key(self, char: str):
        handler = InputHandler()
        key = FakeKey(char=char)
        event = handler.process(key)
        assert event.action == InputAction.LEADERBOARD


class TestInputHandlerUnknownKeys:
    """Tests for unknown key handling."""

    @pytest.mark.parametrize("char", ['x', 'z', '5', '!', '@'])
    def test_unbound_keys_return_none_action(self, char: str):
        handler = InputHandler()
        key = FakeKey(char=char)
        event = handler.process(key)
        assert event.action == InputAction.NONE


class TestInputHandlerMouseEvents:
    """Tests for mouse event processing."""

    def test_process_mouse_down(self):
        handler = InputHandler(mouse_enabled=True)
        event = handler.process_mouse_event('left', 'pressed', 42, 15)
        assert event.action == InputAction.MOUSE_DOWN
        assert event.mouse_x == 42
        assert event.mouse_y == 15

    def test_process_mouse_up(self):
        handler = InputHandler(mouse_enabled=True)
        event = handler.process_mouse_event('left', 'released', 42, 15)
        assert event.action == InputAction.MOUSE_UP
        assert event.mouse_x == 42
        assert event.mouse_y == 15

    def test_process_right_click_cancels(self):
        handler = InputHandler(mouse_enabled=True)
        event = handler.process_mouse_event('right', 'pressed', 10, 10)
        assert event.action == InputAction.CANCEL

    def test_process_right_release_ignored(self):
        handler = InputHandler(mouse_enabled=True)
        event = handler.process_mouse_event('right', 'released', 10, 10)
        assert event.action == InputAction.NONE

    def test_process_unknown_button_ignored(self):
        handler = InputHandler(mouse_enabled=True)
        event = handler.process_mouse_event('middle', 'pressed', 10, 10)
        assert event.action == InputAction.NONE


class TestInputHandlerMouseDisabled:
    """Tests for mouse event handling when mouse support is disabled."""

    @pytest.mark.parametrize("button,action", [
        ('left', 'pressed'),
        ('left', 'released'),
        ('right', 'pressed'),
        ('right', 'released'),
        ('middle', 'pressed'),
    ])
    def test_mouse_events_ignored_when_disabled(self, button: str, action: str):
        handler = InputHandler(mouse_enabled=False)
        event = handler.process_mouse_event(button, action, 10, 20)
        assert event.action == InputAction.NONE
        assert event.mouse_x is None
        assert event.mouse_y is None


class TestInputHandlerTimeout:
    """Tests for timeout/no-input handling."""

    def test_none_key_returns_none_action(self):
        handler = InputHandler()
        event = handler.process(None)
        assert event.action == InputAction.NONE

    def test_empty_key_returns_none_action(self):
        handler = InputHandler()
        key = FakeKey()
        event = handler.process(key)
        assert event.action == InputAction.NONE
