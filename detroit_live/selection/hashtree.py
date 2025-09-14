from hashlib import sha1
from lxml import etree

def hash_path(path: str) -> str:
    """
    Returns a hashed 16-character hexadecimal string given the specific path.

    Parameters
    ----------
    path : str
        Element path

    Returns
    -------
    str
        16-character hexadecimal string
    """
    return sha1(path.encode()).hexdigest()[:16]

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


class HashTree:
    """
    Hash Tree object which helps to get a unique ID for each node. Unfortunatly
    it is not sufficient to use :code:`hash(node)`.

    Notes
    -----
    The root tree element will be found based on the node given in arguments.
    """

    def __init__(self):
        self._root = None
        self._tree = None
        self._map = {}

    def set_root(self, node: etree.Element):
        """
        Sets the root node and the element tree given the node.

        Parameters
        ----------
        node : etree.Element
            Node element
        """
        self._root = get_root(node)
        self._tree = etree.ElementTree(self._root)
        self._map[self.hash(node)] = node

    @property
    def root(self) -> etree.Element | None:
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
        Hashes a node element into a 16-character hexadecimal string given the
        specific path.

        Parameters
        ----------
        node : etree.Element
            Node element

        Returns
        -------
        str
           Hashed 16-character hexadecimal string
        """
        path = self._tree.getelementpath(node)
        return hash_path(f"{path}[1]" if path[-1] != "]" else path)

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

    def get(self, hash_key: str) -> etree.Element:
        """
        Gets the node element given a hash key value

        Parameters
        ----------
        hash_key : str
            Hashed 16-character hexadecimal string

        Returns
        -------
        etree.Element
            Node element
        """
        return self._map[hash_key]
