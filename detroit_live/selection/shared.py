from .hashtree import HashTree
from lxml import etree

class SharedState:
    def __init__(self):
        self.data = {}
        self.events = {}
        self.tree = None

    def init_tree(self, nodes: list[etree.Element]):
        if self.tree is None and len(nodes) > 0:
            self.tree = HashTree(nodes[0])
