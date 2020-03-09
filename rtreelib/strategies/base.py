"""
This module defines strategies and helper functions that are shared by more than one R-tree variant.
"""

import math
from typing import TypeVar, List
from ..rtree import RTreeBase, RTreeEntry, RTreeNode, EPSILON
from rtreelib.models import Rect, union_all


T = TypeVar('T')


def insert(tree: RTreeBase[T], data: T, rect: Rect) -> RTreeEntry[T]:
    """
    Strategy for inserting a new entry into the tree. This makes use of the choose_leaf strategy to find an
    appropriate leaf node where the new entry should be inserted. If the node is overflowing after inserting the entry,
    then overflow_strategy is invoked (either to split the node in case of Guttman, or do a combination of forced
    reinsert and/or split in the case of R*).
    :param tree: R-tree instance
    :param data: Entry data
    :param rect: Bounding rectangle
    :return: RTreeEntry instance for the newly-inserted entry.
    """
    entry = RTreeEntry(rect, data=data)
    node = tree.choose_leaf(tree, entry)
    node.entries.append(entry)
    split_node = None
    if len(node.entries) > tree.max_entries:
        split_node = tree.overflow_strategy(tree, node)
    tree.adjust_tree(tree, node, split_node)
    return entry


def least_area_enlargement(entries: List[RTreeEntry[T]], rect: Rect) -> RTreeEntry[T]:
    """
    Selects a child entry that requires least area enlargement for inserting an entry with the given bounding box. This
    is used as the sole criterion for choosing a leaf node in the original Guttman implementation of the R-tree, and is
    also used in the R*-tree implementation for the level above the leaf nodes (for higher levels, R*-tree uses least
    overlap enlargement instead of least area enlargement).
    """
    areas = [child.rect.area() for child in entries]
    enlargements = [rect.union(child.rect).area() - areas[i] for i, child in enumerate(entries)]
    min_enlargement = min(enlargements)
    indices = [i for i, v in enumerate(enlargements) if math.isclose(v, min_enlargement, rel_tol=EPSILON)]
    # If a single entry is a clear winner, choose that entry. Otherwise, if there are multiple entries having the
    # same enlargement, choose the entry having the smallest area as a tie-breaker.
    if len(indices) == 1:
        return entries[indices[0]]
    else:
        min_area = min([areas[i] for i in indices])
        i = areas.index(min_area)
        return entries[i]


def adjust_tree_strategy(tree: RTreeBase[T], node: RTreeNode[T], split_node: RTreeNode[T] = None) -> None:
    """
    Ascend from a leaf node to the root, adjusting covering rectangles and propagating node splits as necessary.
    """
    while not node.is_root:
        parent = node.parent
        node.parent_entry.rect = union_all([entry.rect for entry in node.entries])
        if split_node is not None:
            rect = union_all([e.rect for e in split_node.entries])
            entry = RTreeEntry(rect, child=split_node)
            parent.entries.append(entry)
            if len(parent.entries) > tree.max_entries:
                split_node = tree.overflow_strategy(tree, parent)
            else:
                split_node = None
        node = parent
    if split_node is not None:
        tree.grow_tree([node, split_node])
