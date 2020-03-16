from typing import List, TypeVar, Optional, Dict
from ..rtree import RTreeNode

T = TypeVar('T')


class RStarCache:
    """Helper class used to cache information during an insert operation in an R* tree."""
    def __init__(self):
        # List of all nodes on every level of the tree. Storing this is memory intensive, but it only gets populated in
        # case a forced reinsert occurs. In case of a forced reinsert, an entry can get reinserted at any node in the
        # same level (even if it's in a different subtree than the one it's currently in). Getting the list of all nodes
        # at a given level requires us to do a level-traversal of the entire tree anyway, and having the list of nodes
        # at higher levels may be necessary if propagation of node splits causes further reinserts at higher levels in
        # the tree.
        # TODO: Candidate for optimization (consider adding this cache to RTreeBase and keeping it updated during
        #  inserts/deletes/updates, instead of having to do a full tree traversal to construct it from scratch whenever
        #  we have an overflow).
        self.levels: Optional[List[List[RTreeNode[T]]]] = None
        # Dictionary to keep track of which levels of the tree a forced reinsert has occurred already. During a forced
        # reinsert, a subset of the entries from an overflowing node may get inserted into a different node at the same
        # level, which could cause that node to also overflow. In that scenario, we must avoid triggering an additional
        # forced reinsert at the same level, and instead perform a regular split. (This split may cause the parent to
        # overflow, which can trigger a forced reinsert at the higher level, but again, only once at each level.)
        self.reinsert: Dict[int, bool] = dict()
