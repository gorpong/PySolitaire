"""Move execution and state updates for Solitaire."""

from dataclasses import dataclass
from typing import List

from pysolitaire.model import Card, GameState
from pysolitaire.rules import (
    FOUNDATION_SUIT_ORDER,
    can_draw_from_stock,
    can_pick_from_tableau,
    can_pick_from_waste,
    can_place_on_foundation,
    can_place_on_tableau,
)


@dataclass
class MoveResult:
    """Result of a move attempt."""
    success: bool
    message: str = ""


def _flip_top_if_needed(pile: List[Card]) -> None:
    """Flip the top card of a pile face-up if it's face-down."""
    if pile and not pile[-1].face_up:
        pile[-1] = pile[-1].flip()


def move_tableau_to_tableau(
    state: GameState,
    src_pile: int,
    card_index: int,
    dest_pile: int
) -> MoveResult:
    """
    Move cards from one tableau pile to another.

    Moves all cards from card_index to end of src_pile to dest_pile.
    Auto-flips the newly exposed card in src_pile if face-down.
    """
    src = state.tableau[src_pile]
    dest = state.tableau[dest_pile]

    if not can_pick_from_tableau(src, card_index):
        return MoveResult(False, "Cannot pick from that position")

    cards_to_move = src[card_index:]
    moving_card = cards_to_move[0]

    if not can_place_on_tableau(moving_card, dest):
        return MoveResult(False, "Cannot place there")

    state.tableau[src_pile] = src[:card_index]
    state.tableau[dest_pile] = dest + cards_to_move

    _flip_top_if_needed(state.tableau[src_pile])

    return MoveResult(True)


def move_waste_to_tableau(state: GameState, dest_pile: int) -> MoveResult:
    """Move the top waste card to a tableau pile."""
    if not can_pick_from_waste(state):
        return MoveResult(False, "Waste is empty")

    card = state.waste[-1]
    dest = state.tableau[dest_pile]

    if not can_place_on_tableau(card, dest):
        return MoveResult(False, "Cannot place there")

    state.waste.pop()
    state.tableau[dest_pile].append(card)

    return MoveResult(True)


def move_waste_to_foundation(state: GameState, dest_foundation: int) -> MoveResult:
    """Move the top waste card to a foundation pile."""
    if not can_pick_from_waste(state):
        return MoveResult(False, "Waste is empty")

    card = state.waste[-1]
    dest = state.foundations[dest_foundation]
    foundation_suit = FOUNDATION_SUIT_ORDER[dest_foundation]

    if not can_place_on_foundation(card, dest, foundation_suit):
        return MoveResult(False, "Cannot place on foundation")

    state.waste.pop()
    state.foundations[dest_foundation].append(card)

    return MoveResult(True)


def move_tableau_to_foundation(
    state: GameState,
    src_pile: int,
    dest_foundation: int
) -> MoveResult:
    """Move the top tableau card to a foundation pile."""
    src = state.tableau[src_pile]

    if not src:
        return MoveResult(False, "Tableau pile is empty")

    card = src[-1]

    if not card.face_up:
        return MoveResult(False, "Cannot move face-down card")

    dest = state.foundations[dest_foundation]
    foundation_suit = FOUNDATION_SUIT_ORDER[dest_foundation]

    if not can_place_on_foundation(card, dest, foundation_suit):
        return MoveResult(False, "Cannot place on foundation")

    state.tableau[src_pile].pop()
    state.foundations[dest_foundation].append(card)

    _flip_top_if_needed(state.tableau[src_pile])

    return MoveResult(True)


def move_foundation_to_tableau(
    state: GameState,
    src_foundation: int,
    dest_pile: int
) -> MoveResult:
    """Move the top foundation card back to a tableau pile."""
    src = state.foundations[src_foundation]

    if not src:
        return MoveResult(False, "Foundation is empty")

    card = src[-1]
    dest = state.tableau[dest_pile]

    if not can_place_on_tableau(card, dest):
        return MoveResult(False, "Cannot place on tableau")

    state.foundations[src_foundation].pop()
    state.tableau[dest_pile].append(card)

    return MoveResult(True)


def draw_from_stock(state: GameState, draw_count: int = 1) -> MoveResult:
    """
    Draw cards from stock to waste.

    Draws up to draw_count cards (or fewer if stock has less).
    Cards are flipped face-up when moved to waste.
    """
    if not can_draw_from_stock(state):
        return MoveResult(False, "Stock is empty")

    num_to_draw = min(draw_count, len(state.stock))

    # Stock uses list-end as "top" so pop() yields the next card to draw
    for _ in range(num_to_draw):
        card = state.stock.pop()
        if not card.face_up:
            card = card.flip()
        state.waste.append(card)

    return MoveResult(True)


def bury_top_of_stock(state: GameState) -> MoveResult:
    """
    Move the top card of stock to the bottom of stock.

    Used in Draw-3 stall recovery: when a full pass through the stock
    produced no legal moves, the player may bury the top card so the
    next Draw-3 cycle sees a different sequence.
    """
    if not state.stock:
        return MoveResult(False, "Stock is empty")

    top_card = state.stock.pop()
    state.stock.insert(0, top_card)

    return MoveResult(True)


def recycle_waste_to_stock(state: GameState) -> MoveResult:
    """
    Recycle waste pile back to stock.

    Only allowed when stock is empty.
    Cards are flipped face-down and order is reversed.
    """
    if state.stock:
        return MoveResult(False, "Stock is not empty")

    if not state.waste:
        return MoveResult(False, "Waste is empty")

    # Popping from waste end-to-end reverses order, matching how stock was originally dealt
    while state.waste:
        card = state.waste.pop()
        if card.face_up:
            card = card.flip()
        state.stock.append(card)

    return MoveResult(True)
