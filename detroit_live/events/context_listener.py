from collections.abc import Callable
from lxml import etree
from typing import Generic, Optional, TypeVar

from .tracking_tree import TrackingTree
from .base import Event
from .utils import (
    to_string,
    diffdict,
    get_node_attribs,
    xpath_to_query_selector,
)

T = TypeVar("T")

EMPTY_DIFF = {'remove': [], 'change': []}

class ContextListener(Generic[T]):
    def __init__(
        self,
        updated_nodes: list[etree.Element],
        listener: Callable[[Event, T | None, Optional[etree.Element]], None],
        data_accessor: Callable[[etree.Element], T],
    ):
        self._updated_nodes = updated_nodes
        self._listener = listener
        self._data_accessor = data_accessor

    def __call__(self, event: Event):
        ttree = TrackingTree()
        states = [(node, get_node_attribs(node)) for node in self._updated_nodes]

        node = self.get_node()
        self._listener(event, self._data_accessor(node), node)

        nodes = set(self._updated_nodes)
        for node, old_attrib in states:
            element_id = xpath_to_query_selector(ttree.get_path(node))
            if len(node) == 0 or len(set(node) | nodes) != 0: # No child
                new_attrib = dict(node.attrib)
                new_attrib["innerHTML"] = node.text
                diff = diffdict(old_attrib, new_attrib)
                if diff != EMPTY_DIFF:
                    yield {"elementId": element_id, "diff": diff}
            else:
                yield {"elementId": element_id, "outerHTML": to_string(node)}

    def get_listener(
        self
    ) -> Callable[[Event, T | None, Optional[etree.Element]], None]:
        return self._listener

    def get_node(self) -> etree.Element:
        return self._updated_nodes[0]

    def __str__(self):
        return (
            f"ContextListener(listener={self._listener},"
            f" node={self.get_node()},"
            f" data={self._data_accessor(self.get_node())},"
            f" updated_nodes={self._updated_nodes})"
        )

    def __repr__(self):
        return str(self)
