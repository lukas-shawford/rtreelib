from unittest import TestCase
from rtreelib import Rect, RTree, RTreeEntry
from rtreelib.strategies.base import least_area_enlargement


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
        t = RTree(max_entries=3)

        # Act
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        t.insert('d', Rect(8, 8, 10, 10))
        t.insert('e', Rect(9, 9, 10, 10))

        # Assert
        entries = list(t.get_leaf_entries())
        self.assertCountEqual(['a', 'b', 'c', 'd', 'e'], [entry.data for entry in entries])

    def test_bounding_rect_multiple_inserts_with_split(self):
        """
        Ensure root note bounding rect encompasses the bounding rect of all entries after multiple inserts (forcing a
        split)
        """
        # Arrange
        t = RTree(max_entries=3)

        # Act
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        t.insert('d', Rect(8, 8, 10, 10))
        t.insert('e', Rect(9, 9, 10, 10))

        # Assert
        rect = t.root.get_bounding_rect()
        self.assertEqual(Rect(0, 0, 10, 10), rect)
