import pytest

import detroit_live as d3
from detroit_live.events.context_listener import ContextListener
from detroit_live.events.event_listeners import (
    EventListener,
    EventListeners,
    EventListenersGroup,
    TrackingTree,
    parse_target,
)
from detroit_live.events.types import MouseEvent


@pytest.mark.parametrize(
    "target, typename, node, expected",
    [
        [None, None, None, "document"],
        ["foo", None, None, "foo"],
        [None, "open", None, "socket"],
        [None, "resize", None, "window"],
        [None, "wheel", None, "window"],
        [None, "mouseover", None, "document"],
        [None, "change", None, "document.querySelector('select')"],
    ],
)
def test_parse_target(target, typename, node, expected, monkeypatch):
    if typename == "change":

        def mock_get_path(self, node):
            return "select"

        monkeypatch.setattr(TrackingTree, "get_path", mock_get_path)
    assert parse_target(target, typename, node) == expected


def test_event_listener():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    def data_accessor(node):
        return "Hello world"

    event_listener = EventListener(
        "mouseover", "drag", ContextListener([svg.node()], [], listener, data_accessor)
    )
    assert event_listener.node == svg.node()
    assert event_listener.target == "document"

    assert event_listener.into_script("{hello: 'world'}") == (
        "document.addEventListener('mouseover', "
        "(e) => f({hello: 'world'}, 'mouseover', p(e.srcElement)));"
    )


def test_event_listeners_group_1():
    group = EventListenersGroup("mouseover")
    assert group.event.__name__ == "MouseEvent"
    assert group.event_type == "MouseEvent"
    assert group.event_json() == group.event.json_format()
    assert group._event_listeners == {}
    assert group._previous_node is None
    assert group._mousedowned_node is None


@pytest.fixture
def group_and_svg():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    def data_accessor(node):
        return "Hello world"

    group = EventListenersGroup("mouseover")

    for typename, name in [
        ("mouseup", "drag"),
        ("mouseover", "drag"),
        ("mousedown", "drag"),
        ("mouseleave", "drag"),
        ("click", ""),
    ]:
        group[(svg.node(), typename, name)] = EventListener(
            typename, name, ContextListener([svg.node()], [], listener, data_accessor)
        )
    return group, svg.node()


def test_event_listeners_group_2(group_and_svg):
    group, svg = group_and_svg
    assert group.get((svg, "mouseover", "drag")) is not None
    assert group.get((svg, "click", "drag")) is None
    assert group.get((svg, "click", "")) is not None


def test_event_listeners_group_3(group_and_svg):
    group, svg = group_and_svg
    assert group.pop((svg, "mouseup", "drag")) is not None
    assert group.get((svg, "mouseup", "drag")) is None
    assert group.pop((svg, "mouseup", "drag"), "foo") == "foo"


def test_event_listeners_group_4(group_and_svg):
    group, svg = group_and_svg
    assert len(group.search()) == 5
    assert len(group.search(name="drag")) == 4
    assert len(group.search(typename="click")) == 1
    assert len(group.search(typename="mouseup")) == 1
    assert len(group.search(typename="change")) == 0


def test_event_listeners_group_5(group_and_svg):
    group, _ = group_and_svg

    # Program to split long string
    #
    # ```python
    # length = len(string)
    # q, r = divmod(length, 80) # 88 - 8 spaces
    # for i in range(q):
    #     print(f"\"{string[i * 80: (i + 1) * 80]}\"")
    # print(f"\"{string[q * 80: q * 80 + r]}\"")
    # ```
    assert group.into_script() == (
        "function _ev(e){return {type: 'MouseEvent', x: event.x, y: event.y, clientX: eve"
        "nt.clientX, clientY: event.clientY, pageX: event.pageX, pageY: event.pageY, butt"
        "on: event.button, ctrlKey: event.ctrlKey, shiftKey: event.shiftKey, altKey: even"
        "t.altKey, elementId: event.elementId, rectTop: event.srcElement.getBoundingClien"
        "tRect().top, rectLeft: event.srcElement.getBoundingClientRect().left}}window.add"
        "EventListener('mouseup', (e) =>  f(_ev(e), 'mouseup', p(e.srcElement)));window.a"
        "ddEventListener('mouseover', (e) =>  f(_ev(e), 'mouseover', p(e.srcElement)));wi"
        "ndow.addEventListener('mousedown', (e) =>  f(_ev(e), 'mousedown', p(e.srcElement"
        ")));window.addEventListener('mouseleave', (e) =>  f(_ev(e), 'mouseleave', p(e.sr"
        "cElement)));window.addEventListener('click', (e) =>  f(_ev(e), 'click', p(e.srcE"
        "lement)));"
    )


