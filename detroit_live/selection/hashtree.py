from hashlib import sha1

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

def hash_path(path: str):
    return sha1(path.encode()).hexdigest()[:16]

class HashTree:
    """
    Hash Tree object which helps to get a unique ID for each node. Unfortunatly
    it is not sufficient to use :code:`hash(node)`.

    Parameters
    ----------
    node : etree.Element
        Any starting node element

    Notes
    -----
    The root tree element will be found based on the node given in arguments.
    """

    def __init__(self, node: etree.Element):
        self._root = get_root(node)
        self._tree = etree.ElementTree(self._root)
        self._map = {self.hash(node): node}

    @property
    def root(self) -> etree.Element:
        """
        Returns the root node of the tree

        Returns
        -------
        etree.Element
            Root node
        """
        return self._root

    def hash(self, node: etree.Element) -> str:
        """
        Hashes a node element

        Parameters
        ----------
        node : etree.Element
            Node element

        Returns
        -------
        str
           Hash value
        """
        path = self._tree.getelementpath(node)
        path = f"{path}[1]" if path[-1] != "]" else path
        return sha1(path.encode()).hexdigest()[:16]

    def insert(self, node: etree.Element) -> str:
        """
        Inserts a node in the mapping attribute and returns its hash key.

        Parameters
        ----------
        node : etree.Element
            Node element

        Returns
        -------
        str
            Hash value of the inserted node
        """
        hash_key = self.hash(node)
        self._map[hash_key] = node
        return str(hash_key)

    def get(self, hash_key: int) -> etree.Element:
        """
        Gets the node element given a hash key value

        Parameters
        ----------
        hash_key : int
            Hash key value

        Returns
        -------
        etree.Element
            Node element
        """
        return self._map[hash_key]
