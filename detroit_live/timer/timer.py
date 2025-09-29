import asyncio
import time
from collections.abc import Callable


def now() -> float:
    """
    Returns the current time as defined by `time.perf_counter()`.

    The current time is updated at the start of a frame; it is thus consistent
    during the frame, and any timers scheduled during the same frame will be
    synchronized. If this method is called outside of a frame, such as in
    response to a user event, the current time is calculated and then fixed
    until the next frame, again ensuring consistent timing during event
    handling.

    Returns
    -------
    float
        Current time value
    """
    return time.perf_counter()


class TimerEvent:
    def __init__(self):
        self.__is_set = False

    def is_set(self) -> bool:
        return self.__is_set

    def set(self):
        self.__is_set = True

    def clear(self):
        self.__is_set = False


class Timer:
    def __init__(self):
        self._time_event = TimerEvent()
        self._callback = None
        self._start = None

    async def restart(
        self,
        callback: Callable[[float, TimerEvent], None],
        delay: float | None = None,
        starting_time: float | None = None,
    ) -> int:
        try:
            starting_time = now() if starting_time is None else starting_time
            delay = 0 if delay is None else delay * 1e-3
            difftime = (starting_time - now()) * 1e-3 + delay
            frame_freq = 504 * 1e-6
            if difftime > 0:
                await asyncio.sleep(frame_freq)

            self._start = now()
            self._time_event = TimerEvent()
            self._callback = callback

            while not self._time_event.is_set():
                await asyncio.sleep(frame_freq)
                self._callback((now() - self._start) * 1e3, self._time_event)
            return id(self)
        except asyncio.CancelledError:
            return id(self)

    def stop(self):
        self._time_event.set()

    def __str__(self):
        return f"Timer({self._time_event}, {self._callback}, {self._start})"


async def timer(
    callback: Callable[[float, TimerEvent], None],
    delay: float | None = None,
    starting_time: float | None = None,
) -> Timer:
    """
    Schedules a new timer, invoking the specified :code:`callback` repeatedly
    until the timer is stopped. An optional numeric delay in milliseconds may
    be specified to invoke the given :code:`callback` after a :code:`delay`; if
    :code:`delay` is not specified, it defaults to zero. The :code:`delay` is
    relative to the specified :code:`starting_time` in milliseconds; if
    :code:`starting_time` is not specified, it defaults to now.

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
    Timer
        Timer
    """
    timer = Timer()
    await timer.restart(callback, delay, starting_time)
    return timer
