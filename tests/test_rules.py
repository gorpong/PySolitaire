"""Tests for move validation rules."""

from pysolitaire.model import Card, GameState, Rank, Suit
from pysolitaire.rules import (
    can_draw_from_stock,
    can_pick_from_tableau,
    can_pick_from_waste,
    can_place_on_foundation,
    can_place_on_tableau,
    get_valid_foundation_destinations,
    get_valid_tableau_destinations,
)


class TestCanPlaceOnTableau:
    """Tests for placing cards on tableau piles."""

    def test_king_on_empty_tableau(self):
        """Kings can be placed on empty tableau piles."""
        king = Card(Rank.KING, Suit.HEARTS, face_up=True)
        empty_pile = []
        assert can_place_on_tableau(king, empty_pile) is True

    def test_non_king_on_empty_tableau(self):
        """Non-kings cannot be placed on empty tableau piles."""
        queen = Card(Rank.QUEEN, Suit.HEARTS, face_up=True)
        empty_pile = []
        assert can_place_on_tableau(queen, empty_pile) is False

    def test_card_on_opposite_color_one_higher(self):
        """Card can be placed on opposite color card one rank higher."""
        red_queen = Card(Rank.QUEEN, Suit.HEARTS, face_up=True)
        black_king = Card(Rank.KING, Suit.SPADES, face_up=True)
        pile = [black_king]
        assert can_place_on_tableau(red_queen, pile) is True

    def test_card_on_same_color_rejected(self):
        """Card cannot be placed on same color card."""
        red_queen = Card(Rank.QUEEN, Suit.HEARTS, face_up=True)
        red_king = Card(Rank.KING, Suit.DIAMONDS, face_up=True)
        pile = [red_king]
        assert can_place_on_tableau(red_queen, pile) is False

    def test_card_on_wrong_rank_rejected(self):
        """Card cannot be placed if rank difference is not exactly 1."""
        red_jack = Card(Rank.JACK, Suit.HEARTS, face_up=True)
        black_king = Card(Rank.KING, Suit.SPADES, face_up=True)
        pile = [black_king]
        # Jack is 2 less than King, not 1
        assert can_place_on_tableau(red_jack, pile) is False

    def test_ace_can_go_on_two(self):
        """Ace can be placed on a two (opposite color, one rank lower)."""
        ace = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        two = Card(Rank.TWO, Suit.SPADES, face_up=True)
        pile = [two]
        # This is a valid move - Ace is one less than Two, opposite colors
        assert can_place_on_tableau(ace, pile) is True

    def test_face_down_destination_rejected(self):
        """Cannot place on a face-down card."""
        red_queen = Card(Rank.QUEEN, Suit.HEARTS, face_up=True)
        black_king = Card(Rank.KING, Suit.SPADES, face_up=False)
        pile = [black_king]
        assert can_place_on_tableau(red_queen, pile) is False

    def test_all_red_black_combinations(self):
        """Test all valid color combinations for tableau moves."""
        # Red on black
        assert can_place_on_tableau(
            Card(Rank.QUEEN, Suit.HEARTS, face_up=True),
            [Card(Rank.KING, Suit.CLUBS, face_up=True)]
        ) is True
        assert can_place_on_tableau(
            Card(Rank.QUEEN, Suit.DIAMONDS, face_up=True),
            [Card(Rank.KING, Suit.SPADES, face_up=True)]
        ) is True

        # Black on red
        assert can_place_on_tableau(
            Card(Rank.QUEEN, Suit.CLUBS, face_up=True),
            [Card(Rank.KING, Suit.HEARTS, face_up=True)]
        ) is True
        assert can_place_on_tableau(
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),
            [Card(Rank.KING, Suit.DIAMONDS, face_up=True)]
        ) is True


