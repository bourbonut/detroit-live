from typing import Any

from lxml import etree

from ..dispatch import Dispatch
from ..events import Event
from .transform import Transform


class ZoomEvent:
    """
    Zoom Event

    Attributes
    ----------
    event_type : str
        The event type
    source_event : Event
        The underlying input event such as mousemove or touchmove
    target : etree.Element
        The associated zoom behavior
    transform : Transform
        The current zoom transform
    dispatch : Dispatch
        The dispatch listeners
    """

    def __init__(
        self,
        event_type: str,
        source_event: Event,
        target: etree.Element,
        transform: Transform,
        dispatch: Dispatch,
    ):
        self.event_type = event_type
        self.source_event = source_event
        self.target = target
        self.transform = transform
        self.dispatch = dispatch

    def __getitem__(self, attribute: str) -> Any:
        return getattr(self, attribute)
