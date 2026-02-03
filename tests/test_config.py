"""Tests for GameConfig."""

import pytest
from src.config import GameConfig


class TestGameConfig:
    """Tests for GameConfig dataclass."""

    def test_default_config(self):
        config = GameConfig()
        assert config.draw_count == 1
        assert config.seed is None
        assert config.compact is False
        assert config.mouse_enabled is True

    def test_draw_count_1(self):
        config = GameConfig(draw_count=1)
        assert config.draw_count == 1

    def test_draw_count_3(self):
        config = GameConfig(draw_count=3)
        assert config.draw_count == 3

    def test_invalid_draw_count(self):
        with pytest.raises(ValueError):
            GameConfig(draw_count=2)

    def test_seed(self):
        config = GameConfig(seed=12345)
        assert config.seed == 12345

    def test_compact_mode(self):
        config = GameConfig(compact=True)
        assert config.compact is True

    def test_mouse_disabled(self):
        config = GameConfig(mouse_enabled=False)
        assert config.mouse_enabled is False

    def test_all_options(self):
        config = GameConfig(
            draw_count=3,
            seed=42,
            compact=True,
            mouse_enabled=False,
        )
        assert config.draw_count == 3
        assert config.seed == 42
        assert config.compact is True
        assert config.mouse_enabled is False
