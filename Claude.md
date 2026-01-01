We are building a **terminal-based ASCII Solitaire (Klondike) game in Python**, designed to be **playable and fun** but not a full commercial product. We follow the gameplay and setup rules as specified in [Solitaire Rules](https://officialgamerules.org/game-rules/solitaire/).

### Core goals

* **Single-player Klondike Solitaire**, rendered entirely in a terminal (ASCII / glyph grid).
* Written in **Python 3.12+**, prioritizing **clarity, explicit control flow, and readable loops**.
* Use **simple, idiomatic Python**—no clever tricks, no premature abstractions.
* Prefer **small classes / dataclasses** for state, but keep it pragmatic.
* **Deterministic** where possible (seedable shuffle for testability).
* The game must feel good: responsive input, clear highlighting, helpful status messages.

---

## Input & UX requirements (CRITICAL)

### Keyboard controls

The user plays using:

* **Arrow keys**: move a **cursor/pointer** around the board.
* **Enter**: **select / pick up / drop** depending on context.
* **Esc** (or `q`): quit (confirm required).
* Optional but nice:

  * `u`: undo
  * `r`: restart (confirm)
  * `h` or `?`: help/legend overlay

### Selection semantics

This is the core interaction model:

1. **Cursor moves** to a location (stock, waste, a tableau pile, or a foundation pile).
2. **Enter** on a **source**:

   * If it’s a valid movable card or run (tableau): “pick up” that card stack.
   * If it’s waste top card: pick up that card.
   * If it’s a foundation top card: pick up that card (optional; if allowing moves back).
3. Cursor moves to a **destination**.
4. **Enter** again attempts to **drop/move**:

   * If legal per rules → commit move, update state.
   * If illegal → keep holding the selection and show an error message.
5. **Enter** on the same source again cancels selection (or `Esc` cancels).
6. If there's only one possible destination for the **source** card, animate the movement of the card to the destination position automatically when it is selected
6. Highlighting:

   * Cursor location is always visible.
   * When holding cards, show them as “selected” and highlight valid destinations (optional but desirable).

### Board navigation model

To make arrow-key navigation sane, represent the board as a small set of “focusable zones”:

* Stock
* Waste
* Foundations: 4 piles
* Tableau: 7 piles (with an internal row index for pointing at a specific face-up card)

Arrow keys move between zones and within tableau stacks in a predictable way.

---

## Game rules & scope

Follow the rules as specified in the [Solitaire Rules](https://officialgamerules.org/game-rules/solitaire/) site, but allow these variations:

### Draw rules

Implement a **configurable draw mode**:

* Draw **1** (default) OR draw **3** (optional toggle via config).
* Cycling stock when empty: support “turn over waste to stock”, optionally configurable (some variants limit passes; we can ignore pass limits for MVP unless asked).

### Win/loss

* Win: all cards in foundations.
* No formal “loss”; allow continue/quit. Optionally detect “no moves” for a message.  
  * If using the Draw-1 variant and an entire pass has gone with no legal move possible, the game is over with a "loss"
  * If using the Draw-3 variant, and an entire pass has gone with no legal move possible, have a "Top-card to Bottom?" request to allow them to bury the top card and start with the Draw-3 again.

---

## Minimal feature set (MVP but fun)

Implement these fully and cleanly:

1. **Terminal rendering**

   * Clear ASCII layout for stock, waste, foundations, tableau.
   * Cursor + selection highlighting.
   * Status line / message log (last 3–5 messages).

2. **Input handling**

   * Arrow keys + Enter selection semantics.
   * Cancel selection, quit.

3. **Rules engine**

   * Move validation for all pile types.
   * Draw from stock into waste (1 or 3).
   * Auto flip exposed face-down tableau cards.

4. **Quality-of-life**

   * Restart (reshuffle).
   * Help overlay showing keys.
   * Optional: Undo (strongly recommended if not too hard).

---

## Technical constraints

* Use a terminal UI library suitable for real-time key input and screen redraw.  This can be **`curses`** or **`blessed`**.
* Rendering should be **grid-based**, not a heavy widget UI.
* Separate concerns:

  * **Model**: deck/cards/piles/game state
  * **Rules**: move validation, dealing, draw logic
  * **UI**: rendering + input mapping + cursor model
* All state should be explicit and inspectable (easy to print/debug).

---

## Code quality expectations

* Clear naming—avoid one-letter variables except tight loops.
* No hidden global state except where justified (e.g., RNG seed, constants).
* Comments explain *why*, not *what*.
* Keep files small and purpose-driven.

Suggested structure (not mandatory):

```
PySolitaire/
  src/
    __main__.py          # entrypoint
    ui_curses.py         # curses loop, rendering, input mapping
    model.py             # Card, Pile, GameState dataclasses
    rules.py             # validation + move application helpers
    dealing.py           # shuffle/deal setup logic
    undo.py              # optional command stack
    config.py            # draw-1/draw-3, seed, etc.
  tests/
    test_rules.py
    test_dealing.py
    test_undo.py
```

---

## Test-Driven Development (TDD)

**TDD is mandatory. Follow this cycle strictly:**

1. **RED**: write tests first
2. **GREEN**: minimal code to pass
3. **REFACTOR**: clean up while staying green

Focus tests on:

* Move legality (tableau↔tableau, waste→tableau, tableau→foundation, etc.)
* Deal correctness (7 tableau piles with correct face-up tops)
* Draw behavior (1/3 draw, recycle stock)
* Flip behavior after moves

UI code can be lightly tested, but most logic should be tested via model/rules functions.

---

## Output expectations

Start by proposing:

1. A **high-level architecture** (files/modules).
2. A **development plan** broken into milestones.

Then proceed step by step, writing real Python code.

After each completed milestone:

* provide a **specific commit message**
* if there are post-milestone fixes, make them as separate commits (e.g., `Fix:` prefix)

Ask clarifying questions only if a decision has a significant impact on the build (otherwise choose a reasonable default and note it).

The goal is a **polished, playable terminal Solitaire** with **cursor + enter pick/drop** controls.

---

## Implementation Decisions Made

This section documents the decisions made during development.

### Terminal UI Library: **blessed**

After researching options (curses, blessed, prompt_toolkit, rich, Textual, asciimatics), **blessed** was chosen for:
- Excellent mouse support via SGR 1006 protocol (tmux compatible)
- Simple, Pythonic API with unified `inkey()` for keyboard and mouse
- 24-bit color support for cursor visibility
- Active maintenance (November 2025 release)
- Grid-based rendering without heavy widget framework

### Display Layout

- **Board size**: 100×40 characters
- **Card size**: 5 wide × 3 tall
- **Tableau spacing**: 10 characters between piles for clear differentiation
- **Foundation placement**: Right side (user preference)
- **Cursor style**: Bright cyan brackets `[ ]` on blue background

### Default Configuration

- **Draw mode**: Draw-1 (default) for easier gameplay and loss detection
- **Draw-3**: Available via `--draw3` command line flag
- **Seed**: Optional `--seed <number>` for reproducible games

### TAB Key Behavior

- When a card is selected, pressing **TAB** shows all valid placement destinations
- When hovering over a card (not selected), pressing **TAB** shows where that card could go
- Valid destinations are highlighted with inverted colors
- Any other input clears the highlighting

### Loss Detection (Draw-1 mode)

After 2 full passes through the stock without any successful moves, a warning is displayed suggesting the game may be unwinnable. Player can continue or restart.

### Undo System

- Command pattern with state snapshots
- Maximum 100 states stored
- Triggered by **U** key
- State saved before each move, popped on failed moves

### File Structure

```
PySolitaire/
├── src/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   ├── config.py        # GameConfig dataclass
│   ├── model.py         # Card, Suit, Rank, GameState
│   ├── dealing.py       # Shuffle/deal with seedable RNG
│   ├── rules.py         # Move validation (pure functions)
│   ├── moves.py         # Move execution with auto-flip
│   ├── cursor.py        # Zone-based navigation model
│   ├── renderer.py      # ASCII rendering functions
│   ├── ui_blessed.py    # Blessed terminal UI and game loop
│   └── undo.py          # UndoStack and state helpers
├── tests/               # 152+ passing tests (TDD)
├── requirements.txt     # blessed>=1.20.0, pytest>=8.0.0
├── pyproject.toml       # Package configuration
└── Claude.md            # This file
```

### Entry Points

The game can be run via:
- `pysolitaire` or `solitaire` (after pip install)
- `python -m src` (development)

### Minimum Terminal Size

The game requires a terminal of at least **100×40** characters. If the terminal is smaller, the game exits with an error message explaining the requirement.
