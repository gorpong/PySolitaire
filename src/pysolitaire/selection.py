"""Selection and highlight data types for Solitaire UI.

These data classes represent the user's current card selection and
valid placement destinations for highlighting.
"""

from dataclasses import dataclass, field
from typing import Set

from pysolitaire.cursor import CursorZone


@dataclass
class Selection:
    """Represents currently selected cards.
    
    Attributes:
        zone: The board zone where the selection originated.
        pile_index: Index within the zone (0-3 for foundations, 0-6 for tableau).
        card_index: For tableau selections, the starting card of a run.
    """
    zone: CursorZone
    pile_index: int = 0
    card_index: int = 0


@dataclass
class HighlightedDestinations:
    """Valid destinations to highlight for the current selection.
    
    Used to show the player where their selected card(s) can legally
    be placed.
    
    Attributes:
        tableau_piles: Set of tableau pile indices (0-6) that are valid.
        foundation_piles: Set of foundation pile indices (0-3) that are valid.
    """
    tableau_piles: Set[int] = field(default_factory=set)
    foundation_piles: Set[int] = field(default_factory=set)

    @classmethod
    def empty(cls) -> "HighlightedDestinations":
        """Create an instance with no highlighted destinations."""
        return cls(tableau_piles=set(), foundation_piles=set())

    def has_any(self) -> bool:
        """Return True if there is at least one valid destination."""
        return bool(self.tableau_piles or self.foundation_piles)

    def count(self) -> int:
        """Return total number of valid destinations."""
        return len(self.tableau_piles) + len(self.foundation_piles)
