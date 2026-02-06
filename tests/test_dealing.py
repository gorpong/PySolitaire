"""Tests for dealing logic (shuffle, deal, deck creation)."""

from pysolitaire.dealing import create_deck, deal_game, shuffle_deck
from pysolitaire.model import GameState, Rank, Suit


class TestCreateDeck:
    """Tests for deck creation."""

    def test_deck_has_52_cards(self):
        deck = create_deck()
        assert len(deck) == 52

    def test_deck_has_all_suits(self):
        deck = create_deck()
        suits = {card.suit for card in deck}
        assert suits == {Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES}

    def test_deck_has_all_ranks(self):
        deck = create_deck()
        ranks = {card.rank for card in deck}
        assert len(ranks) == 13
        assert Rank.ACE in ranks
        assert Rank.KING in ranks

    def test_deck_has_13_cards_per_suit(self):
        deck = create_deck()
        for suit in Suit:
            suit_cards = [c for c in deck if c.suit == suit]
            assert len(suit_cards) == 13

    def test_deck_cards_are_face_down(self):
        deck = create_deck()
        assert all(card.face_up is False for card in deck)

    def test_deck_has_unique_cards(self):
        deck = create_deck()
        # Compare by rank and suit (ignoring face_up for uniqueness check)
        card_ids = [(c.rank, c.suit) for c in deck]
        assert len(card_ids) == len(set(card_ids))


class TestShuffleDeck:
    """Tests for shuffling."""

    def test_shuffle_returns_52_cards(self):
        deck = create_deck()
        shuffled = shuffle_deck(deck, seed=42)
        assert len(shuffled) == 52

    def test_shuffle_is_deterministic_with_seed(self):
        deck1 = create_deck()
        deck2 = create_deck()

        shuffled1 = shuffle_deck(deck1, seed=12345)
        shuffled2 = shuffle_deck(deck2, seed=12345)

        # Same seed should produce same order
        for c1, c2 in zip(shuffled1, shuffled2):
            assert c1.rank == c2.rank
            assert c1.suit == c2.suit

    def test_shuffle_different_seeds_produce_different_orders(self):
        deck1 = create_deck()
        deck2 = create_deck()

        shuffled1 = shuffle_deck(deck1, seed=111)
        shuffled2 = shuffle_deck(deck2, seed=222)

        # Different seeds should (almost certainly) produce different orders
        same_position = sum(
            1 for c1, c2 in zip(shuffled1, shuffled2)
            if c1.rank == c2.rank and c1.suit == c2.suit
        )
        # Very unlikely all 52 are in same position with different seeds
        assert same_position < 52

    def test_shuffle_preserves_all_cards(self):
        deck = create_deck()
        shuffled = shuffle_deck(deck, seed=42)

        # Use enum values for sorting since Enums aren't directly comparable
        def card_key(card):
            return (card.rank.value, card.suit.value)

        original_ids = sorted(deck, key=card_key)
        shuffled_ids = sorted(shuffled, key=card_key)

        # Compare by rank and suit
        for orig, shuf in zip(original_ids, shuffled_ids):
            assert orig.rank == shuf.rank
            assert orig.suit == shuf.suit

    def test_shuffle_does_not_modify_original(self):
        deck = create_deck()
        original_first = (deck[0].rank, deck[0].suit)
        shuffle_deck(deck, seed=42)
        # Original deck should be unchanged
        assert (deck[0].rank, deck[0].suit) == original_first


class TestDealGame:
    """Tests for dealing a Klondike game."""

    def test_deal_returns_game_state(self):
        state = deal_game(seed=42)
        assert isinstance(state, GameState)

    def test_deal_has_seven_tableau_piles(self):
        state = deal_game(seed=42)
        assert len(state.tableau) == 7

    def test_deal_tableau_pile_sizes(self):
        """Tableau piles should have 1, 2, 3, 4, 5, 6, 7 cards respectively."""
        state = deal_game(seed=42)
        for i, pile in enumerate(state.tableau):
            expected_size = i + 1
            assert len(pile) == expected_size, f"Pile {i} should have {expected_size} cards"

    def test_deal_tableau_top_card_face_up(self):
        """The top card of each tableau pile should be face up."""
        state = deal_game(seed=42)
        for i, pile in enumerate(state.tableau):
            # Top card (last in list) should be face up
            assert pile[-1].face_up is True, f"Top of pile {i} should be face up"

    def test_deal_tableau_bottom_cards_face_down(self):
        """All cards except the top should be face down."""
        state = deal_game(seed=42)
        for i, pile in enumerate(state.tableau):
            for j, card in enumerate(pile[:-1]):  # All but last
                assert card.face_up is False, f"Card {j} of pile {i} should be face down"

    def test_deal_stock_has_remaining_cards(self):
        """Stock should have 52 - 28 = 24 cards."""
        state = deal_game(seed=42)
        # 1+2+3+4+5+6+7 = 28 cards dealt to tableau
        assert len(state.stock) == 24

    def test_deal_stock_cards_face_down(self):
        state = deal_game(seed=42)
        assert all(card.face_up is False for card in state.stock)

    def test_deal_waste_is_empty(self):
        state = deal_game(seed=42)
        assert len(state.waste) == 0

    def test_deal_foundations_are_empty(self):
        state = deal_game(seed=42)
        assert len(state.foundations) == 4
        assert all(len(pile) == 0 for pile in state.foundations)

    def test_deal_total_cards_is_52(self):
        state = deal_game(seed=42)
        total = (
            len(state.stock) +
            len(state.waste) +
            sum(len(p) for p in state.tableau) +
            sum(len(p) for p in state.foundations)
        )
        assert total == 52

    def test_deal_is_deterministic(self):
        """Same seed should produce same deal."""
        state1 = deal_game(seed=99999)
        state2 = deal_game(seed=99999)

        # Check stock is same
        for c1, c2 in zip(state1.stock, state2.stock):
            assert c1.rank == c2.rank
            assert c1.suit == c2.suit

        # Check tableau is same
        for pile1, pile2 in zip(state1.tableau, state2.tableau):
            for c1, c2 in zip(pile1, pile2):
                assert c1.rank == c2.rank
                assert c1.suit == c2.suit

    def test_deal_different_seeds_produce_different_games(self):
        state1 = deal_game(seed=111)
        state2 = deal_game(seed=222)

        # Compare the visible (top) cards of tableau
        tops1 = [(p[-1].rank, p[-1].suit) for p in state1.tableau]
        tops2 = [(p[-1].rank, p[-1].suit) for p in state2.tableau]

        # Very unlikely all 7 top cards are the same with different seeds
        assert tops1 != tops2
