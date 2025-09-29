import detroit_live as d3
from detroit_live.events.tracking_tree import TrackingTree

def test_zoom_event_1():
    div = d3.create("div").datum("hello")
    ttree = TrackingTree()
    ttree.set_root(div.node())
    z = d3.zoom()
    event = {
        "x": 150,
        "y": 250,
        "clientX": 100,
        "clientY": 200,
        "pageX": 300,
        "pageY": 400,
        "button": 1,
        "ctrlKey": True,
        "shiftKey": False,
        "altKey": True,
        "elementId": "div",
        "rectTop": 75,
        "rectLeft": 100,
        "typename": "mousedown",
        "type": "MouseEvent",
    }
    a = [None]
    b = [None]

    def callback(*args):
        b[0] = list(args)

    def filter_func(*args):
        a[0] = list(args)

    div.call(z.on("zoom", callback).set_filter(filter_func))
    list(div.event_listeners(event))
    assert a[0][0].element_id == "div"
    assert a[0][1] == "hello"
    assert b[0] is None

    def filter_func(*args):
        return True
    z.set_filter(filter_func)
    list(div.event_listeners(event))
    event["typename"] = "mousemove"
    list(div.event_listeners(event))
    assert b[0] is not None

def test_zoom_event_2():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    extent = z.get_extent()
    event = {
        "x": 150,
        "y": 250,
        "clientX": 100,
        "clientY": 200,
        "pageX": 300,
        "pageY": 400,
        "button": 1,
        "ctrlKey": True,
        "shiftKey": False,
        "altKey": True,
        "elementId": "div",
        "rectTop": 75,
        "rectLeft": 100,
        "typename": "dblclick",
        "type": "MouseEvent",
    }
    a = [None]
    def extent_func(*args):
        a[0] = list(args)
        return extent(*args)
    def filter_func(*args):
        return True
    z.set_filter(filter_func).set_extent(extent_func)
    div.call(z)
    div.call(z.transform, d3.zoom_identity, None, None)
    list(div.event_listeners(event))
    assert a[0][0] == div.node()
