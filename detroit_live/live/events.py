from abc import ABC, abstractclassmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

from lxml import etree

T = TypeVar("T")

Self = TypeVar("Self")

EVENT_HEADERS = (
    'let s = new WebSocket("ws://localhost:5000/ws");'
    "let w = window;"
    "let d = document;"
    "function f(o, t, p){ o.elementId = p; o.typename = t; s.send(JSON.stringify(o, null, 0)); }"
    "s.addEventListener('message', (e) => { const r = new FileReader();"
    " r.onload = function(o) { const v = JSON.parse(o.target.result);"
    " const el = d.getElementById(v.elementId);"
    " if (v.diff != undefined) {"
    " v.diff.change.forEach(pair => el[pair[0]] = pair[1]);"
    " v.diff.remove.forEach(pair => el[pair[0]] = undefined); }"
    " else { el.outerHTML = v.outerHTML } };"
    " r.readAsText(e.data); });"
)

NAMESPACE = {
    "document": "d",
    "event": "e",
    "socket": "s",
    "window": "w",
}


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


class JsonFormat(ABC):
    @abstractclassmethod
    def json_format(cls: type[Self]) -> str: ...


class FromJson(ABC):
    @abstractclassmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self: ...


class Event(JsonFormat, FromJson): ...


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
    ctrl_key: bool
    shift_key: bool
    alt_key: bool
    element_id: int
    rect_top: int
    rect_left: int

    @classmethod
    def json_format(cls: type[Self]) -> str:
        return json_format(cls, "event", {
            "element_id": "path",
            "rect_top": "srcElement.getBoundingClientRect().top",
            "rect_left": "srcElement.getBoundingClientRect().left",
        })

    @classmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self:
        return from_json(cls, content)


def parse_target(
    target: str | None = None,
    typename: str | None = None,
    node: str | None = None,
):
    if target is not None:
        return target
    if typename == "open":
        return "socket"
    if node is not None:
        return "document"
    match typename:
        case "open":
            return "socket"
        case "resize":
            return "window"
        case "wheel":
            return "window"
        case _:
            return "document"


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


class EventHandler(Generic[T]):
    def __init__(
        self,
        typename: str,
        listener: Callable[[Event, T | None, Optional[etree.Element]], None],
        target: str | None = None,
        node: str | None = None,
        extra_nodes: list[str] | None = None,
    ):
        self.typename = typename
        self.node = node
        self.extra_nodes = extra_nodes
        self.target = parse_target(target, typename, node)
        self.listener = listener

    def listener_script(self, event_json: str) -> str:
        target = NAMESPACE.get(self.target, self.target)
        typename = repr(self.typename)
        return f"{target}.addEventListener({typename}, (e) => f({event_json}, {typename}));"

    def nodes(self):
        return [self.node] + self.extra_nodes

    def __str__(self) -> str:
        return (
            f"EventHandler({self.typename}, {self.node},"
            f" {self.target}, {self.listener})"
        )

    def __repr__(self) -> str:
        return str(self)

getpath = """
function getDomPath(el) {
  if (!el) return '';
  if (el === document.body) return 'body';
  let parent = el.parentNode;
  if (parent === null || parent === undefined) return '';
  let siblings = Array.from(parent.children).filter(e => e.tagName === el.tagName);
  let idx = siblings.indexOf(el) + 1;
  let tag = el.tagName.toLowerCase();
  let path = getDomPath(parent) + '/' + tag;
  if (siblings.length > 1) path += `[${idx}]`;
  return path;
}
"""

class EventGroup(Generic[T]):
    def __init__(self, event: type[Event]):
        self.event = event
        self.handlers = []

    def __iter__(self) -> Iterator[EventHandler]:
        return iter(self.handlers)

    def __len__(self) -> int:
        return len(self.handlers)

    def append(self, handler: EventHandler):
        self.handlers.append(handler)

    def listener_script(self):
        if self.event_type() == "MouseEvent":
            event_json = self.event_json()
            element_ids = [repr(hash(handler.node)) for handler in self.handlers]
            typenames = [handler.typename for handler in self.handlers]
            groups = {}
            for element_id, typename in zip(element_ids, typenames):
                groups.setdefault(typename, []).append(element_id)
            listeners = [
                (
                    f"window.addEventListener({typename!r}, (e) =>"
                    f" {{ {getpath} const path = getDomPath(e.srcElement); f({event_json}, {typename!r}, path)}});"
                )
                for typename, element_ids in groups.items()
            ]
            return "".join(listeners)
        else:
            event_json = self.event_json()
            return "".join(
                handler.listener_script(event_json) for handler in self.handlers
            )

    def event_type(self) -> str:
        return self.event.__name__

    def event_json(self) -> str:
        event_json = self.event.json_format()
        for old, new in NAMESPACE.items():
            event_json = event_json.replace(old, new)
        return event_json

    def __str__(self) -> str:
        return f"EventGroup({self.handlers})"

    def __repr__(self) -> str:
        return str(self)
