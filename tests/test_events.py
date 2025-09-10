from detroit_live.events import MouseEvent, WheelEvent, WindowSizeEvent


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
        == "{type: 'WheelEvent', deltaX: event.deltaX, deltaY: event.deltaY}"
    )
    assert WheelEvent.from_json({"deltaX": 10, "deltaY": 20}) == WheelEvent(10, 20)


def test_json_format_3():
    assert MouseEvent.json_format() == (
        "{type: 'MouseEvent', clientX: event.clientX, clientY: event.clientY,"
        " ctrlKey: event.ctrlKey, shiftKey: event.shiftKey, altKey: event.altKey,"
        " elementId: event.srcElement.id}"
    )
    assert MouseEvent.from_json(
        {
            "clientX": 10,
            "clientY": 20,
            "ctrlKey": False,
            "shiftKey": True,
            "altKey": False,
            "elementId": 777,
        }
    ) == MouseEvent(10, 20, False, True, False, 777)
