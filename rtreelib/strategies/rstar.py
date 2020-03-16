"""
R*-Tree implementation, as described in this paper:
https://infolab.usc.edu/csci599/Fall2001/paper/rstar-tree.pdf
"""

import math
from typing import List, TypeVar, Iterable, Callable, Any, Dict, Optional
from ..rtree import RTreeBase, RTreeEntry, RTreeNode, DEFAULT_MAX_ENTRIES, EPSILON, EntryDivision, EntryOrdering
from rtreelib.models import Rect, Axis, Dimension, EntryDistribution, RStarStat, RStarCache, union_all
from .base import insert, least_area_enlargement, adjust_tree_strategy

T = TypeVar('T')


# noinspection PyProtectedMember
def rstar_insert(tree: RTreeBase[T], data: T, rect: Rect) -> RTreeEntry[T]:
    """
    Strategy for inserting a new entry into the R*-tree. R* insert is identical to the Guttman insert, except for
    overflow treatment. In case of overflow, R* performs a forced reinsert of a subset of the entries as a method of
    balancing the tree.
    :param tree: R-tree instance
    :param data: Entry data
    :param rect: Bounding rectangle
    :return: RTreeEntry instance for the newly-inserted entry.
    """
    e = insert(tree, data, rect)
    tree._cache = None
    return e


# noinspection PyProtectedMember
def rstar_adjust_tree(tree: RTreeBase[T], node: RTreeNode[T], split_node: RTreeNode[T] = None) -> None:
    # Invalidate the cache if we have a split node, since the tree now has a different structure. The cache is
    # repopulated if necessary in _choose_subtree_reinsert if we have additional entries that still need to be
    # reinserted as part of this insert operation.
    # TODO: Candidate for optimization (modify the cache in place instead of blowing it all away)
    if tree._cache is not None and split_node is not None:
        tree._cache.levels = None
    # Invoke adjust_tree_strategy from base
    adjust_tree_strategy(tree, node, split_node)


# noinspection PyProtectedMember
def rstar_overflow(tree: RTreeBase[T], node: RTreeNode[T]) -> RTreeNode[T]:
    """
    R* overflow treatment. The outer method initializes a cache to store information about the tree's current state,
    including the current state of the nodes at every level of the tree, as well as a dictionary of which levels we
    have performed a force reinsert on.
    :param tree: R-tree instance
    :param node: Overflowing node
    :return: New node resulting from a split, or None
    """
    if not tree._cache:
        tree._cache = RStarCache()
    if not tree._cache.levels:
        tree._cache.levels = tree.get_levels()
    levels_from_leaf = _get_levels_from_leaf(tree._cache.levels, node)
    return _rstar_overflow(tree, node, levels_from_leaf)


def _get_levels_from_leaf(levels: List[List[RTreeNode[T]]], node: RTreeNode[T]) -> int:
    return len(levels) - next((i for i, level in enumerate(levels) if node in level)) - 1


# noinspection PyProtectedMember
def _rstar_overflow(tree: RTreeBase[T], node: RTreeNode[T], levels_from_leaf: int) -> Optional[RTreeNode[T]]:
    # If the level is not the root level and this is the first call of _rstar_overflow on the given level, then
    # perform a forced reinsert of a subset of the entries in the node. Otherwise, do a regular node split.
    if node.is_root or tree._cache.reinsert.get(levels_from_leaf, False):
        split_node = rstar_split(tree, node)
        tree.adjust_tree(tree, node, split_node)
    else:
        reinsert(tree, node, levels_from_leaf)
    return None


