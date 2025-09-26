import asyncio
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from typing import Any

from lxml import etree

from ..timer import Interval, Timer, TimerEvent
from .event_source import EventSource
from .tracking_tree import TrackingTree
from .utils import (
    diffdict,
    node_attribs,
    xpath_to_query_selector,
)

EMPTY_DIFF = {"remove": [], "change": []}


class TimerStatus(Enum):
    STOP = auto()
    RESTART = auto()


@dataclass(
    init=True,
    repr=True,
    eq=False,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=False,
    kw_only=False,
    slots=True,
)
class TimerParameters:
    timer: Timer
    callback: Callable[[float, TimerEvent], None]
    updated_nodes: list[etree.Element]
    html_nodes: list[etree.Element]
    delay: float | None
    starting_time: float | None


class TimerModifier:
    def __init__(self, timer, updated_nodes, future_tasks):
        self._timer = timer
        self._updated_nodes = updated_nodes
        self._future_tasks = future_tasks

    def restart(
        self,
        callback: Callable[[float, TimerEvent], None],
        delay: float | None = None,
        starting_time: float | None = None,
    ):
        self.stop()
        self._timer = Timer()
        self._future_tasks.put(
            (
                TimerStatus.RESTART,
                TimerParameters(
                    self._timer, callback, self._updated_nodes, delay, starting_time
                ),
            )
        )

    def stop(self):
        self._timer.stop()
        self._future_tasks.put((TimerStatus.STOP, id(self._timer)))


class SharedState:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.restart = {}
        self.pending = set()
        self.future_tasks = Queue()


class EventProducers:

    _shared_state = SharedState()

    def __init__(self):
        self._queue = self._shared_state.queue
        self._restart = self._shared_state.restart
        self._pending = self._shared_state.pending
        self._future_tasks = self._shared_state.future_tasks

    def _event_builder(
        self,
        callback: Callable[[float, TimerEvent], None],
        updated_nodes: list[etree.Element] | None,
        html_nodes: list[etree.Element] | None,
    ) -> Callable[[float, TimerEvent], None]:
        updated_nodes = [] if updated_nodes is None else updated_nodes
        html_nodes = set() if html_nodes is None else set(html_nodes)
        ttree = TrackingTree()

        def diffs(states: list[dict]) -> Iterator[dict]:
            for node, old_attrib in states:
                element_id = xpath_to_query_selector(ttree.get_path(node))
                new_attrib = node_attribs(node, node in html_nodes)
                diff = diffdict(old_attrib, new_attrib)
                if diff != EMPTY_DIFF:
                    yield {"elementId": element_id, "diff": diff}

        def wrapper(elapsed: float, time_event: TimerEvent):
            states = [
                (node, node_attribs(node, node in html_nodes))
                for node in updated_nodes
            ]
            callback(elapsed, time_event)
            self._queue.put_nowait((EventSource.PRODUCER, list(diffs(states))))

        return wrapper

    def add_timer(
        self,
        callback: Callable[[float, TimerEvent], None],
        updated_nodes: list[etree.Element] | None = None,
        html_nodes: list[etree.Element] | None = None,
        delay: float | None = None,
        starting_time: float | None = None,
    ) -> TimerModifier:
        timer = Timer()
        timer_id = id(timer)
        self._restart[timer_id] = TimerParameters(
            timer,
            callback,
            updated_nodes,
            html_nodes,
            delay,
            starting_time,
        )
        return TimerModifier(timer, updated_nodes, self._future_tasks)

    def add_interval(
        self,
        callback: Callable[[float, TimerEvent], None],
        updated_nodes: list[etree.Element] | None = None,
        html_nodes: list[etree.Element] | None = None,
        delay: float | None = None,
        starting_time: float | None = None,
    ) -> TimerModifier:
        interval = Interval()
        timer_id = id(interval)
        self._restart[timer_id] = TimerParameters(
            interval,
            callback,
            updated_nodes,
            html_nodes,
            delay,
            starting_time,
        )
        return TimerModifier(interval, updated_nodes, self._future_tasks)

    def remove_timer(self, timer_modifier: TimerModifier):
        self._restart.pop(id(timer_modifier._timer))

    def next_tasks(self, result: Any | None = None) -> set[asyncio.Task] | None:
        while not self._future_tasks.empty():
            match self._future_tasks.get():
                case (TimerStatus.RESTART, timer_params):
                    self._restart[id(timer_params.timer)] = timer_params
                case (TimerStatus.STOP, timer_id):
                    if timer_id in self._pending:
                        self._pending.pop(timer_id).cancel()
        if isinstance(result, int) and result in self._pending:
            self._pending.pop(result)
        if self._restart:
            self._pending = {
                id(timer_params.timer): asyncio.create_task(
                    timer_params.timer.restart(
                        self._event_builder(
                            timer_params.callback,
                            timer_params.updated_nodes,
                            timer_params.html_nodes,
                        ),
                        timer_params.delay,
                        timer_params.starting_time,
                    )
                )
                for timer_params in self._restart.values()
            }
            self._restart.clear()
            return set(self._pending.values())

    def queue_task(self, result: Any | None = None) -> asyncio.Task | None:
        if result is None or (isinstance(result, (int, tuple)) and self._pending):
            return asyncio.create_task(self._queue.get())

def event_producers() -> EventProducers:
    return EventProducers()
