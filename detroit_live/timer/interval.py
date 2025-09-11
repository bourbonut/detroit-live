from collections.abc import Callable
from .timer import Timer, now
import time

class Interval(Timer):

    def __init__(self, delay: float):
        super().__init__()

    def restart(
        self,
        callback: Callable[[float, Callable[[None], None]], None],
        delay: float | None = None,
        starting_time: float | None = None,
    ):
        starting_time = now() if starting_time is None else starting_time
        delay = 0 if delay is None else delay * 1e-3
        difftime = (starting_time - now()) * 1e-3 + delay
        if difftime > 0:
            time.sleep(difftime)
        self._start = now()
        self._stop = False
        self._callback = callback

        while not self._stop:
            time.sleep(0.017 + delay)
            self._callback((now() - self._start) * 1e3, self.stop)


def interval(
    callback: Callable[[float, Callable[[None], None]], None],
    delay: float | None = None,
    starting_time: float | None = None,
):
    timer = Timer() if delay is None else Interval(delay)
    timer.restart(callback, delay, starting_time)
    return timer
