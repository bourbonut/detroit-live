import re
from collections.abc import Callable, Iterator
from copy import deepcopy
from typing import Any, TypeAlias, TypeVar

Callback: TypeAlias = Callable[..., None]
NamedCallback: TypeAlias = tuple[str, Callback]
TDispatch = TypeVar("Dispatch", bound="Dispatch")

TYPENAME_PATTERN = re.compile(r"^|\s+")


def parse_typenames(typenames: str) -> Iterator[tuple[str, str]]:
    for typename in TYPENAME_PATTERN.split(typenames.strip())[1:]:
        name = ""
        if "." in typename:
            i = typename.index(".")
            if i >= 0:
                name = typename[i + 1 :]
                typename = typename[0:i]
        yield (typename, name)


def get_type(callbacks: list[NamedCallback], refname: str) -> Callback | None:
    for name, callback in callbacks:
        if name == refname:
            return callback


def update_callbacks(callbacks: list[NamedCallback], refname: str, callback: Callback):
    for i, (name, _) in enumerate(callbacks):
        if name == refname:
            callbacks.pop(i)
            break
    if callback is not None:
        callbacks.append((refname, callback))


class Dispatch:
    def __init__(self, typenames: dict[str, list[NamedCallback]]):
        self._typenames = typenames

    def __call__(self, typename: str, *args: Any):
        """
        Invokes each registered callback for the specified type, passing the
        callback the specified arguments, with that as the this context.

        Parameters
        ----------
        typename : str
            Typename
        args : Any
            Additional arguments passed to the :code:`callback` function

        """
        if typename not in self._typenames:
            raise ValueError(f"Unknown type: {typename!r}")
        for name, callback in self._typenames[typename]:
            callback(*args)

    def on(self, typename: str, callback: Callback | None = None) -> TDispatch:
        """
        Adds, removes or gets the :code:`callback` for the specified typenames.
        If a callback function is specified, it is registered for the specified
        (fully-qualified) typenames. If a :code:`callback` was already
        registered for the given typenames, the existing callback is removed
        before the new callback is added.

        The specified typenames is a string, such as start or end.foo. The type
        may be optionally followed by a period (.) and a name; the optional
        name allows multiple callbacks to be registered to receive events of
        the same type, such as start.foo and start.bar. To specify multiple
        typenames, separate typenames with spaces, such as start end or
        start.foo start.bar.

        To remove all callbacks for a given name :code:`foo`, say
        :code:`dispatch.on(".foo", null)`.

        If :code:`callback` is not specified, returns the current callback for
        the specified typenames, if any. If multiple typenames are specified,
        the first matching callback is returned.

        Parameters
        ----------
        typename : str
            Typename value
        callback : Callback | None
            Callback

        Returns
        -------
        Dispatch
            Itself
        """
        parsed_types = self.parse_typenames(typename)
        if not callable(callback):
            raise TypeError("'callback' must be a function")
        for typename, name in parsed_types:
            if typename:
                update_callbacks(self._typenames[typename], name, callback)
            elif callback is None:
                for typename in self._typenames:
                    update_callbacks(self._typenames[typename], name, None)
        return self

    def get_callback(self, typename: str) -> Callback | None:
        for typename, name in self.parse_typenames(typename):
            if not typename:
                continue
            if found := get_type(self._typenames[typename], name):
                return found

    def parse_typenames(self, typenames: str) -> list[tuple[str, str]]:
        values = []
        for typename, name in parse_typenames(typenames):
            if typename and typename not in self._typenames:
                raise ValueError(f"Unknown type: {typename!r}")
            values.append((typename, name))
        return values

    def copy(self) -> TDispatch:
        """
        Returns a copy of this dispatch object. Changes to this dispatch do not
        affect the returned copy and vice versa.

        Returns
        -------
        Dispatch
            Dispatch copy
        """
        return Dispatch(deepcopy(self._typenames))

    def __str__(self):
        return f"Dispatch({self._typenames})"


def dispatch(*typenames: str) -> Dispatch:
    """
    Creates a new dispatch for the specified event types. Each type is a
    string, such as :code:`"start"` or :code:`"end"`.

    Parameters
    ----------
    typenames : str
        Typename value such as :code:`"start"` or :code:`"end"`

    Returns
    -------
    Dispatch
        Dispatch object
    """
    dispatch_typenames = {}
    for typename in typenames:
        if (
            not typename
            or typename in dispatch_typenames
            or not TYPENAME_PATTERN.match(typename)
        ):
            raise ValueError(f"Invalid typename: {typename}")
        dispatch_typenames[typename] = []
    return Dispatch(dispatch_typenames)
