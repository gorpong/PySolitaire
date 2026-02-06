"""Deck creation, shuffling, and dealing logic."""

import random
from typing import List, Optional

from pysolitaire.model import Card, GameState, Rank, Suit


def create_deck() -> List[Card]:
    """Create a standard 52-card deck, all face down."""
    return [
        Card(rank, suit, face_up=False)
        for suit in Suit
        for rank in Rank
    ]


def shuffle_deck(deck: List[Card], seed: Optional[int] = None) -> List[Card]:
    """
    Shuffle a deck of cards with an optional seed for reproducibility.
    Returns a new shuffled list, does not modify the original.
    """
    shuffled = deck.copy()
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    return shuffled


def deal_game(seed: Optional[int] = None) -> GameState:
    """
    Deal a new game of Klondike Solitaire.

    Creates and shuffles a deck, then deals:
    - 7 tableau piles with 1, 2, 3, 4, 5, 6, 7 cards
    - Top card of each tableau pile is face up
    - Remaining 24 cards go to the stock
    """
    deck = create_deck()
    shuffled = shuffle_deck(deck, seed)

    state = GameState()
    card_index = 0

    for pile_idx in range(7):
        pile_size = pile_idx + 1
        pile_cards = []

        for card_in_pile in range(pile_size):
            card = shuffled[card_index]
            card_index += 1

            # Klondike rule: only the last card dealt to each pile starts face-up
            is_top_card = (card_in_pile == pile_size - 1)
            if is_top_card:
                card = card.flip()

            pile_cards.append(card)

        state.tableau[pile_idx] = pile_cards

    state.stock = shuffled[card_index:]

    return state
