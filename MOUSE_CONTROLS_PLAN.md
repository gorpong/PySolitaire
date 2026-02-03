# Mouse Controls Implementation Plan

## Overview

This document describes the mouse support implementation for PySolitaire. Mouse controls are fully implemented and working alongside keyboard controls.

---

## Features Implemented

1. **Click-to-Select, Click-to-Place**: Click on a card to select it, click on a destination to place it
2. **Drag-and-Drop**: Drag a card from source to destination in one gesture (mouse down, move, mouse up)
3. **Right-Click Cancel**: Right-click cancels the current selection
4. **Backward Compatibility**: Keyboard controls remain fully functional
5. **Opt-Out Flag**: `--no-mouse` flag to disable mouse support

---

## Technical Details

### Mouse Support in Blessed

Mouse input is enabled via `term.mouse_enabled(clicks=True)` context manager. Blessed reports mouse events as:

- `MOUSE_LEFT`: Left button pressed
- `MOUSE_LEFT_RELEASED`: Left button released
- `MOUSE_RIGHT`: Right button pressed
- `MOUSE_RIGHT_RELEASED`: Right button released
- `MOUSE_MIDDLE`: Middle button pressed
- `MOUSE_MIDDLE_RELEASED`: Middle button released

Coordinates are available via `key.mouse_xy` as a tuple of `(x, y)`.

---

## Coordinate Mapping

### Board Layout Constants

Layout-independent constants from `renderer.py`:

| Constant | Value |
|----------|-------|
| BOARD_WIDTH | 100 |
| BOARD_HEIGHT | 40 |
| STOCK_X | 2 |
| STOCK_Y | 2 |
| WASTE_X | 10 |
| WASTE_Y | 2 |
| FOUNDATION_START_X | 58 |
| FOUNDATION_Y | 2 |
| TABLEAU_START_X | 2 |
| TABLEAU_SPACING | 10 |

### Layout-Dependent Dimensions

| Property | LAYOUT_LARGE (default) | LAYOUT_COMPACT |
|----------|------------------------|----------------|
| card_width | 7 | 5 |
| card_height | 5 | 3 |
| card_overlap_y | 1 | 1 |
| foundation_spacing | 9 | 7 |
| tableau_y | 8 | 7 |

### Calculated Positions

**Foundations:**
- Large layout: x = 58, 67, 76, 85
- Compact layout: x = 58, 65, 72, 79

**Tableau piles:**
- x = 2, 12, 22, 32, 42, 52, 62 (both layouts)
- y = 8 (large) or 7 (compact)

### Board Centering

The board is centered horizontally. Mouse coordinates must be adjusted:

```python
pad_left = max(0, (terminal_width - BOARD_WIDTH) // 2)
canvas_x = mouse_x - pad_left
canvas_y = mouse_y
```

---

## Data Structures

### ClickableRegion

Defined in `src/mouse.py`:

```python
@dataclass
class ClickableRegion:
    x: int              # Top-left x coordinate (canvas coords)
    y: int              # Top-left y coordinate (canvas coords)
    width: int          # Width of region
    height: int         # Height of region
    zone: CursorZone    # Which zone this belongs to
    pile_index: int     # Which pile (0-3 for foundation, 0-6 for tableau)
    card_index: int     # Which card in pile (for tableau), 0 for others
```

### MouseEvent

Defined in `src/mouse.py`:

```python
@dataclass
class MouseEvent:
    button: str  # 'left', 'right', 'middle', 'unknown'
    action: str  # 'pressed', 'released'
    x: int       # Column (terminal coords, 0-based)
    y: int       # Row (terminal coords, 0-based)
```

### Drag State

In `SolitaireUI`:

```python
self.drag_start: Optional[Tuple[int, int]] = None
self.drag_start_region: Optional[ClickableRegion] = None
```

---

## Implementation

### Click vs Drag Detection

- On `MOUSE_LEFT` (press): Record position and region as drag start
- On `MOUSE_LEFT_RELEASED` (release): Compare release region to drag start
  - Same region → treat as click
  - Different region → treat as drag

### Mouse Event Flow

1. `_handle_input()` detects mouse event via `is_mouse_event(key)`
2. `parse_mouse_event(key)` extracts button, action, and coordinates
3. For left button:
   - Press → `_handle_mouse_down()` records drag start
   - Release → `_handle_mouse_up()` determines click vs drag
4. For right button press → `_cancel_selection()`

### Drag Execution

`_handle_drag(source, dest)`:
1. Set cursor to source region
2. Call `_try_select()` to select the card(s)
3. Set cursor to destination region
4. Call `_try_place()` to place the card(s)

This reuses existing selection/placement logic.

---

## Files

### New Files

| File | Purpose |
|------|---------|
| `src/mouse.py` | Hit detection, region calculation, mouse event parsing |
| `tests/test_mouse.py` | Unit tests for mouse functionality |

### Modified Files

| File | Changes |
|------|---------|
| `src/config.py` | Added `mouse_enabled: bool = True` |
| `src/ui_blessed.py` | Mouse event handling, drag-and-drop support |

---

## Configuration

Mouse is enabled by default. Disable with:

```bash
pysolitaire --no-mouse
```

---

## Testing

### Unit Tests

`tests/test_mouse.py` covers:
- Coordinate translation
- Clickable region calculation for both layouts
- Hit detection with edge cases
- Mouse event parsing for all button types
- Drag detection logic

### Manual Testing Completed

- [x] Click stock draws cards
- [x] Click empty stock with waste recycles
- [x] Click waste selects top card
- [x] Click foundation selects top card
- [x] Click tableau face-up card selects from that card down
- [x] Click tableau face-down card shows error
- [x] Click empty tableau pile with King selected places King
- [x] Click destination with selection places card
- [x] Click same source cancels selection
- [x] Click invalid destination shows error, keeps selection
- [x] Right-click cancels selection
- [x] ESC still cancels selection
- [x] Drag from waste to tableau executes move
- [x] Drag from waste to foundation executes move
- [x] Drag from tableau to tableau executes move
- [x] Drag from tableau to foundation executes move
- [x] Drag from foundation to tableau executes move
- [x] Drag to invalid destination shows error
- [x] Drag and release on same card acts as click
- [x] Drag starting from face-down card does nothing
- [x] Drag from stock area draws cards
- [x] `--no-mouse` flag disables all mouse handling
- [x] Keyboard controls still work with mouse enabled
- [x] Works with `--compact` layout
- [x] Works with default large layout

---

## Future Enhancements (Not Implemented)

These features were considered but not implemented:

1. **Double-Click Auto-Move**: Double-click to auto-move card to best destination
2. **Hover Effects**: Highlight cards on mouse hover
3. **Visual Drag Feedback**: Show card following cursor during drag

These may be added in future updates if desired.
