from collections.abc import Callable
import time

FRAME_TIME = 0.017 # 504 * 1e-6

def now() -> float:
    return time.time()

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
):
    timer = Timer()
    timer.restart(callback, delay, starting_time)
    return timer
