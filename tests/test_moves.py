"""Tests for move execution and state updates."""

import pytest
from src.model import Card, Suit, Rank, GameState
from src.moves import (
    move_tableau_to_tableau,
    move_waste_to_tableau,
    move_waste_to_foundation,
    move_tableau_to_foundation,
    move_foundation_to_tableau,
    draw_from_stock,
    recycle_waste_to_stock,
    bury_top_of_stock,
    MoveResult,
)


def make_card(rank: Rank, suit: Suit, face_up: bool = True) -> Card:
    """Helper to create cards more concisely."""
    return Card(rank, suit, face_up)


class TestMoveTableauToTableau:
    """Tests for moving cards between tableau piles."""

    def test_move_single_card(self):
        """Move a single card from one tableau to another."""
        state = GameState()
        state.tableau[0] = [make_card(Rank.QUEEN, Suit.HEARTS)]
        state.tableau[1] = [make_card(Rank.KING, Suit.SPADES)]

        result = move_tableau_to_tableau(state, src_pile=0, card_index=0, dest_pile=1)

        assert result.success is True
        assert len(state.tableau[0]) == 0
        assert len(state.tableau[1]) == 2
        assert state.tableau[1][-1].rank == Rank.QUEEN

    def test_move_multiple_cards(self):
        """Move a run of cards."""
        state = GameState()
        state.tableau[0] = [
            make_card(Rank.QUEEN, Suit.HEARTS),
            make_card(Rank.JACK, Suit.SPADES),
        ]
        state.tableau[1] = [make_card(Rank.KING, Suit.CLUBS)]

        # Move both cards (starting from Queen at index 0)
        result = move_tableau_to_tableau(state, src_pile=0, card_index=0, dest_pile=1)

        assert result.success is True
        assert len(state.tableau[0]) == 0
        assert len(state.tableau[1]) == 3
        assert state.tableau[1][-1].rank == Rank.JACK
        assert state.tableau[1][-2].rank == Rank.QUEEN

    def test_move_king_to_empty(self):
        """King can move to empty pile."""
        state = GameState()
        state.tableau[0] = [make_card(Rank.KING, Suit.HEARTS)]
        state.tableau[1] = []

        result = move_tableau_to_tableau(state, src_pile=0, card_index=0, dest_pile=1)

        assert result.success is True
        assert len(state.tableau[0]) == 0
        assert len(state.tableau[1]) == 1

    def test_illegal_move_fails(self):
        """Illegal move does not modify state."""
        state = GameState()
        state.tableau[0] = [make_card(Rank.QUEEN, Suit.HEARTS)]
        state.tableau[1] = [make_card(Rank.KING, Suit.HEARTS)]  # Same color!

        result = move_tableau_to_tableau(state, src_pile=0, card_index=0, dest_pile=1)

        assert result.success is False
        assert len(state.tableau[0]) == 1  # Unchanged
        assert len(state.tableau[1]) == 1  # Unchanged

    def test_auto_flip_after_move(self):
        """Face-down card is auto-flipped when exposed."""
        state = GameState()
        state.tableau[0] = [
            make_card(Rank.KING, Suit.HEARTS, face_up=False),
            make_card(Rank.QUEEN, Suit.SPADES),  # Black Queen
        ]
        state.tableau[1] = [make_card(Rank.KING, Suit.DIAMONDS)]  # Red King

        result = move_tableau_to_tableau(state, src_pile=0, card_index=1, dest_pile=1)

        assert result.success is True
        # The formerly hidden King should now be face up
        assert state.tableau[0][0].face_up is True

    def test_no_flip_if_pile_empty(self):
        """No error when pile becomes empty after move."""
        state = GameState()
        state.tableau[0] = [make_card(Rank.KING, Suit.HEARTS)]
        state.tableau[1] = []

        result = move_tableau_to_tableau(state, src_pile=0, card_index=0, dest_pile=1)

        assert result.success is True
        assert len(state.tableau[0]) == 0

    def test_cannot_pick_face_down(self):
        """Cannot move a face-down card."""
        state = GameState()
        state.tableau[0] = [make_card(Rank.KING, Suit.HEARTS, face_up=False)]
        state.tableau[1] = []

        result = move_tableau_to_tableau(state, src_pile=0, card_index=0, dest_pile=1)

        assert result.success is False


