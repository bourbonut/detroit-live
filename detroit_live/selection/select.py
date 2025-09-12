from lxml import etree

from .selection import LiveSelection


def select(
    node: etree.Element,
    ref_selection: LiveSelection | None = None,
) -> LiveSelection:
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
    if ref_selection is None:
        return LiveSelection([[node]], [node])
    return LiveSelection(
        [[node]],
        [node],
        data=ref_selection._data,
        tree=ref_selection._tree,
        events=ref_selection._events,
    )
