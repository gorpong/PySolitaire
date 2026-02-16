# PySolitaire 🂡

A terminal-based ASCII Klondike Solitaire game in Python

PySolitaire is a **single-player Klondike Solitaire** game played entirely
in your terminal.  It uses **cursor-based navigation** with **Enter to
pick up / drop cards**, aiming to feel natural, responsive, and faithful
to classic Solitaire—without becoming a heavy GUI application.

The game is designed to be **playable, deterministic, and test-driven**,
while remaining simple and fun.

---

## Features

* Classic **Klondike Solitaire** rules
* Fully **terminal-based ASCII UI**
* **Arrow keys + Enter** interaction model
* **Mouse** controls also supported
* **Draw-1** mode (default), **Draw-3** supported
* Auto-flip exposed tableau cards
* Undo support
* Up to **10 save slots** with resume on startup
* Draw mode (Draw-1 / Draw-3) preserved across save/resume
* Timer and move counter
* Leaderboards (separate for Draw-1 / Draw-3)
* Optional reproducible games via RNG seed

---

## Requirements

* **Python 3.12+**
* A terminal that supports:

  * ANSI escape codes
  * 24-bit color (recommended)
* Minimum terminal size: **100 × 40 characters**

### Python dependencies

Dependencies are intentionally minimal:

```
blessed>=1.20.0
pytest>=8.0.0   # for development/testing
```

---

## Installation

### Clone the repository, install the game locally

```powershell
git clone https://github.com/gorpong/PySolitaire
cd PySolitaire
python -m pip install .
```

### Create a virtual environment (recommended if editing)

```powershell
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux / macOS
pip install .
```

### Directory Structure

```text
PySolitaire
├── .coveragerc
├── .gitignore
├── Makefile
├── mutmut_config.py
├── pyproject.toml
├── LICENSE.md
├── README.md
├── requirements.txt
├── src
│   └── pysolitaire
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── cursor.py
│       ├── dealing.py
│       ├── dialogs.py
│       ├── game_controller.py
│       ├── input_handler.py
│       ├── leaderboard.py
│       ├── model.py
│       ├── mouse.py
│       ├── moves.py
│       ├── overlays.py
│       ├── renderer.py
│       ├── rules.py
│       ├── save_state.py
│       ├── selection.py
│       ├── timer.py
│       ├── ui_blessed.py
│       └── undo.py
└── tests
    ├── __init__.py
    ├── test_config.py
    ├── test_cursor.py
    ├── test_dealing.py
    ├── test_dialogs.py
    ├── test_game_controller.py
    ├── test_input_handler.py
    ├── test_leaderboard.py
    ├── test_model.py
    ├── test_mouse.py
    ├── test_moves.py
    ├── test_overlays.py
    ├── test_renderer.py
    ├── test_rules.py
    ├── test_save_state.py
    ├── test_selection.py
    ├── test_timer.py
    ├── test_ui_integration.py
    └── test_undo.py
```

---

## Running the Game

### Run directly (development)

```powershell
python -m pysolitaire
```

### After installation (optional)

If installed as a package:

```powershell
pysolitaire
# or
solitaire
```

---

## Basic Controls

| Key            | Action                           |
| -------------- | -------------------------------- |
| **Arrow Keys** | Move cursor                      |
| **Enter**      | Pick up / drop card(s)           |
| **Esc**        | Cancel selection / close dialogs |
| **Q**          | Quit (auto-saves)                |
| **U**          | Undo last move                   |
| **R**          | Restart game                     |
| **H / ?**      | Help overlay                     |
| **TAB**        | Show valid destinations          |
| **L**          | View leaderboard                 |

---

## How to Play (Quick Start)

### The Core Interaction Model

PySolitaire uses a **cursor-driven pick/drop model**:

1. Use **arrow keys** to move the cursor to a card or pile.
2. Press **Enter** to **pick up**:

   * A face-up card (or run) from a tableau pile
   * The top card from the waste
   * (Optionally) the top card from a foundation
3. Move the cursor to a destination pile.
4. Press **Enter** again to **drop**:

   * If the move is legal → it succeeds
   * If illegal → the selection remains and an error message is shown
5. Press **Enter** again on the original source (or **Esc**) to cancel.

If there is **only one legal destination**, the game may automatically move the card for you.

#### Mouse Controls

PySolitaire also allows the use of the mouse for selecting and moving the cards. Click-to-Select
and then Click-to-Drop works as well as Drag-and-Drop mode. The card won't be animated when
dragging, but when the mouse is released it will be displayed in its new location or if there was
an invalid move, the selection will remain and the error message is shown.

---

## Board Layout

* **Stock**: Draw pile (top left)
* **Waste**: Face-up drawn cards
* **Foundations (4)**: Build Ace → King by suit
* **Tableau (7)**: Build descending, alternating colors

The cursor moves between these zones predictably using the arrow keys.

---

## Draw Modes

### Draw-1 (default)

* Draw one card at a time from stock to waste
* Easier gameplay
* Enables loss detection after full passes with no legal moves

### Draw-3 (optional)

Enable via command-line flag:

```powershell
pysolitaire --draw3
```

Draw-3 rules follow classic Klondike behavior, including stock recycling.

---

## Saving & Resuming

* The game **auto-saves on quit** to one of **10 save slots**
* On startup, if any saves exist you'll see a slot list showing:

  * Slot number
  * Draw mode (Draw-1 / Draw-3)
  * Move count
  * Elapsed time
  * Date/time last saved
* Press the slot number (1–9, or 0 for slot 10) to resume, **N** for a new game, or **Esc** to exit
* The draw mode from the save is always restored, regardless of command-line flags
* If all 10 slots are full when you quit, you'll be prompted to choose a slot to overwrite
* Save file location:

  ```
  ~/.config/pysolitaire/save.json
  ```

* Each save includes:

  * Full game state
  * Draw mode
  * Timer
  * Move count

Winning or losing a game automatically clears that save slot.

---

## Undo System

* Press **U** to undo the last move
* Up to **100 moves** are stored
* Undo restores:

  * Card positions
  * Face-up / face-down state
  * Timer and move count

---

## Leaderboards

* Separate leaderboards for **Draw-1** and **Draw-3**
* Top **20 scores** per mode
* Sorted by:

  1. Fewest moves
  2. Fastest time
* Stored at:

  ```
  ~/.config/pysolitaire/leaderboard.json
  ```

After winning, you'll be prompted for **3-letter initials** (arcade-style).

---

## Configuration & Reproducibility

### Seeded games

For reproducible deals:

```powershell
pysolitaire --seed 12345
```

This is useful for:

* Testing
* Debugging
* Sharing specific deals

---

## Development Notes

* Core logic is **fully test-driven**
* Game rules are implemented as **pure functions**
* UI code is isolated from rules and state
* Deterministic shuffling via seedable RNG
* Designed for Linux / macOS / WSL terminals (also runs on Windows via PowerShell)

### Running tests

```powershell
pytest
```

### Coverage report

```powershell
pytest --cov --cov-branch --cov-report=html
```

### Linting / formatting

```powershell
ruff check src tests
black src tests
```

---

## Troubleshooting

### Terminal too small

If your terminal is smaller than **100×40**, the game will exit with an explanatory error.
Resize your terminal window and try again.

---

## License

This project is for **educational and personal use** under the MIT license (see `LICENSE.md`).
Not affiliated with or endorsed by any commercial Solitaire product.

---

Enjoy the game ♠️
If you get stuck, press **H** in-game for a quick reminder of controls.
