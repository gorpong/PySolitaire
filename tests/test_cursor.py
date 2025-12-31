"""Tests for cursor navigation model."""

import pytest
from src.model import Card, Suit, Rank, GameState
from src.cursor import CursorZone, Cursor


class TestCursorZone:
    """Tests for CursorZone enum."""

    def test_zone_values(self):
        assert CursorZone.STOCK.value == "stock"
        assert CursorZone.WASTE.value == "waste"
        assert CursorZone.FOUNDATION.value == "foundation"
        assert CursorZone.TABLEAU.value == "tableau"


class TestCursorInitialization:
    """Tests for cursor creation."""

    def test_default_cursor(self):
        cursor = Cursor()
        assert cursor.zone == CursorZone.STOCK
        assert cursor.pile_index == 0
        assert cursor.card_index == 0

    def test_cursor_with_zone(self):
        cursor = Cursor(zone=CursorZone.WASTE)
        assert cursor.zone == CursorZone.WASTE


class TestCursorMovement:
    """Tests for cursor navigation with arrow keys."""

    def create_standard_state(self) -> GameState:
        """Create a state with cards in standard positions."""
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS, face_up=False)]
        state.waste = [Card(Rank.TWO, Suit.HEARTS, face_up=True)]
        state.foundations = [
            [Card(Rank.ACE, Suit.HEARTS, face_up=True)],
            [],
            [],
            [],
        ]
        state.tableau = [
            [Card(Rank.KING, Suit.HEARTS, face_up=True)],
            [Card(Rank.KING, Suit.SPADES, face_up=False),
             Card(Rank.QUEEN, Suit.HEARTS, face_up=True)],
            [Card(Rank.KING, Suit.CLUBS, face_up=True)],
            [],
            [Card(Rank.ACE, Suit.SPADES, face_up=True)],
            [],
            [Card(Rank.KING, Suit.DIAMONDS, face_up=True)],
        ]
        return state

    # === STOCK Movement ===

    def test_stock_right_to_waste(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.STOCK)
        cursor.move_right(state)
        assert cursor.zone == CursorZone.WASTE

    def test_stock_down_to_tableau_0(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.STOCK)
        cursor.move_down(state)
        assert cursor.zone == CursorZone.TABLEAU
        assert cursor.pile_index == 0

    def test_stock_left_stays(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.STOCK)
        cursor.move_left(state)
        assert cursor.zone == CursorZone.STOCK

    def test_stock_up_stays(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.STOCK)
        cursor.move_up(state)
        assert cursor.zone == CursorZone.STOCK

    # === WASTE Movement ===

    def test_waste_left_to_stock(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.WASTE)
        cursor.move_left(state)
        assert cursor.zone == CursorZone.STOCK

    def test_waste_right_to_foundation_0(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.WASTE)
        cursor.move_right(state)
        assert cursor.zone == CursorZone.FOUNDATION
        assert cursor.pile_index == 0

    def test_waste_down_to_tableau_1(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.WASTE)
        cursor.move_down(state)
        assert cursor.zone == CursorZone.TABLEAU
        assert cursor.pile_index == 1

    # === FOUNDATION Movement ===

    def test_foundation_left_between_foundations(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.FOUNDATION, pile_index=2)
        cursor.move_left(state)
        assert cursor.zone == CursorZone.FOUNDATION
        assert cursor.pile_index == 1

    def test_foundation_0_left_to_waste(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.FOUNDATION, pile_index=0)
        cursor.move_left(state)
        assert cursor.zone == CursorZone.WASTE

    def test_foundation_right_between_foundations(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.FOUNDATION, pile_index=1)
        cursor.move_right(state)
        assert cursor.zone == CursorZone.FOUNDATION
        assert cursor.pile_index == 2

    def test_foundation_3_right_stays(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.FOUNDATION, pile_index=3)
        cursor.move_right(state)
        assert cursor.zone == CursorZone.FOUNDATION
        assert cursor.pile_index == 3

    def test_foundation_down_to_tableau(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.FOUNDATION, pile_index=0)
        cursor.move_down(state)
        assert cursor.zone == CursorZone.TABLEAU
        # Foundation 0 maps to tableau 5 or 6 area (rightmost)
        assert cursor.pile_index >= 5

    # === TABLEAU Movement ===

    def test_tableau_left_between_piles(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=3)
        cursor.move_left(state)
        assert cursor.zone == CursorZone.TABLEAU
        assert cursor.pile_index == 2

    def test_tableau_0_left_stays(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=0)
        cursor.move_left(state)
        assert cursor.zone == CursorZone.TABLEAU
        assert cursor.pile_index == 0

    def test_tableau_right_between_piles(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=3)
        cursor.move_right(state)
        assert cursor.zone == CursorZone.TABLEAU
        assert cursor.pile_index == 4

    def test_tableau_6_right_stays(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=6)
        cursor.move_right(state)
        assert cursor.zone == CursorZone.TABLEAU
        assert cursor.pile_index == 6

    def test_tableau_0_up_to_stock(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=0)
        cursor.move_up(state)
        assert cursor.zone == CursorZone.STOCK

    def test_tableau_1_up_to_waste(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=1)
        cursor.move_up(state)
        assert cursor.zone == CursorZone.WASTE

    def test_tableau_6_up_to_foundation(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=6)
        cursor.move_up(state)
        assert cursor.zone == CursorZone.FOUNDATION

    # === TABLEAU Card Index Movement (within pile) ===

    def test_tableau_down_moves_card_index(self):
        state = self.create_standard_state()
        # Pile 1 has 2 cards
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=1, card_index=0)
        cursor.move_down(state)
        assert cursor.card_index == 1

    def test_tableau_down_at_bottom_stays(self):
        state = self.create_standard_state()
        # Pile 1 has 2 cards, start at last card
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=1, card_index=1)
        cursor.move_down(state)
        assert cursor.card_index == 1

    def test_tableau_up_moves_card_index(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=1, card_index=1)
        # First up should move within pile if there are face-up cards above
        # But card at index 0 is face-down, so it goes to zone above
        cursor.move_up(state)
        # Should go to waste since we can't select face-down
        assert cursor.zone == CursorZone.WASTE

    def test_card_index_reset_on_pile_change(self):
        state = self.create_standard_state()
        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=1, card_index=1)
        cursor.move_left(state)
        # Card index should reset when changing piles
        assert cursor.pile_index == 0
        assert cursor.card_index == 0


