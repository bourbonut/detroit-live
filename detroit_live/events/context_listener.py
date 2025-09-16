from collections.abc import Callable
from hashlib import sha256
from lxml import etree
from io import StringIO
from typing import Any, Generic, Optional, TypeVar

from ..tracking_tree import TrackingTree
from .base import Event
from .diffdict import diffdict

T = TypeVar("T")

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

def get_node_attribs(node: etree.Element) -> dict[str, Any]:
    """
    Gets the attributes of a node

    Parameters
    ----------
    node : etree.Element
        Node

    Returns
    -------
    dict[str, Any]
        Attributes of the node
    """
    attribs = dict(node.attrib)
    attribs["innerHTML"] = node.text
    return attribs


def xpath_to_query_selector(path: str) -> str:
    string = StringIO()
    for el in path.split("/"):
        if "[" in el:
            el, times = el.replace("]", "").split("[")
            string.write(f" {el}:nth-of-type({times})")
        else:
            string.write(f" {el}")
    return string.getvalue()

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
        states = [
            (
                node,
                get_node_attribs(node),
                sha256(to_bytes(node)).digest(),
            ) for node in self._updated_nodes
        ]

        node = self.get_node()
        self._listener(event, self._data_accessor(node), node)

        for node, old_attrib, sha256_value in states:
            if sha256_value != sha256(to_bytes(node)).digest():
                element_id = xpath_to_query_selector(ttree.get_path(node))
                if len(node) == 0: # No child
                    new_attrib = dict(node.attrib)
                    new_attrib["innerHTML"] = node.text
                    diff = diffdict(old_attrib, new_attrib)
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
        return f"ContextListener(listener={self._listener}, node={self.get_node()}, data={self._data_accessor(self.get_node())}, updated_nodes={self._updated_nodes})"

    def __repr__(self):
        return str(self)
