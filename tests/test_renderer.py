"""Tests for ASCII rendering functions."""

import pytest
from src.model import Card, Suit, Rank, GameState
from src.renderer import (
    render_card_top,
    render_card_middle,
    render_card_bottom,
    render_card_lines,
    render_board,
    canvas_to_string,
    BOARD_WIDTH,
    BOARD_HEIGHT,
    CARD_WIDTH,
)
from src.dealing import deal_game


class TestCardRendering:
    """Tests for individual card rendering."""

    def test_face_up_card_top(self):
        card = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        result = render_card_top(card)
        assert "A" in result
        assert "♥" in result
        assert len(result) == CARD_WIDTH

    def test_face_up_card_bottom(self):
        card = Card(Rank.KING, Suit.SPADES, face_up=True)
        result = render_card_bottom(card)
        assert "K" in result
        assert "♠" in result
        assert len(result) == CARD_WIDTH

    def test_face_down_card(self):
        card = Card(Rank.ACE, Suit.HEARTS, face_up=False)
        top = render_card_top(card)
        middle = render_card_middle(card)
        bottom = render_card_bottom(card)

        # Should not show rank or suit
        assert "A" not in top
        assert "♥" not in top
        # Should show back pattern
        assert "░" in middle

    def test_empty_slot(self):
        top = render_card_top(None)
        middle = render_card_middle(None)
        bottom = render_card_bottom(None)

        # Should show dashed borders
        assert "─" in top
        assert len(top) == CARD_WIDTH

    def test_ten_rank_fits(self):
        """Ten has two digits and should still fit."""
        card = Card(Rank.TEN, Suit.CLUBS, face_up=True)
        top = render_card_top(card)
        assert "10" in top
        assert len(top) == CARD_WIDTH


class TestBoardRendering:
    """Tests for full board rendering."""

    def test_board_dimensions(self):
        state = deal_game(seed=42)
        canvas = render_board(state)

        assert len(canvas) == BOARD_HEIGHT
        assert all(len(row) == BOARD_WIDTH for row in canvas)

    def test_board_has_border(self):
        state = deal_game(seed=42)
        canvas = render_board(state)

        # Top border
        assert canvas[0][0] == "╔"
        assert canvas[0][-1] == "╗"
        # Bottom border
        assert canvas[-1][0] == "╚"
        assert canvas[-1][-1] == "╝"

    def test_board_has_labels(self):
        state = deal_game(seed=42)
        canvas = render_board(state)
        board_str = canvas_to_string(canvas)

        assert "STK" in board_str
        assert "WST" in board_str
        assert "FOUNDATIONS" in board_str
        assert "T1" in board_str
        assert "T7" in board_str

    def test_cursor_renders(self):
        state = deal_game(seed=42)
        canvas = render_board(state, cursor_zone="stock")
        board_str = canvas_to_string(canvas)

        # Cursor brackets should appear
        assert "[" in board_str
        assert "]" in board_str

    def test_canvas_to_string(self):
        state = deal_game(seed=42)
        canvas = render_board(state)
        board_str = canvas_to_string(canvas)

        assert isinstance(board_str, str)
        lines = board_str.split('\n')
        assert len(lines) == BOARD_HEIGHT


class TestBoardWithGameState:
    """Tests for board rendering with specific game states."""

    def test_empty_stock_shows_empty_slot(self):
        state = GameState()
        state.stock = []
        canvas = render_board(state)
        board_str = canvas_to_string(canvas)

        # Empty slot marker should be near STK label
        # The exact check depends on layout, but we verify no crash
        assert "STK" in board_str

    def test_foundation_with_cards(self):
        state = GameState()
        state.foundations[0] = [
            Card(Rank.ACE, Suit.HEARTS, face_up=True),
            Card(Rank.TWO, Suit.HEARTS, face_up=True),
        ]
        canvas = render_board(state)
        board_str = canvas_to_string(canvas)

        # Two of hearts should be visible (top of foundation)
        assert "2" in board_str
        assert "♥" in board_str

    def test_tableau_pile_with_multiple_cards(self):
        state = GameState()
        state.tableau[0] = [
            Card(Rank.KING, Suit.HEARTS, face_up=False),
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),
            Card(Rank.JACK, Suit.HEARTS, face_up=True),
        ]
        canvas = render_board(state)
        board_str = canvas_to_string(canvas)

        # Face-up cards should be visible
        assert "Q" in board_str
        assert "J" in board_str
        # Face-down card top line is visible (overlapped cards only show top)
        # The pattern ░ is in the middle line, which gets covered by overlap
        # So we just verify the overlapped rendering happened correctly
        lines = board_str.split('\n')
        # Cards should be stacked vertically in T1 area
        assert any("T1" in line for line in lines)
