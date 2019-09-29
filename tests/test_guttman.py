from unittest import TestCase
from rtreelib import RTreeGuttman, RTreeNode, RTreeEntry, Rect
from rtreelib.strategies.guttman import quadratic_split, adjust_tree_strategy


class TestGuttman(TestCase):
    """Tests for Guttman R-Tree implementation"""

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

    def test_adjust_tree_without_split(self):
        """
        Ensure parent entry bounding rectangles are updated correctly when an entry is added without necessitating a
        node split.
        """
        # Arrange
        t = RTreeGuttman(max_entries=3)
        r1 = Rect(0, 0, 3, 2)
        r2 = Rect(5, 5, 7, 7)
        t.root = RTreeNode(t, is_leaf=False)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        n1 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_a])
        n2 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_b])
        e1 = RTreeEntry(r1, child=n1)
        e2 = RTreeEntry(r2, child=n2)
        t.root.entries = [e1, e2]
        # Arrange entry being inserted
        r3 = Rect(2, 1, 4, 3)
        entry_c = RTreeEntry(r3, data='c')
        # Manually insert the new entry into node n1, but without adjusting the covering rectangle of the corresponding
        # parent entry in the root node (e1), since that is what we are testing.
        n1.entries.append(entry_c)
        # At this point, the parent entry's covering rectangle will not be correct yet as it only encompasses entry_a.
        # Ensure this is the case (though this is not the focus of this test)
        self.assertEqual(Rect(0, 0, 3, 2), e1.rect)

        # Act
        adjust_tree_strategy(t, n1, None)

        # Assert
        # Ensure e1's bounding rectangle now encompasses both entry_a and entry_c
        self.assertEqual(Rect(0, 0, 4, 3), e1.rect)
        # e2's bounding rectangle should remain unchanged
        self.assertEqual(Rect(5, 5, 7, 7), e2.rect)

    def test_adjust_tree_with_split_no_propagate(self):
        """
        Ensure parent entry bounding rectangles are updated correctly when a node is split, but it is not necessary to
        propagate the split upward.
        """
        # Arrange
        t = RTreeGuttman(max_entries=3)
        r1 = Rect(0, 0, 3, 2)
        r2 = Rect(2, 1, 5, 3)
        r3 = Rect(4, 2, 6, 4)
        r4 = Rect(6, 6, 8, 8)
        r5 = Rect(7, 7, 10, 9)
        t.root = RTreeNode(t, is_leaf=False)
        entry_a = RTreeEntry(r1, data='a')
        entry_b = RTreeEntry(r2, data='b')
        entry_c = RTreeEntry(r3, data='c')
        entry_d = RTreeEntry(r4, data='d')
        entry_e = RTreeEntry(r5, data='e')
        n1 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_a, entry_b, entry_c])
        n2 = RTreeNode(t, is_leaf=True, parent=t.root, entries=[entry_d, entry_e])
        e1 = RTreeEntry(Rect(0, 0, 6, 4), child=n1)
        e2 = RTreeEntry(Rect(6, 6, 10, 9), child=n2)
        t.root.entries = [e1, e2]
        # Arrange entry being inserted
        r6 = Rect(1, 3, 2, 5)
        entry_f = RTreeEntry(r6, data='f')
        # Manually insert the new entry into node n1, causing it to be overfull.
        n1.entries.append(entry_f)
        # Manually perform node split, but without adjusting the tree yet (since that is the focus of this test)
        split_node = t.perform_node_split(n1, [entry_a, entry_f], [entry_c, entry_b])
        # Ensure preconditions:
        # At this point, the parent entry e1 in the root node will still have the old covering rectangle.
        self.assertEqual(Rect(0, 0, 6, 4), e1.rect)
        # At this point, the root node will only have 2 entries for e1 and e2
        self.assertCountEqual([e1, e2], t.root.entries)

        # Act
        adjust_tree_strategy(t, n1, split_node)

        # Assert
        # Ensure the root node now has 3 child entries
        self.assertEqual(3, len(t.root.entries))
        # The child entries should correspond to nodes n1, n2, and the new split node
        self.assertEqual([n1, n2, split_node], [e.child for e in t.root.entries])
        # Ensure each node has the correct entries
        self.assertEqual([entry_a, entry_f], n1.entries)
        self.assertEqual([entry_d, entry_e], n2.entries)
        self.assertEqual([entry_c, entry_b], split_node.entries)
        # Ensure bounding rectangles have been property updated for all entries
        self.assertEqual(Rect(0, 0, 3, 5), t.root.entries[0].rect)
        self.assertEqual(Rect(6, 6, 10, 9), t.root.entries[1].rect)
        self.assertEqual(Rect(2, 1, 6, 4), t.root.entries[2].rect)
        # Bounding rectangle for the root node should encompass all entries
        self.assertEqual(Rect(0, 0, 10, 9), t.root.get_bounding_rect())

    def test_adjust_tree_with_split_and_propagate(self):
        """
        Ensure parent entry bounding rectangles are updated correctly when a node is split, and it is necessary to
        propagate the split upward. This scenario should result in a new root node being created, and the tree growing
        an extra level.
        """
        # Arrange
        t = RTreeGuttman(max_entries=2)
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
        # Arrange entry being inserted
        r5 = Rect(4, 2, 6, 4)
        entry_e = RTreeEntry(r5, data='e')
        # Manually insert the new entry into node n1, causing it to be overfull.
        n1.entries.append(entry_e)
        # Manually perform node split, but without adjusting the tree yet (since that is the focus of this test)
        split_node = t.perform_node_split(n1, [entry_a], [entry_e, entry_b])
        # Ensure preconditions:
        # At this point, the parent entry e1 in the root node will still have the old covering rectangle.
        self.assertEqual(Rect(0, 0, 5, 3), e1.rect)
        # At this point, the root node will only have 2 entries for e1 and e2
        self.assertCountEqual([e1, e2], t.root.entries)

        # Act
        adjust_tree_strategy(t, n1, split_node)

        # Assert
        # Root node bounding rectangle should encompass all entries
        self.assertEqual(Rect(0, 0, 10, 9), t.root.get_bounding_rect())
        # Root node should have 2 child entries
        self.assertEqual(2, len(t.root.entries))
        root_entry_1, root_entry_2 = t.root.entries
        # Root entry 1 bounding rectangle should encompass leaf entries [a, b, e]
        self.assertEqual(Rect(0, 0, 6, 4), root_entry_1.rect)
        # Root entry 2 bounding rectangle should encompass leaf entries [c, d]
        self.assertEqual(Rect(6, 6, 10, 9), root_entry_2.rect)
        # Get the children nodes corresponding to the entries in the root node.
        intermediate_node_1 = root_entry_1.child
        intermediate_node_2 = root_entry_2.child
        # Ensure the intermediate nodes are not marked as leaf or root
        self.assertFalse(intermediate_node_1.is_leaf)
        self.assertFalse(intermediate_node_1.is_root)
        self.assertFalse(intermediate_node_2.is_leaf)
        self.assertFalse(intermediate_node_2.is_root)
        # Intermediate node 1 should contain 2 child entries
        self.assertEqual(2, len(intermediate_node_1.entries))
        # Intermediate node 1 bounding rectangle should encompass leaf entries [a, b, e]
        self.assertEqual(Rect(0, 0, 6, 4), intermediate_node_1.get_bounding_rect())
        # Intermediate node 2 should contain 1 child entry
        self.assertEqual(1, len(intermediate_node_2.entries))
        # Intermediate node 2 bounding rectangle should encompass leaf entries [c, d]
        self.assertEqual(Rect(6, 6, 10, 9), intermediate_node_2.get_bounding_rect())
        # Get references to the entries in the intermediate nodes
        intermediate_entry_1 = intermediate_node_1.entries[0]
        intermediate_entry_2 = intermediate_node_1.entries[1]
        intermediate_entry_3 = intermediate_node_2.entries[0]
        # Ensure the bounding rectangles are correct for the entries in the intermediate nodes
        self.assertEqual(Rect(0, 0, 3, 2), intermediate_entry_1.rect)
        self.assertEqual(Rect(2, 1, 6, 4), intermediate_entry_2.rect)
        self.assertEqual(Rect(6, 6, 10, 9), intermediate_entry_3.rect)
        # Get the leaf nodes from the child entries of the intermediate nodes
        leaf_node_1 = intermediate_entry_1.child
        leaf_node_2 = intermediate_entry_2.child
        leaf_node_3 = intermediate_entry_3.child
        # Ensure the leaf nodes are properly marked as being leaf nodes
        self.assertTrue(leaf_node_1.is_leaf)
        self.assertTrue(leaf_node_2.is_leaf)
        self.assertTrue(leaf_node_3.is_leaf)
        # Leaf node 1 should contain a single child entry for entry_a
        self.assertEqual([entry_a], leaf_node_1.entries)
        # Leaf node 2 should contain entries [e, b]
        self.assertEqual([entry_e, entry_b], leaf_node_2.entries)
        # Leaf node 3 should contain entries [c, d]
        self.assertEqual([entry_c, entry_d], leaf_node_3.entries)
        # Ensure leaf node bounding rectangles are correct
        self.assertEqual(Rect(0, 0, 3, 2), leaf_node_1.get_bounding_rect())
        self.assertEqual(Rect(2, 1, 6, 4), leaf_node_2.get_bounding_rect())
        self.assertEqual(Rect(6, 6, 10, 9), leaf_node_3.get_bounding_rect())

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
