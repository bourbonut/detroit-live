from dataclasses import dataclass
from typing import Any

from .base import Event, Self


def snake_to_camel(string: str) -> str:
    """
    Converts a string from snake case to camel case.

    Parameters
    ----------
    string : str
        String to convert

    Returns
    -------
    str
       Converted string
    """
    strings = string.split("_")
    return "".join(strings[:1] + [word.title() for word in strings[1:]])


def json_format(cls: type[Self], prefix: str, mapping: dict[str, str]) -> str:
    """
    Convenient function to convert a class to a dictionary.

    Parameters
    ----------
    cls : type[Self]
        Event class
    prefix : str
        Name of the function's input of Javascript (e.g. :code:`"event"`)
    mapping : dict[str, str]
        Helps to default values

    Returns
    -------
    str
        JSON string
    """
    attrs = list(cls.__annotations__)
    targets = (snake_to_camel(mapping.get(value, value)) for value in attrs)
    attrs = map(snake_to_camel, attrs)
    parts = [f"type: {repr(cls.__name__)}"]
    parts += [f"{attr}: {prefix}.{target}" for attr, target in zip(attrs, targets)]
    return f"{{{', '.join(parts)}}}"


def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
    """
    Convenient function for passing values from a dictionary object to the
    specified class.

    Parameters
    ----------
    cls : type[Self]
        Event class
    content : dict[str, Any]
        JSON dictionary object

    Returns
    -------
    Self
        Event
    """
    return cls(*(content.get(snake_to_camel(attr)) for attr in cls.__annotations__))


@dataclass
class ChangeEvent(Event):
    value: str

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return "{value: e.srcElement.value, type: 'ChangeEvent'}"

    @classmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
        return from_json(cls, content)


@dataclass
class WindowSizeEvent(Event):
    inner_width: int
    inner_height: int

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return json_format(cls, "window", {})

    @classmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
        return from_json(cls, content)


@dataclass
class WheelEvent(Event):
    client_x: int
    client_y: int
    delta_x: int
    delta_y: int
    delta_mode: int
    ctrl_key: bool
    button: int
    rect_top: int
    rect_left: int

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return json_format(
            cls,
            "event",
            {
                "rect_top": "srcElement.getBoundingClientRect().top",
                "rect_left": "srcElement.getBoundingClientRect().left",
            },
        )

    @classmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
        return from_json(cls, content)


@dataclass
class MouseEvent(Event):
    x: int
    y: int
    client_x: int
    client_y: int
    page_x: int
    page_y: int
    button: int
    ctrl_key: bool
    shift_key: bool
    alt_key: bool
    element_id: str
    rect_top: int
    rect_left: int

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return json_format(
            cls,
            "event",
            {
                "rect_top": "srcElement.getBoundingClientRect().top",
                "rect_left": "srcElement.getBoundingClientRect().left",
            },
        )

    @classmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
        return from_json(cls, content)


def parse_event(typename: str | None = None) -> type[Event]:
    """
    Returns the corresponding event class given the specified typename.

    Parameters
    ----------
    typename : str | None
        Typename

    Returns
    -------
    type[Event]
        Event class
    """
    match typename:
        case "open" | "resize":
            return WindowSizeEvent
        case "change" | "input":
            return ChangeEvent
        case "wheel":
            return WheelEvent
        case _:
            return MouseEvent
