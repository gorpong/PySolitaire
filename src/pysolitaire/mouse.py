"""Mouse input handling for Solitaire."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from pysolitaire.cursor import CursorZone
from pysolitaire.model import GameState
from pysolitaire.renderer import (
    CardLayout,
    get_foundation_position,
    get_stock_position,
    get_tableau_card_y,
    get_tableau_pile_positions,
    get_waste_position,
)


@dataclass
class ClickableRegion:
    """Represents a clickable area on the board."""

    x: int  # Top-left x coordinate (canvas coords)
    y: int  # Top-left y coordinate (canvas coords)
    width: int  # Width of region
    height: int  # Height of region
    zone: CursorZone  # Which zone this belongs to
    pile_index: int  # Which pile (0-3 for foundation, 0-6 for tableau)
    card_index: int  # Which card in pile (for tableau), 0 for others


@dataclass
class MouseEvent:
    """Parsed mouse event from blessed."""

    button: str  # 'left', 'right', 'middle', 'unknown'
    action: str  # 'pressed', 'released'
    x: int  # Column (terminal coords, 0-based)
    y: int  # Row (terminal coords, 0-based)


def translate_mouse_coords(mouse_x: int, mouse_y: int, pad_left: int) -> Tuple[int, int]:
    """Convert terminal coordinates to canvas coordinates.

    Args:
        mouse_x: X coordinate from terminal (0-based)
        mouse_y: Y coordinate from terminal (0-based)
        pad_left: Left padding used for centering the board

    Returns:
        Tuple of (canvas_x, canvas_y)
    """
    canvas_x = mouse_x - pad_left
    canvas_y = mouse_y
    return canvas_x, canvas_y


def calculate_clickable_regions(state: GameState, layout: CardLayout) -> List[ClickableRegion]:
    """Generate clickable regions based on current board state.

    Args:
        state: Current game state
        layout: Card layout configuration

    Returns:
        List of ClickableRegion objects for all clickable areas
    """
    regions: List[ClickableRegion] = []

    # Stock region (always clickable, even when empty - to show "no cards")
    stock_x, stock_y = get_stock_position()
    regions.append(
        ClickableRegion(
            x=stock_x,
            y=stock_y,
            width=layout.card_width,
            height=layout.card_height,
            zone=CursorZone.STOCK,
            pile_index=0,
            card_index=0,
        )
    )

    # Waste region
    waste_x, waste_y = get_waste_position()
    regions.append(
        ClickableRegion(
            x=waste_x,
            y=waste_y,
            width=layout.card_width,
            height=layout.card_height,
            zone=CursorZone.WASTE,
            pile_index=0,
            card_index=0,
        )
    )

    # Foundation regions
    for i in range(4):
        fx, fy = get_foundation_position(i, layout)
        regions.append(
            ClickableRegion(
                x=fx,
                y=fy,
                width=layout.card_width,
                height=layout.card_height,
                zone=CursorZone.FOUNDATION,
                pile_index=i,
                card_index=0,
            )
        )

    # Tableau regions - need individual regions for each card to support
    # clicking on specific cards in a pile
    for pile_idx in range(7):
        tx, ty = get_tableau_pile_positions(pile_idx, layout)
        pile = state.tableau[pile_idx]

        if not pile:
            # Empty pile - single clickable region for placing Kings
            regions.append(
                ClickableRegion(
                    x=tx,
                    y=ty,
                    width=layout.card_width,
                    height=layout.card_height,
                    zone=CursorZone.TABLEAU,
                    pile_index=pile_idx,
                    card_index=0,
                )
            )
        else:
            # Create regions for each card, from bottom to top
            # Later cards (higher index) should be checked first since they're on top
            for card_idx in range(len(pile)):
                card_y = get_tableau_card_y(card_idx, layout)
                is_last = card_idx == len(pile) - 1

                if is_last:
                    # Last card shows full height
                    height = layout.card_height
                else:
                    # Overlapped cards only show overlap portion
                    height = layout.card_overlap_y

                regions.append(
                    ClickableRegion(
                        x=tx,
                        y=card_y,
                        width=layout.card_width,
                        height=height,
                        zone=CursorZone.TABLEAU,
                        pile_index=pile_idx,
                        card_index=card_idx,
                    )
                )

    return regions


def find_clicked_region(
    x: int, y: int, regions: List[ClickableRegion]
) -> Optional[ClickableRegion]:
    """Find which region was clicked.

    For overlapping regions (tableau cards), returns the topmost card
    (highest card_index) that contains the click point.

    Args:
        x: Canvas x coordinate
        y: Canvas y coordinate
        regions: List of clickable regions

    Returns:
        The clicked region, or None if click was outside all regions
    """
    # Filter to regions that contain the click point
    matching = []
    for region in regions:
        if (
            region.x <= x < region.x + region.width
            and region.y <= y < region.y + region.height
        ):
            matching.append(region)

    if not matching:
        return None

    # If multiple matches (overlapping tableau cards), prefer:
    # 1. Higher card_index (topmost card in pile)
    # 2. For same card_index, prefer tableau over other zones
    matching.sort(key=lambda r: (r.card_index, r.zone == CursorZone.TABLEAU), reverse=True)

    return matching[0]


def is_mouse_event(key) -> bool:
    """Check if a blessed key is a mouse event.

    Blessed mouse event names start with 'MOUSE_'.
    Examples: MOUSE_LEFT, MOUSE_LEFT_RELEASED, MOUSE_RIGHT, MOUSE_RIGHT_RELEASED

    Args:
        key: A key object from blessed's inkey()

    Returns:
        True if this is a mouse event
    """
    if not hasattr(key, 'name') or key.name is None:
        return False

    return key.name.startswith("MOUSE_")


def parse_mouse_event(key) -> Optional[MouseEvent]:
    """Parse a blessed key into a MouseEvent if it's a mouse event.

    Blessed mouse event names:
    - MOUSE_LEFT: left button pressed
    - MOUSE_LEFT_RELEASED: left button released
    - MOUSE_RIGHT: right button pressed
    - MOUSE_RIGHT_RELEASED: right button released
    - MOUSE_MIDDLE: middle button pressed
    - MOUSE_MIDDLE_RELEASED: middle button released

    Args:
        key: A key object from blessed's inkey()

    Returns:
        MouseEvent if this was a mouse event, None otherwise
    """
    if not is_mouse_event(key):
        return None

    name = key.name  # e.g., "MOUSE_LEFT" or "MOUSE_LEFT_RELEASED"

    # Determine if this is a press or release event
    if name.endswith("_RELEASED"):
        action = "released"
        # Remove "_RELEASED" suffix to get the button part
        button_part = name[6:-9]  # Remove "MOUSE_" prefix and "_RELEASED" suffix
    else:
        action = "pressed"
        # Remove "MOUSE_" prefix to get the button
        button_part = name[6:]  # Remove "MOUSE_" prefix

    # Parse button
    button_part_lower = button_part.lower()
    if button_part_lower == "left":
        button = "left"
    elif button_part_lower == "right":
        button = "right"
    elif button_part_lower == "middle":
        button = "middle"
    else:
        button = "unknown"

    # Get coordinates from mouse_xy attribute (0-based)
    if not hasattr(key, 'mouse_xy'):
        return None

    x, y = key.mouse_xy

    # Check for invalid coordinates (blessed uses -1, -1 for non-mouse events)
    if x < 0 or y < 0:
        return None

    return MouseEvent(button=button, action=action, x=x, y=y)