# noinspection PyProtectedMember
def reinsert(tree: RTreeBase[T], node: RTreeNode[T], levels_from_leaf: int):
    """
    Performs a forced reinsert on a subset of the entries in the given node.
    :param tree: R-tree instance
    :param node: Overflowing node
    :param levels_from_leaf: Level of the node in the tree (starting with the leaf level being 0). Forced reinsert is
        done at most once per level during an insert operation. The inverse level (with leaf level being 0, rather than
        the root level being 0) is used because a split can cause the tree to grow in the middle of the reinsert
        operation, which would cause the level (in the normal sense, with root being 0) to change, whereas
        levels_from_leaf would stay the same.
    """
    # Indicate that we have performed a forced reinsert at the current level. Forced reinsert is done at most once per
    # level during an insert operation.
    tree._cache.reinsert[levels_from_leaf] = True

    # Sort the entries in order of increasing distance from the node's centroid
    node_centroid = node.get_bounding_rect().centroid()
    sorted_entries = sorted(node.entries, key=lambda e: _dist(e.rect.centroid(), node_centroid))

    # Get the subset of entries to reinsert. Per the paper, reinserting the closest 30% yields the best performance.
    p = math.ceil(0.3 * len(sorted_entries))
    entries_to_reinsert = sorted_entries[:p]

    # Remove entries that will be reinserted from the node and adjust the node's bounding rectangle to
    # fit the remaining entries.
    node.entries = [e for e in node.entries if e not in entries_to_reinsert]
    node.parent_entry.rect = union_all([entry.rect for entry in node.entries])

    # Reinsert the entries at the same level in the tree.
    for e in entries_to_reinsert:
        _reinsert_entry(tree, e, levels_from_leaf)


def _dist(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2-x1)**2 + (y2-y1)**2)


# noinspection PyProtectedMember
def _reinsert_entry(tree: RTreeBase[T], entry: RTreeEntry[T], levels_from_leaf: int):
    node = _choose_subtree_reinsert(tree, entry.rect, levels_from_leaf)
    node.entries.append(entry)
    tree._fix_children(node)
    split_node = None
    if len(node.entries) > tree.max_entries:
        split_node = rstar_split(tree, node)
    tree.adjust_tree(tree, node, split_node)


# noinspection PyProtectedMember
def _choose_subtree_reinsert(tree: RTreeBase[T], rect: Rect, levels_from_leaf: int) -> RTreeNode[T]:
    """
    Helper method for choosing a subtree during the reinsert operation. While similar to rstar_choose_leaf, this
    method allows for an entry to be inserted at any node in an arbitrary level of the tree.
    :param rect: Bounding box of the entry being reinserted.
    :param levels_from_leaf: Level of the tree where the entry is being reinserted, with the leaf level being 0 and the
        root level being (depth-1).
    :return: Node where the entry should be reinserted.
    """
    if not tree._cache.levels:
        tree._cache.levels = tree.get_levels()
    is_leaf_level = levels_from_leaf == 0
    depth = len(tree._cache.levels)
    nodes = tree._cache.levels[depth - levels_from_leaf - 1]
    entries = [node.parent_entry for node in nodes]
    if is_leaf_level:
        e = least_overlap_enlargement(entries, rect)
    else:
        e = least_area_enlargement(entries, rect)
    return e.child


