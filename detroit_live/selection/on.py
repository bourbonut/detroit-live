from collections.abc import Callable
from typing import Optional

from detroit.types import T
from lxml import etree

from ..events import ContextListener, Event, EventListener, EventListeners


def on_add(
    event_listeners: EventListeners,
    listener: Callable[[Event, T | None, Optional[etree.Element]], None],
    data_accessor: Callable[[etree.Element], T],
    extra_nodes: list[etree.Element],
    html_nodes: list[etree.Element],
    active: bool,
    target: str | None,
) -> Callable[[str, str, etree.Element], None]:
    def on(typename: str, name: str, node: etree.Element):
        updated_nodes = [node] + extra_nodes
        event_listeners.add_event_listener(
            EventListener(
                typename,
                name,
                ContextListener(
                    updated_nodes,
                    html_nodes,
                    listener,
                    data_accessor,
                ),
                active,
                target,
            )
        )

    return on


def on_remove(
    event_listeners: EventListeners,
) -> Callable[[str, str, etree.Element], None]:
    def on(typename: str, name: str, node: etree.Element):
        event_listeners.remove_event_listener(typename, name, node)

    return on
