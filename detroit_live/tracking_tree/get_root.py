from lxml import etree

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
