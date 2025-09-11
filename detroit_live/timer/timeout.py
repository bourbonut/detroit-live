from collections.abc import Callable
from .timer import Timer

def timeout(
    callback: Callable[[float], None],
    delay: float | None = None,
    starting_time: float | None = None,
):
    timer = Timer()
    delay = 0 if delay is None else delay

    def timeout_callback(
        elapsed: float,
        stop: Callable[[None], None],
    ):
        stop()
        callback(elapsed + delay)

    timer.restart(timeout_callback)
    return timer
