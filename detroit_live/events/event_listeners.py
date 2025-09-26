import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from lxml import etree

from .base import Event
from .context_listener import ContextListener
from .headers import headers
from .tracking_tree import TrackingTree
from .types import parse_event
from .utils import search, xpath_to_query_selector

T = TypeVar("T")

log = logging.getLogger(__name__)


def parse_target(
    target: str | None = None,
    typename: str | None = None,
    node: str | None = None,
) -> str:
    """
    Returns the corresponding :code:`target` given the specified arguments, if
    :code:`target` is not specified.

    Parameters
    ----------
    target : str | None
        Target
    typename : str | None
        Typename
    node : str | None
        Node element

    Returns
    -------
    str
        Target value (e.g. :code:`"window"`)
    """
    if target is not None:
        return target
    match typename:
        case "change":
            ttree = TrackingTree()
            path = ttree.get_path(node)
            selector = xpath_to_query_selector(path)
            return f"document.querySelector({selector!r})"
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
    """
    Event listener

    Attributes
    ----------
    typename : str
        Typename
    name : str
        Name associated to the typename
    listener : ContextListener
        Context listener
    active : bool
        Helps to know if the event listener is activated
    node : etree.Element
        Node associated to the event listener
    target : str
        Target
    """

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

    def into_script(self, event_json: str) -> str:
        typename = repr(self.typename)
        return (
            f"{self.target}.addEventListener({typename}, "
            f"(e) => f({event_json}, {typename}, p(e.srcElement)));"
        )


