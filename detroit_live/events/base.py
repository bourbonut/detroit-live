from abc import ABC, abstractclassmethod
from typing import Any, TypeVar

Self = TypeVar("Self")


class JsonFormat(ABC):
    @abstractclassmethod
    def json_format(cls: type[Self]) -> str: ...


class FromJson(ABC):
    @abstractclassmethod
    def from_json(cls: type[Self], content: dict[str, Any]) -> Self: ...


class Event(JsonFormat, FromJson): ...
