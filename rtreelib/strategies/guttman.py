"""
Implementation of the Guttman R-Tree strategies described in this paper:
http://www-db.deis.unibo.it/courses/SI-LS/papers/Gut84.pdf

This implementation is used as the default for this library.
"""

import math
import itertools
from typing import List, TypeVar
from ..rtree import RTreeBase, RTreeEntry, RTreeNode, DEFAULT_MAX_ENTRIES
from ..rect import Rect, union_all

T = TypeVar('T')


def least_enlargement(tree: RTreeBase[T], entry: RTreeEntry[T]) -> RTreeNode[T]:
    """
    Select a leaf node in which to place a new index entry. This strategy always inserts into the subtree that requires
    least enlargement of its bounding box.
    """
    node = tree.root
    while not node.is_leaf:
        areas = [child.rect.area() for child in node.entries]
        enlargements = [entry.rect.union(child.rect).area() - areas[i] for i, child in enumerate(node.entries)]
        min_enlargement = min(enlargements)
        indices = [i for i, v in enumerate(enlargements) if math.isclose(v, min_enlargement, rel_tol=1e-5)]
        # If a single entry is a clear winner, choose that entry. Otherwise, if there are multiple entries having the
        # same enlargement, choose the entry having the smallest area as a tie-breaker.
        if len(indices) == 1:
            child_entry = node.entries[indices[0]]
        else:
            min_area = min(areas)
            i = areas.index(min_area)
            child_entry = node.entries[i]
        node = child_entry.child
    return node


def adjust_tree_strategy(tree: RTreeBase[T], node: RTreeNode[T], split_node: RTreeNode[T] = None) -> None:
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
        tree.grow_tree([node, split_node])


def quadratic_split(tree: RTreeBase[T], node: RTreeNode[T]) -> RTreeNode[T]:
    """
    Split an overflowing node. This algorithm attempts to find a small-area split, but is not guaranteed to
    find one with the smallest area possible. It's a good tradeoff between runtime efficiency and optimal area.
    Pages in this tree tend to overlap a lot, but the bounding rectangles are generally small, which makes for
    fast lookup.

    From the original paper:

    "The division should be done in a way that makes it as unlikely as possible that both new nodes will need to
    be examined on subsequent searches. Since the decision whether to visit a node depends on whether its covering
    rectangle overlaps the search area, the total area of the two covering rectangles after a split should be
    minimized."
    """
    entries = node.entries[:]
    seed1, seed2 = _pick_seeds(entries)
    entries.remove(seed1)
    entries.remove(seed2)
    group1, group2 = ([seed1], [seed2])
    rect1, rect2 = (seed1.rect, seed2.rect)
    num_entries = len(entries)
    while num_entries > 0:
        # If one group has so few entries that all the rest must be assigned to it in order for it to meet the
        # min_entries requirement, assign them and stop. (If both groups are underfull, then proceed with the
        # algorithm to determine the best group to extend.)
        len1, len2 = (len(group1), len(group2))
        group1_underfull = len1 < tree.min_entries <= len1 + num_entries
        group2_underfull = len2 < tree.min_entries <= len2 + num_entries
        if group1_underfull and not group2_underfull:
            group1.extend(entries)
            break
        if group2_underfull and not group1_underfull:
            group2.extend(entries)
            break
        # Pick the next entry to assign
        area1, area2 = rect1.area(), rect2.area()
        entry = _pick_next(entries, rect1, area1, rect2, area2)
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


def _pick_seeds(entries: List[RTreeEntry[T]]) -> (RTreeEntry[T], RTreeEntry[T]):
    seeds = None
    max_wasted_area = None
    for e1, e2 in itertools.combinations(entries, 2):
        combined_rect = e1.rect.union(e2.rect)
        wasted_area = combined_rect.area() - e1.rect.area() - e2.rect.area()
        if max_wasted_area is None or wasted_area > max_wasted_area:
            max_wasted_area = wasted_area
            seeds = (e1, e2)
    return seeds


def _pick_next(remaining_entries: List[RTreeEntry[T]],
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


class RTreeGuttman(RTreeBase[T]):
    """R-Tree implementation that uses Guttman's strategies for insertion, splitting, and deletion."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES, min_entries: int = None):
        """
        Initializes the R-Tree using Guttman's strategies for insertion, splitting, and deletion.
        :param max_entries: Maximum number of entries per node.
        :param min_entries: Minimum number of entries per node. Defaults to ceil(max_entries/2).
        """
        super().__init__(choose_leaf=least_enlargement, adjust_tree=adjust_tree_strategy, split_node=quadratic_split,
                         max_entries=max_entries, min_entries=min_entries)
