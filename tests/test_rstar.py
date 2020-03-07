from unittest import TestCase
from unittest.mock import patch
from rtreelib import Rect, RTree, RTreeNode, RTreeEntry
from rtreelib.strategies.rstar import (
    RStarTree, rstar_choose_leaf, least_overlap_enlargement, get_possible_divisions, choose_split_axis,
    choose_split_index, rstar_split, get_rstar_stat, EntryDistribution)


class TestRStar(TestCase):
    """Tests for R*-Tree implementation"""

    def test_least_overlap_enlargement(self):
        """
        Basic test of least overlap enlargement helper method. This test demonstrates a scenario where least area
        enlargement would favor one entry, but least overlap enlargement favors another.
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 4, 5))
        b = RTreeEntry(data='b', rect=Rect(2, 4, 5, 6))
        rect = Rect(4, 3, 5, 4)

        # Act
        entry = least_overlap_enlargement([a, b], rect)

        # Assert
        self.assertEqual(a, entry)

    def test_least_overlap_enlargement_tie(self):
        """Ensure least area enlargement is used as a tie-breaker when overlap enlargements are equal."""
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 4, 5))
        b = RTreeEntry(data='b', rect=Rect(3, 4, 5, 6))
        rect = Rect(2, 5, 3, 6)

        # Act
        entry = least_overlap_enlargement([a, b], rect)

        # Assert
        self.assertEqual(b, entry)

    @patch('rtreelib.strategies.rstar.least_overlap_enlargement')
    @patch('rtreelib.strategies.rstar.least_area_enlargement')
    def test_choose_leaf_uses_least_overlap_enlargement_for_level_above_leaf(
            self, least_area_enlargement_mock, least_overlap_enlargement_mock):
        """
        Ensure that the choose subtree strategy uses the least overlap enlargement strategy when picking a subtree at
        the level just above a leaf.
        """
        # Arrange
        tree = RTree()
        leaf = RTreeNode(tree, is_leaf=True)
        root = RTreeNode(tree, is_leaf=False, entries=[RTreeEntry(Rect(0, 0, 0, 0), child=leaf)])
        tree.root = root
        e = RTreeEntry(Rect(0, 0, 0, 0))

        # Act
        rstar_choose_leaf(tree, e)

        # Assert
        least_overlap_enlargement_mock.assert_called_once_with(root.entries, e.rect)
        least_area_enlargement_mock.assert_not_called()

    @patch('rtreelib.strategies.rstar.least_overlap_enlargement')
    @patch('rtreelib.strategies.rstar.least_area_enlargement')
    def test_choose_leaf_uses_least_area_enlargement_for_higher_levels(
            self, least_area_enlargement_mock, least_overlap_enlargement_mock):
        """
        Ensure that the choose subtree strategy uses the least area enlargement strategy when picking a subtree at
        levels higher than the one just above the leaf level.
        """
        # Arrange
        tree = RTree()
        leaf = RTreeNode(tree, is_leaf=True)
        intermediate = RTreeNode(tree, is_leaf=False, entries=[RTreeEntry(Rect(0, 0, 0, 0), child=leaf)])
        intermediate_entry = RTreeEntry(Rect(0, 0, 0, 0), child=intermediate)
        root = RTreeNode(tree, is_leaf=False, entries=[intermediate_entry])
        tree.root = root
        e = RTreeEntry(Rect(0, 0, 0, 0))
        least_area_enlargement_mock.return_value = intermediate_entry

        # Act
        rstar_choose_leaf(tree, e)

        # Assert
        least_area_enlargement_mock.assert_called_once_with(root.entries, e.rect)
        least_overlap_enlargement_mock.assert_called_once_with(intermediate.entries, e.rect)

    @patch('rtreelib.strategies.rstar.least_overlap_enlargement')
    @patch('rtreelib.strategies.rstar.least_area_enlargement')
    def test_choose_leaf_returns_leaf_node_when_root_is_leaf(
            self, least_area_enlargement_mock, least_overlap_enlargement_mock):
        """
        When the root node is a leaf, it should be returned without invoking either the least area or overlap
        enlargement strategies.
        """
        # Arrange
        tree = RTree()
        root = RTreeNode(tree, is_leaf=True, entries=[RTreeEntry(Rect(0, 0, 1, 1))])
        tree.root = root
        e = RTreeEntry(Rect(0, 0, 0, 0))

        # Act
        node = rstar_choose_leaf(tree, e)

        # Assert
        self.assertEqual(root, node)
        least_area_enlargement_mock.assert_not_called()
        least_overlap_enlargement_mock.assert_not_called()

    def test_get_possible_divisions_1_3(self):
        """Tests get_possible_divisions with m=1 and M=3"""
        # Arrange
        rect = Rect(0, 0, 0, 0)
        a = RTreeEntry(data='a', rect=rect)
        b = RTreeEntry(data='b', rect=rect)
        c = RTreeEntry(data='c', rect=rect)
        d = RTreeEntry(data='d', rect=rect)

        # Act
        divisions = get_possible_divisions([a, b, c, d], 1, 3)

        # Assert
        self.assertEqual(3, len(divisions))
        self.assertEqual(([a], [b, c, d]), divisions[0])
        self.assertEqual(([a, b], [c, d]), divisions[1])
        self.assertEqual(([a, b, c], [d]), divisions[2])

    def test_get_possible_divisions_2_4(self):
        """Tests get_possible_divisions with m=2 and M=4"""
        # Arrange
        rect = Rect(0, 0, 0, 0)
        a = RTreeEntry(data='a', rect=rect)
        b = RTreeEntry(data='b', rect=rect)
        c = RTreeEntry(data='c', rect=rect)
        d = RTreeEntry(data='d', rect=rect)
        e = RTreeEntry(data='e', rect=rect)

        # Act
        divisions = get_possible_divisions([a, b, c, d, e], 2, 4)

        # Assert
        self.assertEqual(2, len(divisions))
        self.assertEqual(([a, b], [c, d, e]), divisions[0])
        self.assertEqual(([a, b, c], [d, e]), divisions[1])

    def test_get_possible_divisions_1_4(self):
        """Tests get_possible_divisions with m=1 and M=4"""
        # Arrange
        rect = Rect(0, 0, 0, 0)
        a = RTreeEntry(data='a', rect=rect)
        b = RTreeEntry(data='b', rect=rect)
        c = RTreeEntry(data='c', rect=rect)
        d = RTreeEntry(data='d', rect=rect)
        e = RTreeEntry(data='e', rect=rect)

        # Act
        divisions = get_possible_divisions([a, b, c, d, e], 1, 4)

        # Assert
        self.assertEqual(4, len(divisions))
        self.assertEqual(([a], [b, c, d, e]), divisions[0])
        self.assertEqual(([a, b], [c, d, e]), divisions[1])
        self.assertEqual(([a, b, c], [d, e]), divisions[2])
        self.assertEqual(([a, b, c, d], [e]), divisions[3])

    def test_get_rstar_stat_same_distribution_for_all_4_sort_types(self):
        """
        Tests get_rstar_stat when all 4 sort types (min_x, max_x, min_y, and max_y) result in the same distribution
        of entries.
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 1, 1))
        b = RTreeEntry(data='b', rect=Rect(1, 1, 2, 2))
        c = RTreeEntry(data='c', rect=Rect(2, 2, 3, 3))
        d = RTreeEntry(data='d', rect=Rect(3, 3, 4, 4))

        # Act
        stat = get_rstar_stat([a, b, c, d], 1, 3)

        # Assert
        unique_distributions = [
            EntryDistribution(([a], [b, c, d])),
            EntryDistribution(([a, b], [c, d])),
            EntryDistribution(([a, b, c], [d]))
        ]
        self.assertCountEqual(unique_distributions, stat.unique_distributions)
        self.assertCountEqual(unique_distributions, stat.get_axis_unique_distributions('x'))
        self.assertCountEqual(unique_distributions, stat.get_axis_unique_distributions('y'))
        self.assertEqual(96, stat.get_axis_perimeter('x'))
        self.assertEqual(96, stat.get_axis_perimeter('y'))

    def test_get_rstar_stat_sorts_entries_by_both_min_and_max(self):
        """
        List of possible divisions should be based on entries sorted by both the minimum as well as maximum coordinate.
        In the example below, when the entries are sorted by either minx, miny, or maxy, the sort order is always
        (a,b,c), but when sorted by maxx, the order is (b,a,c). This ordering enables the [(b), (a,c)] division (which
        turns out to be optimal).
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 7, 2))
        b = RTreeEntry(data='b', rect=Rect(1, 1, 2, 3))
        c = RTreeEntry(data='c', rect=Rect(2, 2, 8, 4))

        # Act
        stat = get_rstar_stat([a, b, c], 1, 2)

        # Assert
        self.assertCountEqual([
            EntryDistribution(([a], [b, c])),
            EntryDistribution(([a, b], [c])),
            EntryDistribution(([b], [a, c]))
        ], stat.unique_distributions)
        self.assertCountEqual([
            EntryDistribution(([a], [b, c])),
            EntryDistribution(([a, b], [c])),
            EntryDistribution(([b], [a, c]))
        ], stat.get_axis_unique_distributions('x'))
        self.assertCountEqual([
            EntryDistribution(([a], [b, c])),
            EntryDistribution(([a, b], [c]))
        ], stat.get_axis_unique_distributions('y'))
        self.assertEqual(140, stat.get_axis_perimeter('x'))
        self.assertEqual(148, stat.get_axis_perimeter('y'))

    def test_get_rstar_stat_different_distributions_for_each_sort(self):
        """
        More complex test of get_rstar_stat where each of the 4 sort types (min_x, max_x, min_y, and max_y) results in
        a different sort order of entries (and sometimes different distributions, though some are equivalent).
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 3, 2))
        b = RTreeEntry(data='b', rect=Rect(1, 1, 5, 5))
        c = RTreeEntry(data='c', rect=Rect(6, -1, 8, 3))
        d = RTreeEntry(data='d', rect=Rect(4, 2, 9, 4))

        # Act
        stat = get_rstar_stat([a, b, c, d], 1, 3)

        # Assert
        self.assertCountEqual([
            EntryDistribution(([a], [b, c, d])),
            EntryDistribution(([a, b], [c, d])),
            EntryDistribution(([a, b, c], [d])),
            EntryDistribution(([a, c], [b, d])),
            EntryDistribution(([b], [a, c, d])),
            EntryDistribution(([c], [a, b, d])),
        ], stat.unique_distributions)
        self.assertCountEqual([
            EntryDistribution(([a], [b, c, d])),
            EntryDistribution(([a, b], [c, d])),
            EntryDistribution(([a, b, c], [d])),
            EntryDistribution(([c], [a, b, d])),
        ], stat.get_axis_unique_distributions('x'))
        self.assertCountEqual([
            EntryDistribution(([a], [b, c, d])),
            EntryDistribution(([a, b, c], [d])),
            EntryDistribution(([a, c], [b, d])),
            EntryDistribution(([b], [a, c, d])),
            EntryDistribution(([c], [a, b, d])),
        ], stat.get_axis_unique_distributions('y'))
        self.assertEqual(238, stat.get_axis_perimeter('x'))
        self.assertEqual(260, stat.get_axis_perimeter('y'))

    def test_choose_split_axis(self):
        """
        Ensure split axis is chosen based on smallest overall perimeter of all possible divisions of a list of entries.
        In the below scenario, there is a clear winner with the best division being ([a, b, c], [d]).
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 1, 1))
        b = RTreeEntry(data='b', rect=Rect(1, 0, 2, 1))
        c = RTreeEntry(data='c', rect=Rect(2, 0, 3, 1))
        d = RTreeEntry(data='d', rect=Rect(1, 7, 2, 8))
        stat = get_rstar_stat([a, b, c, d], 1, 3)

        # Act
        result = choose_split_axis(stat)

        # Assert
        self.assertEqual('y', result)

    def test_choose_split_index(self):
        """Ensures best split index is chosen based on minimum overlap."""
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 1, 4, 5))
        b = RTreeEntry(data='b', rect=Rect(3, 5, 6, 8))
        c = RTreeEntry(data='c', rect=Rect(7, 0, 9, 4))
        d = RTreeEntry(data='d', rect=Rect(8, 7, 10, 9))
        distributions = [
            EntryDistribution(([a], [b, c, d])),
            EntryDistribution(([a, b], [c, d])),
            EntryDistribution(([a, b, c], [d]))
        ]

        # Act
        i = choose_split_index(distributions)

        # Assert
        self.assertEqual(1, i)

    def test_choose_split_index_tie(self):
        """When multiple divisions have the same overlap, ensure split index is chosen based on minimum area."""
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 2, 1))
        b = RTreeEntry(data='b', rect=Rect(1, 0, 3, 2))
        c = RTreeEntry(data='c', rect=Rect(2, 2, 4, 3))
        d = RTreeEntry(data='d', rect=Rect(9, 9, 10, 10))
        distributions = [
            EntryDistribution(([a], [b, c, d])),
            EntryDistribution(([a, b], [c, d])),
            EntryDistribution(([a, b, c], [d]))
        ]

        # Act
        i = choose_split_index(distributions)

        # Assert
        self.assertEqual(2, i)

    def test_rstar_split(self):
        """
        Ensures the R*-Tree split sets the entries in the original and split nodes correctly after performing a split.
        Note that the tree is not reorganized until adjust_tree is called, which is done on insert rather than split, so
        the resulting structure when calling rstar_split is not necessarily the final structure of the tree.
        """
        # Arrange
        tree = RTree(min_entries=1, max_entries=2)
        a = RTreeEntry(data='a', rect=Rect(0, 0, 7, 2))
        b = RTreeEntry(data='b', rect=Rect(1, 1, 2, 3))
        c = RTreeEntry(data='c', rect=Rect(2, 2, 8, 4))
        root = RTreeNode(tree, is_leaf=True, entries=[a, b, c])
        tree.root = root

        # Act
        split_node = rstar_split(tree, root)

        # Assert
        # The original node should contain entries from the first group in the optimal division. The optimal division
        # in this example is [(b), (a,c)], so the original node should contain entry 'b'.
        self.assertEqual(1, len(tree.root.entries))
        entry_b = tree.root.entries[0]
        self.assertEqual('b', entry_b.data)
        self.assertEqual(Rect(1, 1, 2, 3), tree.root.get_bounding_rect())
        self.assertEqual(Rect(1, 1, 2, 3), entry_b.rect)
        self.assertTrue(tree.root.is_root)
        self.assertTrue(tree.root.is_leaf)
        self.assertIsNone(entry_b.child)
        # The split node should contain entries (a,c)
        self.assertEqual(2, len(split_node.entries))
        self.assertEqual(Rect(0, 0, 8, 4), split_node.get_bounding_rect())
        # Entry 'a'
        entry_a = next((e for e in split_node.entries if e.data == 'a'))
        self.assertEqual(Rect(0, 0, 7, 2), entry_a.rect)
        self.assertTrue(entry_a.is_leaf)
        self.assertIsNone(entry_a.child)
        # Entry 'c'
        entry_c = next((e for e in split_node.entries if e.data == 'c'))
        self.assertEqual('c', entry_c.data)
        self.assertTrue(entry_c.is_leaf)
        self.assertIsNone(entry_c.child)
        self.assertEqual(Rect(2, 2, 8, 4), entry_c.rect)
        self.assertTrue(entry_c.is_leaf)
        self.assertIsNone(entry_c.child)

    def test_rstar_insert_empty(self):
        """Tests inserting into an empty tree"""
        # Arrange
        tree = RTree(min_entries=1, max_entries=3)

        # Act
        tree.insert('a', Rect(0, 0, 5, 5))

        # Assert
        # Ensure root entry has the correct data and bounding box
        self.assertEqual(1, len(tree.root.entries))
        e = tree.root.entries[0]
        self.assertEqual('a', e.data)
        self.assertEqual(Rect(0, 0, 5, 5), e.rect)
        self.assertIsNone(e.child)
        # Ensure root node has correct structure
        node = tree.root
        self.assertTrue(node.is_root)
        self.assertTrue(node.is_leaf)
        self.assertEqual(Rect(0, 0, 5, 5), tree.root.get_bounding_rect())
        # Ensure root entry has correct structure
        self.assertTrue(e.is_leaf)
        self.assertIsNone(e.child)
        # Ensure there is only 1 level and 1 node in the tree
        self.assertEqual(1, len(tree.get_levels()))
        self.assertEqual(1, len(list(tree.get_nodes())))

    def test_rstar_insert_no_split(self):
        """Tests multiple inserts which do not require a node split"""
        # Arrange
        tree = RTree(min_entries=1, max_entries=2)

        # Act
        tree.insert('a', Rect(0, 0, 5, 2))
        tree.insert('b', Rect(2, 3, 4, 7))

        # Assert
        # Root node
        self.assertTrue(tree.root.is_root)
        self.assertTrue(tree.root.is_leaf)
        self.assertEqual(2, len(tree.root.entries))
        self.assertEqual(Rect(0, 0, 5, 7), tree.root.get_bounding_rect())
        # Entry 'a'
        entry_a = next((e for e in tree.root.entries if e.data == 'a'))
        self.assertEqual(Rect(0, 0, 5, 2), entry_a.rect)
        self.assertTrue(entry_a.is_leaf)
        self.assertIsNone(entry_a.child)
        # Entry 'b'
        entry_b = next((e for e in tree.root.entries if e.data == 'b'))
        self.assertEqual(Rect(2, 3, 4, 7), entry_b.rect)
        self.assertTrue(entry_b.is_leaf)
        self.assertIsNone(entry_b.child)

    def test_rstar_insert_with_split(self):
        """Complete test of tree structure after performing multiple inserts which require a node split."""
        # TODO: This test currently uses the default Guttman implementation (since the R*-Tree has not been fully
        #  implemented yet, so an implementation is not available). Once the R*-Tree implementation is available, this
        #  test (and all tests in this module) should use it. Further, it would be beneficial to come up with a better
        #  example where the Guttman implementation results in a different split than R*-Tree, since this test currently
        #  passes even with Guttman.

        # Arrange
        tree = RTree(min_entries=1, max_entries=2)

        # Act
        tree.insert('a', Rect(0, 0, 5, 2))
        tree.insert('b', Rect(2, 3, 4, 7))
        tree.insert('c', Rect(3, 1, 7, 4))

        # Assert
        # Root node
        self.assertTrue(tree.root.is_root)
        self.assertFalse(tree.root.is_leaf)
        self.assertEqual(2, len(tree.root.entries))
        self.assertEqual(Rect(0, 0, 7, 7), tree.root.get_bounding_rect())
        # Find parent entry at root level that contains child entries 'a' and 'c' and test its properties
        parent_ac = next((e for e in tree.root.entries if e.rect == Rect(0, 0, 7, 4)))
        self.assertIsNone(parent_ac.data)
        self.assertFalse(parent_ac.is_leaf)
        self.assertIsNotNone(parent_ac.child)
        # Test properties of node that contains entries 'a' and 'c'
        node_ac = parent_ac.child
        self.assertEqual(Rect(0, 0, 7, 4), node_ac.get_bounding_rect())
        self.assertFalse(node_ac.is_root)
        self.assertTrue(node_ac.is_leaf)
        self.assertEqual(2, len(node_ac.entries))
        self.assertEqual(tree.root, node_ac.parent)
        self.assertEqual(parent_ac, node_ac.parent_entry)
        self.assertEqual(tree, node_ac.tree)
        # Entry 'a'
        entry_a = next((e for e in node_ac.entries if e.data == 'a'))
        self.assertEqual(Rect(0, 0, 5, 2), entry_a.rect)
        self.assertTrue(entry_a.is_leaf)
        self.assertIsNone(entry_a.child)
        # Entry 'c'
        entry_c = next((e for e in node_ac.entries if e.data == 'c'))
        self.assertEqual(Rect(3, 1, 7, 4), entry_c.rect)
        self.assertTrue(entry_c.is_leaf)
        self.assertIsNone(entry_c.child)
        # Find parent entry at root level that contains child entry 'b' and test its properties
        parent_b = next((e for e in tree.root.entries if e.rect == Rect(2, 3, 4, 7)))
        self.assertIsNone(parent_b.data)
        self.assertFalse(parent_b.is_leaf)
        self.assertIsNotNone(parent_b.child)
        # Test properties of node that contains entry 'b'
        node_b = parent_b.child
        self.assertEqual(Rect(2, 3, 4, 7), node_b.get_bounding_rect())
        self.assertFalse(node_b.is_root)
        self.assertTrue(node_b.is_leaf)
        self.assertEqual(1, len(node_b.entries))
        self.assertEqual(tree.root, node_b.parent)
        self.assertEqual(parent_b, node_b.parent_entry)
        self.assertEqual(tree, node_b.tree)
        # Entry 'b'
        entry_b = node_b.entries[0]
        self.assertEqual(Rect(2, 3, 4, 7), entry_b.rect)
        self.assertTrue(entry_b.is_leaf)
        self.assertIsNone(entry_b.child)
        # Ensure there are two levels total in the tree and the levels contain the correct data
        levels = tree.get_levels()
        self.assertEqual(2, len(levels))
        # Assert nodes at root level
        level_0 = levels[0]
        self.assertEqual(1, len(level_0))
        self.assertEqual(tree.root, level_0[0])
        # Assert nodes at level below the root
        level_1 = levels[1]
        self.assertEqual(2, len(level_1))
        self.assertCountEqual([node_ac, node_b], level_1)
        # Assert full list of nodes
        self.assertCountEqual([tree.root, node_ac, node_b], tree.get_nodes())
        # Assert leaf nodes
        self.assertCountEqual([node_ac, node_b], tree.get_leaves())
        # Assert leaf entries
        self.assertCountEqual([entry_a, entry_b, entry_c], tree.get_leaf_entries())

    def test_rstar_insert(self):
        # Arrange
        t = RStarTree(max_entries=2)
        r1 = Rect(0, 0, 3, 2)
        r2 = Rect(2, 1, 5, 3)
        r3 = Rect(6, 6, 8, 8)
        r4 = Rect(7, 7, 10, 9)
        t.root = RTreeNode(t, is_leaf=False)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        entry_c = RTreeEntry(r3, data='c')
        entry_d = RTreeEntry(r4, data='d')
        n1 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_a, entry_b])
        n2 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_c, entry_d])
        e1 = RTreeEntry(Rect(0, 0, 5, 3), child=n1)
        e2 = RTreeEntry(Rect(6, 6, 10, 9), child=n2)
        t.root.entries = [e1, e2]
        # Rectangle being imported
        r5 = Rect(4, 2, 6, 4)

        # Act
        t.insert('e', r5)
