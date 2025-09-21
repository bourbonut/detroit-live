from lxml import etree
from typing import TypeVar
from .transform import Transform

Gesture = TypeVar("Gesture", bound="Gesture")

class ZoomState:

    def __init__(self):
        self.__zoom  = {}
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
