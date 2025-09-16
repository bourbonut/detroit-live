from lxml import etree
from collections.abc import Callable
from typing import Any, TypeVar
from ..dispatch import Dispatch
from ..live import Event

TDragEvent = TypeVar("DragEvent", bound="DragEvent")

class DragEvent:
    def __init__(
        self,
        event_type: str,
        source_event: Event,
        subject: etree.Element | None,
        target: etree.Element,
        identifier: str,
        active: int,
        x: float,
        y: float,
        dx: float,
        dy: float,
        dispatch: Dispatch,
    ):
        self.event_type = event_type
        self.source_event = source_event
        self.subject = subject
        self.target = target
        self.identifier = identifier
        self.active = active
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.dispatch = dispatch

    def __getitem__(self, attribute: str) -> Any:
        return getattr(self, attribute)

    def on(self, typename: str, callback: Callable[..., None]) -> TDragEvent:
        self.dispatch.on(typename, callback)
        return self

    def get_callback(self, typename: str) -> Callable[..., None] | None:
        return self.dispatch.get_callback(typename)
