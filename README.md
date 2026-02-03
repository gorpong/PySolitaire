# PySolitaire 🂡

A terminal-based ASCII Klondike Solitaire game in Python

PySolitaire is a **single-player Klondike Solitaire** game played entirely in your terminal.
It uses **cursor-based navigation** with **Enter to pick up / drop cards**, aiming to feel natural, responsive, and faithful to classic Solitaire—without becoming a heavy GUI application.

The game is designed to be **playable, deterministic, and test-driven**, while remaining simple and fun.

---

## Features

* Classic **Klondike Solitaire** rules
* Fully **terminal-based ASCII UI**
* **Arrow keys + Enter** interaction model
* **Draw-1** mode (default), **Draw-3** supported
* Auto-flip exposed tableau cards
* Undo support
* Save & resume on quit
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

```python
blessed>=1.20.0
pytest>=8.0.0   # for development/testing
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/yourname/pysolitaire.git
cd pysolitaire
```

### Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

### Directory Structure

```text
PySolitaire
├── MOUSE_CONTROLS_PLAN.md
├── pyproject.toml
├── README.md
├── requirements.txt
├── src
│   ├── config.py
│   ├── cursor.py
│   ├── dealing.py
│   ├── __init__.py
│   ├── leaderboard.py
│   ├── __main__.py
│   ├── model.py
│   ├── moves.py
│   ├── overlays.py
│   ├── renderer.py
│   ├── rules.py
│   ├── save_state.py
│   ├── ui_blessed.py
│   └── undo.py
└── tests
    ├── __init__.py
    ├── test_config.py
    ├── test_cursor.py
    ├── test_dealing.py
    ├── test_leaderboard.py
    ├── test_model.py
    ├── test_moves.py
    ├── test_overlays.py
    ├── test_renderer.py
    ├── test_rules.py
    ├── test_save_state.py
    └── test_undo.py
```

---

## Running the Game

### Run directly (development)

```bash
python -m src
```

### After installation (optional)

If installed as a package:

```bash
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

```bash
pysolitaire --draw3
```

Draw-3 rules follow classic Klondike behavior, including stock recycling.

---

## Saving & Resuming

* The game **auto-saves on quit**
* On startup, you’ll be prompted to:

  * Resume the previous game
  * Start a new one
* Save file location:

  ```bash
  ~/.config/pysolitaire/save.json
  ```

* Saves include:

  * Full game state
  * Timer
  * Move count

Winning a game automatically clears the save.

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

  ```bash
  ~/.config/pysolitaire/leaderboard.json
  ```

After winning, you’ll be prompted for **3-letter initials** (arcade-style).

---

## Configuration & Reproducibility

### Seeded games

For reproducible deals:

```bash
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
* Designed for Linux / macOS / WSL terminals

---

## Troubleshooting

### Terminal too small

If your terminal is smaller than **100×40**, the game will exit with an explanatory error.
Resize your terminal window and try again.

---

## License

This project is for **educational and personal use**.
Not affiliated with or endorsed by any commercial Solitaire product.

---

Enjoy the game ♠️
If you get stuck, press **H** in-game for a quick reminder of controls.
