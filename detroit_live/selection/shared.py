from ..events import EventListeners
from ..tracking_tree import TrackingTree
from typing import Generic, TypeVar
from lxml import etree

T = TypeVar("T")

class SharedState(Generic[T]):
    def __init__(self):
        self.data: dict[etree.Element, T] = {}
        self.events: EventListeners = EventListeners()
        self.tree: TrackingTree = TrackingTree()

    def set_tree_root(self, nodes: list[etree.Element]):
        if self.tree.root is None and len(nodes) > 0:
            self.tree.set_root(nodes[0])
