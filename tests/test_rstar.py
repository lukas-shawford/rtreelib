from unittest import TestCase
from unittest.mock import patch
from rtreelib import Rect, RTree, RTreeNode, RTreeEntry
from rtreelib.strategies.rstar import (
    rstar_choose_leaf, least_overlap_enlargement, get_entry_divisions, choose_split_axis, choose_split_index)


class TestRStar(TestCase):
    """Tests for R*-Tree implementation"""

    def test_least_overlap_enlargement(self):
        """
        Basic test of least overlap enlargement helper method. This test demonstrates a scenario where least area
        enlargement would favor one entry, but least overlap enlargment favors another.
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
        the level above a leaf.
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

    def test_get_entry_divisions_1_3(self):
        """Tests get_entry_divisions with m=1 and M=3"""
        # Arrange
        rect = Rect(0, 0, 0, 0)
        a = RTreeEntry(data='a', rect=rect)
        b = RTreeEntry(data='b', rect=rect)
        c = RTreeEntry(data='c', rect=rect)
        d = RTreeEntry(data='d', rect=rect)
        # Act
        divisions = get_entry_divisions([a, b, c, d], 1, 3)
        # Assert
        self.assertEqual(3, len(divisions))
        self.assertEqual(([a], [b, c, d]), divisions[0])
        self.assertEqual(([a, b], [c, d]), divisions[1])
        self.assertEqual(([a, b, c], [d]), divisions[2])

    def test_get_entry_divisions_2_4(self):
        """Tests get_entry_divisions with m=2 and M=4"""
        # Arrange
        rect = Rect(0, 0, 0, 0)
        a = RTreeEntry(data='a', rect=rect)
        b = RTreeEntry(data='b', rect=rect)
        c = RTreeEntry(data='c', rect=rect)
        d = RTreeEntry(data='d', rect=rect)
        e = RTreeEntry(data='e', rect=rect)
        # Act
        divisions = get_entry_divisions([a, b, c, d, e], 2, 4)
        # Assert
        self.assertEqual(2, len(divisions))
        self.assertEqual(([a, b], [c, d, e]), divisions[0])
        self.assertEqual(([a, b, c], [d, e]), divisions[1])

    def test_get_entry_divisions_1_4(self):
        """Tests get_entry_divisions with m=1 and M=4"""
        # Arrange
        rect = Rect(0, 0, 0, 0)
        a = RTreeEntry(data='a', rect=rect)
        b = RTreeEntry(data='b', rect=rect)
        c = RTreeEntry(data='c', rect=rect)
        d = RTreeEntry(data='d', rect=rect)
        e = RTreeEntry(data='e', rect=rect)
        # Act
        divisions = get_entry_divisions([a, b, c, d, e], 1, 4)
        # Assert
        self.assertEqual(4, len(divisions))
        self.assertEqual(([a], [b, c, d, e]), divisions[0])
        self.assertEqual(([a, b], [c, d, e]), divisions[1])
        self.assertEqual(([a, b, c], [d, e]), divisions[2])
        self.assertEqual(([a, b, c, d], [e]), divisions[3])

    def test_choose_split_axis(self):
        """
        Ensure split axis is chosen based on smallest overall perimeter of all possible divisions of a list of entries.
        In the below scenario, there is a clear winner with the best division being ([a, b, c], [d]).
        """
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 0, 1, 1))
        b = RTreeEntry(data='a', rect=Rect(1, 0, 2, 1))
        c = RTreeEntry(data='a', rect=Rect(2, 0, 3, 1))
        d = RTreeEntry(data='a', rect=Rect(1, 7, 2, 8))
        # Act
        result = choose_split_axis([a, b, c, d], 1, 3)
        # Assert
        self.assertEqual('y', result.axis)
        self.assertEqual([0, 0, 0, 7], [e.rect.min_y for e in result.sorted_entries_min])

    def test_choose_split_index(self):
        """Ensures best split index is chosen based on minimum overlap."""
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 1, 4, 5))
        b = RTreeEntry(data='b', rect=Rect(3, 5, 6, 8))
        c = RTreeEntry(data='c', rect=Rect(7, 0, 9, 4))
        d = RTreeEntry(data='d', rect=Rect(8, 7, 10, 9))
        divisions = [
            ([a], [b, c, d]),
            ([a, b], [c, d]),
            ([a, b, c], [d])
        ]
        # Act
        i = choose_split_index(divisions)
        # Assert
        self.assertEqual(1, i)

    def test_choose_split_index_tie(self):
        """When multiple divisions have the same overlap, ensure split index is chosen based on minimum area."""
        # Arrange
        a = RTreeEntry(data='a', rect=Rect(0, 1, 4, 5))
        b = RTreeEntry(data='b', rect=Rect(3, 5, 6, 8))
        c = RTreeEntry(data='c', rect=Rect(6, 0, 8, 4))
        d = RTreeEntry(data='d', rect=Rect(8, 7, 10, 9))
        divisions = [
            ([a], [b, c, d]),
            ([a, b], [c, d]),
            ([a, b, c], [d])
        ]
        # Act
        i = choose_split_index(divisions)
        # Assert
        self.assertEqual(2, i)
