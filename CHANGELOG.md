# Changelog

## [0.2.0] - 2020-05-02

### Added
- Core: Added methods for querying R-tree nodes and entries by location (`query`
and `query_nodes`), as well as by an arbitrary condition (`search` and
`search_nodes`).
- Core: Added `traverse_node` to allow traversing a subtree beginning at a given
node.
- Core: Added `Rect.intersects` (returns a `bool` if a given rectangle intersects
another) and `Rect.intersection` (returns a `Rect` representing the intersection
region of two rectangles, or `None` if the rectangles do not intersect).

### Changed
- Core: `RTreeBase.traverse` and `RTreeBase.traverse_level_order` now accept an
optional `condition` function that gets evaluated at each node. This can be used
to eliminate entire subtrees from being traversed.
- Core: `RTreeBase.traverse` and `RTreeBase.traverse_level_order` now `yield` the
result of the passed function, and `traverse` and `traverse_level_order` now return
an iterable instead of `None`. This allows one to start consuming the results while
still traversing the tree.

## [0.1.0] - 2020-03-17

### Added
- Core: Initial implementation of R*-Tree
- Core: Provide additional exports of base strategies to aid custom implementations
- Diagram: Added support for PNG (which is now the default), in addition to PostScript
- Diagram: Launching viewer is now optional (will launch by default, but if
`open_diagram` is `False`, the viewer will not be launched)
- Diagram: Add ability to pass keyword arguments to pydot
- PostGIS: Save python object ids when exporting R-tree nodes and entries to PostGIS

### Changed
- Core: Insert strategy is now pluggable (and required for custom R-tree implementations)
- Diagram: Diagram utility now outputs to PNG by default (instead of PostScript)
- PostGIS: Restart identity when clearing R-tree tables in PostGIS

## [0.0.3] - 2020-03-01

### Fixed
- Fix flaw in Guttman least enlargement implementation in a tie scenario
- Fix flaw with adjust_tree strategy in Guttman implementation

## [0.0.2] - 2019-04-14

### Added
- Added ability to export R-tree to PostGIS

## [0.0.1] - 2019-04-13

Initial release

### Added
- Guttman implementation (with framework for alternative implementations)
- Diagram creation
