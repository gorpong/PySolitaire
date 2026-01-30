"""Tests for GameConfig dataclass."""

import pytest
from src.config import GameConfig


class TestGameConfigDefaults:
    """Tests for default configuration values."""

    def test_default_draw_count(self):
        config = GameConfig()
        assert config.draw_count == 1

    def test_default_seed(self):
        config = GameConfig()
        assert config.seed is None


class TestGameConfigValidation:
    """Tests for configuration validation."""

    def test_draw_count_1_accepted(self):
        """draw_count of 1 is a valid configuration."""
        config = GameConfig(draw_count=1)
        assert config.draw_count == 1

    def test_draw_count_3_accepted(self):
        """draw_count of 3 is a valid configuration."""
        config = GameConfig(draw_count=3)
        assert config.draw_count == 3

    def test_invalid_draw_count_raises(self):
        """draw_count outside {1, 3} is rejected at construction time
        so callers learn immediately rather than at first draw."""
        with pytest.raises(ValueError, match="draw_count must be 1 or 3"):
            GameConfig(draw_count=2)

    def test_seed_accepts_integer(self):
        """An explicit integer seed is stored for reproducible games."""
        config = GameConfig(seed=42)
        assert config.seed == 42
