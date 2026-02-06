"""ASCII rendering functions for Solitaire cards and board."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from pysolitaire.model import Card, GameState, Rank, Suit


@dataclass(frozen=True)
class CardLayout:
    """All dimensions that differ between the large and compact card styles.

    Frozen so instances are safe to share and impossible to mutate mid-game.
    """
    card_width: int
    card_height: int
    card_overlap_y: int          # Rows visible per overlapped card in tableau
    foundation_spacing: int      # Horizontal gap between foundation piles
    tableau_y: int               # Y coordinate where tableau piles begin


# Large layout: 7×5 cards with a centred suit on the middle row.
# STK/WST labels go above the piles (y=1) because the cards reach y=6 and
# the T-labels need y=7.  Foundation spacing widens to 9 to keep the right
# edge (column 92) inside the 100-column border.
LAYOUT_LARGE = CardLayout(
    card_width=7,
    card_height=5,
    card_overlap_y=1,
    foundation_spacing=9,
    tableau_y=8,
)

# Compact layout: original 5×3 cards.  Labels sit below the top-row piles
# exactly as they did before the large layout was introduced.
LAYOUT_COMPACT = CardLayout(
    card_width=5,
    card_height=3,
    card_overlap_y=1,
    foundation_spacing=7,
    tableau_y=7,
)


# Board layout constants (independent of card size)
BOARD_WIDTH = 100
BOARD_HEIGHT = 40

# Positions (in character coordinates)
STOCK_X = 2
STOCK_Y = 2

WASTE_X = 10
WASTE_Y = 2

FOUNDATION_START_X = 58
FOUNDATION_Y = 2

TABLEAU_START_X = 2
TABLEAU_SPACING = 10


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


def render_card_top(card: Optional[Card], layout: CardLayout) -> str:
    """Render the top line of a card."""
    interior = layout.card_width - 2
    if card is None:
        # Dashes inset by one space on each side to visually distinguish from a real card border
        return "┌ " + "─" * (interior - 2) + " ┐"
    if not card.face_up:
        return "┌" + "─" * interior + "┐"
    rank_display = card.rank.display
    # Rank left-aligned in 2 chars, suit right-aligned in 1 char, gap fills the rest
    pad = " " * (interior - 3)
    return f"┌{rank_display:<2}{pad}{card.suit.symbol}┐"


def render_card_lines(card: Optional[Card], layout: CardLayout) -> List[str]:
    """Render all lines of a card for the given layout.

    Returns exactly layout.card_height strings, each exactly layout.card_width
    characters wide.  Face-up cards show rank+suit in the corners; large layouts
    additionally centre the suit on the middle row for quick colour reading.
    """
    interior = layout.card_width - 2

    if card is None:
        top = "┌ " + "─" * (interior - 2) + " ┐"
        bot = "└ " + "─" * (interior - 2) + " ┘"
        blank = "│" + " " * interior + "│"
        return [top] + [blank] * (layout.card_height - 2) + [bot]

    if not card.face_up:
        top = "┌" + "─" * interior + "┐"
        bot = "└" + "─" * interior + "┘"
        back = "│" + "░" * interior + "│"
        return [top] + [back] * (layout.card_height - 2) + [bot]

    rank_display = card.rank.display
    suit = card.suit.symbol
    pad = " " * (interior - 3)

    top = f"┌{rank_display:<2}{pad}{suit}┐"
    bot = f"└{suit}{pad}{rank_display:>2}┘"

    # Build interior rows.  Large layouts (card_height > 3) place the suit
    # centred on the middle row; compact layouts leave interior rows blank.
    centre = (layout.card_height - 2) // 2
    interior_rows = []
    for i in range(layout.card_height - 2):
        if layout.card_height > 3 and i == centre:
            interior_rows.append(f"│{suit:^{interior}}│")
        else:
            interior_rows.append("│" + " " * interior + "│")

    return [top] + interior_rows + [bot]


def render_empty_slot_with_label(label: str, layout: CardLayout) -> List[str]:
    """Render an empty foundation slot with a suit-symbol label centred inside."""
    interior = layout.card_width - 2
    top = "┌ " + "─" * (interior - 2) + " ┐"
    bot = "└ " + "─" * (interior - 2) + " ┘"
    blank = "│" + " " * interior + "│"

    # Place the label on the vertical centre row so it lines up with where
    # the suit would appear on a large face-up card.
    centre = (layout.card_height - 2) // 2
    rows = []
    for i in range(layout.card_height - 2):
        if i == centre:
            rows.append(f"│{label:^{interior}}│")
        else:
            rows.append(blank)

    return [top] + rows + [bot]


def get_tableau_pile_positions(pile_index: int, layout: CardLayout) -> Tuple[int, int]:
    """Get the x, y coordinates for a tableau pile."""
    x = TABLEAU_START_X + pile_index * TABLEAU_SPACING
    return x, layout.tableau_y


def get_foundation_position(foundation_index: int, layout: CardLayout) -> Tuple[int, int]:
    """Get the x, y coordinates for a foundation pile."""
    x = FOUNDATION_START_X + foundation_index * layout.foundation_spacing
    return x, FOUNDATION_Y


def get_stock_position() -> Tuple[int, int]:
    """Get the x, y coordinates for the stock pile."""
    return STOCK_X, STOCK_Y


def get_waste_position() -> Tuple[int, int]:
    """Get the x, y coordinates for the waste pile."""
    return WASTE_X, WASTE_Y


def get_tableau_card_y(card_index: int, layout: CardLayout) -> int:
    """Calculate Y position for a specific card in a tableau pile.

    Cards overlap, so each card only shows card_overlap_y lines
    except the last card which shows its full height.
    """
    return layout.tableau_y + card_index * layout.card_overlap_y


def get_max_tableau_height(state: GameState, layout: CardLayout) -> int:
    """Calculate the maximum height of all tableau piles."""
    max_height = 0
    for pile in state.tableau:
        if pile:
            # Each card except the last only contributes its overlap rows; the final card is fully visible
            pile_height = (len(pile) - 1) * layout.card_overlap_y + layout.card_height
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
    card: Optional[Card],
    layout: CardLayout,
) -> None:
    """Draw a complete card at position (x, y)."""
    lines = render_card_lines(card, layout)
    for i, line in enumerate(lines):
        draw_text(canvas, x, y + i, line)


def draw_card_top_only(
    canvas: List[List[str]],
    x: int,
    y: int,
    card: Card,
    layout: CardLayout,
) -> None:
    """Draw just the top line of a card (for overlapped stacks)."""
    draw_text(canvas, x, y, render_card_top(card, layout))


def draw_border(canvas: List[List[str]], width: int, height: int) -> None:
    """Draw a border around the play area."""
    draw_text(canvas, 0, 0, "╔" + "═" * (width - 2) + "╗")
    draw_text(canvas, 0, height - 1, "╚" + "═" * (width - 2) + "╝")
    for y in range(1, height - 1):
        canvas[y][0] = "║"
        canvas[y][width - 1] = "║"


def draw_cursor(
    canvas: List[List[str]],
    x: int,
    y: int,
    layout: CardLayout,
    height: Optional[int] = None,
) -> None:
    """Draw cursor brackets around a card position.

    height defaults to layout.card_height when not specified (single-card cursor).
    Multi-card runs pass an explicit height so the brackets span the whole run.
    """
    if height is None:
        height = layout.card_height
    left_x = x - 1
    right_x = x + layout.card_width

    for dy in range(height):
        if 0 <= y + dy < len(canvas):
            if 0 <= left_x < len(canvas[0]):
                canvas[y + dy][left_x] = "["
            if 0 <= right_x < len(canvas[0]):
                canvas[y + dy][right_x] = "]"


def draw_highlight(
    canvas: List[List[str]],
    x: int,
    y: int,
    layout: CardLayout,
    height: Optional[int] = None,
) -> None:
    """Draw highlight markers around a card position using asterisks.

    Used to show valid placement destinations.  height defaults to
    layout.card_height when not specified.
    """
    if height is None:
        height = layout.card_height
    left_x = x - 1
    right_x = x + layout.card_width

    for dy in range(height):
        if 0 <= y + dy < len(canvas):
            if 0 <= left_x < len(canvas[0]):
                canvas[y + dy][left_x] = "*"
            if 0 <= right_x < len(canvas[0]):
                canvas[y + dy][right_x] = "*"


def render_board(
    state: GameState,
    cursor_zone: Optional[str] = None,
    cursor_index: int = 0,
    cursor_card_index: int = 0,
    highlighted_tableau: Optional[set] = None,
    highlighted_foundations: Optional[set] = None,
    layout: Optional[CardLayout] = None,
) -> List[List[str]]:
    """
    Render the complete game board.

    Args:
        state: Current game state
        cursor_zone: Zone where cursor is ("stock", "waste", "foundation", "tableau")
        cursor_index: Index within zone (0-3 for foundations, 0-6 for tableau)
        cursor_card_index: Card index within tableau pile (for selection)
        highlighted_tableau: Set of tableau pile indices to highlight as valid destinations
        highlighted_foundations: Set of foundation pile indices to highlight as valid destinations
        layout: CardLayout to use; defaults to LAYOUT_LARGE when None

    Returns:
        2D canvas with the rendered board
    """
    if layout is None:
        layout = LAYOUT_LARGE
    if highlighted_tableau is None:
        highlighted_tableau = set()
    if highlighted_foundations is None:
        highlighted_foundations = set()
    canvas = create_canvas(BOARD_WIDTH, BOARD_HEIGHT)
    draw_border(canvas, BOARD_WIDTH, BOARD_HEIGHT)

    title = "═══ KLONDIKE SOLITAIRE ═══"
    draw_text(canvas, (BOARD_WIDTH - len(title)) // 2, 0, title)

    # --- Stock & Waste -------------------------------------------------------
    stock_x, stock_y = get_stock_position()
    if state.stock:
        # Render as a single face-down card regardless of how many remain
        draw_card(canvas, stock_x, stock_y, Card(Rank.ACE, Suit.SPADES, face_up=False), layout)
    else:
        draw_card(canvas, stock_x, stock_y, None, layout)

    # Large cards reach y=6 so STK/WST labels go above (y=1) to avoid
    # colliding with the T-labels at y=7.  Compact cards end at y=4 so
    # labels fit below as they always did.
    if layout.card_height > 3:
        draw_text(canvas, stock_x, stock_y - 1, "STK")
    else:
        draw_text(canvas, stock_x, stock_y + layout.card_height, "STK")

    if cursor_zone == "stock":
        draw_cursor(canvas, stock_x, stock_y, layout)

    waste_x, waste_y = get_waste_position()
    if state.waste:
        draw_card(canvas, waste_x, waste_y, state.waste[-1], layout)
    else:
        draw_card(canvas, waste_x, waste_y, None, layout)

    if layout.card_height > 3:
        draw_text(canvas, waste_x, waste_y - 1, "WST")
    else:
        draw_text(canvas, waste_x, waste_y + layout.card_height, "WST")

    if cursor_zone == "waste":
        draw_cursor(canvas, waste_x, waste_y, layout)

    # --- Foundations ----------------------------------------------------------
    foundation_suits = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
    for i, suit in enumerate(foundation_suits):
        fx, fy = get_foundation_position(i, layout)
        pile = state.foundations[i]
        if pile:
            draw_card(canvas, fx, fy, pile[-1], layout)
        else:
            # Empty foundations show their target suit so the player knows which card to look for
            lines = render_empty_slot_with_label(suit.symbol, layout)
            for j, line in enumerate(lines):
                draw_text(canvas, fx, fy + j, line)

        if cursor_zone == "foundation" and cursor_index == i:
            draw_cursor(canvas, fx, fy, layout)
        elif i in highlighted_foundations:
            draw_highlight(canvas, fx, fy, layout)

    # Compact layout: FOUNDATIONS label sits on its own row below the cards,
    # so draw it here before the tableau loop.
    if layout.card_height <= 3:
        draw_text(canvas, FOUNDATION_START_X + 7, FOUNDATION_Y + layout.card_height, "FOUNDATIONS")

    # --- Tableau -------------------------------------------------------------
    for pile_idx in range(7):
        tx, ty = get_tableau_pile_positions(pile_idx, layout)
        pile = state.tableau[pile_idx]

        draw_text(canvas, tx + 1, ty - 1, f"T{pile_idx + 1}")

        if not pile:
            draw_card(canvas, tx, ty, None, layout)
            if cursor_zone == "tableau" and cursor_index == pile_idx:
                draw_cursor(canvas, tx, ty, layout)
            elif pile_idx in highlighted_tableau:
                draw_highlight(canvas, tx, ty, layout)
            continue

        for card_idx, card in enumerate(pile):
            card_y = get_tableau_card_y(card_idx, layout)
            is_last = (card_idx == len(pile) - 1)

            if is_last:
                draw_card(canvas, tx, card_y, card, layout)
            else:
                draw_card_top_only(canvas, tx, card_y, card, layout)

        if cursor_zone == "tableau" and cursor_index == pile_idx:
            cursor_y = get_tableau_card_y(cursor_card_index, layout)
            # Cursor bracket must span the entire selected run, not just one card
            remaining_cards = len(pile) - cursor_card_index
            if remaining_cards == 1:
                cursor_height = layout.card_height
            else:
                cursor_height = (remaining_cards - 1) * layout.card_overlap_y + layout.card_height
            draw_cursor(canvas, tx, cursor_y, layout, cursor_height)
        elif pile_idx in highlighted_tableau:
            # Highlight the bottom card because that is where a drop would land
            bottom_card_y = get_tableau_card_y(len(pile) - 1, layout)
            draw_highlight(canvas, tx, bottom_card_y, layout)

    # Large layout: FOUNDATIONS label sits on the T-label row but shifted
    # right past T7 (which ends at col 64) so the two don't collide.
    if layout.card_height > 3:
        draw_text(canvas, 66, layout.tableau_y - 1, "FOUNDATIONS")

    # --- Status bar ----------------------------------------------------------
    status_y = BOARD_HEIGHT - 4
    draw_text(canvas, 2, status_y, "─" * (BOARD_WIDTH - 4))
    draw_text(canvas, 2, status_y + 1, "[H]elp  [U]ndo  [R]estart  [Q]uit")
    draw_text(canvas, 2, status_y + 2, "Arrow keys to move, ENTER to select/place")

    return canvas


def canvas_to_string(canvas: List[List[str]]) -> str:
    """Convert canvas to a single string for display."""
    return '\n'.join(''.join(row) for row in canvas)
