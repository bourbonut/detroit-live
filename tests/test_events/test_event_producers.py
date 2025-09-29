import asyncio
import detroit_live as d3
from detroit_live.timer import Timer, Interval
from detroit_live.events.event_producers import TimerParameters
import pytest

def test_event_producers_1():
    event_producers = d3.event_producers()
    def callback(elapsed, timer_event):
        timer_event.set()
    modifier = event_producers.add_timer(callback)
    assert id(modifier._timer) in event_producers._restart

def test_event_producers_2():
    event_producers = d3.event_producers()
    def callback(elapsed, timer_event):
        timer_event.set()
    modifier = event_producers.add_timer(callback)
    modifier.restart(callback)
    # First message for stop()
    source, id_ = event_producers._future_tasks.get()
    assert isinstance(id_, int)
    # Second message for restart()
    source, timer_params = event_producers._future_tasks.get()
    assert isinstance(timer_params, TimerParameters)
    
def test_event_producers_3():
    event_producers = d3.event_producers()
    def callback(elapsed, timer_event):
        timer_event.set()
    modifier = event_producers.add_timer(callback)
    modifier.stop()
    # Only message for stop()
    source, id_ = event_producers._future_tasks.get()
    assert isinstance(id_, int)

@pytest.mark.parametrize(
    "method, expected_type", [
        ["add_timer", Timer],
        ["add_interval", Interval],
    ]
)
def test_event_producers_4(method, expected_type):
    event_producers = d3.event_producers()
    def callback(elapsed, timer_event):
        timer_event.set()
    method_to_call = getattr(event_producers, method)
    modifier = method_to_call(callback)
    assert isinstance(modifier._timer, expected_type)
    assert isinstance(event_producers._restart[id(modifier._timer)].timer , expected_type)


@pytest.mark.asyncio
async def test_event_producers_5():
    event_producers = d3.event_producers()
    event_producers._restart.clear()
    assert len(event_producers._restart) == 0
    def callback(elapsed, timer_event):
        timer_event.set()
    modifier = event_producers.add_timer(callback)
    modifier.restart(callback)
    assert event_producers._future_tasks.empty() is False
    assert len(event_producers._restart) != 0
    assert len(event_producers._pending) == 0
    pending = event_producers.next_tasks()
    assert pending is not None
    assert event_producers._future_tasks.empty() is True
    assert len(event_producers._restart) == 0
    assert len(event_producers._pending) == 1
    id_ = list(event_producers._pending)[0]
    pending = event_producers.next_tasks(id_)
    assert pending is None
    assert len(event_producers._pending) == 0

@pytest.mark.asyncio
async def test_event_producers_6():
    event_producers = d3.event_producers()
    async def task():
        pass
    assert event_producers.queue_task("{}") is  None
    assert event_producers.queue_task(None) is not None
    assert event_producers.queue_task(0) is None
    assert event_producers.queue_task((0, 0)) is None
    event_producers._pending[0] = asyncio.Task(task())
    assert event_producers.queue_task(None) is not None
    assert event_producers.queue_task(0) is not None
    assert event_producers.queue_task((0, 0)) is not None
