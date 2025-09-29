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
    """
    Timer status enum
    """

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
    """
    Data class which holds all parameters to make a :code:`Timer`

    Attributes
    ----------
    timer : Timer
        Initialized empty timer instance
    callback : Callable[[float, TimerEvent], None]
        Timer callback
    updated_nodes : list[etree.Element] | None
        Nodes to update when the timer callback is called
    html_nodes : list[etree.Element] | None
        Same as :code:`updated_nodes` but update the :code:`innerHTML` as well
    delay : float | None
        Delay value
    starting_time : float | None
        Starting time value
    """

    timer: Timer
    callback: Callable[[float, TimerEvent], None]
    updated_nodes: list[etree.Element] | None
    html_nodes: list[etree.Element] | None
    delay: float | None
    starting_time: float | None


class TimerModifier:
    """
    Class which holds a :code:`Timer` and supplies :code:`restart` and
    :code:`stop` methods applied on the timer object.
    Also future tasks and stopped tasks information are shared to
    :code:`EventProducers` when calling these methods.

    Parameters
    ----------
    updated_nodes : list[etree.Element] | None
        Nodes to update when the timer callback is called
    html_nodes : list[etree.Element] | None
        Same as :code:`updated_nodes` but update the :code:`innerHTML` as well
    future_tasks : Queue[tuple[TimerStatus, TimerParameters | int]] | None
        Queue to share future tasks and stopped tasks to :code:`EventProducers`
    """

    def __init__(
        self,
        timer: Timer,
        updated_nodes: list[etree.Element] | None,
        html_nodes: list[etree.Element] | None,
        future_tasks: Queue[tuple[TimerStatus, TimerParameters | int]] | None,
    ):
        self._timer = timer
        self._updated_nodes = updated_nodes
        self._html_nodes = html_nodes
        self._future_tasks = future_tasks

    def restart(
        self,
        callback: Callable[[float, TimerEvent], None],
        delay: float | None = None,
        starting_time: float | None = None,
    ):
        """
        Restarts the timer.

        Parameters
        ----------
        callback : Callable[[float, TimerEvent], None]
            Timer callback
        delay : float | None
            Delay value
        starting_time : float | None
            Starting time value
        """
        self.stop()
        self._timer = Timer()
        self._future_tasks.put(
            (
                TimerStatus.RESTART,
                TimerParameters(
                    self._timer,
                    callback,
                    self._updated_nodes,
                    self._html_nodes,
                    delay,
                    starting_time,
                ),
            )
        )

    def stop(self):
        """
        Stops the timer.
        """
        self._timer.stop()
        self._future_tasks.put((TimerStatus.STOP, id(self._timer)))


class SharedState:
    """
    Shared state for global context when instanciating :code:`EventProducers`.

    Attributes
    ----------
    queue : asyncio.Queue
        Updated node attributes to send to the websocket
    restart : dict[int, TimerParameters]
        Tasks to restart
    pending : dict[int, asyncio.Task]
        Mapping between timer ids and timer tasks
    future_tasks : Queue[tuple[TimerStatus, TimerParameters | int]]
        Restart and stop events from :code:`TimerModifier`
    """

    def __init__(self):
        self.queue = asyncio.Queue()
        self.restart = {}
        self.pending = {}
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
        """
        Decorator function; for any call of :code:`callback`, gathers node
        changes and puts them into an asynchronous queue.

        Parameters
        ----------
        callback : Callable[[float, TimerEvent], None]
            Timer callback
        updated_nodes : list[etree.Element] | None
            Nodes to update when the timer callback is called
        html_nodes : list[etree.Element] | None
            Same as :code:`updated_nodes` but update the :code:`innerHTML` as well

        Returns
        -------
        Callable[[float, TimerEvent], None]
            Decorated callback
        """
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
                (node, node_attribs(node, node in html_nodes)) for node in updated_nodes
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
        """
        Adds a timer which will calls :code:`callback` until its timer event is
        set.

        Parameters
        ----------
        callback : Callable[[float, TimerEvent], None]
            Timer callback
        updated_nodes : list[etree.Element] | None
            Nodes to update when the timer callback is called
        html_nodes : list[etree.Element] | None
            Same as :code:`updated_nodes` but update the :code:`innerHTML` as well
        delay : float | None
            Delay value
        starting_time : float | None
            Starting time value

        Returns
        -------
        TimerModifier
            Timer modifier
        """
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
        return TimerModifier(timer, updated_nodes, html_nodes, self._future_tasks)

    def add_interval(
        self,
        callback: Callable[[float, TimerEvent], None],
        updated_nodes: list[etree.Element] | None = None,
        html_nodes: list[etree.Element] | None = None,
        delay: float | None = None,
        starting_time: float | None = None,
    ) -> TimerModifier:
        """
        Adds a interval timer which will calls :code:`callback` until its timer
        event is set.

        Parameters
        ----------
        callback : Callable[[float, TimerEvent], None]
            Timer callback
        updated_nodes : list[etree.Element] | None
            Nodes to update when the timer callback is called
        html_nodes : list[etree.Element] | None
            Same as :code:`updated_nodes` but update the :code:`innerHTML` as well
        delay : float | None
            Delay value
        starting_time : float | None
            Starting time value

        Returns
        -------
        TimerModifier
            Timer modifier
        """
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
        return TimerModifier(interval, updated_nodes, html_nodes, self._future_tasks)

    def remove_timer(self, timer_modifier: TimerModifier):
        """
        Removes a non started timer.

        Parameters
        ----------
        timer_modifier : TimerModifier
            Timer Modifier
        """
        self._restart.pop(id(timer_modifier._timer))

    def next_tasks(self, timer_id: int | None = None) -> set[asyncio.Task] | None:
        """
        Returns the next tasks to await if some new tasks have to be (re)started.
        Removes the :code:`timer_id` of pending tasks if the specified value is
        valid.

        Parameters
        ----------
        result : int | None
            Last result

        Returns
        -------
        set[asyncio.Task] | None
            Next tasks to await
        """
        while not self._future_tasks.empty():
            match self._future_tasks.get():
                case (TimerStatus.RESTART, timer_params):
                    self._restart[id(timer_params.timer)] = timer_params
                case (TimerStatus.STOP, timer_id):
                    if timer_id in self._restart:
                        self._restart.pop(timer_id)
                    if timer_id in self._pending:
                        self._pending.pop(timer_id).cancel()
        if isinstance(timer_id, int) and timer_id in self._pending:
            self._pending.pop(timer_id)
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
        """
        Returns a queue task (:code:`asyncio.create_task(queue.get())`)
        depending the last result.

        Parameters
        ----------
        result : Any | None
            Last result

        Returns
        -------
        asyncio.Task | None
            Asynchrous :code:`queue.get` task
        """
        if result is None or (isinstance(result, (int, tuple)) and self._pending):
            return asyncio.create_task(self._queue.get())


def event_producers() -> EventProducers:
    """
    Returns a new instance of event producers.

    Returns
    -------
    EventProducers
        Event Producers
    """
    return EventProducers()
