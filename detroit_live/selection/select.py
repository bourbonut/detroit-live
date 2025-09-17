from lxml import etree

from .selection import LiveSelection


def select(node: etree.Element) -> LiveSelection:
    """
    Returns a selection object given a node

    Parameters
    ----------
    node : etree.Element
        Node
    ref_selection : LiveSelection | None
        Reference selection for sharing data, tree and events attributes

    Returns
    -------
    LiveSelection
        Selection object
    """
    return LiveSelection([[node]], [node])
