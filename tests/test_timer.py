"""Tests for game timer functionality."""

import time

import pytest

from pysolitaire.timer import GameTimer


class TestGameTimerInitialization:
    """Tests for timer creation and initial state."""

    def test_new_timer_starts_at_zero(self):
        timer = GameTimer()
        assert timer.get_elapsed() == 0.0

    def test_new_timer_is_not_running(self):
        timer = GameTimer()
        assert timer.is_running is False

    def test_new_timer_is_not_paused(self):
        timer = GameTimer()
        assert timer.is_paused is False


class TestGameTimerRunning:
    """Tests for timer start and elapsed time tracking."""

    def test_start_begins_tracking(self):
        timer = GameTimer()
        timer.start()
        assert timer.is_running is True

    def test_elapsed_increases_while_running(self):
        timer = GameTimer()
        timer.start()
        time.sleep(0.05)
        elapsed = timer.get_elapsed()
        assert elapsed >= 0.04  # Allow small timing variance

    def test_start_when_already_running_is_noop(self):
        timer = GameTimer()
        timer.start()
        time.sleep(0.02)
        first_elapsed = timer.get_elapsed()
        timer.start()  # Should not reset
        assert timer.get_elapsed() >= first_elapsed


class TestGameTimerPauseResume:
    """Tests for pause and resume functionality."""

    def test_pause_stops_accumulation(self):
        timer = GameTimer()
        timer.start()
        time.sleep(0.03)
        timer.pause()
        paused_elapsed = timer.get_elapsed()
        time.sleep(0.03)
        assert timer.get_elapsed() == pytest.approx(paused_elapsed, abs=0.01)

    def test_pause_sets_paused_flag(self):
        timer = GameTimer()
        timer.start()
        timer.pause()
        assert timer.is_paused is True
        assert timer.is_running is False

    def test_resume_continues_from_paused_time(self):
        timer = GameTimer()
        timer.start()
        time.sleep(0.02)
        timer.pause()
        paused_elapsed = timer.get_elapsed()
        time.sleep(0.02)
        timer.resume()
        time.sleep(0.02)
        # Should be paused_elapsed + ~0.02, not paused_elapsed + ~0.04
        assert timer.get_elapsed() >= paused_elapsed + 0.01
        assert timer.get_elapsed() < paused_elapsed + 0.05

    def test_resume_clears_paused_flag(self):
        timer = GameTimer()
        timer.start()
        timer.pause()
        timer.resume()
        assert timer.is_paused is False
        assert timer.is_running is True

    def test_pause_when_not_running_is_noop(self):
        timer = GameTimer()
        timer.pause()
        assert timer.is_paused is False
        assert timer.is_running is False

    def test_resume_when_not_paused_is_noop(self):
        timer = GameTimer()
        timer.start()
        elapsed_before = timer.get_elapsed()
        timer.resume()  # Already running, not paused
        assert timer.is_running is True
        assert timer.get_elapsed() >= elapsed_before

    def test_multiple_pause_resume_cycles(self):
        timer = GameTimer()
        timer.start()
        
        # First cycle
        time.sleep(0.02)
        timer.pause()
        after_first = timer.get_elapsed()
        time.sleep(0.02)  # Should not count
        
        # Second cycle
        timer.resume()
        time.sleep(0.02)
        timer.pause()
        after_second = timer.get_elapsed()
        time.sleep(0.02)  # Should not count
        
        # Third cycle
        timer.resume()
        time.sleep(0.02)
        final = timer.get_elapsed()
        
        # Should have ~0.06s of actual running time, not ~0.10s
        assert after_second > after_first
        assert final > after_second
        assert final < 0.15  # Well under if pauses worked


class TestGameTimerReset:
    """Tests for timer reset functionality."""

    def test_reset_clears_elapsed(self):
        timer = GameTimer()
        timer.start()
        time.sleep(0.02)
        timer.reset()
        assert timer.get_elapsed() == 0.0

    def test_reset_stops_timer(self):
        timer = GameTimer()
        timer.start()
        timer.reset()
        assert timer.is_running is False
        assert timer.is_paused is False

    def test_reset_while_paused(self):
        timer = GameTimer()
        timer.start()
        timer.pause()
        timer.reset()
        assert timer.get_elapsed() == 0.0
        assert timer.is_paused is False


class TestGameTimerSetElapsed:
    """Tests for setting elapsed time (save/restore support)."""

    def test_set_elapsed_on_stopped_timer(self):
        timer = GameTimer()
        timer.set_elapsed(125.5)
        assert timer.get_elapsed() == pytest.approx(125.5, abs=0.01)

    def test_set_elapsed_and_start_continues_from_value(self):
        timer = GameTimer()
        timer.set_elapsed(100.0)
        timer.start()
        time.sleep(0.02)
        assert timer.get_elapsed() >= 100.01

    def test_set_elapsed_while_running_adjusts_baseline(self):
        timer = GameTimer()
        timer.start()
        time.sleep(0.02)
        timer.set_elapsed(50.0)
        time.sleep(0.02)
        elapsed = timer.get_elapsed()
        assert elapsed >= 50.01
        assert elapsed < 50.1

    def test_set_elapsed_while_paused(self):
        timer = GameTimer()
        timer.start()
        timer.pause()
        timer.set_elapsed(200.0)
        assert timer.get_elapsed() == pytest.approx(200.0, abs=0.01)
        assert timer.is_paused is True


class TestGameTimerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_set_elapsed_zero(self):
        timer = GameTimer()
        timer.set_elapsed(50.0)
        timer.set_elapsed(0.0)
        assert timer.get_elapsed() == 0.0

    def test_set_elapsed_negative_treated_as_zero(self):
        timer = GameTimer()
        timer.set_elapsed(-10.0)
        assert timer.get_elapsed() == 0.0

    def test_get_elapsed_never_negative(self):
        timer = GameTimer()
        # Even with timing edge cases, should never return negative
        for _ in range(10):
            assert timer.get_elapsed() >= 0.0
