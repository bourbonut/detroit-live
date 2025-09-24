import detroit_live as d3
from detroit_live.events import ContextListener, TrackingTree


class Event:
    pass


def test_context_listener_1():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    def data_accessor(node):
        pass

    context_listener = ContextListener([svg.node()], [], listener, data_accessor)
    assert context_listener.get_listener() == listener
    assert context_listener.get_node() == svg.node()


def test_context_listener_2():
    svg = d3.create("svg")
    ttree = TrackingTree()
    ttree.set_root(svg.node())
    results = []

    def listener(event, d, node):
        results.append([event, d, node])

    def data_accessor(node):
        return "data"

    context_listener = ContextListener([svg.node()], [], listener, data_accessor)
    event = Event()
    list(context_listener(event))
    assert results == [[event, "data", svg.node()]]


def test_context_listener_3():
    svg = d3.create("svg")
    ttree = TrackingTree()
    ttree.set_root(svg.node())

    def listener(event, d, node):
        d3.select(node).attr("width", d["width"]).attr("height", d["height"])

    def data_accessor(node):
        return {"width": 100, "height": 200}

    context_listener = ContextListener([svg.node()], [], listener, data_accessor)
    event = Event()
    jsons = list(context_listener(event))
    assert len(jsons) == 1
    jsons[0]["diff"]["change"].sort(key=lambda value: value[0], reverse=True)
    assert jsons == [
        {
            "elementId": "svg",
            "diff": {"remove": [], "change": [["width", "100"], ["height", "200"]]},
        }
    ]
