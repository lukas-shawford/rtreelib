"""
R*-Tree implementation, as described in this paper:
https://infolab.usc.edu/csci599/Fall2001/paper/rstar-tree.pdf
"""

import math
from collections import namedtuple
from typing import List, Tuple, TypeVar
from ..rtree import RTreeBase, RTreeEntry, RTreeNode, DEFAULT_MAX_ENTRIES, EPSILON
from ..rect import Rect, union_all
from .base import least_area_enlargement

T = TypeVar('T')
RStarAxisStats = namedtuple('RStarAxisStats', ['axis', 'sorted_entries_min', 'sorted_entries_max', 'divisions_min',
                                               'divisions_max'])


def rstar_choose_leaf(tree: RTreeBase[T], entry: RTreeEntry[T]) -> RTreeNode[T]:
    node = tree.root
    while not node.is_leaf:
        if _are_children_leaves(node):
            e = least_overlap_enlargement(node.entries, entry.rect)
        else:
            e = least_area_enlargement(node.entries, entry.rect)
        node = e.child
    return node


def _are_children_leaves(node: RTreeNode[T]) -> bool:
    for entry in node.entries:
        if entry.child is not None:
            if entry.child.is_leaf:
                return True
    return False


def least_overlap_enlargement(entries: List[RTreeEntry[T]], rect: Rect) -> RTreeEntry[T]:
    overlaps = [overlap(e.rect, [e2.rect for e2 in without(entries, e)]) for e in entries]
    overlap_enlargements = [overlap(e.rect.union(rect), [e2.rect for e2 in without(entries, e)]) - overlaps[i]
                            for i, e in enumerate(entries)]
    min_enlargement = min(overlap_enlargements)
    indices = [i for i, v in enumerate(overlap_enlargements) if math.isclose(v, min_enlargement, rel_tol=EPSILON)]
    # If a single entry is a clear winner, choose that entry.
    if len(indices) == 1:
        return entries[indices[0]]
    else:
        # If multiple entries have the same overlap enlargement, use least area enlargement strategy as a tie-breaker.
        entries = [entries[i] for i in indices]
        return least_area_enlargement(entries, rect)


def without(items: List[T], item: T) -> List[T]:
    """Returns all items in a list except the given item."""
    return [i for i in items if i != item]


def overlap(rect: Rect, rects: List[Rect]) -> float:
    """
    Returns the total overlap area of one rectangle with respect to the others. Any common areas where multiple
    rectanges intersect will be counted multiple times.
    """
    return sum([rect.get_intersection_area(r) for r in rects])


def choose_split_axis(entries: List[RTreeEntry[T]], min_entries: int, max_entries: int) -> RStarAxisStats:
    """
    Determines the axis perpendicular to which the entries should be split, based on the one with the smallest overall
    perimeter after determining all possible divisions of the entries that satisfy min_entries and max_entries.
    :param entries: List of entries
    :param min_entries: Minimum number of entries per node
    :param max_entries: Maximum number of entries per node
    :return: An object containing the best split axis ('x' or 'y') along with some associated properties of that split
        axis (e.g., sorted list of entries and possible divisions of entries along the axis), so as to avoid having
        to recompute these properties when calling choose_split_index.
    """
    winner = None
    min_perimeter = None
    xstat = _get_axis_stats('x', entries, min_entries, max_entries)
    ystat = _get_axis_stats('y', entries, min_entries, max_entries)
    for stat in [xstat, ystat]:
        for division in stat.divisions_min + stat.divisions_max:
            r1, r2 = get_division_rects(division)
            perimeter = r1.perimeter() + r2.perimeter()
            if min_perimeter is None or perimeter < min_perimeter:
                winner = stat
                min_perimeter = perimeter
    return winner


def _get_axis_stats(axis: str, entries: List[RTreeEntry[T]], min_entries: int, max_entries: int) -> RStarAxisStats:
    sorted_entries_min = sorted(entries, key=((lambda e: e.rect.min_x) if axis == 'x' else (lambda e: e.rect.min_y)))
    divisions_min = get_entry_divisions(sorted_entries_min, min_entries, max_entries)
    sorted_entries_max = sorted(entries, key=((lambda e: e.rect.max_x) if axis == 'x' else (lambda e: e.rect.max_y)))
    divisions_max = get_entry_divisions(sorted_entries_max, min_entries, max_entries)
    return RStarAxisStats(axis, sorted_entries_min, sorted_entries_max, divisions_min, divisions_max)


def get_entry_divisions(entries: List[RTreeEntry[T]], min_entries: int, max_entries: int) \
        -> List[Tuple[List[RTreeEntry[T]], List[RTreeEntry[T]]]]:
    """
    Returns a list of all possible divisions of a sorted list of entries into two groups (preserving order), where each
    group has at least min_entries number of entries.
    :param entries: List of entries, sorted by some criteria.
    :param min_entries: Minimum number of entries in each group.
    :param max_entries: Maximum number of entries in each group. It is assumed that the entries list contains one
        greater than the maximum number of entries (i.e., the entries list corresponds to a node that is now overflowing
        after the insertion of a new entry).
    :return: List of tuples representing the possible divisions.
    """
    m = min_entries
    return [(entries[:(m-1+k)], entries[(m-1+k):]) for k in range(1, max_entries - 2*m + 3)]


def get_division_rects(division: Tuple[List[RTreeEntry[T]], List[RTreeEntry[T]]]) -> Tuple[Rect, Rect]:
    """
    Returns the two rectangles corresponding to the bounding boxes of each group in a division of entries into two
    groups.
    :param division: A tuple representing a possible grouping of R-tree entries into two groups.
    :return: A tuple containing the two corresponding bounding boxes.
    """
    r1 = union_all([e.rect for e in division[0]])
    r2 = union_all([e.rect for e in division[1]])
    return r1, r2


def choose_split_index(divisions: List[Tuple[List[RTreeEntry[T]], List[RTreeEntry[T]]]]) -> int:
    """
    Chooses the best split index based on minimum overlap (or minimum area in case of tie).
    :param divisions: List of possible divisions of entries along the best split axis.
    :return: Index of the best division among the list of possible divisions.
    """
    division_rects = [get_division_rects(d) for d in divisions]
    division_overlaps = [r1.get_intersection_area(r2) for r1, r2 in division_rects]
    min_overlap = min(division_overlaps)
    indices = [i for i, v in enumerate(division_overlaps) if math.isclose(v, min_overlap, rel_tol=EPSILON)]
    # If a single index is a clear winner, choose that index.
    if len(indices) == 1:
        return indices[0]
    else:
        # Resolve ties by choosing the distribution with minimum area
        min_area = None
        split_index = None
        for i in indices:
            r1, r2 = division_rects[i]
            area = r1.area() + r2.area()
            if min_area is None or area < min_area:
                min_area = area
                split_index = i
        return split_index
