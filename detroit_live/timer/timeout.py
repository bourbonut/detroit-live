from collections.abc import Callable

from .timer import Timer, TimerEvent


async def timeout(
    callback: Callable[[float, TimerEvent], None],
    delay: float | None = None,
    starting_time: float | None = None,
) -> Timer:
    """
    Automatically stops on its first callback.

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
        Timer with timeout
    """
    timer = Timer()
    delay = 0 if delay is None else delay

    def timeout_callback(
        elapsed: float,
        stop: Callable[[None], None],
    ):
        stop()
        callback(elapsed + delay)

    await timer.restart(timeout_callback, delay, starting_time)
    return timer
