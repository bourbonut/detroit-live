import pytest

from detroit_live.events.types import (
    ChangeEvent,
    MouseEvent,
    WheelEvent,
    WindowSizeEvent,
    parse_event,
    snake_to_camel,
)


def test_json_format_1():
    assert WindowSizeEvent.json_format() == (
        "{type: 'WindowSizeEvent', innerWidth: window.innerWidth, innerHeight: window.innerHeight}"
    )
    assert WindowSizeEvent.from_json(
        {"innerWidth": 100, "innerHeight": 200}
    ) == WindowSizeEvent(100, 200)


def test_json_format_2():
    assert (
        WheelEvent.json_format()
        == "{type: 'WheelEvent', clientX: event.clientX, clientY: event.clientY,"
        " deltaX: event.deltaX, deltaY: event.deltaY, deltaMode: event.deltaMode,"
        " ctrlKey: event.ctrlKey, button: event.button, rectTop: "
        "event.srcElement.getBoundingClientRect().top, rectLeft: "
        "event.srcElement.getBoundingClientRect().left}"
    )
    json = {
        "clientX": 100,
        "clientY": 200,
        "deltaX": 10,
        "deltaY": -20,
        "deltaMode": 0,
        "ctrlKey": True,
        "button": 2,
        "rectTop": 50,
        "rectLeft": 75,
    }

    expected = WheelEvent(
        client_x=100,
        client_y=200,
        delta_x=10,
        delta_y=-20,
        delta_mode=0,
        ctrl_key=True,
        button=2,
        rect_top=50,
        rect_left=75,
    )
    assert WheelEvent.from_json(json) == expected


def test_json_format_3():
    assert MouseEvent.json_format() == (
        "{type: 'MouseEvent', x: event.x, y: event.y, clientX: event.clientX, "
        "clientY: event.clientY, pageX: event.pageX, pageY: event.pageY, button:"
        " event.button, ctrlKey: event.ctrlKey, shiftKey: event.shiftKey, altKey:"
        " event.altKey, elementId: event.elementId, rectTop:"
        " event.srcElement.getBoundingClientRect().top, "
        "rectLeft: event.srcElement.getBoundingClientRect().left}"
    )
    json = {
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
        "elementId": "svg",
        "rectTop": 75,
        "rectLeft": 100,
    }
    expected = MouseEvent(
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
    assert MouseEvent.from_json(json) == expected


def test_json_format_4():
    assert (
        ChangeEvent.json_format() == "{value: e.srcElement.value, type: 'ChangeEvent'}"
    )

    assert ChangeEvent.from_json({"value": "hello"}) == ChangeEvent("hello")


@pytest.mark.parametrize(
    "value, expected",
    [
        ["client_x", "clientX"],
        ["point_from_element", "pointFromElement"],
    ],
)
def test_snake_to_camel(value, expected):
    assert snake_to_camel(value) == expected


@pytest.mark.parametrize(
    "typename, expected",
    [
        [None, MouseEvent],
        ["open", WindowSizeEvent],
        ["resize", WindowSizeEvent],
        ["change", ChangeEvent],
        ["input", ChangeEvent],
        ["wheel", WheelEvent],
        ["mouseover", MouseEvent],
        ["foo", MouseEvent],
    ],
)
def test_parse_event(typename, expected):
    assert parse_event(typename) == expected
