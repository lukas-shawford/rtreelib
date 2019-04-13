from unittest import TestCase
from rtreelib import RTreeGuttman, RTreeEntry, Rect
from rtreelib.strategies.guttman import least_enlargement, quadratic_split


class TestGuttman(TestCase):
    """Tests for Guttman R-Tree implementation"""

    def test_least_enlargement(self):
        """
        Ensure the node whose bounding box needs least enlargement is chosen for a new entry in the case where there is
        a clear winner.
        """
        # Arrange
        t = RTreeGuttman(max_entries=1)
        t.insert('a', Rect(0, 0, 3, 3))
        t.insert('b', Rect(9, 9, 10, 10))
        e = RTreeEntry(Rect(2, 2, 4, 4), data='c')
        # Act
        node = least_enlargement(t, e)
        # Assert
        self.assertEqual(Rect(0, 0, 3, 3), node.get_bounding_rect())

    def test_least_enlargement_tie(self):
        """
        When two nodes need to be enlarged by the same amount, the strategy should pick the node having the smallest
        area as a tie-breaker.
        """
        # Arrange
        t = RTreeGuttman(max_entries=1)
        t.insert('a', Rect(0, 0, 4, 2))
        t.insert('b', Rect(5, 1, 7, 3))
        e = RTreeEntry(Rect(4, 1, 5, 2), data='c')
        # Act
        node = least_enlargement(t, e)
        # Assert
        self.assertEqual(Rect(5, 1, 7, 3), node.get_bounding_rect())

    def test_quadratic_split(self):
        """Ensures that a split results in the smallest total area."""
        # Arrange
        t = RTreeGuttman(max_entries=4)
        t.insert('a', Rect(2, 8, 5, 9))
        t.insert('b', Rect(4, 0, 5, 10))
        t.insert('c', Rect(5, 0, 6, 10))
        t.insert('d', Rect(5, 7, 8, 8))
        # Act
        split_node = quadratic_split(t, t.root)
        # Assert
        group1 = [e.data for e in t.root.entries]
        group2 = [e.data for e in split_node.entries]
        self.assertCountEqual(['a', 'd'], group1)
        self.assertCountEqual(['b', 'c'], group2)

    def test_multiple_inserts_with_split(self):
        """
        Ensure multiple inserts causing a node split result in correct node structure.
        """
        t = RTreeGuttman(max_entries=3, min_entries=1)
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        t.insert('d', Rect(8, 8, 10, 10))
        t.insert('e', Rect(9, 9, 10, 10))
        self.assertEqual(Rect(0, 0, 10, 10), t.root.get_bounding_rect())
        self.assertEqual(2, len(t.root.entries))
        node1 = t.root.entries[0].child
        node2 = t.root.entries[1].child
        self.assertEqual(Rect(0, 0, 6, 6), node1.get_bounding_rect())
        self.assertEqual(Rect(8, 8, 10, 10), node2.get_bounding_rect())
