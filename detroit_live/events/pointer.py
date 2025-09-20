from .types import MouseEvent, WheelEvent

def pointer(event: MouseEvent | WheelEvent) -> tuple[float, float]:
    if isinstance(event, MouseEvent):
        return event.page_x, event.page_y
    else:
        return event.client_x - event.rect_left, event.client_y - event.rect_top
