from typing import Generic

from lxml import etree

from ..events import EventListeners, EventProducers, TrackingTree
from ..types import T


class SharedState(Generic[T]):
    def __init__(self):
        self.data: dict[etree.Element, T] = {}
        self.event_listeners: EventListeners = EventListeners()
        self.event_producers: EventProducers = EventProducers()
        self.tree: TrackingTree = TrackingTree()

    def set_tree_root(self, nodes: list[etree.Element]):
        if self.tree.root is None and len(nodes) > 0:
            self.tree.set_root(nodes[0])
