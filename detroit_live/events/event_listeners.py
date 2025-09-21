from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from lxml import etree
from .tracking_tree import TrackingTree
from .base import Event
from .context_listener import ContextListener
from .types import parse_event
from .headers import headers
from .utils import search

T = TypeVar("T")

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


@dataclass
class EventListener:
    typename: str
    name: str
    listener: ContextListener
    active: bool = True
    target: str | None = None

    def __post_init__(self):
        self.node = self.listener.get_node()
        self.target = parse_target(
            self.target,
            self.typename,
            self.node,
        )

    def partial_cmp(
        self,
        typename: str,
        name: str,
        node: Optional[etree.Element] = None,
    ) -> bool:
        if node is None:
            return (
                self.typename == typename and
                self.name == name
            )
        else:
            return (
                self.typename == typename and
                self.name == name and
                self.node == node
            )

    def into_script(self, event_json: str) -> str:
        typename = repr(self.typename)
        return (
            f"{self.target}.addEventListener({typename}, "
            f"(e) => f({event_json}, {typename}, p(e.srcElement)));"
        )


class EventListenersGroup:
    def __init__(self, typename: str):
        self.event: type[Event] = parse_event(typename)
        self.event_type: str = self.event.__name__
        self._event_listeners: dict[etree.Element, dict[str, dict[str, EventListener]]] = {}
        self._previous_node = None
        self._mousedowned_node = None

    def __contains__(self, key: tuple[etree.Element, str, str]) -> bool:
        return key in self._event_listeners

    def __setitem__(self, key: tuple[etree.Element, str, str], event_listener: EventListener):
        node, typename, name = key
        (self._event_listeners.setdefault(typename, {}).setdefault(node, {})[name]) = event_listener

    def get(self, key: tuple[etree.Element, str, str]) -> EventListener | None:
        node, typename, name = key
        if by_nodes := self._event_listeners.get(typename):
            if by_names := by_nodes.get(node):
                return by_names.get(name)

    def pop(self, key: tuple[etree.Element, str, str], default: Any = None) -> EventListener | None:
        node, typename, name = key
        if by_nodes := self._event_listeners.get(typename):
            if by_names := by_nodes.get(node):
                return by_names.pop(name, default)

    def search(
        self,
        node: Optional[etree.Element] = None,
        typename: str | None = None,
        name: str | None = None,
    ) -> list[EventListener]:
        return list(search(self._event_listeners, (typename, node, name)))

    def filter_by(self, event: Event, event_typename: str) -> list[EventListener]:
        ttree = TrackingTree()
        if hasattr(event, "element_id"): # MouseEvent and events with attribute 'element_id'
            element_id = event.element_id
            next_node = ttree.get_node(element_id)
            if next_node is None and self._mousedowned_node is None:
                return []

            # Update states for mouse events
            # `previous_node` is the node that the mouse has left
            # `mousedowned_node` is the node that the mouse is currently "holding"
            match event_typename:
                case "mouseover":
                    event_listeners = (
                        self.search(self._previous_node, "mouseleave") +
                        self.search(next_node, event_typename)
                    )
                    self._previous_node = next_node
                    return event_listeners
                case "mousedown":
                    self._mousedowned_node = next_node

            target = next_node if self._mousedowned_node is None else self._mousedowned_node
            if event_typename == "mouseup":
                self._mousedowned_node = None
            return self.search(target, event_typename)
        else: # Other event types
            return self.search(typename=event_typename)

    def propagate(self, event: dict[str, Any]):
        typename = event["typename"]
        event = self.event.from_json(event)
        result = self.filter_by(event, typename)
        for event_listener in result:
            if not event_listener.active:
                continue
            for json in event_listener.listener(event):
                yield json

    def event_json(self) -> str:
        return self.event.json_format()

    def from_json(self, content: dict[str, Any]):
        return self.event.from_json(content)

    def into_script(self):
        event_json = self.event_json()
        if self.event_type == "MouseEvent":
            typenames = list(self._event_listeners)
            listeners = [
                (
                    f"window.addEventListener({typename!r}, (e) => "
                    f" f({event_json}, {typename!r}, p(e.srcElement)));"
                )
                for typename in typenames
            ]
            return "".join(listeners)
        else:
            return "".join(
                event_listener.into_script(event_json)
                for event_listener in self.search()
            )

class EventListeners:
    def __init__(self):
        self._event_listeners: dict[str, EventListenersGroup] = {}

    def __getitem__(self, event_type: str) -> EventListenersGroup:
        return self._event_listeners[event_type]

    def __contains__(self, event_type: str) -> bool:
        return event_type in self._event_listeners

    def __call__(self, event: dict[str, Any]):
        event_type = event.get("type")
        if event_listener_group := self._event_listeners.get(event_type):
            for json in event_listener_group.propagate(event):
                yield json

    def add_event_listener(self, target: EventListener):
        key = (target.node, target.typename, target.name)
        event_type = parse_event(target.typename).__name__
        if event_listeners_group := self._event_listeners.get(event_type):
            if key in event_listeners_group:
                event_listeners_group[key] = target
                return
        event_listeners_group = (
            self._event_listeners.setdefault(
                event_type,
                EventListenersGroup(target.typename),
            )
        )
        event_listeners_group[key] = target

    def remove_event_listener(self, typename: str, name: str, node: etree.Element):
        key = (node, typename, name)
        for event_listeners_group in self._event_listeners.values():
            event_listeners_group.pop(key)

    def into_script(self, host: str | None = None, port: int | None = None):
        host = "localhost" if host is None else host
        port = 5000 if port is None else port
        return headers(host, port) + "".join(
            group.into_script() for group in self._event_listeners.values()
        )

    def keys(self) -> set[str]:
        return set(self._event_listeners.keys())

    def values(self) -> list[EventListenersGroup]:
        return list(self._event_listeners.values())
