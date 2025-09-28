import detroit_live as d3
from detroit_live.zoom.zoom_event import ZoomEvent
import pytest

@pytest.mark.parametrize("typename", ["zoom", "start", "end"])
def test_callback_1(typename):
    div = d3.create("div")
    z = d3.zoom()
    a = [None]
    event = ZoomEvent(typename, None, z, d3.zoom_identity, None)
    def callback(event, d, node):
        a[0] = {"event": event, "d": d, "node": node}
    z.on(typename, callback)
    div.call(z)
    div.call(z.transform, d3.zoom_identity, None, None)
    assert a[0]["d"] is None
    assert a[0]["node"] == div.node()
    assert a[0]["event"].event_type == event.event_type
    assert a[0]["event"].source_event == event.source_event
    assert a[0]["event"].transform == event.transform

def test_callback_2():
    div = d3.create("div")
    z = d3.zoom()
    a = []
    def callback(event, d, node):
        a.append(event.event_type)
    z.on("start zoom end", callback)
    div.call(z)
    div.call(z.transform, d3.zoom_identity, None, None)
    assert a == ["start", "zoom", "end"]
