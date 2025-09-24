from lxml import etree

from ..events import MouseEvent
from ..types import T


def noevent(event: MouseEvent, d: T | None, node: etree.Element):
    pass
