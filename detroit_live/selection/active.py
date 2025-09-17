from lxml import etree
from collections.abc import Callable
from ..events import EventListeners

def set_active(
    event_listeners: EventListeners,
    active: bool,
) -> Callable[[etree.Element, str, str], None]:
    def set_active_event(typename: str, name: str, node: etree.Element):
        target = (node, typename, name)
        def compare(node: etree.Element, typename: str, name: str) -> bool:
            return (node, typename, name) == target

        for listeners in event_listeners.values():
            for event_listener in listeners.filter(compare):
                event_listener.active = active
    return set_active_event