class TestMoveWasteToTableau:
    """Tests for moving from waste to tableau."""

    def test_move_waste_to_tableau(self):
        """Move waste card to valid tableau pile."""
        state = GameState()
        state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]

        result = move_waste_to_tableau(state, dest_pile=0)

        assert result.success is True
        assert len(state.waste) == 0
        assert len(state.tableau[0]) == 2
        assert state.tableau[0][-1].rank == Rank.QUEEN

    def test_move_waste_empty_fails(self):
        """Cannot move from empty waste."""
        state = GameState()
        state.waste = []
        state.tableau[0] = [make_card(Rank.KING, Suit.SPADES)]

        result = move_waste_to_tableau(state, dest_pile=0)

        assert result.success is False

    def test_illegal_move_fails(self):
        """Illegal waste to tableau move fails."""
        state = GameState()
        state.waste = [make_card(Rank.QUEEN, Suit.HEARTS)]
        state.tableau[0] = [make_card(Rank.KING, Suit.HEARTS)]  # Same color

        result = move_waste_to_tableau(state, dest_pile=0)

        assert result.success is False
        assert len(state.waste) == 1  # Unchanged


class TestMoveWasteToFoundation:
    """Tests for moving from waste to foundation."""

    def test_move_ace_to_foundation(self):
        """Move Ace from waste to empty foundation."""
        state = GameState()
        state.waste = [make_card(Rank.ACE, Suit.HEARTS)]

        result = move_waste_to_foundation(state, dest_foundation=0)

        assert result.success is True
        assert len(state.waste) == 0
        assert len(state.foundations[0]) == 1
        assert state.foundations[0][0].rank == Rank.ACE

    def test_move_sequential_to_foundation(self):
        """Move card to foundation with correct predecessor."""
        state = GameState()
        state.waste = [make_card(Rank.TWO, Suit.HEARTS)]
        state.foundations[0] = [make_card(Rank.ACE, Suit.HEARTS)]

        result = move_waste_to_foundation(state, dest_foundation=0)

        assert result.success is True
        assert len(state.foundations[0]) == 2

    def test_illegal_foundation_move_fails(self):
        """Cannot skip ranks on foundation."""
        state = GameState()
        state.waste = [make_card(Rank.THREE, Suit.HEARTS)]
        state.foundations[0] = [make_card(Rank.ACE, Suit.HEARTS)]

        result = move_waste_to_foundation(state, dest_foundation=0)

        assert result.success is False


class TestMoveTableauToFoundation:
    """Tests for moving from tableau to foundation."""

    def test_move_ace_from_tableau(self):
        """Move Ace from tableau to foundation."""
        state = GameState()
        state.tableau[0] = [make_card(Rank.ACE, Suit.HEARTS)]

        result = move_tableau_to_foundation(state, src_pile=0, dest_foundation=0)

        assert result.success is True
        assert len(state.tableau[0]) == 0
        assert len(state.foundations[0]) == 1

    def test_auto_flip_after_foundation_move(self):
        """Auto-flip when moving to foundation exposes face-down card."""
        state = GameState()
        state.tableau[0] = [
            make_card(Rank.KING, Suit.SPADES, face_up=False),
            make_card(Rank.ACE, Suit.HEARTS),
        ]

        result = move_tableau_to_foundation(state, src_pile=0, dest_foundation=0)

        assert result.success is True
        assert state.tableau[0][0].face_up is True

    def test_only_top_card_moves(self):
        """Only top card of tableau can move to foundation."""
        state = GameState()
        state.tableau[0] = [
            make_card(Rank.ACE, Suit.HEARTS),
            make_card(Rank.TWO, Suit.SPADES),
        ]

        # The Ace is at index 0, but it's not the top card
        # Top card is Two of Spades - can't go to hearts foundation
        result = move_tableau_to_foundation(state, src_pile=0, dest_foundation=0)

        assert result.success is False


