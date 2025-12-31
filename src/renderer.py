"""ASCII rendering functions for Solitaire cards and board."""

from typing import List, Optional, Tuple
from src.model import Card, Suit, Rank, GameState


# Card dimensions
CARD_WIDTH = 5
CARD_HEIGHT = 3
CARD_OVERLAP_Y = 1  # When stacked face-up, show this many lines per card

# Board layout constants
BOARD_WIDTH = 100
BOARD_HEIGHT = 40

# Positions (in character coordinates)
STOCK_X = 2
STOCK_Y = 2

WASTE_X = 10
WASTE_Y = 2

FOUNDATION_START_X = 58
FOUNDATION_Y = 2
FOUNDATION_SPACING = 7

TABLEAU_START_X = 2
TABLEAU_Y = 7
TABLEAU_SPACING = 10  # Increased for better differentiation


# Color codes for blessed terminal
class Colors:
    """Color names for blessed terminal styling."""
    RED = "red"
    BLACK = "black"
    CURSOR = "bright_cyan"
    SELECTED = "bright_green"
    VALID_DEST = "bright_yellow"
    CARD_BG = "on_white"
    CARD_BACK = "blue"


def get_card_color(card: Card) -> str:
    """Get the color for a card's suit."""
    if card.is_red():
        return Colors.RED
    return Colors.BLACK


def render_card_top(card: Optional[Card]) -> str:
    """Render the top line of a card."""
    if card is None:
        return "┌ ─ ┐"  # Empty slot
    if not card.face_up:
        return "┌───┐"
    rank_display = card.rank.display
    return f"┌{rank_display:<2}{card.suit.symbol}┐"


def render_card_middle(card: Optional[Card]) -> str:
    """Render the middle line of a card."""
    if card is None:
        return "│   │"  # Empty slot
    if not card.face_up:
        return "│░░░│"
    return "│   │"


def render_card_bottom(card: Optional[Card]) -> str:
    """Render the bottom line of a card."""
    if card is None:
        return "└ ─ ┘"  # Empty slot
    if not card.face_up:
        return "└───┘"
    rank_display = card.rank.display
    return f"└{card.suit.symbol}{rank_display:>2}┘"


def render_card_lines(card: Optional[Card]) -> List[str]:
    """Render all 3 lines of a card."""
    return [
        render_card_top(card),
        render_card_middle(card),
        render_card_bottom(card),
    ]


def render_empty_slot_with_label(label: str) -> List[str]:
    """Render an empty slot with a label inside."""
    # Center the label
    padded = f"{label:^3}"
    return [
        "┌ ─ ┐",
        f"│{padded}│",
        "└ ─ ┘",
    ]


def get_tableau_pile_positions(pile_index: int) -> Tuple[int, int]:
    """Get the x, y coordinates for a tableau pile."""
    x = TABLEAU_START_X + pile_index * TABLEAU_SPACING
    y = TABLEAU_Y
    return x, y


def get_foundation_position(foundation_index: int) -> Tuple[int, int]:
    """Get the x, y coordinates for a foundation pile."""
    x = FOUNDATION_START_X + foundation_index * FOUNDATION_SPACING
    y = FOUNDATION_Y
    return x, y


def get_stock_position() -> Tuple[int, int]:
    """Get the x, y coordinates for the stock pile."""
    return STOCK_X, STOCK_Y


def get_waste_position() -> Tuple[int, int]:
    """Get the x, y coordinates for the waste pile."""
    return WASTE_X, WASTE_Y


def get_tableau_card_y(pile: List[Card], card_index: int) -> int:
    """
    Calculate Y position for a specific card in a tableau pile.

    Cards overlap, so each card only shows CARD_OVERLAP_Y lines
    except the last card which shows full CARD_HEIGHT.
    """
    return TABLEAU_Y + card_index * CARD_OVERLAP_Y


def get_max_tableau_height(state: GameState) -> int:
    """Calculate the maximum height of all tableau piles."""
    max_height = 0
    for pile in state.tableau:
        if pile:
            # Height = overlap lines for all but last + full card for last
            pile_height = (len(pile) - 1) * CARD_OVERLAP_Y + CARD_HEIGHT
            max_height = max(max_height, pile_height)
    return max_height


def create_canvas(width: int, height: int) -> List[List[str]]:
    """Create a blank canvas filled with spaces."""
    return [[' ' for _ in range(width)] for _ in range(height)]


def draw_text(canvas: List[List[str]], x: int, y: int, text: str) -> None:
    """Draw text onto the canvas at position (x, y)."""
    for i, char in enumerate(text):
        if 0 <= y < len(canvas) and 0 <= x + i < len(canvas[0]):
            canvas[y][x + i] = char


def draw_card(
    canvas: List[List[str]],
    x: int,
    y: int,
    card: Optional[Card]
) -> None:
    """Draw a complete card at position (x, y)."""
    lines = render_card_lines(card)
    for i, line in enumerate(lines):
        draw_text(canvas, x, y + i, line)


def draw_card_top_only(
    canvas: List[List[str]],
    x: int,
    y: int,
    card: Card
) -> None:
    """Draw just the top line of a card (for overlapped stacks)."""
    draw_text(canvas, x, y, render_card_top(card))


def draw_border(canvas: List[List[str]], width: int, height: int) -> None:
    """Draw a border around the play area."""
    # Top border
    draw_text(canvas, 0, 0, "╔" + "═" * (width - 2) + "╗")
    # Bottom border
    draw_text(canvas, 0, height - 1, "╚" + "═" * (width - 2) + "╝")
    # Side borders
    for y in range(1, height - 1):
        canvas[y][0] = "║"
        canvas[y][width - 1] = "║"


