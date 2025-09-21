from lxml import etree
import re
from typing import Optional
from .types import MouseEvent, WheelEvent
import warnings

TRANSFORM_PATTERN = re.compile(r"(translate|scale)\(([^)]+)\)")

def pointer(event: MouseEvent | WheelEvent, node: Optional[etree.Element] = None) -> tuple[float, float]:
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
                        warnings.warn(
                            f"Unknown transformation: {unknown} with values {values}",
                            category=UserWarning,
                        )
            return (event.client_x - tx) / k, (event.client_y - ty) / k
        # return event.client_x - event.rect_left, event.client_y - event.rect_top
        return event.page_x, event.page_y
    else:
        return event.client_x, event.client_y
