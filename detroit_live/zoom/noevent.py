from lxml import etree

from ..events import MouseEvent, WheelEvent
from ..types import T


def noevent(event: MouseEvent | WheelEvent, d: T | None, node: etree.Element):
    pass