def rstar_choose_leaf(tree: RTreeBase[T], entry: RTreeEntry[T]) -> RTreeNode[T]:
    """
    Strategy used for choosing a leaf node when inserting a new entry. For choosing non-leaf nodes, the strategy is
    based on least area enlargement (same as the original Guttman implementation). For choosing leaf nodes, R*-tree uses
    minimum overlap enlargement instead.
    :param tree: R-Tree instance
    :param entry: Entry being inserted
    :return: Leaf node where the entry should be inserted. This node may or may not have the capacity for the new entry.
        If the insertion of the new node results in the node overflowing, it will be split according to the strategy
        defined by split_node.
    """
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
    """
    Least overlap enlargement strategy (used when inserting an entry into a leaf node).
    :param entries: Entries in the node where the insert is occurring
    :param rect: Bounding rectangle of the entry being inserted
    :return: Returns the entry from 'entries' whose bounding rectangle results in least overlap enlargement if it is
        expanded to accommodate 'rect'. In case of tie, this strategy falls back to least area enlargement.
    """
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
    rectangles intersect will be counted multiple times.
    """
    return sum([rect.get_intersection_area(r) for r in rects])


def get_rstar_stat(entries: List[RTreeEntry[T]], min_entries: int, max_entries: int) -> RStarStat:
    """
    Calculates metrics used by the split algorithm when splitting an overflowing node. Since these metrics are used
    in multiple steps, they are calculated here once and then cached. These metrics are primarily the list of possible
    divisions of entries along each axis ('x' and 'y'), as well as dimension ('min' and 'max'). The RStarStat helper
    class also provides methods for calculating the total perimeter value along each axis.
    :param entries: List of entries in the node being split
    :param min_entries: Minimum number of entries per node
    :param max_entries: Maximum number of entries per node
    :return: Cached statistics for this list of entries
    """
    sort_divisions: Dict[EntryOrdering, List[EntryDivision]] = {}
    stat = RStarStat()
    for axis in ['x', 'y']:
        for dimension in ['min', 'max']:
            sorted_entries = tuple(sorted(entries, key=_get_sort_key(axis, dimension)))
            divisions = sort_divisions.get(sorted_entries, None)
            if divisions is None:
                divisions = get_possible_divisions(sorted_entries, min_entries, max_entries)
                sort_divisions[sorted_entries] = divisions
            for division in divisions:
                stat.add_distribution(axis, dimension, division)
    return stat


def _get_sort_key(axis: Axis, dimension: Dimension) -> Callable[[RTreeEntry[T]], Any]:
    if axis == 'x' and dimension == 'min':
        return lambda e: e.rect.min_x
    if axis == 'x' and dimension == 'max':
        return lambda e: e.rect.max_x
    if axis == 'y' and dimension == 'min':
        return lambda e: e.rect.min_y
    if axis == 'y' and dimension == 'max':
        return lambda e: e.rect.max_y


def choose_split_axis(stat: RStarStat) -> Axis:
    """
    Determines the axis perpendicular to which the entries should be split, based on the one with the smallest overall
    perimeter after determining all possible divisions of the entries that satisfy min_entries and max_entries.
    :param stat: RStarStat instance (as returned by get_rstar_stat)
    :return: Best split axis ('x' or 'y')
    """
    perimeter_x = stat.get_axis_perimeter('x')
    perimeter_y = stat.get_axis_perimeter('y')
    return 'x' if perimeter_x <= perimeter_y else 'y'


def get_possible_divisions(entries: Iterable[RTreeEntry[T]], min_entries: int, max_entries: int) -> List[EntryDivision]:
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


def choose_split_index(distributions: List[EntryDistribution]) -> int:
    """
    Chooses the best split index based on minimum overlap (or minimum area in case of tie).
    :param distributions: List of possible distributions of entries along the best split axis.
    :return: Index of the best distribution among the list of possible distributions.
    """
    division_rects = [d.get_rects() for d in distributions]
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


def rstar_split(tree: RTreeBase[T], node: RTreeNode[T]) -> RTreeNode[T]:
    """
    Split an overflowing node. The R*-Tree implementation first determines the optimum split axis (minimizing overall
    perimeter), then chooses the best split index along the chosen axis (based on minimum overlap).
    :param tree: RTreeBase[T]: R-tree instance.
    :param node: RTreeNode[T]: Overflowing node that needs to be split.
    :return: Newly-created split node whose entries are a subset of the original node's entries.
    """
    stat = get_rstar_stat(node.entries, tree.min_entries, tree.max_entries)
    axis = choose_split_axis(stat)
    distributions = stat.get_axis_unique_distributions(axis)
    i = choose_split_index(distributions)
    distribution = distributions[i]
    d1 = list(distribution.set1)
    d2 = list(distribution.set2)
    return tree.perform_node_split(node, d1, d2)


class RStarTree(RTreeBase[T]):
    """R-tree implementation that uses R* strategies for insertion, splitting, and deletion."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES, min_entries: int = None):
        """
        Initializes the R-Tree using R* strategies for insertion, splitting, and deletion.
        :param max_entries: Maximum number of entries per node.
        :param min_entries: Minimum number of entries per node. Defaults to ceil(max_entries/2).
        """
        super().__init__(
            max_entries=max_entries,
            min_entries=min_entries,
            insert=rstar_insert,
            choose_leaf=rstar_choose_leaf,
            adjust_tree=rstar_adjust_tree,
            overflow_strategy=rstar_overflow
        )
