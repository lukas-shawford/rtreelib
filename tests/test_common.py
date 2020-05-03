from typing import Iterable
from unittest import TestCase
from unittest.mock import Mock
from rtreelib import Point, Rect, RTree, RTreeEntry, RTreeNode
from rtreelib.strategies.base import least_area_enlargement
from tests.util import create_simple_tree, create_complex_tree


# noinspection PyPep8Naming
class TestCommon(TestCase):
    """
    Common tests for basic R-Tree operations and common strategies. Note the default implementation uses the Guttman
    strategy, so there will be some duplication between the common tests and Guttman tests.
    """

    def test_least_area_enlargement(self):
        """
        Ensure the node whose bounding box needs least enlargement is chosen for a new entry in the case where there is
        a clear winner.
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 3, 3))
        b = RTreeEntry(data='b', rect=Rect(9, 9, 10, 10))
        rect = Rect(2, 2, 4, 4)

        # Act
        entry = least_area_enlargement([a, b], rect)

        # Assert
        self.assertEqual(a, entry)

    def test_least_area_enlargement_tie(self):
        """
        When two nodes need to be enlarged by the same amount, the strategy should pick the node having the smallest
        area as a tie-breaker.
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 4, 2))
        b = RTreeEntry(data='b', rect=Rect(5, 1, 7, 3))
        c = RTreeEntry(data='c', rect=Rect(0, 4, 1, 5))
        rect = Rect(4, 1, 5, 2)

        # Act
        entry = least_area_enlargement([a, b, c], rect)

        # Assert
        self.assertEqual(b, entry)

    def test_insert_creates_entry(self):
        """Basic test ensuring an insert creates an entry."""
        # Arrange
        t = RTree()

        # Act
        e = t.insert('foo', Rect(0, 0, 1, 1))

        # Assert
        self.assertEqual('foo', e.data)
        self.assertEqual(Rect(0, 0, 1, 1), e.rect)

    def test_multiple_inserts_without_split(self):
        """
        Ensure multiple inserts work (all original entries are returned) without a split (fewer entries than
        max_entries)
        """
        # Arrange
        t = RTree(max_entries=5)

        # Act
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))

        # Assert
        entries = list(t.get_leaf_entries())
        self.assertCountEqual(['a', 'b', 'c'], [entry.data for entry in entries])

    def test_bounding_rect_multiple_inserts_without_split(self):
        """
        Ensure root note bounding rect encompasses the bounding rect of all entries after multiple inserts (without
        forcing a split)
        """
        # Arrange
        t = RTree(max_entries=5)

        # Act
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))

        # Assert
        rect = t.root.get_bounding_rect()
        self.assertEqual(Rect(0, 0, 6, 6), rect)

    def test_multiple_inserts_with_split(self):
        """
        Ensure multiple inserts work (all original entries are returned) forcing a split (number of entries exceeds
        max_entries)
        """
        # Arrange
        t = create_simple_tree(self)

        # Act
        entries = list(t.get_leaf_entries())

        # Assert
        self.assertCountEqual(['a', 'b', 'c', 'd', 'e'], [entry.data for entry in entries])

    def test_bounding_rect_multiple_inserts_with_split(self):
        """
        Ensure root note bounding rect encompasses the bounding rect of all entries after multiple inserts (forcing a
        split)
        """
        # Arrange
        t = create_simple_tree(self)

        # Act
        rect = t.root.get_bounding_rect()

        # Assert
        self.assertEqual(Rect(0, 0, 10, 10), rect)

    def test_traverse(self):
        """Tests that a given function is called on every node of the tree when calling traverse"""
        # Arrange
        nodes = dict()
        t = create_simple_tree(self, nodes)
        R, L1, L2 = nodes['R'], nodes['L1'], nodes['L2']

        # Act
        result = t.traverse(_yield_node)

        # Assert
        self.assertEqual([R, L1, L2], list(result))

    def test_traverse_empty(self):
        """Test traversing an "empty" R-tree. An "empty" R-tree only has a root node."""
        # Arrange
        t = RTree()

        # Act
        result = list(t.traverse(_yield_node))

        # Assert
        self.assertEqual([t.root], result)

    def test_traverse_with_condition(self):
        """
        Tests traversing a tree with a condition function. Only nodes that pass the condition are traversed. If the
        condition returns False at the parent level, the child nodes should not be traversed.
        :return:
        """
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def condition(node: RTreeNode):
            return node.is_root or node.get_bounding_rect().max_x <= 10

        # Act
        result = t.traverse(_yield_node, condition)

        # Assert
        # Note node "L2" should not be present, even though it passed the condition, since its parent I2 did not.
        self.assertEqual([
            nodes['R'],       # Root
            nodes['I1'],      # Intermediate child 1
            nodes['L1'],      # Leaf child 1
            nodes['L2']       # Leaf child 2
        ], list(result))

    def test_traverse_level_order(self):
        """Tests that nodes are traversed in level-order when calling traverse_level_order"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def fn(n: RTreeNode, lvl: int):
            yield (lvl, n)

        # Act
        result = list(t.traverse_level_order(fn))

        # Assert
        # Root node should be visited first
        level, node = result[0]
        self.assertEqual(0, level)
        self.assertEqual(nodes['R'], node)
        # Intermediate child 1 should be visited next
        level, node = result[1]
        self.assertEqual(1, level)
        self.assertEqual(nodes['I1'], node)
        # Intermediate child 2 should be visited next
        level, node = result[2]
        self.assertEqual(1, level)
        self.assertEqual(nodes['I2'], node)
        # Leaf child 1 should be visited next
        level, node = result[3]
        self.assertEqual(2, level)
        self.assertEqual(nodes['L1'], node)
        # Leaf child 2 should be visited next
        level, node = result[4]
        self.assertEqual(2, level)
        self.assertEqual(nodes['L2'], node)
        # Leaf child 3 should be visited next
        level, node = result[5]
        self.assertEqual(2, level)
        self.assertEqual(nodes['L3'], node)
        # Leaf child 4 should be visited last
        level, node = result[6]
        self.assertEqual(2, level)
        self.assertEqual(nodes['L4'], node)
        # Ensure there are no more results
        self.assertEqual(7, len(result))

    def test_traverse_level_order_with_condition(self):
        """Tests traverse_level_order with a condition function."""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def fn(n: RTreeNode, lvl: int):
            yield (lvl, n)

        def condition(n: RTreeNode, lvl: int):
            mbr = n.get_bounding_rect()
            max_x = mbr.max_x
            max_y = mbr.max_y
            return lvl == 0 or max_x == 10 or max_y == 5

        # Act
        result = list(t.traverse_level_order(fn, condition))

        # Assert
        # Root node should be visited first
        level, node = result[0]
        self.assertEqual(0, level)
        self.assertEqual(nodes['R'], node)
        # Intermediate child 1 should be visited next
        level, node = result[1]
        self.assertEqual(1, level)
        self.assertEqual(nodes['I1'], node)
        # Intermediate child 2 should be visited next
        level, node = result[2]
        self.assertEqual(1, level)
        self.assertEqual(nodes['I2'], node)
        # Leaf child 2 should be visited next
        level, node = result[3]
        self.assertEqual(2, level)
        self.assertEqual(nodes['L2'], node)
        # Leaf child 3 should be visited next
        level, node = result[4]
        self.assertEqual(2, level)
        self.assertEqual(nodes['L3'], node)
        # Ensure there are no more results
        self.assertEqual(5, len(result))

    def test_traverse_level_order_empty(self):
        """Test traversing an "empty" R-tree in level-order. An "empty" R-tree only has a root node."""
        # Arrange
        t = RTree()

        def fn(node: RTreeNode, lvl: int):
            yield (lvl, node.get_bounding_rect())

        # Act
        result = list(t.traverse_level_order(fn))

        # Assert
        self.assertEqual(1, len(result))
        level, rect = result[0]
        self.assertEqual(0, level)
        self.assertIsNone(rect)

    def test_query_point_no_matches(self):
        """Tests query method with a Point location returning no matches."""
        # Arrange
        t = create_complex_tree(self)
        loc = Point(5, 8)

        # Act
        result = list(t.query(loc))

        # Assert
        self.assertEqual(0, len(result))

    def test_query_point_single_match(self):
        """Tests query method with a Point location returning a single match."""
        # Arrange
        t = create_complex_tree(self)
        loc = Point(8, 3)

        # Act
        result = list(t.query(loc))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual('h', result[0].data)

    def test_query_point_multiple_matches(self):
        """Tests query method with a Point location returning multiple matches."""
        # Arrange
        t = create_complex_tree(self)
        loc = Point(1.5, 1.5)

        # Act
        result = list(t.query(loc))

        # Assert
        self.assertCountEqual(['a', 'b'], [e.data for e in result])

    def test_query_point_tuple_single_match(self):
        """Tests query method with a point tuple location returning a single match."""
        # Arrange
        t = create_complex_tree(self)
        loc = (8, 3)

        # Act
        result = list(t.query(loc))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual('h', result[0].data)

    def test_query_point_list_multiple_matches(self):
        """Tests query method with a point location passed in as a list of 2 coordinates returning multiple matches."""
        # Arrange
        t = create_complex_tree(self)
        loc = [1.5, 5.5]

        # Act
        result = list(t.query(loc))

        # Assert
        self.assertCountEqual(['f', 'j'], [e.data for e in result])

    def test_query_point_on_border_matches(self):
        """Ensures that a point that is on the border (but not within) an entry MBR matches."""
        # Arrange
        t = create_complex_tree(self)
        loc = Point(4, 4)

        # Act
        result = list(t.query(loc))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual('c', result[0].data)

    def test_query_rect_no_matches(self):
        """Tests query method with a Rect location returning no matches."""
        # Arrange
        t = create_complex_tree(self)
        r = Rect(4, 5, 5, 7)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertEqual(0, len(result))

    def test_query_rect_overlap_single_match(self):
        """
        Tests query method with a Rect location returning a single match. Rectangle overlaps but is not equal to matched
        entry.
        """
        # Arrange
        t = create_complex_tree(self)
        r = Rect(4, 3, 6, 5)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual('c', result[0].data)

    def test_query_rect_overlap_multiple_matches(self):
        """
        Tests query method with a Rect location returning a multiple matches. Rectangle overlaps but is not equal to
        any of the matched entries.
        """
        # Arrange
        t = create_complex_tree(self)
        r = Rect(4, 3, 8, 5)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertCountEqual(['c', 'h'], [e.data for e in result])

    def test_query_rect_tuple_overlap_multiple_matches(self):
        """
        Tests query method with a Rect location passed in as a tuple of coordinates, returning a multiple matches.
        Rectangle overlaps but is not equal to any of the matched entries.
        """
        # Arrange
        t = create_complex_tree(self)
        r = (0, 6, 2, 8)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertCountEqual(['f', 'j'], [e.data for e in result])

    def test_query_rect_list_overlap_multiple_matches(self):
        """
        Tests query method with a Rect location passed in as a list of coordinates, returning a multiple matches.
        Rectangle overlaps but is not equal to any of the matched entries.
        """
        # Arrange
        t = create_complex_tree(self)
        r = [0.5, 6, 2, 7.5]

        # Act
        result = list(t.query(r))

        # Assert
        self.assertCountEqual(['f', 'j'], [e.data for e in result])

    def test_query_rect_contains_single_match(self):
        """
        Tests query method with a Rect location returning a single match. Rectangle entirely contains the MBR of matched
        entry.
        """
        # Arrange
        t = create_complex_tree(self)
        r = Rect(2, 2, 6, 5)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual('c', result[0].data)

    def test_query_rect_equals_single_match(self):
        """
        Tests query method with a Rect location returning a single match. Rectangle exactly matches the MBR of matched
        entry.
        """
        # Arrange
        t = create_complex_tree(self)
        r = (2, 2, 6, 4)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual('c', result[0].data)

    def test_query_rect_contains_multiple_matches(self):
        """
        Tests query method with a Rect location returning multiple matches. Rectangle wholly contains the MBRs of all
        matched entries.
        """
        # Arrange
        t = create_complex_tree(self)
        r = [5.5, 6, 12, 13.5]

        # Act
        result = list(t.query(r))

        # Assert
        self.assertCountEqual(['d', 'e'], [e.data for e in result])

    def test_query_adjacent_rect_does_not_match(self):
        """
        Ensures that a query for a rect that is adjacent to but does not intersect with an entry does not match.
        """
        # Arrange
        t = create_complex_tree(self)
        r = Rect(5, 0, 9, 2)

        # Act
        result = list(t.query(r))

        # Assert
        self.assertEqual(0, len(result))

    def test_query_root_mbr_returnes_all_entries(self):
        """
        Ensures that a query for a rect that matches the bounding rectangle of the root node returns all entries.
        """
        # Arrange
        t = create_complex_tree(self)

        # Act
        result = list(t.query(t.root.get_bounding_rect()))

        # Assert
        self.assertCountEqual(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'], [e.data for e in result])

    def test_query_nodes_point_single_match(self):
        """Tests query_nodes method with a Point location returning a single match"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        loc = Point(8, 1)

        # Act
        result = list(t.query_nodes(loc))

        # Assert
        self.assertCountEqual([nodes['L3']], result)

    def test_query_nodes_point_no_matches(self):
        """Tests query_nodes method with a Point location returning no matches"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        loc = (5, 6)

        # Act
        result = list(t.query_nodes(loc))

        # Assert
        self.assertEqual(0, len(result))

    def test_query_nodes_point_multiple_matches(self):
        """Tests query_nodes method with a Point location returning multiple matches"""
        # Arrange
        t = RTree(max_entries=3, min_entries=2)
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        t.insert('d', Rect(8, 8, 10, 10))
        t.insert('e', Rect(9, 9, 10, 10))
        loc = [5, 5]

        # Act
        result = list(t.query_nodes(loc))

        # Assert
        self.assertEqual(2, len(result))
        self.assertEqual(Rect(0, 0, 5, 5), result[0].get_bounding_rect())
        self.assertEqual(Rect(4, 4, 10, 10), result[1].get_bounding_rect())

    def test_query_nodes_rect_single_match(self):
        """Tests query_nodes method with a Rect location returning a single match"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        loc = Rect(6, 4, 8, 6)

        # Act
        result = list(t.query_nodes(loc))

        # Assert
        self.assertCountEqual([nodes['L3']], result)

    def test_query_nodes_rect_multiple_matches(self):
        """Tests query_nodes method with a Rect location returning multiple matches"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        L3, L4 = nodes['L3'], nodes['L4']
        loc = (5, 0, 8, 1)

        # Act
        result = list(t.query_nodes(loc))

        # Assert
        self.assertCountEqual([L3, L4], result)

    def test_query_nodes_rect_no_matches(self):
        """Tests query_nodes method with a Rect location returning no matches"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        loc = [4, 5, 6, 10]

        # Act
        result = list(t.query_nodes(loc))

        # Assert
        self.assertEqual(0, len(result))

    def test_query_nodes_intermediate_levels_multiple_matches(self):
        """Tests query_nodes method with leaves=False (returning intermediate nodes), returning multiple matches."""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        R, I1, L1 = nodes['R'], nodes['I1'], nodes['L1']
        loc = Rect(3, 9, 4, 10)

        # Act
        result = list(t.query_nodes(loc, leaves=False))

        # Assert
        self.assertCountEqual([R, I1, L1], result)

    def test_query_nodes_intermediate_levels_single_match(self):
        """Tests query_nodes method with leaves=False (returning intermediate nodes), returning a single match."""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        loc = (11, 10)

        # Act
        result = list(t.query_nodes(loc, leaves=False))

        # Assert
        self.assertEqual(1, len(result))
        self.assertEqual(t.root, result[0])

    def test_query_nodes_intermediate_levels_no_matches(self):
        """Tests query_nodes method with leaves=False (returning intermediate nodes), returning no matches"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        loc = (12, 12)

        # Act
        result = list(t.query_nodes(loc, leaves=False))

        # Assert
        self.assertEqual(0, len(result))

    def test_search_with_node_and_entry_conditions(self):
        """Tests search method with both a node and an entry constraint"""
        # Arrange
        t = create_simple_tree(self)

        def node_condition(node: RTreeNode):
            return node.get_bounding_rect().intersects(Rect(0, 0, 1, 1))

        def entry_condition(entry: RTreeEntry):
            return entry.data in ['a', 'c', 'e']

        # Act
        result = list(t.search(node_condition, entry_condition))

        # Assert
        self.assertCountEqual(['a', 'c'], [e.data for e in result])

    def test_search_with_node_condition_only(self):
        """Tests search method with only a node constraint (no entry constraint)"""
        # Arrange
        t = create_simple_tree(self)

        def node_condition(node: RTreeNode):
            return node.get_bounding_rect().intersects(Rect(0, 0, 1, 1))

        # Act
        result = list(t.search(node_condition))

        # Assert
        self.assertCountEqual(['a', 'b', 'c'], [e.data for e in result])

    def test_search_with_entry_condition_only(self):
        """Tests search method with only an entry constraint (no node constraint)"""
        # Arrange
        t = create_simple_tree(self)

        def entry_condition(entry: RTreeEntry):
            return entry.data in ['a', 'c', 'e']

        # Act
        result = list(t.search(node_condition=None, entry_condition=entry_condition))

        # Assert
        self.assertCountEqual(['a', 'c', 'e'], [e.data for e in result])

    def test_search_with_no_conditions(self):
        """Tests search method with no constraints on node or entry (should return all leaf entries)"""
        # Arrange
        t = create_simple_tree(self)

        # Act
        result = list(t.search(None))

        # Assert
        self.assertCountEqual(['a', 'b', 'c', 'd', 'e'], [e.data for e in result])

    def test_search_nodes_no_matches(self):
        """Tests search_nodes method with leaves=True and a condition that results in no leaf nodes matching"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def condition(node: RTreeNode):
            return node.get_bounding_rect() == Rect(0, 5, 10, 10)

        # Act
        result = list(t.search_nodes(condition))

        # Assert
        self.assertEqual(0, len(result))

    def test_search_nodes_single_match(self):
        """Tests search_nodes method with leaves=True and a condition that results in a single leaf node matching"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def condition(node: RTreeNode):
            return node.get_bounding_rect().intersects(Rect(0, 9, 1, 10))

        # Act
        result = list(t.search_nodes(condition))

        # Assert
        self.assertCountEqual([nodes['L1']], result)

    def test_search_nodes_multiple_matches(self):
        """Tests search_nodes method with leaves=True and a condition that results in multiple leaf nodes matching"""
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        L1, L4 = nodes['L1'], nodes['L4']

        def condition(node: RTreeNode):
            return node.get_bounding_rect().min_x == 0

        # Act
        result = list(t.search_nodes(condition))

        # Assert
        self.assertCountEqual([L1, L4], result)

    def test_search_nodes_intermediate_no_matches(self):
        """
        Tests search_nodes method with leaves=False (return intermediate matches) and a condition that results in no
        leaf nodes matching.
        """
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def condition(node: RTreeNode):
            return node.get_bounding_rect() == Rect(8, 7, 10, 9)

        # Act
        result = list(t.search_nodes(condition, leaves=False))

        # Assert
        self.assertEqual(0, len(result))

    def test_search_nodes_intermediate_single_match(self):
        """
        Tests search_nodes method with leaves=False (return intermediate matches) and a condition that results in a
        single intermediate node matching.
        """
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)

        def condition(node: RTreeNode):
            return node.get_bounding_rect() == Rect(0, 0, 11, 10)

        # Act
        result = list(t.search_nodes(condition, leaves=False))

        # Assert
        self.assertCountEqual([nodes['R']], result)

    def test_search_nodes_intermediate_multiple_matches(self):
        """
        Tests search_nodes method with leaves=False (return intermediate matches) and a condition that results in
        multiple intermediate and leaf nodes matching.
        """
        # Arrange
        nodes = dict()
        t = create_complex_tree(self, nodes)
        R, I2, L3, L4 = nodes['R'], nodes['I2'], nodes['L3'], nodes['L4']

        def condition(node: RTreeNode):
            return node.get_bounding_rect().intersects(Rect(4, 1, 8, 3))

        # Act
        result = list(t.search_nodes(condition, leaves=False))

        # Assert
        self.assertCountEqual([R, I2, L3, L4], result)


def _yield_node(node: RTreeNode) -> Iterable[RTreeNode]:
    yield node