def test_event_listeners_group_6(group_and_svg):
    group, svg = group_and_svg
    event = MouseEvent(
        x=150,
        y=250,
        client_x=100,
        client_y=200,
        page_x=300,
        page_y=400,
        button=1,
        ctrl_key=True,
        shift_key=False,
        alt_key=True,
        element_id="svg",
        rect_top=75,
        rect_left=100,
    )
    ttree = TrackingTree()
    ttree.set_root(svg)
    assert ttree.get_node("svg") == svg
    assert len(group.filter_by(event, "mouseover")) == 2
    assert group._previous_node == svg
    assert len(group.filter_by(event, "mousedown")) == 1
    assert group._mousedowned_node == svg
    assert len(group.filter_by(event, "mouseup")) == 1
    assert group._mousedowned_node is None
    assert len(group.filter_by(event, "click")) == 1
    assert len(group.filter_by(event, "foo")) == 0


def test_event_listeners_group_7(group_and_svg):
    group, svg = group_and_svg
    ttree = TrackingTree()
    ttree.set_root(svg)
    assert ttree.get_node("svg") == svg
    event = {"elementId": "svg", "typename": "mouseover"}
    assert len(list(group.propagate(event))) == 2
    event = {"elementId": "svg", "typename": "click"}
    assert len(list(group.propagate(event))) == 1
    event = {"elementId": "svg", "typename": "foo"}
    assert len(list(group.propagate(event))) == 0
    event = {"elementId": "foo", "typename": "mouseover"}
    assert len(list(group.propagate(event))) == 0


@pytest.fixture
def event_listeners_and_svg():
    svg = d3.create("svg")

    def listener(event, d, node):
        pass

    def data_accessor(node):
        return "Hello world"

    event_listeners = EventListeners()

    for typename, name in [
        ("mouseup", "drag"),
        ("mouseover", "drag"),
        ("mousedown", "drag"),
        ("mouseleave", "drag"),
        ("click", ""),
    ]:
        event_listeners.add_event_listener(
            EventListener(
                typename,
                name,
                ContextListener([svg.node()], [], listener, data_accessor),
            )
        )
    return event_listeners, svg.node()


def test_event_listeners_1(event_listeners_and_svg):
    event_listeners, svg = event_listeners_and_svg
    assert "MouseEvent" in event_listeners
    assert event_listeners["MouseEvent"] is not None
    event_listeners.remove_event_listener("mouseover", "drag", svg)
    assert event_listeners["MouseEvent"].get((svg, "mouseover", "drag")) is None
    assert event_listeners.keys() == {"MouseEvent"}
    assert event_listeners.values() == [event_listeners["MouseEvent"]]