class TestMoveFoundationToTableau:
    """Tests for moving from foundation back to tableau."""

    def test_move_from_foundation_to_tableau(self):
        """Can move card from foundation back to tableau."""
        state = GameState()
        state.foundations[0] = [
            make_card(Rank.ACE, Suit.HEARTS),
            make_card(Rank.TWO, Suit.HEARTS),
        ]
        state.tableau[0] = [make_card(Rank.THREE, Suit.SPADES)]

        result = move_foundation_to_tableau(state, src_foundation=0, dest_pile=0)

        assert result.success is True
        assert len(state.foundations[0]) == 1
        assert len(state.tableau[0]) == 2
        assert state.tableau[0][-1].rank == Rank.TWO

    def test_move_from_empty_foundation_fails(self):
        """Cannot move from empty foundation."""
        state = GameState()
        state.foundations[0] = []
        state.tableau[0] = [make_card(Rank.THREE, Suit.SPADES)]

        result = move_foundation_to_tableau(state, src_foundation=0, dest_pile=0)

        assert result.success is False


class TestDrawFromStock:
    """Tests for drawing cards from stock to waste."""

    def test_draw_one_card(self):
        """Draw 1 card from stock to waste (draw_count=1)."""
        state = GameState()
        state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
        ]

        result = draw_from_stock(state, draw_count=1)

        assert result.success is True
        assert len(state.stock) == 1
        assert len(state.waste) == 1
        # Card should be face up in waste
        assert state.waste[0].face_up is True
        # The TWO was on top of stock, so it moves to waste
        assert state.waste[0].rank == Rank.TWO

    def test_draw_three_cards(self):
        """Draw 3 cards from stock (draw_count=3)."""
        state = GameState()
        # Stock: bottom [ACE, TWO, THREE, FOUR] top
        state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
            make_card(Rank.THREE, Suit.HEARTS, face_up=False),
            make_card(Rank.FOUR, Suit.HEARTS, face_up=False),
        ]

        result = draw_from_stock(state, draw_count=3)

        assert result.success is True
        assert len(state.stock) == 1  # ACE remains
        assert len(state.waste) == 3
        # All waste cards should be face up
        assert all(c.face_up for c in state.waste)
        # Cards popped in order: FOUR, THREE, TWO - so waste is [FOUR, THREE, TWO]
        # Top of waste (last appended) is TWO
        assert state.waste[-1].rank == Rank.TWO
        assert state.waste[0].rank == Rank.FOUR

    def test_draw_three_with_fewer_cards(self):
        """Draw 3 when stock has fewer than 3 cards."""
        state = GameState()
        state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
        ]

        result = draw_from_stock(state, draw_count=3)

        assert result.success is True
        assert len(state.stock) == 0
        assert len(state.waste) == 2

    def test_draw_from_empty_stock_fails(self):
        """Cannot draw from empty stock."""
        state = GameState()
        state.stock = []

        result = draw_from_stock(state, draw_count=1)

        assert result.success is False

    def test_waste_accumulates(self):
        """Multiple draws accumulate in waste."""
        state = GameState()
        state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),
        ]

        draw_from_stock(state, draw_count=1)
        draw_from_stock(state, draw_count=1)

        assert len(state.stock) == 0
        assert len(state.waste) == 2


