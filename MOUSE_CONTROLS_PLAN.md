# Mouse Controls Implementation Plan

## Overview

This document outlines the comprehensive plan for adding mouse support to PySolitaire while maintaining backward compatibility with keyboard-only controls.

---

## Goals

1. **Click-to-Select, Click-to-Place**: Click on a card to select it, click on a destination to place it
2. **Double-Click Auto-Move**: Double-click a card to automatically move it to the best valid destination (foundation if possible, otherwise first valid tableau)
3. **Drag-and-Drop** (Optional): If technically feasible with blessed's mouse support
4. **Visual Feedback**: Hover effects to show what's clickable
5. **Backward Compatibility**: Keyboard controls remain fully functional
6. **Opt-Out Flag**: `--no-mouse` flag to disable mouse support

---

## Technical Investigation

### Mouse Support in Blessed

The blessed library supports mouse input via:
- **`term.inkey()`**: Returns mouse events when mouse reporting is enabled
- **Mouse protocols**: SGR 1006 (modern, works with tmux/screen)
- **Event types**:
  - Mouse button press/release
  - Mouse movement with button held (drag)
  - Mouse position (x, y coordinates)

### Coordinate Mapping

Current board layout:
- Stock: (2, 2) - card dimensions 5×3
- Waste: (10, 2)
- Foundations: (58, 2), (66, 2), (74, 2), (82, 2)
- Tableau: Starting at y=7, piles at x = 2, 12, 22, 32, 42, 52, 62

Each pile needs a bounding box for hit detection.

---

## Implementation Strategy

### Phase 2A: Basic Click Support

**Tasks:**

1. **Enable Mouse Input**
   - Detect if terminal supports mouse
   - Enable mouse reporting in blessed context
   - Add `--no-mouse` flag to disable

2. **Create Hit Detection System**
   - `class ClickableRegion`: Define bounding box and associated pile/zone
   - `calculate_clickable_regions(state)`: Generate regions based on current board
   - `find_clicked_region(x, y, regions)`: Return which region was clicked

3. **Integrate Mouse Events into Game Loop**
   - Modify `_handle_input()` to process mouse events
   - Parse mouse event data (button, x, y, action)
   - Map clicks to game actions

4. **Click-to-Select**
   - Left click on card → select it (same as Enter on that location)
   - Show visual feedback (existing selection indicator)
   - Right click or ESC → cancel selection

5. **Click-to-Place**
   - Left click on destination when card selected → place card
   - Invalid destination → show error message, keep selection

6. **Stock Click**
   - Left click on stock → draw cards (same as Space)

### Phase 2B: Advanced Features

**Tasks:**

7. **Double-Click Auto-Move**
   - Track last click time and position
   - If same position clicked within 500ms → auto-move
   - Find best destination: foundation first, then first valid tableau

8. **Hover Effects** (if performance permits)
   - Track mouse movement events
   - Highlight hovered card/pile with different color
   - Update on mouse move (may cause flicker, test first)

9. **Drag-and-Drop** (stretch goal)
   - Mouse down on card → start drag
   - Mouse move with button held → show dragged card following cursor
   - Mouse up → drop at current location
   - More complex: requires overlay rendering

---

## Data Structures

### ClickableRegion

```python
@dataclass
class ClickableRegion:
    """Represents a clickable area on the board."""
    x: int              # Top-left x coordinate
    y: int              # Top-left y coordinate
    width: int          # Width of region
    height: int         # Height of region
    zone: CursorZone    # Which zone this belongs to
    pile_index: int     # Which pile (0-3 for foundation, 0-6 for tableau)
    card_index: int     # Which card in pile (for tableau)
```

### MouseEvent

```python
@dataclass
class MouseEvent:
    """Parsed mouse event from blessed."""
    button: str         # 'left', 'right', 'middle', 'scroll_up', 'scroll_down'
    action: str         # 'press', 'release', 'drag'
    x: int              # Column
    y: int              # Row
```

---

## Testing Strategy

### Unit Tests

1. **test_hit_detection.py**
   - Test `calculate_clickable_regions()` returns correct regions
   - Test `find_clicked_region()` returns correct region for coordinates
   - Test edge cases (clicks between cards, out of bounds)

2. **test_mouse_events.py**
   - Test parsing blessed mouse events into MouseEvent
   - Test double-click detection logic
   - Test drag detection (start, move, end)

### Integration Tests

3. **test_mouse_integration.py**
   - Mock mouse clicks on various board locations
   - Verify selection state changes correctly
   - Verify moves are executed on valid click sequences
   - Verify invalid clicks show appropriate errors

