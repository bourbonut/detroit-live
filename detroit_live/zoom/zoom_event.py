from lxml import etree
from typing import Any
from ..dispatch import Dispatch
from ..events import Event
from .transform import Transform

class ZoomEvent:
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
