import asyncio
from collections.abc import Callable

from .timer import Timer, TimerEvent, now


class Interval(Timer):
    async def restart(
        self,
        callback: Callable[[float, TimerEvent], None],
        delay: float | None = None,
        starting_time: float | None = None,
    ) -> int:
        starting_time = now() if starting_time is None else starting_time
        delay = 0 if delay is None else delay * 1e-3
        difftime = (starting_time - now()) * 1e-3 + delay
        if difftime > 0:
            await asyncio.sleep(difftime)
        self._start = now()
        self._stop = False
        self._callback = callback

        while not self._stop:
            await asyncio.sleep(0.017 + delay)
            self._callback((now() - self._start) * 1e3, self.stop)


async def interval(
    callback: Callable[[float, TimerEvent], None],
    delay: float | None = None,
    starting_time: float | None = None,
) -> Timer | Interval:
    """
    The :code:`callback` is invoked only every delay milliseconds; if
    :code:`delay` is not specified, this is equivalent to timer.

    Parameters
    ----------
    callback : Callable[[float, TimerEvent], None]
        Callback
    delay : float | None
        Delay value
    starting_time : float | None
        Starting time value

    Returns
    -------
    Timer | Interval
        :code:`Timer` if :code:`delay` is not specified else :code:`Interval`.
    """
    timer = Timer() if delay is None else Interval()
    await timer.restart(callback, delay, starting_time)
    return timer
