from typing import List, TypeVar
from unittest import TestCase
from unittest.mock import patch
from rtreelib import Rect, RTreeNode, RTreeEntry
from rtreelib.strategies.rstar import (
    RStarTree, rstar_overflow, rstar_choose_leaf, least_overlap_enlargement, get_possible_divisions,
    choose_split_axis, choose_split_index, rstar_split, get_rstar_stat, EntryDistribution)

T = TypeVar('T')


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
        tree = RStarTree()
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
        tree = RStarTree()
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
        tree = RStarTree()
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
        tree = RStarTree(min_entries=1, max_entries=2)
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
        tree = RStarTree(min_entries=1, max_entries=3)

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
        tree = RStarTree(min_entries=1, max_entries=2)

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
        # Arrange
        tree = RStarTree(min_entries=1, max_entries=3)

        # Act
        tree.insert('a', Rect(0, 2, 6, 3))
        tree.insert('b', Rect(4, 1, 5, 5))
        tree.insert('c', Rect(2, 4, 7, 5))
        tree.insert('d', Rect(2, 3, 4, 8))
        tree.insert('e', Rect(1, 0, 3, 5))

        # Assert
        # Root node
        self.assertTrue(tree.root.is_root)
        self.assertFalse(tree.root.is_leaf)
        self.assertEqual(3, len(tree.root.entries))
        self.assertEqual(Rect(0, 0, 7, 8), tree.root.get_bounding_rect())
        # Find entry at root level that contains child entries [a, c, e] and test its properties
        root_entry_ace = next((e for e in tree.root.entries if e.rect == Rect(0, 0, 7, 5)))
        self.assertIsNone(root_entry_ace.data)
        self.assertFalse(root_entry_ace.is_leaf)
        self.assertIsNotNone(root_entry_ace.child)
        # Test properties of node that contains entries [a, c, e]
        node_ace = root_entry_ace.child
        self.assertEqual(Rect(0, 0, 7, 5), node_ace.get_bounding_rect())
        self.assertFalse(node_ace.is_root)
        self.assertTrue(node_ace.is_leaf)
        self.assertEqual(3, len(node_ace.entries))
        self.assertEqual(tree.root, node_ace.parent)
        self.assertEqual(root_entry_ace, node_ace.parent_entry)
        self.assertEqual(tree, node_ace.tree)
        # Entry 'a'
        entry_a = next((e for e in node_ace.entries if e.data == 'a'))
        self.assertEqual(Rect(0, 2, 6, 3), entry_a.rect)
        self.assertTrue(entry_a.is_leaf)
        self.assertIsNone(entry_a.child)
        # Entry 'c'
        entry_c = next((e for e in node_ace.entries if e.data == 'c'))
        self.assertEqual(Rect(2, 4, 7, 5), entry_c.rect)
        self.assertTrue(entry_c.is_leaf)
        self.assertIsNone(entry_c.child)
        # Entry 'c'
        entry_e = next((e for e in node_ace.entries if e.data == 'e'))
        self.assertEqual(Rect(1, 0, 3, 5), entry_e.rect)
        self.assertTrue(entry_e.is_leaf)
        self.assertIsNone(entry_e.child)
        # Find parent entry at root level that contains child entry 'b' and test its properties
        root_entry_b = next((e for e in tree.root.entries if e.rect == Rect(4, 1, 5, 5)))
        self.assertIsNone(root_entry_b.data)
        self.assertFalse(root_entry_b.is_leaf)
        self.assertIsNotNone(root_entry_b.child)
        # Test properties of node that contains entry 'b'
        node_b = root_entry_b.child
        self.assertEqual(Rect(4, 1, 5, 5), node_b.get_bounding_rect())
        self.assertFalse(node_b.is_root)
        self.assertTrue(node_b.is_leaf)
        self.assertEqual(1, len(node_b.entries))
        self.assertEqual(tree.root, node_b.parent)
        self.assertEqual(root_entry_b, node_b.parent_entry)
        self.assertEqual(tree, node_b.tree)
        # Entry 'b'
        entry_b = node_b.entries[0]
        self.assertEqual('b', entry_b.data)
        self.assertEqual(Rect(4, 1, 5, 5), entry_b.rect)
        self.assertTrue(entry_b.is_leaf)
        self.assertIsNone(entry_b.child)
        # Find parent entry at root level that contains child entry 'd' and test its properties
        root_entry_d = next((e for e in tree.root.entries if e.rect == Rect(2, 3, 4, 8)))
        self.assertIsNone(root_entry_d.data)
        self.assertFalse(root_entry_d.is_leaf)
        self.assertIsNotNone(root_entry_d.child)
        # Test properties of node that contains entry 'd'
        node_d = root_entry_d.child
        self.assertEqual(Rect(2, 3, 4, 8), node_d.get_bounding_rect())
        self.assertFalse(node_d.is_root)
        self.assertTrue(node_d.is_leaf)
        self.assertEqual(1, len(node_d.entries))
        self.assertEqual(tree.root, node_d.parent)
        self.assertEqual(root_entry_d, node_d.parent_entry)
        self.assertEqual(tree, node_d.tree)
        # Entry 'd'
        entry_d = node_d.entries[0]
        self.assertEqual('d', entry_d.data)
        self.assertEqual(Rect(2, 3, 4, 8), entry_d.rect)
        self.assertTrue(entry_d.is_leaf)
        self.assertIsNone(entry_d.child)
        # Ensure there are two levels total in the tree and the levels contain the correct data
        levels = tree.get_levels()
        self.assertEqual(2, len(levels))
        # Assert nodes at root level
        level_0 = levels[0]
        self.assertEqual(1, len(level_0))
        self.assertEqual(tree.root, level_0[0])
        # Assert nodes at level below the root
        level_1 = levels[1]
        self.assertEqual(3, len(level_1))
        self.assertCountEqual([node_ace, node_b, node_d], level_1)
        # Assert full list of nodes
        self.assertCountEqual([tree.root, node_ace, node_b, node_d], tree.get_nodes())
        # Assert leaf nodes
        self.assertCountEqual([node_ace, node_b, node_d], tree.get_leaves())
        # Assert leaf entries
        self.assertCountEqual([entry_a, entry_b, entry_c, entry_d, entry_e], tree.get_leaf_entries())

    @patch('rtreelib.strategies.rstar.rstar_split')
    def test_rstar_overflow_reinsert_without_split(self, rstar_split_mock):
        """
        Tests R* overflow scenario that results in forced reinsert of some entries into a different node, but without
        any additional overflows/splits occurring.
        """
        # Arrange
        t = RStarTree(max_entries=3)
        r1 = Rect(0, 0, 1, 1)
        r2 = Rect(9, 0, 10, 1)
        r3 = Rect(0, 1, 1, 2)
        r4 = Rect(9, 5, 10, 6)
        r5 = Rect(3, 2, 10, 4)
        t.root = RTreeNode(t, is_leaf=False)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        entry_c = RTreeEntry(r3, data='c')
        entry_d = RTreeEntry(r4, data='d')
        entry_e = RTreeEntry(r5, data='e')
        n1 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_a, entry_c])
        n2 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_b, entry_d, entry_e])
        e1 = RTreeEntry(Rect(0, 0, 1, 2), child=n1)
        e2 = RTreeEntry(Rect(3, 0, 10, 6), child=n2)
        t.root.entries = [e1, e2]
        # Arrange entry being inserted
        r6 = Rect(2, 1, 3, 2)
        entry_f = RTreeEntry(r6, data='f')
        # Manually insert the new entry into node n2, causing it to be overfull.
        n2.entries.append(entry_f)
        # Ensure preconditions:
        # At this point, the root node entries will still have their old covering rectangles.
        self.assertEqual(Rect(0, 0, 1, 2), e1.rect)
        self.assertEqual(Rect(3, 0, 10, 6), e2.rect)
        # At this point, the root node will only have 2 entries for e1 and e2
        self.assertEqual([e1, e2], t.root.entries)

        # Act
        rstar_overflow(t, n2)

        # Assert
        # Ensure rstar_split was not invoked. In this scenario, it should do a forced reinsert instead (and the reinsert
        # should not result in any additional splits).
        rstar_split_mock.assert_not_called()
        # Ensure the root node still has only 2 entries, and their children are still the nodes n1 and n2.
        self.assertEqual([e1, e2], t.root.entries)
        self.assertEqual(n1, e1.child)
        self.assertEqual(n2, e2.child)
        # Forced insert should have resulted in entry f getting reinserted into node n1 (was previously in n2).
        # Ensure node n1 now has entries [a, c, f].
        self.assertCountEqual([entry_a, entry_c, entry_f], n1.entries)
        # Ensure node n1 bounding box accommodates entries [a, c, f]
        self.assertEqual(Rect(0, 0, 3, 2), n1.get_bounding_rect())
        # Remaining entries [b, d, e] should be in node n2.
        self.assertCountEqual([entry_b, entry_d, entry_e], n2.entries)
        self.assertEqual(Rect(3, 0, 10, 6), n2.get_bounding_rect())
        # Ensure nodes n1 and n2 are leaf nodes, and there are no additional levels in the tree.
        self.assertTrue(n1.is_leaf)
        self.assertTrue(n2.is_leaf)
        self.assertEqual(2, len(t.get_levels()))

    def test_rstar_overflow_reinsert_with_split(self):
        """
        Tests R* overflow scenario that results in forced reinsert of some entries into a different node which is
        already at capacity, causing it to overflow. In this scenario, the second overflow at the same level should
        result in a regular split, not another forced reinsert.
        """
        # Arrange
        t = RStarTree(max_entries=3)
        r1 = Rect(0, 0, 1, 1)
        r2 = Rect(0, 1, 1, 2)
        r3 = Rect(9, 0, 10, 1)
        r4 = Rect(0, 2, 1, 3)
        r5 = Rect(9, 6, 10, 7)
        r6 = Rect(3, 2, 10, 5)
        t.root = RTreeNode(t, is_leaf=False)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        entry_c = RTreeEntry(r3, data='c')
        entry_d = RTreeEntry(r4, data='d')
        entry_e = RTreeEntry(r5, data='e')
        entry_f = RTreeEntry(r6, data='f')
        n1 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_a, entry_b, entry_d])
        n2 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_c, entry_e, entry_f])
        e1 = RTreeEntry(Rect(0, 0, 1, 3), child=n1)
        e2 = RTreeEntry(Rect(3, 0, 10, 7), child=n2)
        t.root.entries = [e1, e2]
        # Arrange entry being inserted
        r7 = Rect(2, 1, 3, 2)
        entry_g = RTreeEntry(r7, data='g')
        # Manually insert the new entry into node n2, causing it to be overfull.
        n2.entries.append(entry_g)
        # Ensure preconditions:
        # At this point, the root node entries will still have their old covering rectangles.
        self.assertEqual(Rect(0, 0, 1, 3), e1.rect)
        self.assertEqual(Rect(3, 0, 10, 7), e2.rect)
        # At this point, the root node will only have 2 entries for e1 and e2
        self.assertEqual([e1, e2], t.root.entries)

        # Act
        rstar_overflow(t, n2)

        # Assert
        # Root node should now have 3 entries (split should have occurred)
        self.assertEqual(3, len(t.root.entries))
        # There should still be 2 levels in the tree (root node should not have split)
        levels = t.get_levels()
        self.assertEqual(2, len(levels))
        # There should be 3 nodes at the leaf level
        leaf_nodes = levels[1]
        self.assertEqual(3, len(leaf_nodes))
        # One of the nodes should have entries [a, b] and with the correct bounding rectangle
        n1 = next((n for n in leaf_nodes if set(_get_leaf_node_data(n)) == {'a', 'b'}))
        self.assertEqual(Rect(0, 0, 1, 2), n1.get_bounding_rect())
        self.assertEqual(Rect(0, 0, 1, 2), n1.parent_entry.rect)
        # Another node should have entries [c, e, f] and with the correct bounding rectangle
        n2 = next((n for n in leaf_nodes if set(_get_leaf_node_data(n)) == {'c', 'e', 'f'}))
        self.assertEqual(Rect(3, 0, 10, 7), n2.get_bounding_rect())
        self.assertEqual(Rect(3, 0, 10, 7), n2.parent_entry.rect)
        # Last node should have entries [d, g] and with the correct bounding rectangle
        n3 = next((n for n in leaf_nodes if set(_get_leaf_node_data(n)) == {'d', 'g'}))
        self.assertEqual(Rect(0, 1, 3, 3), n3.get_bounding_rect())
        self.assertEqual(Rect(0, 1, 3, 3), n3.parent_entry.rect)

    def test_rstar_overflow_split_root(self):
        """
        When the root node overflows, the root node should be split and the tree should grow a level. Forced reinsert
        should not occur at the root level.
        """
        # Arrange
        t = RStarTree(max_entries=3)
        r1 = Rect(0, 0, 3, 2)
        r2 = Rect(7, 7, 10, 9)
        r3 = Rect(2, 1, 5, 3)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        entry_c = RTreeEntry(r3, data='c')
        t.root.entries = [entry_a, entry_b, entry_c]
        # Arrange entry being inserted. Since the root node is at max capacity, this entry should cause the root
        # to overflow.
        r4 = Rect(6, 6, 8, 8)

        # Act
        entry_d = t.insert('d', r4)

        # Assert
        # Root node should no longer be a leaf node (but should still be root)
        self.assertFalse(t.root.is_leaf)
        self.assertTrue(t.root.is_root)
        # Root node bounding box should encompass all entries
        self.assertEqual(Rect(0, 0, 10, 9), t.root.get_bounding_rect())
        # Root node should have 2 child entries
        self.assertEqual(2, len(t.root.entries))
        e1 = t.root.entries[0]
        e2 = t.root.entries[1]
        # e1 bounding box should encompass entries [a, c]
        self.assertEqual(Rect(0, 0, 5, 3), e1.rect)
        # e2 bounding box should encompass entries [b ,d]
        self.assertEqual(Rect(6, 6, 10, 9), e2.rect)
        # Ensure children nodes of e1 and e2 are leaf nodes
        leaf_node_1 = e1.child
        leaf_node_2 = e2.child
        self.assertIsNotNone(leaf_node_1)
        self.assertIsNotNone(leaf_node_2)
        self.assertTrue(leaf_node_1.is_leaf)
        self.assertTrue(leaf_node_2.is_leaf)
        # Leaf node 1 should contain entries [a, c]
        self.assertEqual(Rect(0, 0, 5, 3), leaf_node_1.get_bounding_rect())
        self.assertCountEqual([entry_a, entry_c], leaf_node_1.entries)
        # Leaf node 2 should contain entries [b, d]
        self.assertEqual(Rect(6, 6, 10, 9), leaf_node_2.get_bounding_rect())
        self.assertCountEqual([entry_b, entry_d], leaf_node_2.entries)

    def test_rstar_overflow_reinsert_grow_tree(self):
        """
        When a forced reinsert causes a node split which propagates upward causing the tree to grow, ensure that the
        remaining entries that still need to be re-inserted are inserted at the correct level. The number of levels in
        the tree changes in the middle of an insert operation under this scenario, which makes this rather complex.
        This scenario is also the reason why the R* insert tracks the level as the number of levels from the leaf (i.e.,
        the leaf level is 0), instead of the more traditional approach of referring to the root level as 0.
        """
        # Arrange
        # Create a tree with 2 levels, with the root and all leaf nodes at capacity.
        # Arrange
        t = RStarTree(max_entries=3, min_entries=1)
        r1 = Rect(0, 0, 5, 2)
        r2 = Rect(1, 1, 5, 3)
        r3 = Rect(2, 2, 6, 4)
        r4 = Rect(5, 0, 12, 9)
        r5 = Rect(7, 7, 20, 8)
        r6 = Rect(4, 4, 13, 6)
        r7 = Rect(16, 7, 19, 10)
        r8 = Rect(16, 9, 18, 10)
        r9 = Rect(18, 8, 19, 10)
        t.root = RTreeNode(t, is_leaf=False)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        entry_c = RTreeEntry(r3, data='c')
        entry_d = RTreeEntry(r4, data='d')
        entry_e = RTreeEntry(r5, data='e')
        entry_f = RTreeEntry(r6, data='f')
        entry_g = RTreeEntry(r7, data='g')
        entry_h = RTreeEntry(r8, data='h')
        entry_i = RTreeEntry(r9, data='i')
        n1 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_a, entry_b, entry_c])
        n2 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_d, entry_e, entry_f])
        n3 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_g, entry_h, entry_i])
        e1 = RTreeEntry(Rect(0, 0, 6, 4), child=n1)
        e2 = RTreeEntry(Rect(4, 0, 20, 9), child=n2)
        e3 = RTreeEntry(Rect(16, 7, 19, 10), child=n3)
        t.root.entries = [e1, e2, e3]
        # Arrange entry being inserted
        r10 = Rect(18, 5, 20, 7)
        entry_j = RTreeEntry(r10, data='j')
        # Manually insert the new entry into node n2, causing it to be overfull.
        n2.entries.append(entry_j)
        # Ensure preconditions
        # At this point, the tree should have 2 levels
        self.assertEqual(2, len(t.get_levels()))

        # Act
        # Since this is a complicated case, here is a step-by-step breakdown of what we expect to happen:
        # (1) Upon inserting entry j into node n2, it will overflow (now has 4 entries and max_entries is 3).
        # (2) Forced reinsert will be performed on entries closest to n2's centroid, which are [e, d].
        #     (a) First, entry e will get reinserted into n3, which currently contains entries [g, h, i].
        #     (b) Since n3 now has 4 entries, it overflows.
        #     (c) Since n3 is at the same level as n2, and we already did a forced reinsert at that level, a regular
        #         split gets performed (instead of a forced reinsert).
        #     (d) The split will be propagated upward to the root level.
        #     (e) Since the root node is also at capacity, it will also overflow.
        #     (f) Forced reinsert never occurs at the root level, so a split is performed on the root node.
        #     (g) When the root node is split, the tree grows a level, and a new root node is created.
        #     (h) Forced reinsert of entry e is now complete.
        #     (i) Now, we still need to do the forced reinsert on entry d. Note that the tree structure has completely
        #         changed in the intervening time since entry e got reinserted. The fact that the structure has changed
        #         while we're still in the middle of reinserting entries is a source of much complexity, and the aim of
        #         this test is to ensure that this scenario is properly handled. In particular:
        #           - We must ensure that entry d gets inserted at the correct level of the tree. What was previously
        #             level 1 (immediately below the root) is now actually level 2. (This is why the rstar
        #             implementation keeps track of the level by counting from the leaf level, rather than from the
        #             root, since levels from leaf does not change.)
        #           - Since we must perform a forced reinsert at most once per level, if another forced reinsert causes
        #             another node to overflow, we must ensure to do a split instead of another forced reinsert. Indeed
        #             that is the case when reinserting entry d. Again, because the number of levels has changed, we
        #             must be very careful of how we track what levels we have done a forced reinsert on (this
        #             implementation counts from the leaf instead of from the root).
        #     (j) Entry d gets reinserted into node n1, which currently contains entries [a, b, c].
        #     (k) Since n1 now has 4 entries, it overflows.
        #     (l) Since n1 is at the same level as n2, and we already did a forced reinsert at this level, a regular
        #         split gets performed (instead of a forced reinsert).
        rstar_overflow(t, n2)

        # Assert
        # Tree should now have 3 levels
        self.assertEqual(3, len(t.get_levels()))
        # Root node bounding box should encompass all entries
        self.assertEqual(Rect(0, 0, 20, 10), t.root.get_bounding_rect())
        # Root node should have 2 child entries
        self.assertEqual(2, len(t.root.entries))
        # Ensure entries in the root node have the expected bounding boxes
        root_entry_1 = next((e for e in t.root.entries if e.rect == Rect(0, 0, 12, 9)))
        root_entry_2 = next((e for e in t.root.entries if e.rect == Rect(4, 4, 20, 10)))
        # Ensure children nodes of root_entry_1 and root_entry_2 are intermediate nodes
        intermediate_node_1 = root_entry_1.child
        intermediate_node_2 = root_entry_2.child
        self.assertFalse(intermediate_node_1.is_leaf)
        self.assertFalse(intermediate_node_1.is_root)
        self.assertFalse(intermediate_node_2.is_leaf)
        self.assertFalse(intermediate_node_2.is_root)
        # Ensure intermediate nodes have correct bounding boxes
        self.assertEqual(Rect(0, 0, 12, 9), intermediate_node_1.get_bounding_rect())
        self.assertEqual(Rect(4, 4, 20, 10), intermediate_node_2.get_bounding_rect())
        # Ensure intermediate nodes have the correct number of child entries
        self.assertEqual(2, len(intermediate_node_1.entries))
        self.assertEqual(3, len(intermediate_node_2.entries))
        # Ensure entries in the intermediate nodes have correct bounding boxes
        intermediate_entry_1 = next(e for e in intermediate_node_1.entries if e.rect == Rect(0, 0, 6, 4))
        intermediate_entry_2 = next(e for e in intermediate_node_1.entries if e.rect == Rect(5, 0, 12, 9))
        intermediate_entry_3 = next(e for e in intermediate_node_2.entries if e.rect == Rect(18, 8, 19, 10))
        intermediate_entry_4 = next(e for e in intermediate_node_2.entries if e.rect == Rect(7, 7, 20, 10))
        intermediate_entry_5 = next(e for e in intermediate_node_2.entries if e.rect == Rect(4, 4, 20, 7))
        # Get leaf child nodes
        leaf_node_1 = intermediate_entry_1.child
        leaf_node_2 = intermediate_entry_2.child
        leaf_node_3 = intermediate_entry_3.child
        leaf_node_4 = intermediate_entry_4.child
        leaf_node_5 = intermediate_entry_5.child
        # Ensure leaf nodes are properly marked as leaf nodes
        self.assertTrue(leaf_node_1.is_leaf)
        self.assertTrue(leaf_node_2.is_leaf)
        self.assertTrue(leaf_node_3.is_leaf)
        self.assertTrue(leaf_node_4.is_leaf)
        self.assertTrue(leaf_node_5.is_leaf)
        # Leaf nodes should not be inadvertently marked as root
        self.assertFalse(leaf_node_1.is_root)
        self.assertFalse(leaf_node_2.is_root)
        self.assertFalse(leaf_node_3.is_root)
        self.assertFalse(leaf_node_4.is_root)
        self.assertFalse(leaf_node_5.is_root)
        # Leaf node 1 should have entries [a, b, c]
        self.assertEqual(Rect(0, 0, 6, 4), leaf_node_1.get_bounding_rect())
        self.assertCountEqual([entry_a, entry_b, entry_c], leaf_node_1.entries)
        # Leaf node 2 should have entry [d]
        self.assertEqual(Rect(5, 0, 12, 9), leaf_node_2.get_bounding_rect())
        self.assertCountEqual([entry_d], leaf_node_2.entries)
        # Leaf node 3 should have entry [i]
        self.assertEqual(Rect(18, 8, 19, 10), leaf_node_3.get_bounding_rect())
        self.assertCountEqual([entry_i], leaf_node_3.entries)
        # Leaf node 4 should have entries [e, g, h]
        self.assertEqual(Rect(7, 7, 20, 10), leaf_node_4.get_bounding_rect())
        self.assertCountEqual([entry_e, entry_g, entry_h], leaf_node_4.entries)
        # Leaf node 5 should have entries [f, j]
        self.assertEqual(Rect(4, 4, 20, 7), leaf_node_5.get_bounding_rect())
        self.assertCountEqual([entry_f, entry_j], leaf_node_5.entries)


def _get_leaf_node_data(node: RTreeNode[T]) -> List[T]:
    """
    Returns the data from a leaf node's entries as a list
    :param node: Leaf node in an R-tree
    :return: Data elements in the entries contained in the leaf node
    """
    assert node.is_leaf
    return [e.data for e in node.entries]
