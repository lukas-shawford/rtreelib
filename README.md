# rtreelib

Pluggable R-tree implementation in pure Python.

## Overview

Since the original R-tree data structure has been initially proposed in 1984, there have been
many variations introduced over the years optimized for various use cases [1]. However, there
is no easy way to compare how these implementations behave on real data.

The aim of this library is to provide a "pluggable" R-tree implementation that allows swapping
out the various strategies for insertion, node deletion, and other behaviors so that their
impact can be easily compared. Several of the more common R-tree variations are also provided
as ready-built implementations.

In addition to the various R-tree implementations, this library also provides utilities for
inspecting the R-tree structure (including intermediate non-leaf nodes), creating diagrams,
benchmarking, and exporting the nodes and entries to PostGIS.

This library does not aim to be a production-ready R-tree implementation. Though best efforts
have been made to ensure that it works, use it at your own risk. The intended use is more
academic - as such, this library prioritizes issues like readability, extensibility, and the
ability to examine the inner structure of the R-tree (rather than things like performance
or breadth of features).

## Status

This library is currently in early development. At this time, only the original Guttman
strategy is implemented (insertion only, no deletion), though the framework for swapping
out the strategies is in place. Note that as additional strategies are implemented, it is
anticipated that this framework will need to be extended, resulting in breaking changes.

Contributions for implementing additional strategies are welcome. See the section on
**Extending** below.

There is existing functionality for creating diagrams (explained below), and the ability to
export the R-Tree structure to PostGIS is also in the works.

## Setup

This package is available on PyPI and can be installed using pip:

```
pip install rtreelib
```

This package requires Python 3.6+.

## Usage

To instantiate the default implementation and insert an entry:

```python
from rtreelib import RTree, Rect

t = RTree()
t.insert('foo', Rect(0, 0, 5, 5))
```

The first parameter to the `insert` method represents the data, and can be of any data type
(though you will want to stick to strings, numbers, and other basic data types that can be
easily and succintly represented as a string if you want to create diagrams). The second
parameter represents the minimum bounding rectangle (MBR) of the associated data element.

The default implementation uses Guttman's original strategies for insertion, node splitting,
and deletion, as outlined in his paper from 1984 [2]. However, the behavior can be customized
by either instantiating or inheriting from `RTreeBase` and providing your own implementations
for these behaviors. (Eventually this library will also ship with several ready-made
implementations.) See the section on **Extending** below.

## Creating R-tree Diagrams

This library provides a set of utility functions that can be used to create diagrams of the
entire R-tree structure, including the root and all intermediate and leaf level nodes and
entries.

These features are optional, and the required dependencies are *not* automatically installed
when installing this library. Therefore, you must install them manually. This includes the
following Python dependencies which can be installed using pip:

```
pip install matplotlib pydot tqdm
```

This also includes the following system-level dependencies:

* TkInter
* Graphviz

On Ubuntu, these can be installed using:

```
sudo apt install python3-tk graphviz
```

Once the above dependencies are installed, you can create an R-tree diagram as follows:

```python
from rtreelib import RTree, Rect
from rtreelib.util.diagram import create_rtree_diagram


# Create an RTree instance with some sample data
t = RTree(max_entries=4)
t.insert('a', Rect(0, 0, 3, 3))
t.insert('b', Rect(2, 2, 4, 4))
t.insert('c', Rect(1, 1, 2, 4))
t.insert('d', Rect(8, 8, 10, 10))
t.insert('e', Rect(7, 7, 9, 9))

# Create a diagram of the R-tree structure
create_rtree_diagram(t)
```

This creates a diagram like the following:

![R-tree Diagram](https://github.com/sergkr/rtreelib/blob/master/doc/screenshots/rtree_diagram.png "R-tree Diagram")

The diagram is created in a temp directory as a PostScript file, and the default viewer
is automatically launched for convenience. Each box in the main diagram represents a node
(except at the leaf level, where it represents the leaf entry), and contains a plot that
depicts all of the data spatially. The bounding boxes of each node are represented using
tan rectangles with a dashed outline. The bounding box corresponding to the current node
is highlighted in pink.

The bounding boxes for the original data entries themselves are depicted in blue, and are
labeled using the value that was passed in to `insert`. At the leaf level, the corresponding
data element is highlighted in pink.

The entries contained in each node are depicted along the bottom of the node's box, and
point to either a child node (for non-leaf nodes), or to the data entries (for leaf nodes).

As can be seen in the above screenshot, the diagram depicts the entire tree structure, which
can be quite large depending on the number of nodes and entries. It may also take a while to
generate, since it launches matplotlib to plot the data spatially for each node and entry, and
then graphviz to generate the overall diagram. Given the size and execution time required to
generate these diagrams, it's only practical for R-trees containing a relatively small
amount of data (e.g., no more than about a dozen total entries). To analyze the resulting
R-tree structure when working with a large amount of data, it is recommended to export the
data to PostGIS and use a viewer like QGIS (as explained in the following section).

## Exporting to PostGIS

(This feature is still in development.)

## Extending

As noted above, the purpose of this library is to provide a pluggable R-tree implementation
where the various behaviors can be swapped out and customized to allow comparison. To that
end, this library provides a framework for achieving this.

As an example, the [`RTreeGuttman`](https://github.com/sergkr/rtreelib/blob/master/rtreelib/strategies/guttman.py)
class (aliased as `RTree`) simply inherits from `RTreeBase`, providing an implementation
for the `choose_leaf`, `adjust_tree`, and `split_node` behaviors as follows:

```python
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
```

Each behavior should be a function that implements a specific signature and performs a given
task. Here are the behaviors that are currently required to be specified:

* **`choose_leaf`**: Strategy used for choosing a leaf node when inserting a new entry.
  * Signature: `(tree: RTreeBase[T], entry: RTreeEntry[T]) → RTreeNode[T]`
  * Arguments:
    * `tree: RTreeBase[T]`: R-tree instance.
    * `entry: RTreeEntry[T]`: Entry being inserted.
  * Returns: `RTreeNode[T]`
    * This function should return the leaf node where the new entry should be inserted. This
    node may or may not have the capacity for the new entry. If the insertion of the new node
    results in the node overflowing, it will be split according to the strategy defined by
    `split_node`.
* **`adjust_tree`**: Strategy used for balancing the tree, including propagating node splits,
updating bounding boxes on all nodes and entries as necessary, and growing the tree by
creating a new root if necessary. This strategy is executed after inserting or deleting an
entry.
  * Signature: `(tree: RTreeBase[T], node: RTreeNode[T], split_node: RTreeNode[T]) → None`
  * Arguments:
    * `tree: RTreeBase[T]`: R-tree instance.
    * `node: RTreeNode[T]`: Node where a newly-inserted entry has just been added.
    * `split_node: RTreeNode[T]`: If the insertion of a new entry has caused the node to
    split, this is the newly-created split node. Otherwise, this will be `None`.
  * Returns: `None`
* **`split_node`**: Strategy used for splitting a node that contains more than the maximum
number of entries. This function should break up the node's entries into two groups,
assigning one of the groups to be the entries of the original node, and the other to a
newly-created neighbor node (which this function should return).
  * Signature: `(tree: RTreeBase[T], node: RTreeNode[T]) → RTreeNode[T]`
  * Arguments:
    * `tree: RTreeBase[T]`: R-tree instance.
    * `node: RTreeNode[T]`: Overflowing node that needs to be split.
  * Returns: `RTreeNode[T]`
    * This function should return the newly-created split node whose entries are a subset
    of the original node's entries.

## References

[1]: Nanopoulos, Alexandros & Papadopoulos, Apostolos (2003):
["R-Trees Have Grown Everywhere"](https://pdfs.semanticscholar.org/4e07/e800fe71505fbad686b08334abb49d41fcda.pdf)

[2]:  Guttman, A. (1984):
["R-trees: a Dynamic Index Structure for Spatial Searching"](http://www-db.deis.unibo.it/courses/SI-LS/papers/Gut84.pdf)
(PDF), *Proceedings of the 1984 ACM SIGMOD international conference on Management of data – SIGMOD
'84.* p. 47.