class TestBuryTopOfStock:
    """Tests for burying the top stock card at the bottom."""

    def test_bury_moves_top_to_bottom(self):
        """Top card of stock ends up at index 0 after bury."""
        state = GameState()
        state.stock = [
            make_card(Rank.ACE, Suit.HEARTS, face_up=False),    # index 0 (bottom)
            make_card(Rank.TWO, Suit.HEARTS, face_up=False),    # index 1 (middle)
            make_card(Rank.THREE, Suit.HEARTS, face_up=False),  # index 2 (top)
        ]

        result = bury_top_of_stock(state)

        assert result.success is True
        # THREE was on top (index 2), now at bottom (index 0)
        assert state.stock[0].rank == Rank.THREE
        # TWO is now on top (was middle, now last)
        assert state.stock[-1].rank == Rank.TWO

    def test_bury_two_card_stock_swaps(self):
        """Two-card stock: the two cards swap positions."""
        state = GameState()
        state.stock = [
            make_card(Rank.JACK, Suit.CLUBS, face_up=False),   # index 0 (bottom)
            make_card(Rank.QUEEN, Suit.CLUBS, face_up=False),  # index 1 (top)
        ]

        result = bury_top_of_stock(state)

        assert result.success is True
        # QUEEN was top, now bottom
        assert state.stock[0].rank == Rank.QUEEN
        # JACK was bottom, now top
        assert state.stock[-1].rank == Rank.JACK

    def test_bury_single_card_stock_is_noop(self):
        """Single-card stock: succeeds but order is unchanged."""
        state = GameState()
        state.stock = [
            make_card(Rank.KING, Suit.SPADES, face_up=False),
        ]

        result = bury_top_of_stock(state)

        assert result.success is True
        assert len(state.stock) == 1
        assert state.stock[0].rank == Rank.KING

    def test_bury_empty_stock_fails(self):
        """Empty stock returns failure without modifying state."""
        state = GameState()
        state.stock = []

        result = bury_top_of_stock(state)

        assert result.success is False
        assert len(state.stock) == 0

    def test_bury_preserves_card_count(self):
        """Bury never adds or removes cards from stock."""
        state = GameState()
        state.stock = [
            make_card(Rank.ACE, Suit.DIAMONDS, face_up=False),
            make_card(Rank.TWO, Suit.DIAMONDS, face_up=False),
            make_card(Rank.THREE, Suit.DIAMONDS, face_up=False),
            make_card(Rank.FOUR, Suit.DIAMONDS, face_up=False),
            make_card(Rank.FIVE, Suit.DIAMONDS, face_up=False),
        ]
        original_ranks = {card.rank for card in state.stock}

        result = bury_top_of_stock(state)

        assert result.success is True
        assert len(state.stock) == 5
        # Every rank that was in stock is still there
        assert {card.rank for card in state.stock} == original_ranks


class TestRecycleWasteToStock:
    """Tests for recycling waste back to stock."""

    def test_recycle_waste(self):
        """Recycle waste pile back to stock."""
        state = GameState()
        state.stock = []
        state.waste = [
            make_card(Rank.ACE, Suit.HEARTS),
            make_card(Rank.TWO, Suit.HEARTS),
            make_card(Rank.THREE, Suit.HEARTS),
        ]

        result = recycle_waste_to_stock(state)

        assert result.success is True
        assert len(state.waste) == 0
        assert len(state.stock) == 3
        # All cards should be face down in stock
        assert all(c.face_up is False for c in state.stock)
        # Order should be reversed (Three was top of waste, now bottom of stock)
        assert state.stock[0].rank == Rank.THREE
        assert state.stock[-1].rank == Rank.ACE

    def test_cannot_recycle_if_stock_not_empty(self):
        """Cannot recycle if stock still has cards."""
        state = GameState()
        state.stock = [make_card(Rank.KING, Suit.SPADES, face_up=False)]
        state.waste = [make_card(Rank.ACE, Suit.HEARTS)]

        result = recycle_waste_to_stock(state)

        assert result.success is False
        # State unchanged
        assert len(state.stock) == 1
        assert len(state.waste) == 1

    def test_cannot_recycle_empty_waste(self):
        """Cannot recycle if waste is empty."""
        state = GameState()
        state.stock = []
        state.waste = []

        result = recycle_waste_to_stock(state)

        assert result.success is False