### Manual Testing

4. **Mouse Testing Checklist**
   - [ ] Click stock draws cards
   - [ ] Click waste selects top card
   - [ ] Click foundation selects top card
   - [ ] Click tableau card selects from that card down
   - [ ] Click destination with selection places card
   - [ ] Click same source cancels selection
   - [ ] Invalid destination shows error
   - [ ] Double-click auto-moves to foundation
   - [ ] Double-click auto-moves to tableau if foundation invalid
   - [ ] Right-click cancels selection
   - [ ] Hover effects work (if implemented)
   - [ ] Drag-and-drop works (if implemented)
   - [ ] --no-mouse flag disables mouse
   - [ ] Keyboard controls still work with mouse enabled

---

## Compatibility Considerations

### Terminal Compatibility

- **Modern terminals**: xterm, iTerm2, Windows Terminal → full mouse support
- **tmux/screen**: Works with SGR 1006 protocol (already used by blessed)
- **Old terminals**: May not support mouse, fallback to keyboard only
- **SSH sessions**: Mouse may not work depending on client/server setup

### Detection Strategy

```python
def supports_mouse() -> bool:
    """Check if terminal supports mouse input."""
    # Check TERM environment variable
    # Check if blessed can enable mouse reporting
    # Return True if supported, False otherwise
```

### Graceful Degradation

If mouse not supported or `--no-mouse` flag used:
- Game functions exactly as before
- No mouse event processing
- No error messages about mouse

---

## Implementation Phases

### Phase 2A: Basic Click (Recommended for MVP)

**Estimated Effort**: 1-2 days

- Enable mouse input in blessed
- Implement hit detection
- Click-to-select and click-to-place
- Stock click
- `--no-mouse` flag
- Basic tests

**Deliverable**: Fully functional click-based mouse controls

### Phase 2B: Advanced Features (Optional Enhancement)

**Estimated Effort**: 1 day

- Double-click auto-move
- Hover effects (if performance acceptable)
- Additional tests

**Deliverable**: Enhanced mouse experience with convenience features

### Phase 2C: Drag-and-Drop (Stretch Goal)

**Estimated Effort**: 2-3 days (complex)

- Drag state tracking
- Overlay rendering for dragged card
- Drop validation
- Extensive testing

**Deliverable**: Full drag-and-drop support

---

## Risks and Mitigation

### Risk 1: Performance with Mouse Events

**Issue**: Mouse move events could flood the input queue, causing lag

**Mitigation**:
- Only track mouse move if hover effects enabled
- Throttle mouse move processing (max 10 updates/second)
- Make hover effects optional

### Risk 2: Terminal Compatibility

**Issue**: Mouse may not work in all terminals/SSH sessions

**Mitigation**:
- Detect support before enabling
- Provide `--no-mouse` flag
- Document requirements clearly
- Keyboard controls always available

### Risk 3: Coordinate Mapping Errors

**Issue**: Hit detection may fail if coordinates don't match rendered positions

**Mitigation**:
- Extensive unit tests for coordinate calculations
- Visual debugging mode (show clickable regions)
- Test on multiple terminal sizes

### Risk 4: Blessed Mouse API Limitations

**Issue**: blessed's mouse support may have undocumented limitations

**Mitigation**:
- Prototype mouse handling early
- Test on multiple platforms (Linux, macOS, Windows WSL)
- Have fallback to keyboard-only

---

## Success Criteria

Phase 2A is successful when:
1. Player can complete a full game using only mouse
2. All keyboard controls still work
3. `--no-mouse` flag disables mouse without breaking game
4. No crashes or errors with mouse input
5. All mouse integration tests pass
6. Works on Linux, macOS, and WSL

---

## Alternative Approach: Minimal Mouse Support

If full mouse support proves too complex or unreliable, consider:

**Minimal Mouse Option**: Only implement stock click
- Click stock to draw cards
- Everything else remains keyboard-only
- Much simpler, lower risk
- Still provides some mouse convenience

This could be Phase 2A-lite if the full implementation encounters blockers.

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prototype mouse input** with blessed to verify API capabilities
3. **Implement Phase 2A** (basic click support)
4. **Test thoroughly** on multiple terminals and platforms
5. **Decide on Phase 2B/2C** based on Phase 2A results and user feedback

---

## Open Questions for Discussion

1. Should hover effects be enabled by default or opt-in?
2. Should drag-and-drop be pursued or is click sufficient?
3. What's the priority: getting basic mouse working quickly vs. full-featured mouse?
4. Should there be a "mouse tutorial" message on first launch?
5. Should right-click cancel selection or should it be ESC only?
