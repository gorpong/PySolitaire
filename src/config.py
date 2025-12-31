"""Configuration for PySolitaire."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    """Configuration options for a game of Solitaire."""

    draw_count: int = 1  # Draw 1 or 3 cards from stock
    seed: Optional[int] = None  # Random seed for reproducibility

    def __post_init__(self):
        if self.draw_count not in (1, 3):
            raise ValueError("draw_count must be 1 or 3")
