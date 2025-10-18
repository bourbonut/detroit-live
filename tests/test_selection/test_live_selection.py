import detroit_live as d3


def test_live_selection_1():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    svg.on("foo1", listener)
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo1")
    assert len(event_listeners) == 1
    event_listener = event_listeners[0]
    assert event_listener.active is True
    assert len(event_listener.listener._updated_nodes) == 1
    assert len(event_listener.listener._html_nodes) == 0


def test_live_selection_2():
    svg = d3.create("svg")
    g = svg.select_all().data([None] * 10).enter().append("g")

    def listener(event, d, node):
        pass

    svg.on("foo2", listener, extra_nodes=g.nodes())
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo2")
    assert len(event_listeners) == 1
    event_listener = event_listeners[0]
    assert event_listener.active is True
    assert len(event_listener.listener._updated_nodes) == 1 + 10
    assert len(event_listener.listener._html_nodes) == 0


def test_live_selection_3():
    svg = d3.create("svg")
    g = svg.select_all().data([None] * 10).enter().append("g")

    def listener(event, d, node):
        pass

    svg.on("foo3", listener, extra_nodes=g.nodes(), html_nodes=svg.nodes())
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo3")
    assert len(event_listeners) == 1
    event_listener = event_listeners[0]
    assert event_listener.active is True
    assert len(event_listener.listener._updated_nodes) == 1 + 10
    assert len(event_listener.listener._html_nodes) == 1


def test_live_selection_4():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    svg.on("foo4", listener)
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo4")
    assert len(event_listeners) == 1
    svg.on("foo4")
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo4")
    assert len(event_listeners) == 0


def test_live_selection_5():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    svg.on("foo5", listener, active=False)
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo5")
    assert len(event_listeners) == 1
    event_listener = event_listeners[0]
    assert event_listener.active is False


def test_live_selection_6():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    svg.on("foo6", listener, target="fake")
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo6")
    assert len(event_listeners) == 1
    event_listener = event_listeners[0]
    assert event_listener.target == "fake"


def test_live_selection_7():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    svg.on("foo7", listener, active=False)
    event_listeners = svg.event_listeners["MouseEvent"].search(typename="foo7")
    assert len(event_listeners) == 1
    event_listener = event_listeners[0]
    assert event_listener.active is False
    svg.set_event("foo7", False)
    assert event_listener.active is False
    svg.set_event("foo7", True)
    assert event_listener.active is True
    svg.set_event("foo7", False)
    assert event_listener.active is False
