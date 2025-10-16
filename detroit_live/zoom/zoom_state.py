from typing import TypeVar

from lxml import etree

from .transform import Transform, identity

Gesture = TypeVar("Gesture", bound="Gesture")


class ZoomState:
    def __init__(self):
        self.__zoom = {}
        self.__zooming = {}

    def set_zoom(self, node: etree.Element, transform: Transform):
        self.__zoom[node] = transform

    def get_zoom(self, node: etree.Element) -> Transform | None:
        return self.__zoom.get(node)

    def remove_zoom(self, node: etree.Element):
        self.__zoom.pop(node, None)

    def set_zooming(self, node: etree.Element, gesture: Gesture):
        self.__zooming[node] = gesture

    def get_zooming(self, node: etree.Element) -> Gesture | None:
        return self.__zooming.get(node)

    def remove_zooming(self, node: etree.Element):
        self.__zooming.pop(node, None)


_zoom_state = ZoomState()


def zoom_transform(node: etree.Element) -> Transform:
    """
    Returns the current transform for the specified node. Note that node should
    typically be a DOM element, not a selection. (A selection may consist of
    multiple nodes, in different states, and this function only returns a
    single transform.)

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    Transform
        Transform object
    """
    transform = _zoom_state.get_zoom(node)
    while transform is None:
        node = node.getparent()
        if node is None:
            return identity
        transform = _zoom_state.get_zoom(node)
    return transform
