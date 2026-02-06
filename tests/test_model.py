"""Tests for the game model (Card, Suit, Rank, PileType)."""

from pysolitaire.model import Card, PileType, Rank, Suit


class TestSuit:
    """Tests for Suit enum."""

    def test_suit_has_four_values(self):
        assert len(Suit) == 4

    def test_suit_values(self):
        assert Suit.HEARTS.value == "hearts"
        assert Suit.DIAMONDS.value == "diamonds"
        assert Suit.CLUBS.value == "clubs"
        assert Suit.SPADES.value == "spades"

    def test_suit_is_red(self):
        assert Suit.HEARTS.is_red() is True
        assert Suit.DIAMONDS.is_red() is True
        assert Suit.CLUBS.is_red() is False
        assert Suit.SPADES.is_red() is False

    def test_suit_is_black(self):
        assert Suit.HEARTS.is_black() is False
        assert Suit.DIAMONDS.is_black() is False
        assert Suit.CLUBS.is_black() is True
        assert Suit.SPADES.is_black() is True

    def test_suit_symbol(self):
        assert Suit.HEARTS.symbol == "♥"
        assert Suit.DIAMONDS.symbol == "♦"
        assert Suit.CLUBS.symbol == "♣"
        assert Suit.SPADES.symbol == "♠"


class TestRank:
    """Tests for Rank enum."""

    def test_rank_has_thirteen_values(self):
        assert len(Rank) == 13

    def test_rank_ordering(self):
        # Ace is 1, King is 13
        assert Rank.ACE.value == 1
        assert Rank.TWO.value == 2
        assert Rank.TEN.value == 10
        assert Rank.JACK.value == 11
        assert Rank.QUEEN.value == 12
        assert Rank.KING.value == 13

    def test_rank_display(self):
        assert Rank.ACE.display == "A"
        assert Rank.TWO.display == "2"
        assert Rank.TEN.display == "10"
        assert Rank.JACK.display == "J"
        assert Rank.QUEEN.display == "Q"
        assert Rank.KING.display == "K"

    def test_rank_comparison(self):
        # Ranks should be comparable by value
        assert Rank.ACE.value < Rank.TWO.value
        assert Rank.KING.value > Rank.QUEEN.value
        assert Rank.FIVE.value == 5


class TestCard:
    """Tests for Card dataclass."""

    def test_card_creation(self):
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
        assert card.face_up is False  # Default is face down

    def test_card_face_up(self):
        card = Card(Rank.KING, Suit.HEARTS, face_up=True)
        assert card.face_up is True

    def test_card_is_red(self):
        red_card = Card(Rank.QUEEN, Suit.HEARTS)
        black_card = Card(Rank.QUEEN, Suit.SPADES)
        assert red_card.is_red() is True
        assert black_card.is_red() is False

    def test_card_is_black(self):
        red_card = Card(Rank.JACK, Suit.DIAMONDS)
        black_card = Card(Rank.JACK, Suit.CLUBS)
        assert red_card.is_black() is False
        assert black_card.is_black() is True

    def test_card_opposite_color(self):
        red_card = Card(Rank.FIVE, Suit.HEARTS)
        black_card = Card(Rank.FIVE, Suit.CLUBS)
        assert red_card.is_opposite_color(black_card) is True
        assert black_card.is_opposite_color(red_card) is True

        same_color1 = Card(Rank.THREE, Suit.HEARTS)
        same_color2 = Card(Rank.THREE, Suit.DIAMONDS)
        assert same_color1.is_opposite_color(same_color2) is False

    def test_card_flip(self):
        card = Card(Rank.SEVEN, Suit.CLUBS, face_up=False)
        flipped = card.flip()
        assert flipped.face_up is True
        assert flipped.rank == card.rank
        assert flipped.suit == card.suit

        # Flip again should turn face down
        flipped_again = flipped.flip()
        assert flipped_again.face_up is False

    def test_card_str_face_up(self):
        card = Card(Rank.ACE, Suit.SPADES, face_up=True)
        assert str(card) == "A♠"

    def test_card_str_face_down(self):
        card = Card(Rank.ACE, Suit.SPADES, face_up=False)
        assert str(card) == "##"

    def test_card_equality(self):
        card1 = Card(Rank.KING, Suit.HEARTS, face_up=True)
        card2 = Card(Rank.KING, Suit.HEARTS, face_up=True)
        card3 = Card(Rank.KING, Suit.HEARTS, face_up=False)

        assert card1 == card2
        # Face up state is part of equality
        assert card1 != card3


class TestPileType:
    """Tests for PileType enum."""

    def test_pile_types(self):
        assert PileType.STOCK.value == "stock"
        assert PileType.WASTE.value == "waste"
        assert PileType.FOUNDATION.value == "foundation"
        assert PileType.TABLEAU.value == "tableau"
