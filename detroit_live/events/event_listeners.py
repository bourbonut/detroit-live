from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Optional, TypeVar

from lxml import etree
from .tracking_tree import TrackingTree
from .base import Event
from .context_listener import ContextListener
from .types import parse_event
from .headers import headers

T = TypeVar("T")

NAMESPACE = {
    "document": "d",
    "event": "e",
    "socket": "s",
    "window": "w",
}

def to_bytes(node: etree.Element) -> bytes:
    """
    Converts a node element into bytes.

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    bytes
        Bytes content of the node
    """
    return etree.tostring(node).removesuffix(b"\n")

def to_string(node: etree.Element) -> str:
    """
    Converts a node element into text.

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    str
        Text content of the node.
    """
    return etree.tostring(node, method="html").decode("utf-8").removesuffix("\n")

def diffdict(old: dict, new: dict) -> dict:
    change = []
    remove = []
    okeys = old.keys()
    nkeys = new.keys()
    for key in nkeys - okeys:
        change.append([key, new[key]])
    for key in okeys & nkeys:
        if old[key] != new[key]:
            change.append([key, new[key]])
    for key in okeys - nkeys:
        remove.append([key, old[key]])
    return {"remove": remove, "change": change}

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
        target = NAMESPACE.get(self.target, self.target)
        typename = repr(self.typename)
        return (
            f"{target}.addEventListener({typename}, "
            f"(e) => f({event_json}, {typename}, p(e.srcElement)));"
        )


class EventListenersGroup:
    def __init__(self, typename: str):
        self.event: type[Event] = parse_event(typename)
        self.event_type: str = self.event.__name__
        self._event_listeners: dict[tuple[etree.Element, str, str], EventListener] = {}
        self._previous_node = None
        self._mousedowned_node = None

    def __contains__(self, key: tuple[etree.Element, str, str]) -> bool:
        return key in self._event_listeners

    def __setitem__(self, key: tuple[etree.Element, str, str], event_listener: EventListener):
        self._event_listeners[key] = event_listener

    def get(self, key: tuple[etree.Element, str, str]) -> EventListener | None:
        return self._event_listeners.get(key)

    def pop(self, key: tuple[etree.Element, str, str], default: Any = None) -> EventListener | None:
        return self._event_listeners.pop(key, default)

    def filter(self, filter_func: Callable[[etree.Element, str, str], bool]) -> list[EventListener]:
        return [
            event_listener for (node, typename, name), event_listener in self._event_listeners.items()
            if filter_func(node, typename, name)
        ]

    def select(self, node: etree.Element, typename: str) -> list[EventListener]:
        return [
            event_listener for (el_node, el_typename, _), event_listener in self._event_listeners.items()
            if (el_node == node and el_typename == typename)
        ]

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
                        self.select(self._previous_node, "mouseleave") +
                        self.select(next_node, event_typename)
                    )
                    self._previous_node = next_node
                    return event_listeners
                case "mousedown":
                    self._mousedowned_node = next_node

            target = next_node if self._mousedowned_node is None else self._mousedowned_node
            if event_typename == "mouseup":
                self._mousedowned_node = None
            event_listeners = [
                event_listener for (node, typename, _), event_listener in self._event_listeners.items()
                if node == target and typename == event_typename
            ]
            return event_listeners
        else: # Other event types
            event_listeners = [
                event_listener for (_, typename, _), event_listener in self._event_listeners.items()
                if typename == event_typename
            ]
            return event_listeners

    def propagate(self, event: dict[str, Any]):
        typename = event["typename"]
        event = self.event.from_json(event)
        for event_listener in self.filter_by(event, typename):
            if not event_listener.active:
                continue
            for json in event_listener.listener(event):
                yield json

    def event_json(self) -> str:
        event_json = self.event.json_format()
        for old, new in NAMESPACE.items():
            event_json = event_json.replace(old, new)
        return event_json

    def from_json(self, content: dict[str, Any]):
        return self.event.from_json(content)

    def into_script(self):
        event_json = self.event_json()
        if self.event_type == "MouseEvent":
            typenames = {typename for (_, typename, _) in self._event_listeners}
            listeners = [
                (
                    f"w.addEventListener({typename!r}, (e) => "
                    f" f({event_json}, {typename!r}, p(e.srcElement)));"
                )
                for typename in typenames
            ]
            return "".join(listeners)
        else:
            return "".join(
                event_listener.into_script(event_json)
                for event_listener in self._event_listeners.values()
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
