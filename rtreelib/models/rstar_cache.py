from typing import List, TypeVar, Optional, Dict
from ..rtree import RTreeNode

T = TypeVar('T')


class RStarCache:
    """Helper class used to cache information during an insert operation in an R* tree."""
    def __init__(self):
        self.levels: Optional[List[List[RTreeNode[T]]]] = None
        self.reinsert: Dict[int, bool] = dict()
