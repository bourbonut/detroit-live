from collections.abc import Callable
from typing import Any, TypeVar

from lxml import etree

from ..dispatch import Dispatch
from ..events import Event

TDragEvent = TypeVar("DragEvent", bound="DragEvent")


class DragEvent:
    """
    Drag event

    Attributes
    ----------
    event_type : str
        The event type
    source_event : Event
        The underlying input event, such as mousemove or touchmove
    subject : etree.Element | None
        The drage subject
    target : etree.Element
        The associated drag behavior
    identifier : str
        The string "mouse", or a numeric touch identifier
    active : int
        The number of currently active drag gestures (on start and end, not
        including this one).
    x : float
        The new x-coordinate of the subject
    y : float
        The new y-coordinate of the subject
    dx : float
        The change in x-coordinate since the previous drag event
    dy : float
        The change in y-coordinate since the previous drag event
    dispatch : Dispatch
        The dispatch listeners
    """

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
