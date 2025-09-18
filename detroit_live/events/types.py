from dataclasses import dataclass
from typing import Any
from .base import Event, Self

def snake_to_camel(string: str) -> str:
    strings = string.split("_")
    return "".join(strings[:1] + [word.title() for word in strings[1:]])


def json_format(cls: type[Self], prefix: str, mapping: dict[str, str]) -> str:
    attrs = list(cls.__annotations__)
    targets = (snake_to_camel(mapping.get(value, value)) for value in attrs)
    attrs = map(snake_to_camel, attrs)
    parts = [f"type: {repr(cls.__name__)}"]
    parts += [f"{attr}: {prefix}.{target}" for attr, target in zip(attrs, targets)]
    return f"{{{', '.join(parts)}}}"


def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
    return cls(*(content.get(snake_to_camel(attr)) for attr in cls.__annotations__))


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
    delta_x: int
    delta_y: int
    delta_mode: int
    ctrl_key: bool

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return json_format(cls, "event", {})

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
    element_id: int
    rect_top: int
    rect_left: int

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return json_format(cls, "event", {
            "element_id": "srcElement.id",
            "rect_top": "srcElement.getBoundingClientRect().top",
            "rect_left": "srcElement.getBoundingClientRect().left",
        })

    @classmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
        return from_json(cls, content)


def parse_event(typename: str | None = None) -> type[Event]:
    match typename:
        case "open":
            return WindowSizeEvent
        case "resize":
            return WindowSizeEvent
        case "wheel":
            return WheelEvent
        case _:
            return MouseEvent
