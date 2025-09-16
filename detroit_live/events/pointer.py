from .types import MouseEvent

def pointer(event: MouseEvent) -> tuple[float, float]:
    if event.rect_top is None or event.rect_left:
        return event.page_x, event.page_y
    return event.client_x - event.rect_left, event.client_y - event.rect_top
