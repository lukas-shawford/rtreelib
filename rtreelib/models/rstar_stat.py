from typing import List, Dict
from .axis import Axis
from .dimension import Dimension
from .entry_distribution import EntryDistribution
from ..rtree import EntryDivision


class RStarStat:
    """
    Class used for caching metrics as part of the R*-Tree split algorithm. These metrics are primarily the list of
    possible entry distributions along each axis ('x' or 'y') and dimension ('min' or 'max'), which are required by
    multiple steps of the split algorithm. In particular, the algorithm first requires selecting the optimum split axis
    (based on minimum total perimeter of all possible distributions along that axis), and then the optimum split index
    of all possible distributions along the optimum axis (based on minimum overlap). To avoid having to recompute the
    list of possible distributions, this class is used to cache them so they can be calculated once, and then used for
    both steps. This class also provides some helper methods for getting the total perimeter and unique distributions
    along a given axis.
    """

    def __init__(self):
        self.stat: Dict[Axis, Dict[Dimension, List[EntryDistribution]]] = {
            'x': {
                'min': [],
                'max': []
            },
            'y': {
                'min': [],
                'max': []
            }
        }
        self.unique_distributions: List[EntryDistribution] = []

    def add_distribution(self, axis: Axis, dimension: Dimension, division: EntryDivision):
        """
        Adds a distribution of entries for the given axis and dimension.
        :param axis: Axis ('x' or 'y')
        :param dimension: Dimension ('min' or 'max')
        :param division: Entry division
        """
        distribution = next((d for d in self.unique_distributions if d.is_division_equivalent(division)), None)
        if distribution is None:
            distribution = EntryDistribution(division)
            self.unique_distributions.append(distribution)
        self.stat[axis][dimension].append(distribution)

    def get_axis_perimeter(self, axis: Axis):
        """
        Returns the total overall perimeter of all distributions along the given axis (sorted by both min and max).
        :param axis: Axis ('x' or 'y')
        :return: Total overall perimeter for all distributions along the axis
        """
        distributions_min = self.stat[axis]['min']
        distributions_max = self.stat[axis]['max']
        return sum([d.perimeter for d in (distributions_min + distributions_max)])

    def get_axis_unique_distributions(self, axis: Axis) -> List[EntryDistribution]:
        """
        Returns a list of all unique entry distributions for a given axis
        :param axis: Axis ('x' or 'y')
        :return: List of unique entry distributions for the given axis
        """
        # Use dict.fromkeys() to preserve order. Though order is not technically relevant, it helps to keep the
        # split algorithm deterministic (and reduces flakiness in unit tests).
        distributions = self.stat[axis]['min'] + self.stat[axis]['max']
        return list(dict.fromkeys(distributions).keys())
