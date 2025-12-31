"""Move validation rules for Klondike Solitaire."""

from typing import List

from src.model import Card, Suit, Rank, GameState


# Foundation suit order - maps suit to foundation index
FOUNDATION_SUIT_ORDER = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]


def can_place_on_tableau(card: Card, pile: List[Card]) -> bool:
    """
    Check if a card can be placed on a tableau pile.

    Rules:
    - Empty pile: only Kings can be placed
    - Non-empty pile: card must be opposite color and one rank lower
      than the top card, which must be face-up
    """
    if not pile:
        return card.rank == Rank.KING

    top_card = pile[-1]

    # Can't place on face-down card
    if not top_card.face_up:
        return False

    # Must be opposite color
    if not card.is_opposite_color(top_card):
        return False

    # Must be exactly one rank lower
    return card.rank.value == top_card.rank.value - 1


def can_place_on_foundation(card: Card, pile: List[Card], foundation_suit: Suit) -> bool:
    """
    Check if a card can be placed on a foundation pile.

    Rules:
    - Empty pile: only Ace of matching suit
    - Non-empty pile: next rank up, same suit
    """
    # Must match the foundation's suit
    if card.suit != foundation_suit:
        return False

    if not pile:
        return card.rank == Rank.ACE

    top_card = pile[-1]

    # Must be exactly one rank higher than top card
    return card.rank.value == top_card.rank.value + 1


def can_draw_from_stock(state: GameState) -> bool:
    """Check if we can draw from the stock pile."""
    return len(state.stock) > 0


def can_pick_from_tableau(pile: List[Card], card_index: int) -> bool:
    """
    Check if we can pick up cards starting from card_index.

    Rules:
    - Index must be valid
    - Card at index must be face-up
    """
    if not pile:
        return False

    if card_index < 0 or card_index >= len(pile):
        return False

    return pile[card_index].face_up


def can_pick_from_waste(state: GameState) -> bool:
    """Check if we can pick the top card from waste."""
    return len(state.waste) > 0


def get_valid_tableau_destinations(card: Card, state: GameState) -> List[int]:
    """
    Find all tableau pile indices where the card can be placed.

    Returns list of valid pile indices (0-6).
    """
    valid = []
    for idx, pile in enumerate(state.tableau):
        if can_place_on_tableau(card, pile):
            valid.append(idx)
    return valid


def get_valid_foundation_destinations(card: Card, state: GameState) -> List[int]:
    """
    Find all foundation pile indices where the card can be placed.

    Returns list of valid foundation indices (0-3).
    """
    valid = []
    for idx, pile in enumerate(state.foundations):
        foundation_suit = FOUNDATION_SUIT_ORDER[idx]
        if can_place_on_foundation(card, pile, foundation_suit):
            valid.append(idx)
    return valid
