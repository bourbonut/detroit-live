from copy import deepcopy
import re

TYPENAME_PATTERN = re.compile(r"^|\s+")


class Noop:
    def value(self):
        return


def get_type(type_list, name):
    for c in type_list:
        if c["name"] == name:
            return c["value"]


def set_type(typename, name, callback):
    for i in range(len(typename)):
        if typename[i]["name"] == name:
            typename[i] = Noop()
            typename = typename[0:i] + typename[i + 1:]
            break
    if callback is not None:
        typename.append({"name": name, "value": callback})
    return typename


class Dispatch:
    def __init__(self, typenames):
        self._typenames = typenames

    def __call__(self, typename, that, *args):
        if typename not in self._typenames:
            raise ValueError(f"Unknown type: {typename!r}")
        for typ in self._typenames[typename]:
            typ["value"](that, *args)

    def on(self, parsed_types, callback):
        parsed_types = self.parse_typenames(parsed_types)
        if not callable(callback):
            raise TypeError("'callback' must be a function")
        for parsed_type in parsed_types:
            if typename := parsed_type.get("type"):
                self._typenames[typename] = set_type(
                    self._typenames[typename], parsed_type["name"], callback
                )
            elif callback is None:
                for typename in self._typenames:
                    self._typenames[typename] = set_type(
                        self._typenames[typename], parsed_type["name"], None
                    )
        return self

    def get_callback(self, typenames):
        for typename in self.parse_typenames(typenames):
            if typ := typename.get("type"):
                if found := get_type(self._typenames[typ], typename["name"]):
                    return found

    def parse_typenames(self, typenames):
        values = []
        for typename in TYPENAME_PATTERN.split(typenames.strip())[1:]:
            name = ""
            if "." in typename:
                i = typename.index(".")
                if i >= 0:
                    name = typename[i + 1:]
                    typename = typename[0:i]
            if typename and typename not in self._typenames:
                raise ValueError(f"Unknown type: {typename!r}")
            values.append({"type": typename, "name": name})
        return values

    def copy(self):
        return Dispatch(deepcopy(self._typenames))

    def __str__(self):
        return f"Dispatch({self._typenames})"


def dispatch(*typenames):
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