class EventListenersGroup:
    """
    Class which groups event listeners by typenames, elements (nodes) and
    names.

    Attributes
    ----------
    event : type[Event]
        Event class
    event_type : str
        Event type
    """

    def __init__(self, typename: str):
        self.event: type[Event] = parse_event(typename)
        self.event_type: str = self.event.__name__
        self._event_listeners: dict[
            etree.Element, dict[str, dict[str, EventListener]]
        ] = {}
        self._previous_node = None
        self._mousedowned_node = None

    def __setitem__(
        self, key: tuple[etree.Element, str, str], event_listener: EventListener
    ):
        """
        Sets an event listener given a :code:`key`.

        Parameters
        ----------
        key : tuple[etree.Element, str, str]
            Tuple :code:`(node, typename, name)`
        event_listener : EventListener
            Event listener object
        """
        node, typename, name = key
        (self._event_listeners.setdefault(typename, {}).setdefault(node, {}))[name] = (
            event_listener
        )

    def get(self, key: tuple[etree.Element, str, str]) -> EventListener | None:
        """
        Gets an event listener given the specified :code:`key` if it exists
        else returns :code:`None`.

        Parameters
        ----------
        key : tuple[etree.Element, str, str]
            Tuple :code:`(node, typename, name)`

        Returns
        -------
        EventListener | None
            Even listener if found
        """
        node, typename, name = key
        if by_nodes := self._event_listeners.get(typename):
            if by_names := by_nodes.get(node):
                return by_names.get(name)

    def pop(
        self, key: tuple[etree.Element, str, str], default: Any = None
    ) -> EventListener | Any:
        """
        Pops the event listener given the specified :code:`key`. If not found,
        it returns :code:`default`.

        Parameters
        ----------
        key : tuple[etree.Element, str, str]
            Tuple :code:`(node, typename, name)`
        default : Any
            Value returned if the event listener was not found

        Returns
        -------
        EventListener | Any
            Popped event listener if found else :code:`default`
        """
        node, typename, name = key
        if by_nodes := self._event_listeners.get(typename):
            if by_names := by_nodes.get(node):
                return by_names.pop(name, default)
        return default

    def search(
        self,
        node: Optional[etree.Element] = None,
        typename: str | None = None,
        name: str | None = None,
    ) -> list[EventListener]:
        """
        Searchs all event listeners which match the values of the specified
        :code:`node`, :code:`typename` and :code:`name`.

        Parameters
        ----------
        node : Optional[etree.Element]
            Node element
        typename : str | None
            Typename
        name : str | None
            Name associated of the typename

        Returns
        -------
        list[EventListener]
            List of event listeners
        """
        return list(search(self._event_listeners, (typename, node, name)))

    def filter_by(self, event: Event, typename: str) -> list[EventListener]:
        """
        Filters event listeners based on the given :code:`event` and
        :code:`typename`.

        Parameters
        ----------
        event : Event
            Event
        typename : str
            Typename of the event

        Returns
        -------
        list[EventListener]
            List of event listeners
        """
        ttree = TrackingTree()
        if hasattr(
            event, "element_id"
        ):  # MouseEvent and events with attribute 'element_id'
            element_id = event.element_id
            next_node = ttree.get_node(element_id)
            if next_node is None and self._mousedowned_node is None:
                return []

            # Update states for mouse events
            # `previous_node` is the node that the mouse has left
            # `mousedowned_node` is the node that the mouse is currently "holding"
            match typename:
                case "mouseover":
                    event_listeners = self.search(
                        self._previous_node, "mouseleave"
                    ) + self.search(next_node, typename)
                    self._previous_node = next_node
                    return event_listeners
                case "mousedown":
                    self._mousedowned_node = next_node

            target = (
                next_node if self._mousedowned_node is None else self._mousedowned_node
            )
            if typename == "mouseup":
                self._mousedowned_node = None
            return self.search(target, typename)
        else:  # Other event types
            return self.search(typename=typename)

    def propagate(self, event: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """
        Propagate an :code:`event` to all matched event listeners.

        Parameters
        ----------
        event : dict[str, Any]
            JSON dictionary

        Returns
        -------
        Iterator[list[dict[str, Any]]]
            Iterator of updated values sent through websocket
        """
        typename = event["typename"]
        event = self.event.from_json(event)
        for event_listener in self.filter_by(event, typename):
            if not event_listener.active:
                continue
            yield list(event_listener.listener(event))

    def event_json(self) -> str:
        """
        Returns the event as a JSON string used for JavaScript code.

        Returns
        -------
        str
            JSON of the event
        """
        return self.event.json_format()

    def from_json(self, content: dict[str, Any]) -> Event:
        """
        Converts a JSON dictionary to an event object.

        Parameters
        ----------
        content : dict[str, Any]
            JSON content from JavaScript

        Returns
        -------
        Event
            Event object
        """
        return self.event.from_json(content)

    def into_script(self) -> str:
        """
        Converts event listeners into a script (:code:`str`) used by
        JavaScript.

        Returns
        -------
        str
            Script used by JavaScript
        """
        event_json = self.event_json()
        if self.event_type == "MouseEvent":
            typenames = list(self._event_listeners)
            event_json = f"function _ev(e){{return {event_json}}}"
            listeners = [
                (
                    f"window.addEventListener({typename!r}, (e) => "
                    f" f(_ev(e), {typename!r}, p(e.srcElement)));"
                )
                for typename in typenames
            ]
            return event_json + "".join(listeners)
        else:
            return "".join(
                event_listener.into_script(event_json)
                for event_listener in self.search()
            )


class EventListeners:
    """
    Collection of event listeners mapped by event types.
    """

    def __init__(self):
        self._event_listeners: dict[str, EventListenersGroup] = {}

    def __getitem__(self, event_type: str) -> EventListenersGroup:
        """
        Gets a group of event listeners given the specified :code:`event_type`.

        Parameters
        ----------
        event_type : str
            Event type

        Returns
        -------
        EventListenersGroup
            Group of event listeners
        """
        return self._event_listeners[event_type]

    def __contains__(self, event_type: str) -> bool:
        """
        Checks if the specified :code:`event_type` exists in the collection.

        Parameters
        ----------
        event_type : str
            Event type

        Returns
        -------
        bool
            :code:`True` if found
        """
        return event_type in self._event_listeners

    def __call__(self, event: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """
        Applies the specified :code:`event` to all matched event listeners.

        Parameters
        ----------
        event : dict[str, Any]
            Event received by the websocket

        Returns
        -------
        Iterator[list[dict[str, Any]]]
            Iterator of updated values sent through websocket
        """
        event_type = event.get("type")
        if event_type is None:
            log.warning(f"Unknown type message {event_type!r} (event={event})")
        if event_listener_group := self._event_listeners.get(event_type):
            for json in event_listener_group.propagate(event):
                yield json

    def add_event_listener(self, target: EventListener):
        """
        Adds an event listener to the collection

        Parameters
        ----------
        target : EventListener
            Event listener
        """
        key = (target.node, target.typename, target.name)
        event_type = parse_event(target.typename).__name__
        event_listeners_group = self._event_listeners.setdefault(
            event_type,
            EventListenersGroup(target.typename),
        )
        event_listeners_group[key] = target

    def remove_event_listener(self, typename: str, name: str, node: etree.Element):
        """
        Removes an event listener from the collection

        Parameters
        ----------
        typename : str
            Typename
        name : str
            Name
        node : etree.Element
            Node element
        """
        key = (node, typename, name)
        for event_listeners_group in self._event_listeners.values():
            event_listeners_group.pop(key)

    def into_script(self, host: str | None = None, port: int | None = None) -> str:
        """
        Converts event listeners into a script (:code:`str`) used by
        JavaScript.

        Parameters
        ----------
        host : str | None
            Host name value
        port : int | None
            Port value

        Returns
        -------
        str
            Script used by JavaScript
        """
        host = "localhost" if host is None else host
        port = 5000 if port is None else port
        return headers(host, port) + "".join(
            group.into_script() for group in self._event_listeners.values()
        )

    def keys(self) -> set[str]:
        """
        Returns the set of event types

        Returns
        -------
        set[str]
            Set of event types
        """
        return set(self._event_listeners.keys())

    def values(self) -> list[EventListenersGroup]:
        """
        Returns a list of groups of event listeners

        Returns
        -------
        list[EventListenersGroup]
            List of groups of event listeners
        """
        return list(self._event_listeners.values())
