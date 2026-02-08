"""Integration tests for SolitaireUI behavior.

These tests verify high-level game behaviors remain intact during refactoring.
They focus on state transitions and game flow rather than UI rendering details.
"""

from unittest.mock import MagicMock, patch

from pysolitaire.config import GameConfig
from pysolitaire.cursor import CursorZone
from pysolitaire.dialogs import DialogManager
from pysolitaire.model import Card, GameState, Rank, Suit
from pysolitaire.selection import HighlightedDestinations, Selection
from pysolitaire.ui_blessed import SolitaireUI


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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
    def test_ui_creates_with_draw3_config(self, mock_terminal_class):
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig(draw_count=3)
        ui = SolitaireUI(config)

        assert ui.config.draw_count == 3

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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

    @patch('pysolitaire.ui_blessed.Terminal')
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


class TestUISlotManagement:
    """Tests for multi-slot save/resume flow."""

    @patch('pysolitaire.ui_blessed.Terminal')
    def test_ui_has_current_slot_attribute(self, mock_terminal_class):
        """SolitaireUI tracks which save slot is active."""
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)

        assert hasattr(ui, 'current_slot')

    @patch('pysolitaire.ui_blessed.Terminal')
    def test_resume_sets_draw_count_from_save(self, mock_terminal_class):
        """Resuming a Draw-3 save sets config.draw_count to 3."""
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig(draw_count=1)  # launched without --draw3
        ui = SolitaireUI(config)

        saved_data = {
            'state': GameState(),
            'move_count': 10,
            'elapsed_time': 60.0,
            'draw_count': 3,
            'made_progress_since_last_recycle': True,
            'consecutive_burials': 0,
        }
        ui.controller.load_from_dict(saved_data)

        assert ui.controller.config.draw_count == 3

    @patch('pysolitaire.ui_blessed.Terminal')
    def test_new_game_assigns_slot(self, mock_terminal_class):
        """Starting a new game assigns current_slot to the next free slot."""
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)

        # Simulate save manager reporting slot 3 as the next free
        ui.save_manager.next_free_slot = MagicMock(return_value=3)
        ui._assign_new_slot()

        assert ui.current_slot == 3

    @patch('pysolitaire.ui_blessed.Terminal')
    def test_save_on_quit_uses_current_slot(self, mock_terminal_class):
        """_save_current_game writes to current_slot."""
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.current_slot = 4
        ui.save_manager.save_game = MagicMock()

        ui._save_current_game()

        call_args = ui.save_manager.save_game.call_args
        assert call_args[0][0] == 4  # first positional arg is slot

    @patch('pysolitaire.ui_blessed.Terminal')
    def test_win_clears_current_slot(self, mock_terminal_class):
        """_clear_current_slot deletes the slot for the finished game."""
        mock_term = MagicMock()
        mock_term.width = 120
        mock_term.height = 50
        mock_terminal_class.return_value = mock_term

        config = GameConfig()
        ui = SolitaireUI(config)
        ui.current_slot = 2
        ui.save_manager.delete_save = MagicMock()

        ui._clear_current_slot()

        ui.save_manager.delete_save.assert_called_once_with(2)
