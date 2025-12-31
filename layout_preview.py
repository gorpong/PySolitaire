#!/usr/bin/env python3
"""
Layout preview for terminal Solitaire.
Uses the actual renderer module to show a sample game state.
"""

import sys
sys.path.insert(0, '.')

from src.model import Card, Suit, Rank, GameState
from src.renderer import render_board, canvas_to_string, BOARD_WIDTH, BOARD_HEIGHT
import shutil


def create_sample_state() -> GameState:
    """Create a sample game state for preview."""
    state = GameState()

    # Stock has some cards
    state.stock = [Card(Rank.ACE, Suit.HEARTS, face_up=False) for _ in range(20)]

    # Waste has a card
    state.waste = [Card(Rank.SEVEN, Suit.HEARTS, face_up=True)]

    # Foundations: hearts has Ace, diamonds has up to 3
    state.foundations[0] = [Card(Rank.ACE, Suit.HEARTS, face_up=True)]
    state.foundations[1] = [
        Card(Rank.ACE, Suit.DIAMONDS, face_up=True),
        Card(Rank.TWO, Suit.DIAMONDS, face_up=True),
        Card(Rank.THREE, Suit.DIAMONDS, face_up=True),
    ]

    # Sample tableau piles
    # Pile 0: Just a King
    state.tableau[0] = [Card(Rank.KING, Suit.HEARTS, face_up=True)]

    # Pile 1: 1 face-down, 2 face-up
    state.tableau[1] = [
        Card(Rank.FIVE, Suit.CLUBS, face_up=False),
        Card(Rank.QUEEN, Suit.SPADES, face_up=True),
        Card(Rank.JACK, Suit.HEARTS, face_up=True),
    ]

    # Pile 2: 2 face-down, 1 face-up
    state.tableau[2] = [
        Card(Rank.TWO, Suit.HEARTS, face_up=False),
        Card(Rank.THREE, Suit.CLUBS, face_up=False),
        Card(Rank.NINE, Suit.CLUBS, face_up=True),
    ]

    # Pile 3: 3 face-down, 3 face-up run
    state.tableau[3] = [
        Card(Rank.ACE, Suit.CLUBS, face_up=False),
        Card(Rank.FOUR, Suit.DIAMONDS, face_up=False),
        Card(Rank.SIX, Suit.SPADES, face_up=False),
        Card(Rank.FIVE, Suit.DIAMONDS, face_up=True),
        Card(Rank.FOUR, Suit.CLUBS, face_up=True),
        Card(Rank.THREE, Suit.HEARTS, face_up=True),
    ]

    # Pile 4: 4 face-down, 2 face-up
    state.tableau[4] = [
        Card(Rank.SEVEN, Suit.CLUBS, face_up=False),
        Card(Rank.EIGHT, Suit.HEARTS, face_up=False),
        Card(Rank.NINE, Suit.SPADES, face_up=False),
        Card(Rank.TEN, Suit.DIAMONDS, face_up=False),
        Card(Rank.TEN, Suit.SPADES, face_up=True),
        Card(Rank.NINE, Suit.DIAMONDS, face_up=True),
    ]

    # Pile 5: 5 face-down, 1 face-up
    state.tableau[5] = [
        Card(Rank.JACK, Suit.CLUBS, face_up=False),
        Card(Rank.QUEEN, Suit.HEARTS, face_up=False),
        Card(Rank.KING, Suit.SPADES, face_up=False),
        Card(Rank.ACE, Suit.SPADES, face_up=False),
        Card(Rank.TWO, Suit.CLUBS, face_up=False),
        Card(Rank.SIX, Suit.HEARTS, face_up=True),
    ]

    # Pile 6: 6 face-down, 5 face-up (long run)
    state.tableau[6] = [
        Card(Rank.THREE, Suit.SPADES, face_up=False),
        Card(Rank.FOUR, Suit.HEARTS, face_up=False),
        Card(Rank.FIVE, Suit.SPADES, face_up=False),
        Card(Rank.SIX, Suit.DIAMONDS, face_up=False),
        Card(Rank.SEVEN, Suit.SPADES, face_up=False),
        Card(Rank.EIGHT, Suit.DIAMONDS, face_up=False),
        Card(Rank.KING, Suit.CLUBS, face_up=True),
        Card(Rank.QUEEN, Suit.DIAMONDS, face_up=True),
        Card(Rank.JACK, Suit.SPADES, face_up=True),
        Card(Rank.TEN, Suit.HEARTS, face_up=True),
        Card(Rank.NINE, Suit.CLUBS, face_up=True),
    ]

    return state


def main():
    term_size = shutil.get_terminal_size((100, 40))
    term_width = term_size.columns
    term_height = term_size.lines

    print(f"\nTerminal size: {term_width}x{term_height}")
    print(f"Game board size: {BOARD_WIDTH}x{BOARD_HEIGHT}")

    if term_width < BOARD_WIDTH or term_height < BOARD_HEIGHT:
        print(f"\n⚠️  Warning: Terminal is smaller than the board!")
        print(f"   Need at least {BOARD_WIDTH}x{BOARD_HEIGHT}")

    state = create_sample_state()

    # Render with cursor on waste pile
    canvas = render_board(
        state,
        cursor_zone="waste",
        cursor_index=0,
        cursor_card_index=0,
    )
    board_str = canvas_to_string(canvas)

    # Center the board if terminal is larger
    if term_width > BOARD_WIDTH:
        pad_left = (term_width - BOARD_WIDTH) // 2
        lines = board_str.split('\n')
        board_str = '\n'.join(' ' * pad_left + line for line in lines)

    print("\n" + board_str)
    print(f"\n{'─' * 60}")
    print("PREVIEW - Updated layout with 10-char tableau spacing")
    print("Cursor shown with [ ] brackets around the Waste pile")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