class TestCanPlaceOnFoundation:
    """Tests for placing cards on foundation piles."""

    def test_ace_on_empty_foundation(self):
        """Only aces can start a foundation pile."""
        ace = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        empty_pile = []
        assert can_place_on_foundation(ace, empty_pile, Suit.HEARTS) is True

    def test_non_ace_on_empty_foundation(self):
        """Non-aces cannot start a foundation pile."""
        two = Card(Rank.TWO, Suit.HEARTS, face_up=True)
        empty_pile = []
        assert can_place_on_foundation(two, empty_pile, Suit.HEARTS) is False

    def test_wrong_suit_ace_rejected(self):
        """Ace of wrong suit cannot start a foundation."""
        ace = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        empty_pile = []
        assert can_place_on_foundation(ace, empty_pile, Suit.SPADES) is False

    def test_sequential_same_suit(self):
        """Cards must be sequential and same suit."""
        ace = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        two = Card(Rank.TWO, Suit.HEARTS, face_up=True)
        pile = [ace]
        assert can_place_on_foundation(two, pile, Suit.HEARTS) is True

    def test_skip_rank_rejected(self):
        """Cannot skip ranks on foundation."""
        ace = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        three = Card(Rank.THREE, Suit.HEARTS, face_up=True)
        pile = [ace]
        assert can_place_on_foundation(three, pile, Suit.HEARTS) is False

    def test_wrong_suit_rejected(self):
        """Cannot place card of different suit."""
        ace_hearts = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        two_spades = Card(Rank.TWO, Suit.SPADES, face_up=True)
        pile = [ace_hearts]
        assert can_place_on_foundation(two_spades, pile, Suit.HEARTS) is False

    def test_full_foundation_sequence(self):
        """Test building up a foundation from Ace to King."""
        pile = []
        for rank in Rank:
            card = Card(rank, Suit.DIAMONDS, face_up=True)
            assert can_place_on_foundation(card, pile, Suit.DIAMONDS) is True
            pile.append(card)

        # King is on top, nothing more can be placed
        next_card = Card(Rank.ACE, Suit.DIAMONDS, face_up=True)
        assert can_place_on_foundation(next_card, pile, Suit.DIAMONDS) is False


class TestCanDrawFromStock:
    """Tests for drawing from stock pile."""

    def test_can_draw_when_stock_has_cards(self):
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS)]
        assert can_draw_from_stock(state) is True

    def test_cannot_draw_when_stock_empty(self):
        state = GameState()
        state.stock = []
        assert can_draw_from_stock(state) is False

    def test_can_draw_with_multiple_cards(self):
        state = GameState()
        state.stock = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.TWO, Suit.HEARTS),
            Card(Rank.THREE, Suit.HEARTS),
        ]
        assert can_draw_from_stock(state) is True


class TestCanPickFromTableau:
    """Tests for picking cards from tableau piles."""

    def test_can_pick_single_face_up_card(self):
        """Can pick the top face-up card."""
        card = Card(Rank.KING, Suit.HEARTS, face_up=True)
        pile = [card]
        assert can_pick_from_tableau(pile, card_index=0) is True

    def test_cannot_pick_face_down_card(self):
        """Cannot pick a face-down card."""
        card = Card(Rank.KING, Suit.HEARTS, face_up=False)
        pile = [card]
        assert can_pick_from_tableau(pile, card_index=0) is False

    def test_can_pick_run_of_face_up_cards(self):
        """Can pick a run starting from any face-up card."""
        pile = [
            Card(Rank.KING, Suit.HEARTS, face_up=False),  # index 0
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),  # index 1
            Card(Rank.JACK, Suit.HEARTS, face_up=True),   # index 2
        ]
        # Can pick from index 1 (Queen and Jack)
        assert can_pick_from_tableau(pile, card_index=1) is True
        # Can pick from index 2 (just Jack)
        assert can_pick_from_tableau(pile, card_index=2) is True
        # Cannot pick from index 0 (face down)
        assert can_pick_from_tableau(pile, card_index=0) is False

    def test_cannot_pick_from_empty_pile(self):
        """Cannot pick from empty pile."""
        pile = []
        assert can_pick_from_tableau(pile, card_index=0) is False

    def test_invalid_index_rejected(self):
        """Invalid card index returns False."""
        pile = [Card(Rank.KING, Suit.HEARTS, face_up=True)]
        assert can_pick_from_tableau(pile, card_index=5) is False
        assert can_pick_from_tableau(pile, card_index=-1) is False