def test_event_listeners_2(event_listeners_and_svg):
    event_listeners, _ = event_listeners_and_svg
    assert event_listeners.into_script() == (
        """const socket = new WebSocket("ws://localhost:5000/ws");function f(o, t, u) {"""
        """o.elementId = u;o.typename = t;point = pointer(o, document.querySelector("sv"""
        """g"));o.pageX = point[0];o.pageY = point[1];socket.send(JSON.stringify(o, nul"""
        """l, 0));}function sourceEvent(event) {let sourceEvent;while (sourceEvent = ev"""
        """ent.sourceEvent) event = sourceEvent;return event;}function pointer(event, n"""
        """ode) {event = sourceEvent(event);if (node === undefined) node = event.curren"""
        """tTarget;if (node) {var svg = node.ownerSVGElement || node;if (svg.createSVGP"""
        """oint) {var point = svg.createSVGPoint();point.x = event.clientX, point.y = e"""
        """vent.clientY;point = point.matrixTransform(node.getScreenCTM().inverse());re"""
        """turn [point.x, point.y];}if (node.getBoundingClientRect) {var rect = node.ge"""
        """tBoundingClientRect();return [event.clientX - rect.left - node.clientLeft, e"""
        """vent.clientY - rect.top - node.clientTop];}}return [event.pageX, event.pageY"""
        """];}function p(e) {if (!e) return;if (e === document.body) return 'body';let """
        """t = e.parentNode;if (null == t) return '';let r = Array.from(t.children).fil"""
        """ter((t => t.tagName === e.tagName)),n = r.indexOf(e) + 1,a = e.tagName.toLow"""
        """erCase(),o = p(t) + '/' + a;return r.length > 1 && (o += `[${n}]`), o}functi"""
        """on q(u) {var n, s = u.split(" "), t = s[s.length - 2], els = document.queryS"""
        """electorAll(u);if ((n = els.length) === 1 || t === undefined) {return els[0];"""
        """} else {for (var i = 0, el; i < n; i++){el = els[i];if (el.parentNode.tagNam"""
        """e === t) {return el;}}}}socket.addEventListener('message', (e) => {const fr """
        """= new FileReader();fr.onload = function(o) {const t = JSON.parse(o.target.re"""
        """sult);for (var i1 = 0, r, n = t.length; i1 < n; ++i1) {r = t[i1];const el = """
        """q(r.elementId);if (el == undefined) {continue;}if (r.diff != undefined) {var"""
        """ c = r.diff.change;for (var i2 = 0, k, v, m = c.length; i2 < m; ++i2) {[k, v"""
        """] = c[i2];k === "innerHTML" ? el[k] = v: el.setAttribute(k, v)}c = r.diff.re"""
        """move;for (var i2 = 0, k, v, m = c.length; i2 < m; ++i2) {[k, v] = c[i2];k =="""
        """= "innerHTML" ? el[k] = undefined : el.removeAttribute(k);}} else {el.outerH"""
        """TML = r.outerHTML;}}};fr.readAsText(e.data);});function _ev(e){return {type:"""
        """ 'MouseEvent', x: event.x, y: event.y, clientX: event.clientX, clientY: even"""
        """t.clientY, pageX: event.pageX, pageY: event.pageY, button: event.button, ctr"""
        """lKey: event.ctrlKey, shiftKey: event.shiftKey, altKey: event.altKey, element"""
        """Id: event.elementId, rectTop: event.srcElement.getBoundingClientRect().top, """
        """rectLeft: event.srcElement.getBoundingClientRect().left}}window.addEventList"""
        """ener('mouseup', (e) =>  f(_ev(e), 'mouseup', p(e.srcElement)));window.addEve"""
        """ntListener('mouseover', (e) =>  f(_ev(e), 'mouseover', p(e.srcElement)));win"""
        """dow.addEventListener('mousedown', (e) =>  f(_ev(e), 'mousedown', p(e.srcElem"""
        """ent)));window.addEventListener('mouseleave', (e) =>  f(_ev(e), 'mouseleave',"""
        """ p(e.srcElement)));window.addEventListener('click', (e) =>  f(_ev(e), 'click"""
        """', p(e.srcElement)));"""
    )


def test_event_listeners_3(event_listeners_and_svg):
    event_listeners, svg = event_listeners_and_svg
    ttree = TrackingTree()
    ttree.set_root(svg)
    assert ttree.get_node("svg") == svg
    event = {"elementId": "svg", "typename": "mouseover", "type": "MouseEvent"}
    assert len(list(event_listeners(event))) == 2
    event = {"elementId": "svg", "typename": "click", "type": "MouseEvent"}
    assert len(list(event_listeners(event))) == 1
    event = {"elementId": "svg", "typename": "foo", "type": "MouseEvent"}
    assert len(list(event_listeners(event))) == 0
    event = {"elementId": "foo", "typename": "mouseover", "type": "MouseEvent"}
    assert len(list(event_listeners(event))) == 0
    event = {"elementId": "svg", "typename": "mouseover", "type": "foo"}
    assert len(list(event_listeners(event))) == 0
    event = {"elementId": "svg", "typename": "mouseover"}
    assert len(list(event_listeners(event))) == 0
