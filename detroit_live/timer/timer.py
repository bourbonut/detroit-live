from collections.abc import Callable
import time

FRAME_TIME = 0.017 # 504 * 1e-6

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

class Timer:

    def __init__(self):
        self._start = now()
        self._stop = False
        self._callback = None

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
            time.sleep(FRAME_TIME)
            self._callback((now() - self._start) * 1e3, self.stop)

    def stop(self):
        self._stop = True

def timer(
    callback: Callable[[float, Callable[[None], None]], None],
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
    callback : Callable[[float, Callable[[None], None]], None]
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
    timer.restart(callback, delay, starting_time)
    return timer
