from collections.abc import Callable
from typing import TypeAlias, TypeVar

from lxml import etree

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

EventFunction: TypeAlias = Callable[[etree.Element, U, list[etree.Element]], V]
Extent: TypeAlias = tuple[tuple[float, float], tuple[float, float]]
