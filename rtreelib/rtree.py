import math
from functools import partial
from typing import TypeVar, Generic, List, Iterable, Callable, Optional, Tuple, Any
from rtreelib.models.rect import Rect, union_all

T = TypeVar('T')
DEFAULT_MAX_ENTRIES = 8
EPSILON = 1e-5


class RTreeEntry(Generic[T]):
    """
    R-Tree entry, containing either a pointer to a child RTreeNode instance (if this is not a leaf entry), or data (if
    this is a leaf entry).
    """

    def __init__(self, rect: Rect, child: 'RTreeNode[T]' = None, data: T = None):
        self.rect = rect
        self.child = child
        self.data = data

    def __repr__(self):
        result = f'RTreeEntry({hex(id(self))}'
        result += f', data={self.data})' if self.is_leaf else ')'
        return result

    @property
    def is_leaf(self):
        return self.child is None


EntryDivision = Tuple[Iterable[RTreeEntry[T]], Iterable[RTreeEntry[T]]]
EntryOrdering = Tuple[RTreeEntry[T]]


class RTreeNode(Generic[T]):
    """
    An R-Tree node, which is a container for R-Tree entries. The node is a leaf node if its entries contain data;
    otherwise, if it is a non-leaf node, then its entries contain pointers to children nodes.
    """

    def __init__(self, tree: 'RTreeBase[T]', is_leaf: bool, parent: 'RTreeNode[T]' = None,
                 entries: List[RTreeEntry[T]] = None):
        self._tree = tree
        self._is_leaf = is_leaf
        self.parent = parent
        self.entries = entries or []

    def __repr__(self):
        num_children = len(self.entries)
        suffix = 'child' if num_children == 1 else 'children'
        return f'RTreeNode({hex(id(self))}, {num_children} {suffix})'

    @property
    def tree(self):
        return self._tree

    @property
    def is_leaf(self) -> bool:
        return self._is_leaf

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def parent_entry(self) -> Optional[RTreeEntry[T]]:
        if self.parent is not None:
            return next(entry for entry in self.parent.entries if entry.child is self)
        return None

    def get_bounding_rect(self):
        return union_all([entry.rect for entry in self.entries])


