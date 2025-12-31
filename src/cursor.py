"""Cursor navigation model for Solitaire board."""

from dataclasses import dataclass
from enum import Enum
from src.model import GameState


class CursorZone(Enum):
    """Zones on the board that the cursor can focus."""
    STOCK = "stock"
    WASTE = "waste"
    FOUNDATION = "foundation"
    TABLEAU = "tableau"


@dataclass
class Cursor:
    """
    Represents cursor position on the Solitaire board.

    Attributes:
        zone: Which zone the cursor is in
        pile_index: Index within zone (0-3 for foundation, 0-6 for tableau)
        card_index: Card index within tableau pile (for selecting runs)
    """
    zone: CursorZone = CursorZone.STOCK
    pile_index: int = 0
    card_index: int = 0

    def get_zone_string(self) -> str:
        """Get the zone as a string for renderer."""
        return self.zone.value

    def move_left(self, state: GameState) -> None:
        """Move cursor left."""
        if self.zone == CursorZone.STOCK:
            # Can't go left from stock
            pass
        elif self.zone == CursorZone.WASTE:
            self.zone = CursorZone.STOCK
            self.pile_index = 0
        elif self.zone == CursorZone.FOUNDATION:
            if self.pile_index > 0:
                self.pile_index -= 1
            else:
                self.zone = CursorZone.WASTE
                self.pile_index = 0
        elif self.zone == CursorZone.TABLEAU:
            if self.pile_index > 0:
                self.pile_index -= 1
                self._reset_card_index(state)

    def move_right(self, state: GameState) -> None:
        """Move cursor right."""
        if self.zone == CursorZone.STOCK:
            self.zone = CursorZone.WASTE
            self.pile_index = 0
        elif self.zone == CursorZone.WASTE:
            self.zone = CursorZone.FOUNDATION
            self.pile_index = 0
        elif self.zone == CursorZone.FOUNDATION:
            if self.pile_index < 3:
                self.pile_index += 1
            # Can't go right from foundation 3
        elif self.zone == CursorZone.TABLEAU:
            if self.pile_index < 6:
                self.pile_index += 1
                self._reset_card_index(state)

    def move_up(self, state: GameState) -> None:
        """Move cursor up."""
        if self.zone == CursorZone.STOCK:
            # Can't go up from stock
            pass
        elif self.zone == CursorZone.WASTE:
            # Can't go up from waste
            pass
        elif self.zone == CursorZone.FOUNDATION:
            # Can't go up from foundation
            pass
        elif self.zone == CursorZone.TABLEAU:
            # First check if we can move up within the pile (to earlier face-up card)
            first_selectable = self.get_first_selectable_card_index(state)
            if self.card_index > first_selectable:
                self.card_index -= 1
            else:
                # Move to the zone above
                self._move_to_zone_above(state)

    def move_down(self, state: GameState) -> None:
        """Move cursor down."""
        if self.zone == CursorZone.STOCK:
            self.zone = CursorZone.TABLEAU
            self.pile_index = 0
            self._reset_card_index(state)
        elif self.zone == CursorZone.WASTE:
            self.zone = CursorZone.TABLEAU
            self.pile_index = 1
            self._reset_card_index(state)
        elif self.zone == CursorZone.FOUNDATION:
            # Move to corresponding tableau pile (foundation 0-3 -> tableau 5-6 area)
            self.zone = CursorZone.TABLEAU
            # Map foundation to right-side tableau piles
            self.pile_index = min(5 + self.pile_index // 2, 6)
            self._reset_card_index(state)
        elif self.zone == CursorZone.TABLEAU:
            # Move down within pile if possible
            pile = state.tableau[self.pile_index]
            if pile and self.card_index < len(pile) - 1:
                self.card_index += 1

    def _move_to_zone_above(self, state: GameState) -> None:
        """Move from tableau to the zone above based on pile position."""
        if self.pile_index == 0:
            self.zone = CursorZone.STOCK
        elif self.pile_index == 1:
            self.zone = CursorZone.WASTE
        else:
            # Piles 2-6 go to foundation area
            self.zone = CursorZone.FOUNDATION
            # Map tableau pile to foundation (piles 2-4 -> foundation 0, piles 5-6 -> foundation 1-3)
            if self.pile_index <= 4:
                self.pile_index = 0
            else:
                self.pile_index = min(self.pile_index - 5, 3)
        self.card_index = 0

    def _reset_card_index(self, state: GameState) -> None:
        """Reset card index when changing tableau piles."""
        self.card_index = 0
        self.snap_to_selectable(state)

    def get_first_selectable_card_index(self, state: GameState) -> int:
        """
        Get the index of the first selectable (face-up) card in current tableau pile.
        Returns 0 if pile is empty or not in tableau zone.
        """
        if self.zone != CursorZone.TABLEAU:
            return 0

        pile = state.tableau[self.pile_index]
        if not pile:
            return 0

        # Find first face-up card
        for idx, card in enumerate(pile):
            if card.face_up:
                return idx
        return 0

    def snap_to_selectable(self, state: GameState) -> None:
        """Snap cursor to first selectable card in current tableau pile."""
        if self.zone != CursorZone.TABLEAU:
            return

        pile = state.tableau[self.pile_index]
        if not pile:
            self.card_index = 0
            return

        first_selectable = self.get_first_selectable_card_index(state)
        if self.card_index < first_selectable:
            self.card_index = first_selectable