class TestCanPickFromWaste:
    """Tests for picking from waste pile."""

    def test_can_pick_from_non_empty_waste(self):
        state = GameState()
        state.waste = [Card(Rank.ACE, Suit.HEARTS, face_up=True)]
        assert can_pick_from_waste(state) is True

    def test_cannot_pick_from_empty_waste(self):
        state = GameState()
        state.waste = []
        assert can_pick_from_waste(state) is False


class TestGetValidTableauDestinations:
    """Tests for finding valid tableau destinations for a card/run."""

    def test_king_can_go_to_empty_piles(self):
        """King can move to any empty tableau pile."""
        state = GameState()
        state.tableau = [[], [], [Card(Rank.ACE, Suit.HEARTS, face_up=True)], [], [], [], []]

        king = Card(Rank.KING, Suit.SPADES, face_up=True)
        valid = get_valid_tableau_destinations(king, state)

        # Piles 0, 1, 3, 4, 5, 6 are empty
        assert 0 in valid
        assert 1 in valid
        assert 2 not in valid  # Has a card
        assert 3 in valid

    def test_card_finds_opposite_color_higher_rank(self):
        """Card finds piles with opposite color, one rank higher."""
        state = GameState()
        state.tableau = [
            [Card(Rank.KING, Suit.SPADES, face_up=True)],   # Black King
            [Card(Rank.KING, Suit.HEARTS, face_up=True)],   # Red King
            [Card(Rank.JACK, Suit.CLUBS, face_up=True)],    # Black Jack
            [],
            [],
            [],
            [],
        ]

        red_queen = Card(Rank.QUEEN, Suit.HEARTS, face_up=True)
        valid = get_valid_tableau_destinations(red_queen, state)

        assert 0 in valid  # Can go on Black King
        assert 1 not in valid  # Red King - same color
        assert 2 not in valid  # Black Jack - wrong rank

    def test_no_valid_destinations(self):
        """Returns empty list when no valid destinations."""
        state = GameState()
        state.tableau = [
            [Card(Rank.KING, Suit.HEARTS, face_up=True)],  # Red King
            [Card(Rank.KING, Suit.DIAMONDS, face_up=True)],  # Red King
            [],
            [],
            [],
            [],
            [],
        ]

        # Red Queen can't go on red kings, and non-kings can't go on empty
        red_queen = Card(Rank.QUEEN, Suit.HEARTS, face_up=True)
        valid = get_valid_tableau_destinations(red_queen, state)
        assert len(valid) == 0


class TestGetValidFoundationDestinations:
    """Tests for finding valid foundation destinations."""

    def test_ace_finds_matching_empty_foundation(self):
        """Ace of hearts should find the hearts foundation."""
        state = GameState()
        # Foundations are indexed by suit order: HEARTS=0, DIAMONDS=1, CLUBS=2, SPADES=3
        state.foundations = [[], [], [], []]

        ace = Card(Rank.ACE, Suit.HEARTS, face_up=True)
        valid = get_valid_foundation_destinations(ace, state)

        assert 0 in valid  # Hearts foundation

    def test_two_finds_foundation_with_ace(self):
        """Two of hearts finds hearts foundation with ace."""
        state = GameState()
        state.foundations = [
            [Card(Rank.ACE, Suit.HEARTS, face_up=True)],  # Hearts
            [],
            [],
            [],
        ]

        two = Card(Rank.TWO, Suit.HEARTS, face_up=True)
        valid = get_valid_foundation_destinations(two, state)

        assert 0 in valid

    def test_no_valid_foundation(self):
        """Returns empty when no valid foundation."""
        state = GameState()
        state.foundations = [[], [], [], []]

        # Two can't go on empty foundation
        two = Card(Rank.TWO, Suit.HEARTS, face_up=True)
        valid = get_valid_foundation_destinations(two, state)

        assert len(valid) == 0
