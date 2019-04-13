from unittest import TestCase
from rtreelib import RTree, Rect


class TestCommon(TestCase):
    """
    Common tests for basic R-Tree operations. Note the default implementation uses the Guttman strategy, so there will
    be some duplication between the common tests and Guttman tests.
    """

    def test_insert_creates_entry(self):
        """Basic test ensuring an insert creates an entry."""
        t = RTree()
        e = t.insert('foo', Rect(0, 0, 1, 1))
        self.assertEqual('foo', e.data)
        self.assertEqual(Rect(0, 0, 1, 1), e.rect)

    def test_multiple_inserts_without_split(self):
        """
        Ensure multiple inserts work (all original entries are returned) without a split (fewer entries than
        max_entries)
        """
        t = RTree(max_entries=5)
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        entries = list(t.get_leaf_entries())
        self.assertCountEqual(['a', 'b', 'c'], [entry.data for entry in entries])

    def test_bounding_rect_multiple_inserts_without_split(self):
        """
        Ensure root note bounding rect encompasses the bounding rect of all entries after multiple inserts (without
        forcing a split)
        """
        t = RTree(max_entries=5)
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        rect = t.root.get_bounding_rect()
        self.assertEqual(Rect(0, 0, 6, 6), rect)

    def test_multiple_inserts_with_split(self):
        """
        Ensure multiple inserts work (all original entries are returned) forcing a split (number of entries exceeds
        max_entries)
        """
        t = RTree(max_entries=3)
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        t.insert('d', Rect(8, 8, 10, 10))
        t.insert('e', Rect(9, 9, 10, 10))
        entries = list(t.get_leaf_entries())
        self.assertCountEqual(['a', 'b', 'c', 'd', 'e'], [entry.data for entry in entries])

    def test_bounding_rect_multiple_inserts_with_split(self):
        """
        Ensure root note bounding rect encompasses the bounding rect of all entries after multiple inserts (forcing a
        split)
        """
        t = RTree(max_entries=3)
        t.insert('a', Rect(0, 0, 5, 5))
        t.insert('b', Rect(1, 1, 3, 3))
        t.insert('c', Rect(4, 4, 6, 6))
        t.insert('d', Rect(8, 8, 10, 10))
        t.insert('e', Rect(9, 9, 10, 10))
        rect = t.root.get_bounding_rect()
        self.assertEqual(Rect(0, 0, 10, 10), rect)