class RTreeBase(Generic[T]):
    """
    Base R-Tree class containing functionality common to all R-Tree implementations. The base class requires choosing
    a strategy for insertion, deletion, and other behaviors. For a default implementation that uses Guttman's
    strategies, use the RTree class (alias for RTreeGuttman).
    """

    def __init__(
            self,
            insert: Callable[['RTreeBase[T]', T, Rect], RTreeEntry[T]],
            choose_leaf: Callable[['RTreeBase[T]', RTreeEntry[T]], RTreeNode[T]],
            adjust_tree: Callable[['RTreeBase[T]', RTreeNode[T], RTreeNode[T]], None],
            overflow_strategy: Callable[['RTreeBase[T]', RTreeNode[T]], RTreeNode[T]],
            max_entries: int = DEFAULT_MAX_ENTRIES,
            min_entries: int = None
    ):
        """
        Initializes the R-Tree
        :param insert: Strategy used for inserting a new entry.
        :param choose_leaf: Strategy used for choosing a leaf node when inserting a new entry.
        :param adjust_tree: Strategy used for balancing the tree and updating bounding rectangles after inserting a
            new entry.
        :param overflow_strategy: Strategy used for dealing with an overflowing node (a node where the number of entries
            exceeds max_entries).
        :param max_entries: Maximum number of entries per node.
        :param min_entries: Minimum number of entries per node. Defaults to ceil(max_entries/2).
        """
        self.max_entries = max_entries
        self.min_entries = min_entries or math.ceil(max_entries/2)
        assert self.max_entries >= self.min_entries
        self.insert_strategy = insert
        self.choose_leaf = choose_leaf
        self.adjust_tree = adjust_tree
        self.overflow_strategy = overflow_strategy
        self.root = RTreeNode(self, True)
        # Initialize an untyped "_cache" property that implementations can use for any purpose. R* uses this to keep
        # track of certain information when doing a forced reinsert.
        self._cache: Any = None

    def insert(self, data: T, rect: Rect) -> RTreeEntry[T]:
        """
        Inserts a new entry into the tree
        :param data: Entry data
        :param rect: Bounding rectangle
        :return: RTreeEntry instance for the newly-inserted entry.
        """
        return self.insert_strategy(self, data, rect)

    def perform_node_split(self, node: RTreeNode[T], group1: List[RTreeEntry[T]], group2: List[RTreeEntry[T]])\
            -> RTreeNode[T]:
        """
        Splits a given node into two nodes. The original node will have the entries specified in group1, and the
        newly-created split node will have the entries specified in group2. Both the original and split node will
        have their children nodes adjusted so they have the correct parent.
        :param node: Original node to split
        :param group1: Entries to assign to the original node
        :param group2: Entries to assign to the newly-created split node
        :return: The newly-created split node
        """
        node.entries = group1
        split_node = RTreeNode(self, node.is_leaf, parent=node.parent, entries=group2)
        self._fix_children(node)
        self._fix_children(split_node)
        return split_node

    @staticmethod
    def _fix_children(node: RTreeNode[T]) -> None:
        if not node.is_leaf:
            for entry in node.entries:
                entry.child.parent = node

    def grow_tree(self, nodes: List[RTreeNode[T]]):
        """
        Grows the R-Tree by creating a new root node, with the given nodes as children.
        :param nodes: Existing nodes that will become children of the new root node.
        :return: New root node
        """
        entries = [RTreeEntry(node.get_bounding_rect(), child=node) for node in nodes]
        self.root = RTreeNode(self, False, entries=entries)
        for node in nodes:
            node.parent = self.root
        return self.root

    def traverse(self, fn: Callable[[RTreeNode[T]], None]) -> None:
        """
        Traverses the nodes of the R-Tree in depth-first order, calling the given function on each node. For a
        level-order traversal (breadth-first), use traverse_level_order instead.
        :param fn: Function to execute on each node. The function should accept the node as its only parameter.
        """
        self._traverse(self.root, fn)

    def _traverse(self, node: RTreeNode[T], fn: Callable[[RTreeNode[T]], None]) -> None:
        fn(node)
        if not node.is_leaf:
            for entry in node.entries:
                self._traverse(entry.child, fn)

    def traverse_level_order(self, fn: Callable[[RTreeNode[T], int], None]) -> None:
        """
        Traverses the nodes of the R-Tree in level-order (breadth first), calling the given function on each node. For a
        depth-first traversal, use the traverse method instead.
        :param fn: Function to execute on each node. This function should accept the node, and optionally the current
            level (with 0 corresponding to the root level) as parameters.
        """
        stack = [(self.root, 0)]
        while stack:
            node, level = stack[0]
            stack = stack[1:]
            fn(node, level)
            if not node.is_leaf:
                stack.extend([(entry.child, level + 1) for entry in node.entries])

    def get_levels(self) -> List[List[RTreeNode[T]]]:
        """
        Returns a list containing a list of nodes at each level of the R-Tree (i.e., the i-th element in the return list
        contains a list of nodes at level i of the tree, with level 0 corresponding to the root).
        """
        levels: List[List[RTreeNode[T]]] = []
        fn = partial(_add_node_to_level, levels)
        # noinspection PyTypeChecker
        self.traverse_level_order(fn)
        return levels

    def get_nodes(self) -> Iterable[RTreeNode[T]]:
        """Returns an iterable of all nodes in the R-Tree (including intermediate and leaf nodes)"""
        yield from self._get_nodes(self.root)

    def _get_nodes(self, node: RTreeNode[T]) -> Iterable[RTreeNode[T]]:
        yield node
        if not node.is_leaf:
            for entry in node.entries:
                yield from self._get_nodes(entry.child)

    def get_leaves(self) -> List[RTreeNode[T]]:
        """
        Returns a list of leaf nodes in the R-Tree. Note that R-Tree nodes are simply containers for child entries,
        which contain the actual data. If you want to get the actual data elements, you probably want to use
        get_leaf_entries instead.
        """
        leaves = []
        fn = partial(_append_if_leaf, leaves)
        # noinspection PyTypeChecker
        self.traverse_level_order(fn)
        return leaves

    def get_leaf_entries(self) -> Iterable[RTreeEntry[T]]:
        """Returns an iterable of the leaf entries in the R-Tree which contain the data."""
        for leaf in self.get_leaves():
            for entry in leaf.entries:
                yield entry


def _add_node_to_level(levels: List[List[RTreeNode[T]]], node: RTreeNode[T], level: int):
    if level >= len(levels):
        nodelist = []
        levels.append(nodelist)
    else:
        nodelist = levels[level]
    nodelist.append(node)


def _append_if_leaf(leaves: List[RTreeNode[T]], node: RTreeNode[T], _: int):
    if node.is_leaf:
        leaves.append(node)
