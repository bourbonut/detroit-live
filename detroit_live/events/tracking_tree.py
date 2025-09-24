import logging

from lxml import etree

from .utils import get_root

log = logging.getLogger(__name__)


class CacheTree:
    __slots__ = "__root", "__tree"

    def __init__(self):
        self.__root = None
        self.__tree = None

    def set_root(self, node: etree.Element):
        self.__root = get_root(node)
        self.__tree = etree.ElementTree(self.__root)

    def get_root(self):
        return self.__root

    def get_tree(self):
        return self.__tree


class TrackingTree:
    """
    Tracking Tree object which helps to get :code:`etree.Element` given a path
    (example : `body/g/g[1]/rect[8]`) and vice-versa.

    Once the root element is set, this object can be used globally without
    futher configuration.
    """

    __cache_tree = CacheTree()
    __cache_path = {}
    __cache_node = {}

    def __init__(self):
        self.__root = self.__cache_tree.get_root()
        self.__tree = self.__cache_tree.get_tree()

    def set_root(self, node: etree.Element):
        """
        Finds and sets the root node given the specified node, sets the element
        tree given the node and resets the cache values.

        Parameters
        ----------
        node : etree.Element
            Node element
        """
        self.__cache_tree.set_root(node)
        self.__root = self.__cache_tree.get_root()
        self.__tree = self.__cache_tree.get_tree()
        path = self.__root.tag
        self.__cache_path.clear()
        self.__cache_node.clear()
        self.__cache_path[node] = path
        self.__cache_node[path] = node

    @property
    def root(self) -> etree.Element | None:
        """
        Returns the root node of the tree.

        Returns
        -------
        etree.Element
            Root node
        """
        return self.__root

    def get_path(self, node: etree.Element) -> str:
        """
        Gets the path of the specified node in the tree.

        Parameters
        ----------
        node : etree.Element
            Node element

        Returns
        -------
        str
           Path in the tree of the specified node
        """
        if node in self.__cache_path:
            return self.__cache_path[node]
        path = self.__tree.getelementpath(node)
        path = (
            f"{self.root.tag}/{path}[1]"
            if path[-1] != "]"
            else f"{self.root.tag}/{path}"
        )
        self.__cache_path[node] = path
        self.__cache_node[path] = node
        return path

    def get_node(self, path: str) -> etree.Element | None:
        """
        Gets the node element given a path in the tree.

        Parameters
        ----------
        path : str
            Path in the tree of the specified node

        Returns
        -------
        etree.Element | None
            Node element
        """
        root_tag = self.__root.tag
        if root_tag in path:
            path = path.split(root_tag)[1]  # or root_tag
        if path == "":
            return self.__root
        if path in self.__cache_node:
            return self.__cache_node[path]
        if path == f"/{root_tag}":
            node = self.__tree.xpath(path)[0]
        else:
            try:
                node = self.__tree.xpath(f"/{root_tag}/{path}")[0]
            except IndexError:
                log.warning(f"{path!r} not found in XML tree (root={root_tag}).")
                node = None
        self.__cache_node[path] = node
        self.__cache_path[node] = path
        return node
