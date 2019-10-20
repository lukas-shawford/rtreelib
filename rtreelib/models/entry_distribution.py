from typing import Tuple
from .rect import Rect, union_all
from ..rtree import EntryDivision


class EntryDistribution:
    """
    Represents a distribution of entries into two groups, where the order of entries in each group is not relevant.
    This class is similar to the EntryDivision type alias, but contains additional helper methods for working with
    the distribution (e.g., getting bounding rectangles for each group), as well as equality and hash operators so
    the list of distributions can be used as part of a set (as required by RStarStat).
    """

    def __init__(self, division: EntryDivision):
        """
        Creates an RStarDistribution from an EntryDivision.
        :param division: Entry division. Note that an EntryDivision is nothing more than a type alias for a tuple
            containing two lists of entries.
        """
        self.division = division
        self.set1 = set(division[0])
        self.set2 = set(division[1])
        r1 = union_all([e.rect for e in division[0]])
        r2 = union_all([e.rect for e in division[1]])
        self.overlap = r1.get_intersection_area(r2)
        self.perimeter = r1.perimeter() + r2.perimeter()

    def is_division_equivalent(self, division: EntryDivision) -> bool:
        """
        Returns True if the given entry division may be considered equivalent (i.e., its two groups contain the same
        entries, independent of the order of both the groups themselves, as well as the entries in each group).
        :param division: Entry division
        :return: True if the entry division may be considered equivalent to this distribution
        """
        set1 = set(division[0])
        set2 = set(division[1])
        return (self.set1 == set1 and self.set2 == set2) or (self.set1 == set2 and self.set2 == set1)

    def get_rects(self) -> Tuple[Rect, Rect]:
        """Returns the two rectangles corresponding to the bounding boxes of each group in the distribution."""
        r1 = union_all([e.rect for e in self.division[0]])
        r2 = union_all([e.rect for e in self.division[1]])
        return r1, r2

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.set1 == other.set1 and self.set2 == other.set2) \
                   or (self.set1 == other.set2 and self.set2 == other.set1)
        return False

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(frozenset([frozenset(self.set1), frozenset(self.set2)]))

    def __repr__(self):
        return f'RStarDistribution({[e.data for e in self.set1]}, {[e.data for e in self.set2]})'
