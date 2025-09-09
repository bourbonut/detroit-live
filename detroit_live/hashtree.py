from lxml import etree

def get_root(node: etree.Element) -> etree.Element:
    parent = node.getparent()
    return node if parent is None else get_root(parent)

class HashTree:

    def __init__(self, node: etree.Element):
        self._root = get_root(node)
        self._tree = etree.ElementTree(self._root)
        self._map = {self.hash(node): node}

    @property
    def root(self) -> etree.Element:
        return self._root

    def hash(self, node: etree.Element):
        return hash((self._tree.getelementpath(node), node)) // 1000

    def insert(self, node: etree.Element) -> str:
        hash_key = self.hash(node)
        self._map[hash_key] = node
        return str(hash_key)

    def get(self, hash_key: int) -> etree.Element:
        return self._map[hash_key]
