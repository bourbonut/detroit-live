from enum import Enum, auto


class EventSource(Enum):
    PRODUCER = auto()
    WEBSOCKET = auto()
