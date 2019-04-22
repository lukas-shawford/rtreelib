"""
This module defines strategies and helper functions that are shared by more than one R-tree variant.
"""

import math
from typing import TypeVar, List
from ..rtree import RTreeEntry, EPSILON
from ..rect import Rect

T = TypeVar('T')


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
