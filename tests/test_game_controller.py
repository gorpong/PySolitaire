"""Tests for game controller and session management."""

import pytest

from pysolitaire.config import GameConfig
from pysolitaire.cursor import Cursor, CursorZone
from pysolitaire.game_controller import GameController
from pysolitaire.model import Card, GameState, Rank, Suit
from pysolitaire.selection import Selection


def make_card(rank: Rank, suit: Suit, face_up: bool = True) -> Card:
    """Helper to create cards concisely."""
    return Card(rank, suit, face_up)


class TestGameSessionCreation:
    """Tests for GameSession initialization."""

    def test_session_has_required_attributes(self):
        config = GameConfig()
        controller = GameController(config)
        session = controller.session

        assert isinstance(session.state, GameState)
        assert isinstance(session.cursor, Cursor)
        assert session.selection is None
        assert session.move_count == 0
        assert session.message != ""
        assert session.highlighted is None
        assert session.made_progress_since_last_recycle is True
        assert session.consecutive_burials == 0

    def test_session_with_seed_is_reproducible(self):
        config1 = GameConfig(seed=12345)
        config2 = GameConfig(seed=12345)
        controller1 = GameController(config1)
        controller2 = GameController(config2)

        state1 = controller1.session.state
        state2 = controller2.session.state

        assert len(state1.stock) == len(state2.stock)
        for c1, c2 in zip(state1.stock, state2.stock):
            assert c1.rank == c2.rank
            assert c1.suit == c2.suit


class TestGameControllerTimer:
    """Tests for timer management."""

    def test_timer_starts_on_start_game(self):
        config = GameConfig()
        controller = GameController(config)
        controller.start_game()

        assert controller.timer.is_running is True

    def test_pause_timer(self):
        config = GameConfig()
        controller = GameController(config)
        controller.start_game()
        controller.pause_timer()

        assert controller.timer.is_paused is True

    def test_resume_timer(self):
        config = GameConfig()
        controller = GameController(config)
        controller.start_game()
        controller.pause_timer()
        controller.resume_timer()

        assert controller.timer.is_running is True
        assert controller.timer.is_paused is False

    def test_get_elapsed_time(self):
        config = GameConfig()
        controller = GameController(config)

        elapsed = controller.get_elapsed_time()

        assert elapsed >= 0.0


