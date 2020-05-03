import math
from functools import partial
from typing import TypeVar, Generic, List, Iterable, Callable, Optional, Tuple, Any
from rtreelib.models import Rect, get_loc_intersection_fn, Location, union_all

DEFAULT_MAX_ENTRIES = 8
EPSILON = 1e-5
T = TypeVar('T')
TResult = TypeVar('TResult')


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

    def query(self, loc: Location) -> Iterable[RTreeEntry[T]]:
        """
        Queries leaf entries for a location (either a point or a rectangle), returning an iterable.
        :param loc: Location to query. This may either be a Point or a Rect, or a tuple/list of coordinates representing
            either a point or a rectangle.
        :return: Iterable of leaf entries that matched the location query.
        """
        intersects = get_loc_intersection_fn(loc)
        for leaf in self.search_nodes(lambda node: intersects(node.get_bounding_rect())):
            for e in leaf.entries:
                if intersects(e.rect):
                    yield e

    def query_nodes(self, loc: Location, leaves=True) -> Iterable[RTreeNode[T]]:
        """
        Queries nodes for a location (either a point or a rectangle), returning an iterable. By default, this method
        returns only leaf nodes, though intermediate-level nodes can also be returned by setting the leaves parameter
        to False.
        :param loc: Location to query. This may either be a Point or a Rect, or a tuple/list of coordinates representing
            either a point or a rectangle.
        :param leaves: Indicates whether only leaf-level nodes should be returned. Optional (defaults to True).
        :return: Iterable of nodes that matched the location query.
        """
        yield from self.search_nodes(_node_intersects(loc), leaves)

    def search(self,
               node_condition: Optional[Callable[[RTreeNode[T]], bool]],
               entry_condition: Optional[Callable[[RTreeEntry[T]], bool]] = None) -> Iterable[RTreeEntry[T]]:
        """
        Traverses the tree, returning leaf entries that match a condition. This method optionally accepts both a node
        condition and an entry condition. The node condition is evaluated at each level and eliminates entire subtrees.
        In order for a leaf entry to be returned, all parent node conditions must pass. The entry condition is evaluated
        only at the leaf level. Both conditions are optional, and if neither is passed in, all leaf entries are
        returned.
        :param node_condition: Condition to evaluate for each node at every level. If the condition returns False, the
            subtree is eliminated and will not be traversed. Optional (if not passed in, all nodes are visited).
        :param entry_condition: Condition to evaluate for leaf entries. Optional (if not passed in, all leaf entries
            whose parent nodes passed the node_condition will be returned).
        :return: Iterable of matching leaf entries
        """
        for leaf in self.search_nodes(node_condition):
            for e in leaf.entries:
                if entry_condition is None or entry_condition(e):
                    yield e

    def search_nodes(self, condition: Callable[[RTreeNode[T]], bool], leaves=True) -> Iterable[RTreeNode[T]]:
        """
        Traverses the tree, returning nodes that match a condition. By default, this method returns only leaf nodes, but
        intermediate-level nodes can also be returned by passing leaves=False. The condition is evaluated for each node
        at every level of the tree, and if it returns False, the entire subtree is eliminated.
        :param condition: Condition to evaluate for each node at every level. If the condition returns False, the
            subtree is eliminated and will not be traversed.
        :param leaves: If True, only leaf-level nodes are returned. Otherwise, root and intermediate-level nodes are
            also returned. Optional (defaults to True).
        :return: Iterable of matching nodes
        """
        fn = _yield_if_leaf if leaves else _yield_node
        yield from self.traverse(fn, condition)

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

    def traverse(self, fn: Callable[[RTreeNode[T]], Iterable[TResult]],
                 condition: Optional[Callable[[RTreeNode[T]], bool]] = None) -> Iterable[TResult]:
        """
        Traverses the nodes of the R-Tree in depth-first order, calling the given function on each node. For a
        level-order traversal (breadth-first), use traverse_level_order instead. A condition function may optionally be
        passed to filter which nodes get traversed. If condition returns False, then neither the node nor any of its
        descendants will be traversed.
        :param fn: Function to execute on each node. The function should accept the node as its only parameter and
            should yield its result.
        :param condition: Optional condition function to evaluate on each node. If condition returns False, then neither
            the node nor any of its descendants will be traversed. If not passed in, all nodes will be traversed.
        """
        yield from self.traverse_node(self.root, fn, condition)

    def traverse_node(self, node: RTreeNode[T], fn: Callable[[RTreeNode[T]], Iterable[TResult]],
                      condition: Optional[Callable[[RTreeNode[T]], bool]]) -> Iterable[TResult]:
        """
        Traverses the tree starting from a given node in depth-first order, calling the given function on each node.
        A condition function may optionally be passed to filter which nodes get traversed. If condition returns False,
        then neither the node nor any of its descendants will be traversed.
        :param node: Starting node
        :param fn: Function to execute on each node. The function should accept the node as its only parameter and
            should yield its result.
        :param condition: Optional condition function to evaluate on each node. If condition returns False, then neither
            the node nor any of its descendants will be traversed. If not passed in, all nodes will be traversed.
        """
        if condition is not None and not condition(node):
            return
        yield from fn(node)
        if not node.is_leaf:
            for entry in node.entries:
                yield from self.traverse_node(entry.child, fn, condition)

    def traverse_level_order(self, fn: Callable[[RTreeNode[T], int], Iterable[TResult]],
                             condition: Optional[Callable[[RTreeNode[T]], bool]] = None) -> Iterable[TResult]:
        """
        Traverses the nodes of the R-Tree in level-order (breadth first), calling the given function on each node. For a
        depth-first traversal, use the traverse method instead. A condition function may optionally be passed to filter
        which nodes get traversed. If condition returns False, then neither the node nor any of its descendants will be
        traversed.
        :param fn: Function to execute on each node. This function should accept the node, and optionally the current
            level (with 0 corresponding to the root level) as parameters. The function should yield its result.
        :param condition: Optional condition function to evaluate on each node. The condition function should accept a
            node and a level parameter. If condition returns False, then neither the node nor any of its descendants
            will be traversed. If not passed in, all nodes will be traversed.
        """
        stack = [(self.root, 0)]
        while stack:
            node, level = stack[0]
            stack = stack[1:]
            if condition is None or condition(node, level):
                yield from fn(node, level)
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
        list(self.traverse_level_order(fn))
        return levels

    def get_nodes(self) -> Iterable[RTreeNode[T]]:
        """Returns an iterable of all nodes in the R-Tree (including intermediate and leaf nodes)"""
        return self._get_nodes(self.root)

    def _get_nodes(self, node: RTreeNode[T]) -> Iterable[RTreeNode[T]]:
        yield node
        if not node.is_leaf:
            for entry in node.entries:
                yield from self._get_nodes(entry.child)

    def get_leaves(self) -> Iterable[RTreeNode[T]]:
        """
        Iterates leaf nodes in the R-Tree. Note that R-Tree nodes are simply containers for child entries,
        which contain the actual data. If you want to get the actual data elements, you probably want to use
        get_leaf_entries instead.
        """
        return self.traverse_level_order(_yield_if_leaf_with_lvl_param)

    def get_leaf_entries(self) -> Iterable[RTreeEntry[T]]:
        """Iterates leaf entries in the R-Tree which contain the data."""
        for leaf in self.get_leaves():
            for entry in leaf.entries:
                yield entry


def _add_node_to_level(levels: List[List[RTreeNode[T]]], node: RTreeNode[T], level: int) -> Iterable[None]:
    if level >= len(levels):
        nodelist = []
        levels.append(nodelist)
    else:
        nodelist = levels[level]
    nodelist.append(node)
    yield


def _yield_node(node: RTreeNode[T]) -> Iterable[RTreeNode[T]]:
    yield node


def _yield_if_leaf(node: RTreeNode[T]) -> Iterable[RTreeNode[T]]:
    if node.is_leaf:
        yield node


def _yield_if_leaf_with_lvl_param(node: RTreeNode[T], _) -> Iterable[RTreeNode[T]]:
    if node.is_leaf:
        yield node


def _node_intersects(loc: Location) -> Callable[[RTreeNode[T]], bool]:
    loc_intersects = get_loc_intersection_fn(loc)
    return lambda node: loc_intersects(node.get_bounding_rect())