class TestCursorSelection:
    """Tests for selection-related cursor functionality."""

    def test_get_zone_string(self):
        cursor = Cursor(zone=CursorZone.STOCK)
        assert cursor.get_zone_string() == "stock"

        cursor = Cursor(zone=CursorZone.FOUNDATION, pile_index=2)
        assert cursor.get_zone_string() == "foundation"

    def test_get_selectable_card_index(self):
        """Test finding the first selectable (face-up) card."""
        state = GameState()
        state.tableau[0] = [
            Card(Rank.KING, Suit.HEARTS, face_up=False),
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),
            Card(Rank.JACK, Suit.HEARTS, face_up=True),
        ]

        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=0)
        idx = cursor.get_first_selectable_card_index(state)
        # First face-up card is at index 1
        assert idx == 1

    def test_get_selectable_card_index_empty_pile(self):
        state = GameState()
        state.tableau[0] = []

        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=0)
        idx = cursor.get_first_selectable_card_index(state)
        assert idx == 0  # Default for empty pile

    def test_snap_to_selectable(self):
        """Cursor should snap to first selectable card in tableau."""
        state = GameState()
        state.tableau[0] = [
            Card(Rank.KING, Suit.HEARTS, face_up=False),
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),
        ]

        cursor = Cursor(zone=CursorZone.TABLEAU, pile_index=0)
        cursor.snap_to_selectable(state)
        assert cursor.card_index == 1
