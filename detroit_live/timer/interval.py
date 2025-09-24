import time
from collections.abc import Callable

from .timer import Timer, now


class Interval(Timer):
    def __init__(self, delay: float, sleep_delay: float = 0.017):
        super().__init__(sleep_delay)

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
            time.sleep(self._sleep_delay + delay)
            self._callback((now() - self._start) * 1e3, self.stop)


def interval(
    callback: Callable[[float, Callable[[None], None]], None],
    delay: float | None = None,
    starting_time: float | None = None,
    sleep_delay: float = 0.017,
) -> Timer | Interval:
    """
    The :code:`callback` is invoked only every delay milliseconds; if
    :code:`delay` is not specified, this is equivalent to timer.

    Parameters
    ----------
    callback : Callable[[float, Callable[[None], None]], None]
        Callback
    delay : float | None
        Delay value
    starting_time : float | None
        Starting time value
    sleep_delay : float
        Time delay passed to :code:`time.sleep`; it defaults to :code:`0.017`.

    Returns
    -------
    Timer | Interval
        :code:`Timer` if :code:`delay` is not specified else :code:`Interval`.
    """
    timer = Timer(sleep_delay) if delay is None else Interval(delay, sleep_delay)
    timer.restart(callback, delay, starting_time)
    return timer
