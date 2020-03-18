# Changelog

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
