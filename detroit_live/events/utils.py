from lxml import etree
from io import StringIO
from typing import Any

def to_bytes(node: etree.Element) -> bytes:
    """
    Converts a node element into bytes.

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    bytes
        Bytes content of the node
    """
    return etree.tostring(node).removesuffix(b"\n")

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
    return string.getvalue()

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

def get_node_attribs(node: etree.Element) -> dict[str, Any]:
    """
    Gets the attributes of a node

    Parameters
    ----------
    node : etree.Element
        Node

    Returns
    -------
    dict[str, Any]
        Attributes of the node
    """
    attribs = dict(node.attrib)
    attribs["innerHTML"] = node.text
    return attribs
