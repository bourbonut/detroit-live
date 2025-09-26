import logging
import re
from typing import Optional

from lxml import etree

from .types import MouseEvent, WheelEvent

TRANSFORM_PATTERN = re.compile(r"(translate|scale)\(([^)]+)\)")

log = logging.getLogger(__name__)


def pointer(
    event: MouseEvent | WheelEvent, node: Optional[etree.Element] = None
) -> tuple[float, float]:
    """
    Returns a two-element array of numbers :math:`[x, y]` representing the
    coordinates of the specified event relative to the specified target.

    Parameters
    ----------
    event : MouseEvent | WheelEvent
        Mouse event or wheel event
    node : Optional[etree.Element]
        If the :code:`node` is specified, the event's coordinates are
        transformed using the inverse of the screen coordinate transformation
        matrix.

    Returns
    -------
    tuple[float, float]
        Coordinates :math:`[x, y]`
    """
    tx = 0
    ty = 0
    k = 1
    if isinstance(event, MouseEvent):
        if node is None:
            return event.page_x, event.page_y
        elif transform := node.get("transform"):
            for match_ in TRANSFORM_PATTERN.findall(transform):
                match match_:
                    case ("translate", values):
                        tx, ty = (float(v.strip()) for v in values.split(","))
                    case ("scale", v):
                        k = float(v.strip())
                    case (unknown, values):
                        log.warning(
                            f"Unknown transformation: {unknown} with values {values}",
                        )
            return (event.client_x - tx) / k, (event.client_y - ty) / k
        # return event.client_x - event.rect_left, event.client_y - event.rect_top
        return event.page_x, event.page_y
    else:
        return event.client_x, event.client_y