def draw_cursor(
    canvas: List[List[str]],
    x: int,
    y: int,
    height: int = CARD_HEIGHT
) -> None:
    """
    Draw cursor brackets around a card position.

    The cursor is drawn one column to the left/right of the card.
    """
    left_x = x - 1
    right_x = x + CARD_WIDTH

    for dy in range(height):
        if 0 <= y + dy < len(canvas):
            if 0 <= left_x < len(canvas[0]):
                canvas[y + dy][left_x] = "["
            if 0 <= right_x < len(canvas[0]):
                canvas[y + dy][right_x] = "]"


def render_board(
    state: GameState,
    cursor_zone: Optional[str] = None,
    cursor_index: int = 0,
    cursor_card_index: int = 0,
    selected_zone: Optional[str] = None,
    selected_index: int = 0,
    selected_card_index: int = 0,
) -> List[List[str]]:
    """
    Render the complete game board.

    Args:
        state: Current game state
        cursor_zone: Zone where cursor is ("stock", "waste", "foundation", "tableau")
        cursor_index: Index within zone (0-3 for foundations, 0-6 for tableau)
        cursor_card_index: Card index within tableau pile (for selection)
        selected_zone: Zone of selected cards (if any)
        selected_index: Index within selected zone
        selected_card_index: Starting card index of selection

    Returns:
        2D canvas with the rendered board
    """
    canvas = create_canvas(BOARD_WIDTH, BOARD_HEIGHT)
    draw_border(canvas, BOARD_WIDTH, BOARD_HEIGHT)

    # Title
    title = "═══ KLONDIKE SOLITAIRE ═══"
    draw_text(canvas, (BOARD_WIDTH - len(title)) // 2, 0, title)

    # Draw stock
    stock_x, stock_y = get_stock_position()
    if state.stock:
        # Show face-down card representing stock
        draw_card(canvas, stock_x, stock_y, Card(Rank.ACE, Suit.SPADES, face_up=False))
    else:
        draw_card(canvas, stock_x, stock_y, None)  # Empty slot
    draw_text(canvas, stock_x, stock_y + CARD_HEIGHT, "STK")

    # Draw cursor on stock if applicable
    if cursor_zone == "stock":
        draw_cursor(canvas, stock_x, stock_y)

    # Draw waste
    waste_x, waste_y = get_waste_position()
    if state.waste:
        draw_card(canvas, waste_x, waste_y, state.waste[-1])
    else:
        draw_card(canvas, waste_x, waste_y, None)
    draw_text(canvas, waste_x, waste_y + CARD_HEIGHT, "WST")

    # Draw cursor on waste if applicable
    if cursor_zone == "waste":
        draw_cursor(canvas, waste_x, waste_y)

    # Draw foundations
    foundation_suits = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
    for i, suit in enumerate(foundation_suits):
        fx, fy = get_foundation_position(i)
        pile = state.foundations[i]
        if pile:
            draw_card(canvas, fx, fy, pile[-1])
        else:
            # Show suit symbol in empty foundation
            lines = render_empty_slot_with_label(suit.symbol)
            for j, line in enumerate(lines):
                draw_text(canvas, fx, fy + j, line)

        # Draw cursor on foundation if applicable
        if cursor_zone == "foundation" and cursor_index == i:
            draw_cursor(canvas, fx, fy)

    draw_text(canvas, FOUNDATION_START_X + 7, FOUNDATION_Y + CARD_HEIGHT, "FOUNDATIONS")

    # Draw tableau piles
    for pile_idx in range(7):
        tx, ty = get_tableau_pile_positions(pile_idx)
        pile = state.tableau[pile_idx]

        # Pile label
        draw_text(canvas, tx + 1, ty - 1, f"T{pile_idx + 1}")

        if not pile:
            draw_card(canvas, tx, ty, None)
            if cursor_zone == "tableau" and cursor_index == pile_idx:
                draw_cursor(canvas, tx, ty)
            continue

        # Draw cards with overlap
        for card_idx, card in enumerate(pile):
            card_y = get_tableau_card_y(pile, card_idx)
            is_last = (card_idx == len(pile) - 1)

            if is_last:
                draw_card(canvas, tx, card_y, card)
            else:
                draw_card_top_only(canvas, tx, card_y, card)

        # Draw cursor on tableau if applicable
        if cursor_zone == "tableau" and cursor_index == pile_idx:
            # Cursor on specific card in pile
            cursor_y = get_tableau_card_y(pile, cursor_card_index)
            # Height of cursor: from this card to end of pile
            remaining_cards = len(pile) - cursor_card_index
            if remaining_cards == 1:
                cursor_height = CARD_HEIGHT
            else:
                cursor_height = (remaining_cards - 1) * CARD_OVERLAP_Y + CARD_HEIGHT
            draw_cursor(canvas, tx, cursor_y, cursor_height)

    # Status area
    status_y = BOARD_HEIGHT - 4
    draw_text(canvas, 2, status_y, "─" * (BOARD_WIDTH - 4))
    draw_text(canvas, 2, status_y + 1, "[H]elp  [U]ndo  [R]estart  [Q]uit")
    draw_text(canvas, 2, status_y + 2, "Arrow keys to move, ENTER to select/place")

    return canvas


def canvas_to_string(canvas: List[List[str]]) -> str:
    """Convert canvas to a single string for display."""
    return '\n'.join(''.join(row) for row in canvas)
