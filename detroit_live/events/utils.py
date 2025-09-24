from collections.abc import Iterator
from functools import cache
from io import StringIO
from typing import Any

from lxml import etree

from ..types import U, V


def get_root(node: etree.Element) -> etree.Element:
    """
    Returns the root element given a starting node element.

    Parameters
    ----------
    node : etree.Element
        Starting node tree

    Returns
    -------
    etree.Element
        Root node tree
    """
    parent = node.getparent()
    return node if parent is None else get_root(parent)


def to_string(node: etree.Element) -> str:
    """
    Converts a node element into text.

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    str
        Text content of the node.
    """
    return etree.tostring(node, method="html").decode("utf-8").removesuffix("\n")


@cache
def xpath_to_query_selector(path: str) -> str:
    """
    Changes a xpath string into a query selector string

    Parameters
    ----------
    path : str
        Xpath string

    Returns
    -------
    str
        Query selector string
    """
    string = StringIO()
    for el in path.split("/"):
        if "[" in el:
            el, times = el.replace("]", "").split("[")
            string.write(f" {el}:nth-of-type({times})")
        else:
            string.write(f" {el}")
    return string.getvalue().strip()


def diffdict(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Compares two dictionary and returns the removed attributes and changes as
    dictionary.

    Parameters
    ----------
    old : dict[str, Any]
        Old version of version
    new : dict[str, Any]
       New version of values

    Returns
    -------
    dict[str, dict[str, Any]]
        Differences between :code:`old` and :code:`new`
    """
    change = []
    remove = []
    okeys = old.keys()
    nkeys = new.keys()
    for key in nkeys - okeys:
        change.append([key, new[key]])
    for key in okeys & nkeys:
        if old[key] != new[key]:
            change.append([key, new[key]])
    for key in okeys - nkeys:
        remove.append([key, old[key]])
    return {"remove": remove, "change": change}


def inner_html(node: etree.Element) -> str:
    """
    Returns the inner HTML of a node

    Parameters
    ----------
    node : etree.Element
        Node

    Returns
    -------
    str
        Inner HTML
    """
    string = to_string(node)
    parts = string.split(">")[:-1]
    parts[-1] = "<".join(parts[-1].split("<")[:-1])
    return ">".join(parts[1:])


def node_attribs(node: etree.Element, with_inner_html: bool = False) -> dict[str, Any]:
    """
    Gets the attributes of a node.

    Parameters
    ----------
    node : etree.Element
        Node
    with_inner_html : bool
        :code:`True` for adding :code:`innerHTML` value

    Returns
    -------
    dict[str, Any]
        Attributes of the node
    """
    attribs = dict(node.attrib)
    if with_inner_html:
        attribs["innerHTML"] = node.text or inner_html(node)
    return attribs


def search(mapping: dict[U, ...] | V, keys: list[Any], depth: int = 0) -> Iterator[V]:
    if depth + 1 > len(keys):  # max depth
        if isinstance(mapping, dict):
            for value in mapping.values():
                yield value
        else:
            yield mapping
    else:
        key = keys[depth]
        if key is None:
            for next in mapping.values():
                for value in search(next, keys, depth + 1):
                    yield value
        if next := mapping.get(key):
            for value in search(next, keys, depth + 1):
                yield value
