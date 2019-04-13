import math
import itertools
from functools import partial
from typing import TypeVar, Generic, List, Iterable, Callable, Optional
from .rect import Rect, union_all

T = TypeVar('T')


class RTreeEntry(Generic[T]):
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


class RTreeNode(Generic[T]):
    def __init__(self, tree: 'RTree[T]', is_leaf: bool, parent: 'RTreeNode[T]' = None,
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


def least_enlargement(tree: 'RTree[T]', entry: RTreeEntry[T]) -> RTreeNode[T]:
    node = tree.root
    while not node.is_leaf:
        areas = [child.rect.area() for child in node.entries]
        enlargements = [entry.rect.union(child.rect).area() - areas[i] for i, child in enumerate(node.entries)]
        min_enlargement = min(enlargements)
        indices = [i for i, v in enumerate(enlargements) if math.isclose(v, min_enlargement, rel_tol=1e-5)]
        if len(indices) == 1:
            child_entry = node.entries[indices[0]]
        else:
            # Choose the entry having the smallest area
            min_area = min(areas)
            i = areas.index(min_area)
            child_entry = node.entries[i]
        node = child_entry.child
    return node


def adjust_tree_strategy(tree: 'RTree[T]', node: RTreeNode[T], split_node: RTreeNode[T] = None) -> None:
    """
    Ascend from a leaf node to the root, adjusting covering rectangles and propagating node splits as necessary.
    """
    while not node.is_root:
        parent = node.parent
        node.parent_entry.rect = union_all([node.parent_entry.rect] + [entry.rect for entry in node.entries])
        if split_node is not None:
            rect = union_all([e.rect for e in split_node.entries])
            entry = RTreeEntry(rect, child=split_node)
            parent.entries.append(entry)
            if len(parent.entries) > tree.max_entries:
                split_node = tree.split_node(tree, parent)
            else:
                split_node = None
        node = parent
    if split_node is not None:
        tree.grow_tree(node, split_node)


def quadratic_split(tree: 'RTree[T]', node: RTreeNode[T]) -> RTreeNode[T]:
    """
    Guttman's quadratic split. This algorithm attempts to find a small-area split, but is not guaranteed to
    find one with the smallest area possible. It's a good tradeoff between runtime efficiency and optimal area.
    Pages in this tree tend to overlap a lot, but the bounding rectangles are generally small, which makes for
    fast lookup.
    """
    entries = node.entries[:]
    seed1, seed2 = pick_seeds(entries)
    entries.remove(seed1)
    entries.remove(seed2)
    group1, group2 = ([seed1], [seed2])
    rect1, rect2 = (seed1.rect, seed2.rect)
    num_entries = len(entries)
    while num_entries > 0:
        # If one group has so few entries that all the rest must be assigned to it in order for it to meet the
        # min_entries requirement, assign them and stop.
        len1, len2 = (len(group1), len(group2))
        if len1 < tree.min_entries <= len1 + num_entries:
            group1.extend(entries)
            break
        if len2 < tree.min_entries <= len2 + num_entries:
            group2.extend(entries)
            break
        # Pick the next entry to assign
        area1, area2 = rect1.area(), rect2.area()
        entry = pick_next(entries, rect1, area1, rect2, area2)
        # Add it to the group whose covering rectangle will have to be enlarged the least to accommodate it.
        # Resolve ties by adding the entry to the group with the smaller area, then to the one with fewer
        # entries, then to either.
        urect1, urect2 = rect1.union(entry.rect), rect2.union(entry.rect)
        enlargement1 = urect1.area() - area1
        enlargement2 = urect2.area() - area2
        if enlargement1 == enlargement2:
            if area1 == area2:
                group = group1 if len1 <= len2 else group2
            else:
                group = group1 if area1 < area2 else group2
        else:
            group = group1 if enlargement1 < enlargement2 else group2
        group.append(entry)
        # Update the winning group's covering rectangle
        if group is group1:
            rect1 = urect1
        else:
            rect2 = urect2
        # Update entries list
        entries.remove(entry)
        num_entries = len(entries)
    return tree.perform_node_split(node, group1, group2)


def pick_seeds(entries: List[RTreeEntry[T]]) -> (RTreeEntry[T], RTreeEntry[T]):
    seeds = None
    max_wasted_area = None
    for e1, e2 in itertools.combinations(entries, 2):
        combined_rect = e1.rect.union(e2.rect)
        wasted_area = combined_rect.area() - e1.rect.area() - e2.rect.area()
        if max_wasted_area is None or wasted_area > max_wasted_area:
            max_wasted_area = wasted_area
            seeds = (e1, e2)
    return seeds


def pick_next(remaining_entries: List[RTreeEntry[T]],
              group1_rect: Rect,
              group1_area: float,
              group2_rect: Rect,
              group2_area: float) -> RTreeEntry[T]:
    max_diff = None
    result = None
    for e in remaining_entries:
        d1 = group1_rect.union(e.rect).area() - group1_area
        d2 = group2_rect.union(e.rect).area() - group2_area
        diff = math.fabs(d1 - d2)
        if max_diff is None or diff > max_diff:
            max_diff = diff
            result = e
    return result


class RTree(Generic[T]):
    def __init__(
            self,
            max_entries: int = 8,
            choose_leaf: Callable[['RTree[T]', RTreeEntry[T]], RTreeNode[T]] = least_enlargement,
            adjust_tree: Callable[['RTree[T]', RTreeNode[T], RTreeNode[T]], None] = adjust_tree_strategy,
            split_node: Callable[['RTree[T]', RTreeNode[T]], RTreeNode[T]] = quadratic_split
    ):
        self.max_entries = max_entries
        self.min_entries = math.ceil(max_entries/2)
        self.choose_leaf = choose_leaf
        self.adjust_tree = adjust_tree
        self.split_node = split_node
        self.root = RTreeNode(self, True)

    def insert(self, data: T, rect: Rect) -> RTreeEntry[T]:
        entry = RTreeEntry(rect, data=data)
        node = self.choose_leaf(self, entry)
        node.entries.append(entry)
        split_node = None
        if len(node.entries) > self.max_entries:
            split_node = self.split_node(self, node)
        self.adjust_tree(self, node, split_node)
        return entry

    def perform_node_split(self, node: RTreeNode[T], group1: List[RTreeEntry[T]], group2: List[RTreeEntry[T]])\
            -> RTreeNode[T]:
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

    def grow_tree(self, node1: RTreeNode[T], node2: RTreeNode[T]):
        self.root = RTreeNode(self, False, entries=[
            RTreeEntry(node1.get_bounding_rect(), child=node1),
            RTreeEntry(node2.get_bounding_rect(), child=node2)
        ])
        node1.parent = node2.parent = self.root

    def traverse(self, fn: Callable[[RTreeNode[T]], None]) -> None:
        self._traverse(self.root, fn)

    def _traverse(self, node: RTreeNode[T], fn: Callable[[RTreeNode[T]], None]) -> None:
        fn(node)
        if not node.is_leaf:
            for entry in node.entries:
                self._traverse(entry.child, fn)

    def traverse_level_order(self, fn: Callable[[RTreeNode[T], int], None]) -> None:
        stack = [(self.root, 0)]
        while stack:
            node, level = stack[0]
            stack = stack[1:]
            fn(node, level)
            if not node.is_leaf:
                stack.extend([(entry.child, level + 1) for entry in node.entries])

    def get_levels(self) -> List[List[RTreeNode[T]]]:
        levels: List[List[RTreeNode[T]]] = []
        fn = partial(_add_node_to_level, levels)
        # noinspection PyTypeChecker
        self.traverse_level_order(fn)
        return levels

    def get_nodes(self) -> Iterable[RTreeNode[T]]:
        yield from self._get_nodes(self.root)

    def _get_nodes(self, node: RTreeNode[T]) -> Iterable[RTreeNode[T]]:
        yield node
        if not node.is_leaf:
            for entry in node.entries:
                yield from self._get_nodes(entry.child)

    def get_leaves(self) -> List[RTreeNode[T]]:
        leaves = []
        fn = partial(_append_if_leaf, leaves)
        # noinspection PyTypeChecker
        self.traverse_level_order(fn)
        return leaves

    def get_leaf_entries(self) -> Iterable[RTreeEntry[T]]:
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
