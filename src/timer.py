"""Game timer with pause/resume support."""

import time
from dataclasses import dataclass, field


@dataclass
class GameTimer:
    """Manages game elapsed time with pause/resume support.
    
    The timer tracks elapsed game time independently of wall-clock time,
    correctly handling pause/resume cycles and save/restore operations.
    
    Attributes:
        is_running: True if timer is actively accumulating time.
        is_paused: True if timer was running and is now paused.
    """
    
    _start_time: float = field(default=0.0, repr=False)
    _accumulated: float = field(default=0.0, repr=False)
    _is_running: bool = field(default=False, repr=False)
    _is_paused: bool = field(default=False, repr=False)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def start(self) -> None:
        """Start the timer. No-op if already running."""
        if self._is_running:
            return
        self._start_time = time.time()
        self._is_running = True
        self._is_paused = False

    def pause(self) -> None:
        """Pause the timer. No-op if not running."""
        if not self._is_running:
            return
        self._accumulated += time.time() - self._start_time
        self._is_running = False
        self._is_paused = True

    def resume(self) -> None:
        """Resume the timer. No-op if not paused."""
        if not self._is_paused:
            return
        self._start_time = time.time()
        self._is_running = True
        self._is_paused = False

    def reset(self) -> None:
        """Reset timer to zero and stop it."""
        self._start_time = 0.0
        self._accumulated = 0.0
        self._is_running = False
        self._is_paused = False

    def get_elapsed(self) -> float:
        """Get total elapsed time in seconds."""
        if self._is_running:
            return self._accumulated + (time.time() - self._start_time)
        return self._accumulated

    def set_elapsed(self, seconds: float) -> None:
        """Set elapsed time directly (for save/restore).
        
        Args:
            seconds: Elapsed time to set. Negative values are treated as zero.
        """
        seconds = max(0.0, seconds)
        if self._is_running:
            self._accumulated = seconds
            self._start_time = time.time()
        else:
            self._accumulated = seconds
