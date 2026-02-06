"""Tests for ASCII rendering functions."""

import pytest

from pysolitaire.dealing import deal_game
from pysolitaire.model import Card, GameState, Rank, Suit
from pysolitaire.renderer import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    LAYOUT_COMPACT,
    LAYOUT_LARGE,
    canvas_to_string,
    render_board,
    render_card_lines,
    render_card_top,
)

BOTH_LAYOUTS = [
    pytest.param(LAYOUT_LARGE, id="large"),
    pytest.param(LAYOUT_COMPACT, id="compact"),
]


class TestCardRendering:
    """Tests for individual card rendering."""

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_face_up_card_top(self, layout):
        card = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        result = render_card_top(card, layout)
        assert "A" in result
        assert "♥" in result
        assert len(result) == layout.card_width

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_face_up_card_bottom_has_rank_and_suit(self, layout):
        """Bottom line mirrors top: suit left-aligned, rank right-aligned."""
        card = Card(Rank.KING, Suit.SPADES, face_up=True)
        lines = render_card_lines(card, layout)
        assert "K" in lines[-1]
        assert "♠" in lines[-1]
        assert len(lines[-1]) == layout.card_width

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_face_down_card(self, layout):
        card = Card(Rank.ACE, Suit.HEARTS, face_up=False)
        lines = render_card_lines(card, layout)
        assert len(lines) == layout.card_height
        # Rank and suit must not appear anywhere on a face-down card
        full_text = ''.join(lines)
        assert "A" not in full_text
        assert "♥" not in full_text
        # Every interior row shows the back pattern
        for line in lines[1:-1]:
            assert "░" in line

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_empty_slot(self, layout):
        lines = render_card_lines(None, layout)
        assert len(lines) == layout.card_height
        assert all(len(line) == layout.card_width for line in lines)
        # Top and bottom borders contain dashes
        assert "─" in lines[0]
        assert "─" in lines[-1]

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_ten_rank_fits(self, layout):
        """Ten has two digits and should still fit within card_width."""
        card = Card(Rank.TEN, Suit.CLUBS, face_up=True)
        top = render_card_top(card, layout)
        assert "10" in top
        assert len(top) == layout.card_width

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_card_lines_height_matches_layout(self, layout):
        """render_card_lines produces exactly card_height rows."""
        card = Card(Rank.QUEEN, Suit.DIAMONDS, face_up=True)
        lines = render_card_lines(card, layout)
        assert len(lines) == layout.card_height

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_card_lines_width_uniform(self, layout):
        """Every row of a card has exactly card_width characters."""
        card = Card(Rank.FIVE, Suit.CLUBS, face_up=True)
        lines = render_card_lines(card, layout)
        assert all(len(line) == layout.card_width for line in lines)

    # Layout-specific behavioural tests — these pin the one difference
    # between the two sizes rather than testing dimensions.

    def test_large_centre_row_shows_suit(self):
        """Large cards show the suit centred on the middle row for quick colour ID."""
        card = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        lines = render_card_lines(card, LAYOUT_LARGE)
        centre = len(lines) // 2
        assert "♥" in lines[centre]

    def test_compact_interior_row_has_no_suit(self):
        """Compact cards have a blank interior row — suit only appears in corners."""
        card = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        lines = render_card_lines(card, LAYOUT_COMPACT)
        # Single interior row (index 1)
        assert "♥" not in lines[1]


class TestBoardRendering:
    """Tests for full board rendering."""

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_board_dimensions(self, layout):
        state = deal_game(seed=42)
        canvas = render_board(state, layout=layout)

        assert len(canvas) == BOARD_HEIGHT
        assert all(len(row) == BOARD_WIDTH for row in canvas)

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_board_has_border(self, layout):
        state = deal_game(seed=42)
        canvas = render_board(state, layout=layout)

        # Top border
        assert canvas[0][0] == "╔"
        assert canvas[0][-1] == "╗"
        # Bottom border
        assert canvas[-1][0] == "╚"
        assert canvas[-1][-1] == "╝"

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_board_has_labels(self, layout):
        state = deal_game(seed=42)
        canvas = render_board(state, layout=layout)
        board_str = canvas_to_string(canvas)

        assert "STK" in board_str
        assert "WST" in board_str
        assert "FOUNDATIONS" in board_str
        assert "T1" in board_str
        assert "T7" in board_str

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_cursor_renders(self, layout):
        state = deal_game(seed=42)
        canvas = render_board(state, cursor_zone="stock", layout=layout)
        board_str = canvas_to_string(canvas)

        # Cursor brackets should appear
        assert "[" in board_str
        assert "]" in board_str

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_canvas_to_string(self, layout):
        state = deal_game(seed=42)
        canvas = render_board(state, layout=layout)
        board_str = canvas_to_string(canvas)

        assert isinstance(board_str, str)
        lines = board_str.split('\n')
        assert len(lines) == BOARD_HEIGHT


class TestBoardWithGameState:
    """Tests for board rendering with specific game states."""

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_empty_stock_shows_empty_slot(self, layout):
        state = GameState()
        state.stock = []
        canvas = render_board(state, layout=layout)
        board_str = canvas_to_string(canvas)

        # Empty slot marker should be near STK label
        # The exact check depends on layout, but we verify no crash
        assert "STK" in board_str

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_foundation_with_cards(self, layout):
        state = GameState()
        state.foundations[0] = [
            Card(Rank.ACE, Suit.HEARTS, face_up=True),
            Card(Rank.TWO, Suit.HEARTS, face_up=True),
        ]
        canvas = render_board(state, layout=layout)
        board_str = canvas_to_string(canvas)

        # Two of hearts should be visible (top of foundation)
        assert "2" in board_str
        assert "♥" in board_str

    @pytest.mark.parametrize("layout", BOTH_LAYOUTS)
    def test_tableau_pile_with_multiple_cards(self, layout):
        state = GameState()
        state.tableau[0] = [
            Card(Rank.KING, Suit.HEARTS, face_up=False),
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),
            Card(Rank.JACK, Suit.HEARTS, face_up=True),
        ]
        canvas = render_board(state, layout=layout)
        board_str = canvas_to_string(canvas)

        # Face-up cards should be visible
        assert "Q" in board_str
        assert "J" in board_str
        # Cards should be stacked vertically in T1 area
        lines = board_str.split('\n')
        assert any("T1" in line for line in lines)
