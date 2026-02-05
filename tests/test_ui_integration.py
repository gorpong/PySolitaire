"""Integration tests for SolitaireUI behavior.

These tests verify high-level game behaviors remain intact during refactoring.
They focus on state transitions and game flow rather than UI rendering details.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.model import Card, Suit, Rank, GameState
from src.cursor import CursorZone
from src.config import GameConfig
from src.selection import Selection, HighlightedDestinations
from src.ui_blessed import SolitaireUI
from src.dialogs import DialogManager


def make_card(rank: Rank, suit: Suit, face_up: bool = True) -> Card:
    """Helper to create cards concisely."""
    return Card(rank, suit, face_up)


class TestSelectionDataClass:
    """Tests for Selection data structure."""

    def test_selection_creation(self):
        sel = Selection(zone=CursorZone.WASTE)
        assert sel.zone == CursorZone.WASTE
        assert sel.pile_index == 0
        assert sel.card_index == 0

    def test_selection_with_indices(self):
        sel = Selection(zone=CursorZone.TABLEAU, pile_index=3, card_index=2)
        assert sel.zone == CursorZone.TABLEAU
        assert sel.pile_index == 3
        assert sel.card_index == 2


class TestHighlightedDestinations:
    """Tests for HighlightedDestinations data structure."""

    def test_empty_highlights(self):
        highlights = HighlightedDestinations(
            tableau_piles=set(),
            foundation_piles=set(),
        )
        assert len(highlights.tableau_piles) == 0
        assert len(highlights.foundation_piles) == 0

    def test_highlights_with_destinations(self):
        highlights = HighlightedDestinations(
            tableau_piles={0, 3, 5},
            foundation_piles={1},
        )
        assert 3 in highlights.tableau_piles
        assert 1 in highlights.foundation_piles
        assert 2 not in highlights.tableau_piles


class TestUIInitialization:
    """Tests for SolitaireUI setup."""

    @patch('src.ui_blessed.Terminal')
    def test_ui_creates_with_default_config(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)

        assert ui.config == config
        assert ui.controller.session.move_count == 0
        assert ui.controller.session.selection is None
        assert ui.running is True
        assert ui.show_help is False

    @patch('src.ui_blessed.Terminal')
    def test_ui_creates_with_draw3_config(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig(draw_count=3)
        ui = SolitaireUI(config)

        assert ui.config.draw_count == 3

    @patch('src.ui_blessed.Terminal')
    def test_ui_creates_with_seed(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig(seed=12345)
        ui1 = SolitaireUI(config)

        config2 = GameConfig(seed=12345)
        ui2 = SolitaireUI(config2)

        state1 = ui1.controller.session.state
        state2 = ui2.controller.session.state
        assert len(state1.stock) == len(state2.stock)
        for c1, c2 in zip(state1.stock, state2.stock):
            assert c1.rank == c2.rank
            assert c1.suit == c2.suit

    @patch('src.ui_blessed.Terminal')
    def test_ui_has_dialog_manager(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)

        assert hasattr(ui, 'dialogs')
        assert isinstance(ui.dialogs, DialogManager)


class TestUISelectionLogic:
    """Tests for card selection behavior."""

    @patch('src.ui_blessed.Terminal')
    def test_select_from_waste(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        ui.controller.session.cursor.zone = CursorZone.WASTE

        ui.controller.try_select()

        assert ui.controller.session.selection is not None
        assert ui.controller.session.selection.zone == CursorZone.WASTE

    @patch('src.ui_blessed.Terminal')
    def test_select_from_empty_waste_fails(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = []
        ui.controller.session.cursor.zone = CursorZone.WASTE

        ui.controller.try_select()

        assert ui.controller.session.selection is None
        assert "empty" in ui.controller.session.message.lower()

    @patch('src.ui_blessed.Terminal')
    def test_select_from_tableau_face_up(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0
        ui.controller.session.cursor.card_index = 0

        ui.controller.try_select()

        assert ui.controller.session.selection is not None
        assert ui.controller.session.selection.zone == CursorZone.TABLEAU
        assert ui.controller.session.selection.pile_index == 0

    @patch('src.ui_blessed.Terminal')
    def test_select_from_tableau_face_down_fails(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES, face_up=False)]
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0
        ui.controller.session.cursor.card_index = 0

        ui.controller.try_select()

        assert ui.controller.session.selection is None
        assert "face-down" in ui.controller.session.message.lower()

    @patch('src.ui_blessed.Terminal')
    def test_select_from_foundation(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.foundations[0] = [make_card(Rank.ACE, Suit.HEARTS)]
        ui.controller.session.cursor.zone = CursorZone.FOUNDATION
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_select()

        assert ui.controller.session.selection is not None
        assert ui.controller.session.selection.zone == CursorZone.FOUNDATION


class TestUIPlacementLogic:
    """Tests for card placement behavior."""

    @patch('src.ui_blessed.Terminal')
    def test_place_on_same_pile_cancels_selection(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        ui.controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0)
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_place()

        assert ui.controller.session.selection is None

    @patch('src.ui_blessed.Terminal')
    def test_place_waste_to_tableau_success(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        ui.controller.session.selection = Selection(zone=CursorZone.WASTE)
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_place()

        assert ui.controller.session.selection is None
        assert len(ui.controller.session.state.waste) == 0
        assert len(ui.controller.session.state.tableau[0]) == 2
        assert ui.controller.session.move_count == 1

    @patch('src.ui_blessed.Terminal')
    def test_place_waste_to_foundation_success(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        ui.controller.session.selection = Selection(zone=CursorZone.WASTE)
        ui.controller.session.cursor.zone = CursorZone.FOUNDATION
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_place()

        assert ui.controller.session.selection is None
        assert len(ui.controller.session.state.waste) == 0
        assert len(ui.controller.session.state.foundations[0]) == 1

    @patch('src.ui_blessed.Terminal')
    def test_place_invalid_move_keeps_selection(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.HEARTS)]
        ui.controller.session.selection = Selection(zone=CursorZone.WASTE)
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_place()

        assert ui.controller.session.selection is not None
        assert len(ui.controller.session.state.waste) == 1
        assert "invalid" in ui.controller.session.message.lower() or "cannot" in ui.controller.session.message.lower()


class TestUIStockActions:
    """Tests for stock draw and recycle behavior."""

    @patch('src.ui_blessed.Terminal')
    def test_draw_from_stock(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig(draw_count=1)
        ui = SolitaireUI(config)
        ui.controller.session.state.stock = [make_card(Rank.ACE, Suit.HEARTS, face_up=False)]
        ui.controller.session.state.waste = []

        ui.controller.handle_stock_action()

        assert len(ui.controller.session.state.stock) == 0
        assert len(ui.controller.session.state.waste) == 1
        assert ui.controller.session.state.waste[0].face_up is True

    @patch('src.ui_blessed.Terminal')
    def test_draw_three_from_stock(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig(draw_count=3)
        ui = SolitaireUI(config)
        ui.controller.session.state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
            make_card(Rank.THREE, Suit.HEARTS, face_up=False),
            make_card(Rank.FOUR, Suit.HEARTS, face_up=False),
        ]
        ui.controller.session.state.waste = []

        ui.controller.handle_stock_action()

        assert len(ui.controller.session.state.stock) == 1
        assert len(ui.controller.session.state.waste) == 3


class TestUIUndoSystem:
    """Tests for undo functionality."""

    @patch('src.ui_blessed.Terminal')
    def test_undo_restores_previous_state(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]

        ui.controller.session.selection = Selection(zone=CursorZone.WASTE)
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0
        ui.controller.try_place()

        assert len(ui.controller.session.state.tableau[0]) == 2
        assert ui.controller.session.move_count == 1

        ui.controller.undo()

        assert len(ui.controller.session.state.waste) == 1
        assert len(ui.controller.session.state.tableau[0]) == 1
        assert ui.controller.session.move_count == 0

    @patch('src.ui_blessed.Terminal')
    def test_undo_empty_stack_shows_message(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)

        ui.controller.undo()

        assert "nothing" in ui.controller.session.message.lower()


class TestUIWinDetection:
    """Tests for win condition detection."""

    @patch('src.ui_blessed.Terminal')
    def test_win_detected_with_full_foundations(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)

        for i, suit in enumerate([Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]):
            ui.controller.session.state.foundations[i] = [
                make_card(rank, suit) for rank in Rank
            ]

        total = sum(len(pile) for pile in ui.controller.session.state.foundations)
        assert total == 52
        assert ui.controller.check_win() is True


class TestUIProgressTracking:
    """Tests for stall detection progress tracking."""

    @patch('src.ui_blessed.Terminal')
    def test_progress_flag_set_on_successful_move(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.made_progress_since_last_recycle = False
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        ui.controller.session.selection = Selection(zone=CursorZone.WASTE)
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_place()

        assert ui.controller.session.made_progress_since_last_recycle is True

    @patch('src.ui_blessed.Terminal')
    def test_consecutive_burials_reset_on_move(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.consecutive_burials = 2
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        ui.controller.session.selection = Selection(zone=CursorZone.WASTE)
        ui.controller.session.cursor.zone = CursorZone.TABLEAU
        ui.controller.session.cursor.pile_index = 0

        ui.controller.try_place()

        assert ui.controller.session.consecutive_burials == 0


class TestUICardRetrieval:
    """Tests for getting cards at cursor or selection."""

    @patch('src.ui_blessed.Terminal')
    def test_get_card_under_cursor_waste(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.cursor.zone = CursorZone.WASTE

        card = ui.controller.get_card_under_cursor()

        assert card is not None
        assert card.rank == Rank.QUEEN

    @patch('src.ui_blessed.Terminal')
    def test_get_card_under_cursor_empty_returns_none(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = []
        ui.controller.session.cursor.zone = CursorZone.WASTE

        card = ui.controller.get_card_under_cursor()

        assert card is None

    @patch('src.ui_blessed.Terminal')
    def test_get_selected_card(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.tableau[2] = [
            make_card(Rank.KING, Suit.HEARTS),
            make_card(Rank.QUEEN, Suit.SPADES),
        ]
        ui.controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=2, card_index=1)

        card = ui.controller.get_selected_card()

        assert card is not None
        assert card.rank == Rank.QUEEN


class TestUIHintSystem:
    """Tests for valid destination highlighting."""

    @patch('src.ui_blessed.Terminal')
    def test_tab_shows_valid_destinations(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        ui.controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        ui.controller.session.state.tableau[1] = [make_card(Rank.KING, Suit.CLUBS)]
        ui.controller.session.state.tableau[2] = [make_card(Rank.KING, Suit.HEARTS)]
        ui.controller.session.cursor.zone = CursorZone.WASTE

        highlights = ui.controller.compute_valid_destinations()

        assert highlights is not None
        assert 0 in highlights.tableau_piles
        assert 1 in highlights.tableau_piles
        assert 2 not in highlights.tableau_piles

    @patch('src.ui_blessed.Terminal')
    def test_tab_no_valid_moves_shows_message(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.controller.session.state.waste = [make_card(Rank.FIVE, Suit.HEARTS)]
        ui.controller.session.state.tableau = [[] for _ in range(7)]
        ui.controller.session.cursor.zone = CursorZone.WASTE

        highlights = ui.controller.compute_valid_destinations()

        assert highlights is None
        assert "no valid" in ui.controller.session.message.lower()
