from collections.abc import Callable

from lxml import etree

from ..events import EventListeners


def set_active(
    event_listeners: EventListeners,
    active: bool,
) -> Callable[[etree.Element, str, str], None]:
    def set_active_event(typename: str, name: str, node: etree.Element):
        for listeners in event_listeners.values():
            for event_listener in listeners.search(node, typename, name):
                event_listener.active = active

    return set_active_event