class TestGameControllerSelection:
    """Tests for card selection."""

    def test_select_from_waste(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.cursor.zone = CursorZone.WASTE

        result = controller.try_select()

        assert result is True
        assert controller.session.selection is not None
        assert controller.session.selection.zone == CursorZone.WASTE

    def test_select_from_empty_waste_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = []
        controller.session.cursor.zone = CursorZone.WASTE

        result = controller.try_select()

        assert result is False
        assert controller.session.selection is None
        assert "empty" in controller.session.message.lower()

    def test_select_from_tableau_face_up(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0
        controller.session.cursor.card_index = 0

        result = controller.try_select()

        assert result is True
        assert controller.session.selection is not None
        assert controller.session.selection.zone == CursorZone.TABLEAU

    def test_select_from_tableau_face_down_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES, face_up=False)]
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0
        controller.session.cursor.card_index = 0

        result = controller.try_select()

        assert result is False
        assert controller.session.selection is None
        assert "face-down" in controller.session.message.lower()

    def test_select_from_empty_tableau_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = []
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        result = controller.try_select()

        assert result is False
        assert controller.session.selection is None
        assert "empty" in controller.session.message.lower()

    def test_select_from_foundation(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.foundations[0] = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.cursor.zone = CursorZone.FOUNDATION
        controller.session.cursor.pile_index = 0

        result = controller.try_select()

        assert result is True
        assert controller.session.selection is not None
        assert controller.session.selection.zone == CursorZone.FOUNDATION

    def test_select_from_empty_foundation_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.foundations[0] = []
        controller.session.cursor.zone = CursorZone.FOUNDATION
        controller.session.cursor.pile_index = 0

        result = controller.try_select()

        assert result is False
        assert controller.session.selection is None
        assert "empty" in controller.session.message.lower()

    def test_select_from_stock_triggers_stock_action(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.stock = [make_card(Rank.ACE, Suit.HEARTS, face_up=False)]
        controller.session.state.waste = []
        controller.session.cursor.zone = CursorZone.STOCK

        result = controller.try_select()

        assert result is True
        assert controller.session.selection is None
        assert len(controller.session.state.waste) == 1

    def test_select_multiple_cards_from_tableau(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [
            make_card(Rank.KING, Suit.SPADES),
            make_card(Rank.QUEEN, Suit.HEARTS),
            make_card(Rank.JACK, Suit.SPADES),
        ]
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0
        controller.session.cursor.card_index = 1

        result = controller.try_select()

        assert result is True
        assert controller.session.selection.card_index == 1
        assert "2" in controller.session.message


class TestGameControllerCancelSelection:
    """Tests for cancelling selection."""

    def test_cancel_clears_selection(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.selection = Selection(zone=CursorZone.WASTE)

        controller.cancel_selection()

        assert controller.session.selection is None
        assert "cancel" in controller.session.message.lower()

    def test_cancel_with_no_selection(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.selection = None

        controller.cancel_selection()

        assert controller.session.selection is None


class TestGameControllerPlacement:
    """Tests for card placement."""

    def test_place_waste_to_tableau(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        result = controller.try_place()

        assert result is True
        assert controller.session.selection is None
        assert len(controller.session.state.waste) == 0
        assert len(controller.session.state.tableau[0]) == 2
        assert controller.session.move_count == 1

    def test_place_waste_to_foundation(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.FOUNDATION
        controller.session.cursor.pile_index = 0

        result = controller.try_place()

        assert result is True
        assert controller.session.selection is None
        assert len(controller.session.state.foundations[0]) == 1

    def test_place_tableau_to_tableau(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[1] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0, card_index=0)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 1

        result = controller.try_place()

        assert result is True
        assert len(controller.session.state.tableau[0]) == 0
        assert len(controller.session.state.tableau[1]) == 2

    def test_place_foundation_to_tableau(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.foundations[0] = [
            make_card(Rank.ACE, Suit.HEARTS),
            make_card(Rank.TWO, Suit.HEARTS),
        ]
        controller.session.state.tableau[0] = [make_card(Rank.THREE, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.FOUNDATION, pile_index=0)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        result = controller.try_place()

        assert result is True
        assert len(controller.session.state.foundations[0]) == 1
        assert len(controller.session.state.tableau[0]) == 2

    def test_place_on_same_pile_cancels(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        result = controller.try_place()

        assert result is False
        assert controller.session.selection is None

    def test_place_on_stock_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.STOCK

        result = controller.try_place()

        assert result is False
        assert controller.session.selection is not None
        assert "stock" in controller.session.message.lower()

    def test_place_on_waste_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0)
        controller.session.cursor.zone = CursorZone.WASTE

        result = controller.try_place()

        assert result is False
        assert controller.session.selection is not None
        assert "waste" in controller.session.message.lower()

    def test_invalid_placement_keeps_selection(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.HEARTS)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        result = controller.try_place()

        assert result is False
        assert controller.session.selection is not None
        assert controller.session.move_count == 0

    def test_multi_card_to_foundation_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [
            make_card(Rank.TWO, Suit.HEARTS),
            make_card(Rank.ACE, Suit.SPADES),
        ]
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0, card_index=0)
        controller.session.cursor.zone = CursorZone.FOUNDATION
        controller.session.cursor.pile_index = 0

        result = controller.try_place()

        assert result is False
        assert "single" in controller.session.message.lower()

    def test_foundation_to_foundation_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.foundations[0] = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.selection = Selection(zone=CursorZone.FOUNDATION, pile_index=0)
        controller.session.cursor.zone = CursorZone.FOUNDATION
        controller.session.cursor.pile_index = 1

        result = controller.try_place()

        assert result is False
        assert controller.session.selection is not None


class TestGameControllerStockActions:
    """Tests for stock draw and recycle."""

    def test_draw_from_stock(self):
        config = GameConfig(draw_count=1)
        controller = GameController(config)
        controller.session.state.stock = [make_card(Rank.ACE, Suit.HEARTS, face_up=False)]
        controller.session.state.waste = []

        result = controller.handle_stock_action()

        assert result.success is True
        assert len(controller.session.state.stock) == 0
        assert len(controller.session.state.waste) == 1
        assert controller.session.state.waste[0].face_up is True

    def test_draw_three_from_stock(self):
        config = GameConfig(draw_count=3)
        controller = GameController(config)
        controller.session.state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
            make_card(Rank.THREE, Suit.HEARTS, face_up=False),
            make_card(Rank.FOUR, Suit.HEARTS, face_up=False),
        ]
        controller.session.state.waste = []

        result = controller.handle_stock_action()

        assert result.success is True
        assert len(controller.session.state.stock) == 1
        assert len(controller.session.state.waste) == 3

    def test_recycle_waste_to_stock(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [
            make_card(Rank.ACE, Suit.HEARTS),
            make_card(Rank.TWO, Suit.HEARTS),
        ]

        result = controller.handle_stock_action()

        assert result.success is True
        assert len(controller.session.state.stock) == 2
        assert len(controller.session.state.waste) == 0
        assert controller.session.made_progress_since_last_recycle is False

    def test_stock_action_empty_both_fails(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = []

        result = controller.handle_stock_action()

        assert result.success is False
        assert "empty" in controller.session.message.lower()


class TestGameControllerProgressTracking:
    """Tests for stall detection progress tracking."""

    def test_progress_flag_set_on_successful_move(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.made_progress_since_last_recycle = False
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        controller.try_place()

        assert controller.session.made_progress_since_last_recycle is True

    def test_consecutive_burials_reset_on_move(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.consecutive_burials = 2
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        controller.try_place()

        assert controller.session.consecutive_burials == 0

    def test_needs_bury_prompt_draw3_no_progress(self):
        config = GameConfig(draw_count=3)
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.made_progress_since_last_recycle = False
        controller.session.consecutive_burials = 0

        assert controller.needs_bury_prompt() is True

    def test_needs_bury_prompt_false_with_progress(self):
        config = GameConfig(draw_count=3)
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.made_progress_since_last_recycle = True

        assert controller.needs_bury_prompt() is False

    def test_needs_bury_prompt_false_draw1(self):
        config = GameConfig(draw_count=1)
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.made_progress_since_last_recycle = False

        assert controller.needs_bury_prompt() is False

    def test_is_stalled_draw1_no_progress(self):
        config = GameConfig(draw_count=1)
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.made_progress_since_last_recycle = False

        assert controller.is_stalled() is True

    def test_is_stalled_draw3_max_burials(self):
        config = GameConfig(draw_count=3)
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.made_progress_since_last_recycle = False
        controller.session.consecutive_burials = 2

        assert controller.is_stalled() is True

    def test_is_stalled_false_with_progress(self):
        config = GameConfig(draw_count=1)
        controller = GameController(config)
        controller.session.state.stock = []
        controller.session.state.waste = [make_card(Rank.ACE, Suit.HEARTS)]
        controller.session.made_progress_since_last_recycle = True

        assert controller.is_stalled() is False

    def test_execute_bury(self):
        config = GameConfig(draw_count=3)
        controller = GameController(config)
        controller.session.state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
        ]
        controller.session.consecutive_burials = 0

        controller.execute_bury()

        assert controller.session.consecutive_burials == 1
        assert controller.session.state.stock[0].rank == Rank.TWO


class TestGameControllerUndo:
    """Tests for undo functionality."""

    def test_undo_restores_state(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        controller.try_place()
        assert len(controller.session.state.tableau[0]) == 2

        result = controller.undo()

        assert result is True
        assert len(controller.session.state.waste) == 1
        assert len(controller.session.state.tableau[0]) == 1
        assert controller.session.move_count == 0

    def test_undo_empty_stack(self):
        config = GameConfig()
        controller = GameController(config)

        result = controller.undo()

        assert result is False
        assert "nothing" in controller.session.message.lower()

    def test_can_undo_after_move(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        assert controller.can_undo() is False
        controller.try_place()
        assert controller.can_undo() is True

    def test_undo_clears_selection(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0

        controller.try_place()
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0)
        controller.undo()

        assert controller.session.selection is None


class TestGameControllerWinDetection:
    """Tests for win condition detection."""

    def test_check_win_false_incomplete(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.foundations[0] = [make_card(Rank.ACE, Suit.HEARTS)]

        assert controller.check_win() is False

    def test_check_win_true_complete(self):
        config = GameConfig()
        controller = GameController(config)

        for i, suit in enumerate([Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]):
            controller.session.state.foundations[i] = [
                make_card(rank, suit) for rank in Rank
            ]

        assert controller.check_win() is True


class TestGameControllerHints:
    """Tests for valid destination computation."""

    def test_compute_destinations_from_waste(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]
        controller.session.state.tableau[1] = [make_card(Rank.KING, Suit.CLUBS)]
        controller.session.state.tableau[2] = [make_card(Rank.KING, Suit.HEARTS)]
        controller.session.cursor.zone = CursorZone.WASTE

        highlights = controller.compute_valid_destinations()

        assert highlights is not None
        assert 0 in highlights.tableau_piles
        assert 1 in highlights.tableau_piles
        assert 2 not in highlights.tableau_piles

    def test_compute_destinations_none_available(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.FIVE, Suit.HEARTS)]
        controller.session.state.tableau = [[] for _ in range(7)]
        controller.session.cursor.zone = CursorZone.WASTE

        highlights = controller.compute_valid_destinations()

        assert highlights is None
        assert "no valid" in controller.session.message.lower()

    def test_compute_destinations_no_card(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = []
        controller.session.cursor.zone = CursorZone.WASTE

        highlights = controller.compute_valid_destinations()

        assert highlights is None

    def test_compute_destinations_multi_card_excludes_foundation(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [
            make_card(Rank.TWO, Suit.HEARTS),
            make_card(Rank.ACE, Suit.SPADES),
        ]
        controller.session.state.tableau[1] = [make_card(Rank.THREE, Suit.SPADES)]
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0, card_index=0)

        highlights = controller.compute_valid_destinations()

        assert highlights is not None
        assert len(highlights.foundation_piles) == 0
        assert 1 in highlights.tableau_piles


class TestGameControllerCardRetrieval:
    """Tests for getting cards at cursor or selection."""

    def test_get_card_under_cursor_waste(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.cursor.zone = CursorZone.WASTE

        card = controller.get_card_under_cursor()

        assert card is not None
        assert card.rank == Rank.QUEEN

    def test_get_card_under_cursor_empty(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = []
        controller.session.cursor.zone = CursorZone.WASTE

        card = controller.get_card_under_cursor()

        assert card is None

    def test_get_card_under_cursor_stock_returns_none(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.stock = [make_card(Rank.ACE, Suit.HEARTS, face_up=False)]
        controller.session.cursor.zone = CursorZone.STOCK

        card = controller.get_card_under_cursor()

        assert card is None

    def test_get_card_under_cursor_face_down_returns_none(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [make_card(Rank.KING, Suit.SPADES, face_up=False)]
        controller.session.cursor.zone = CursorZone.TABLEAU
        controller.session.cursor.pile_index = 0
        controller.session.cursor.card_index = 0

        card = controller.get_card_under_cursor()

        assert card is None

    def test_get_selected_card(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[2] = [
            make_card(Rank.KING, Suit.HEARTS),
            make_card(Rank.QUEEN, Suit.SPADES),
        ]
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=2, card_index=1)

        card = controller.get_selected_card()

        assert card is not None
        assert card.rank == Rank.QUEEN

    def test_get_selected_card_no_selection(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.selection = None

        card = controller.get_selected_card()

        assert card is None

    def test_describe_selection_single_card(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        controller.session.selection = Selection(zone=CursorZone.WASTE)

        description = controller.describe_selection()

        assert "Q" in description
        assert "♥" in description

    def test_describe_selection_multiple_cards(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.state.tableau[0] = [
            make_card(Rank.KING, Suit.SPADES),
            make_card(Rank.QUEEN, Suit.HEARTS),
            make_card(Rank.JACK, Suit.SPADES),
        ]
        controller.session.selection = Selection(zone=CursorZone.TABLEAU, pile_index=0, card_index=1)

        description = controller.describe_selection()

        assert "Q" in description
        assert "1 more" in description

    def test_describe_selection_none(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.selection = None

        description = controller.describe_selection()

        assert description == ""


class TestGameControllerNewGame:
    """Tests for starting a new game."""

    def test_new_game_resets_state(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.move_count = 10
        controller.session.selection = Selection(zone=CursorZone.WASTE)
        controller.session.made_progress_since_last_recycle = False
        controller.session.consecutive_burials = 2

        controller.new_game()

        assert controller.session.move_count == 0
        assert controller.session.selection is None
        assert controller.session.made_progress_since_last_recycle is True
        assert controller.session.consecutive_burials == 0

    def test_new_game_with_seed(self):
        config = GameConfig()
        controller = GameController(config)

        controller.new_game(seed=54321)
        state1_stock = [(c.rank, c.suit) for c in controller.session.state.stock]

        controller.new_game(seed=54321)
        state2_stock = [(c.rank, c.suit) for c in controller.session.state.stock]

        assert state1_stock == state2_stock

    def test_new_game_resets_timer(self):
        config = GameConfig()
        controller = GameController(config)
        controller.start_game()
        controller.timer.set_elapsed(100.0)

        controller.new_game()

        assert controller.timer.get_elapsed() < 1.0


class TestGameControllerSaveRestore:
    """Tests for save and restore functionality."""

    def test_save_to_dict(self):
        config = GameConfig()
        controller = GameController(config)
        controller.session.move_count = 5
        controller.session.made_progress_since_last_recycle = False
        controller.session.consecutive_burials = 1
        controller.timer.set_elapsed(120.5)

        data = controller.save_to_dict()

        assert data['move_count'] == 5
        assert data['made_progress_since_last_recycle'] is False
        assert data['consecutive_burials'] == 1
        assert data['elapsed_time'] == pytest.approx(120.5, abs=0.1)
        assert 'state' in data

    def test_load_from_dict(self):
        config = GameConfig()
        controller = GameController(config)

        saved_state = GameState()
        saved_state.waste = [make_card(Rank.ACE, Suit.HEARTS)]

        data = {
            'state': saved_state,
            'move_count': 15,
            'elapsed_time': 200.0,
            'made_progress_since_last_recycle': False,
            'consecutive_burials': 2,
        }

        controller.load_from_dict(data)

        assert controller.session.move_count == 15
        assert controller.session.made_progress_since_last_recycle is False
        assert controller.session.consecutive_burials == 2
        assert len(controller.session.state.waste) == 1
        assert controller.timer.get_elapsed() == pytest.approx(200.0, abs=0.1)
