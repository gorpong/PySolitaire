"""Core game model: Card, Suit, Rank, PileType, GameState."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Suit(Enum):
    """Card suits with color information."""

    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    def is_red(self) -> bool:
        return self in (Suit.HEARTS, Suit.DIAMONDS)

    def is_black(self) -> bool:
        return self in (Suit.CLUBS, Suit.SPADES)

    @property
    def symbol(self) -> str:
        symbols = {
            Suit.HEARTS: "♥",
            Suit.DIAMONDS: "♦",
            Suit.CLUBS: "♣",
            Suit.SPADES: "♠",
        }
        return symbols[self]


class Rank(Enum):
    """Card ranks from Ace (1) to King (13)."""

    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

    @property
    def display(self) -> str:
        displays = {
            Rank.ACE: "A",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
        }
        return displays.get(self, str(self.value))


class PileType(Enum):
    """Types of piles in Solitaire."""

    STOCK = "stock"
    WASTE = "waste"
    FOUNDATION = "foundation"
    TABLEAU = "tableau"


@dataclass
class Card:
    """A playing card with rank, suit, and face-up state."""

    rank: Rank
    suit: Suit
    face_up: bool = False

    def is_red(self) -> bool:
        return self.suit.is_red()

    def is_black(self) -> bool:
        return self.suit.is_black()

    def is_opposite_color(self, other: "Card") -> bool:
        return self.is_red() != other.is_red()

    def flip(self) -> "Card":
        """Return a new Card with flipped face_up state."""
        return Card(self.rank, self.suit, not self.face_up)

    def __str__(self) -> str:
        if not self.face_up:
            return "##"
        return f"{self.rank.display}{self.suit.symbol}"


@dataclass
class GameState:
    """Complete state of a Solitaire game."""

    stock: List[Card] = field(default_factory=list)
    waste: List[Card] = field(default_factory=list)
    foundations: List[List[Card]] = field(default_factory=lambda: [[] for _ in range(4)])
    tableau: List[List[Card]] = field(default_factory=lambda: [[] for _ in range(7)])
