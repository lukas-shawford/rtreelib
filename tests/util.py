"""
Utility functions for creating R-trees shared across multiple tests. These use the default Guttman implementation.
"""

from typing import Dict, Optional
from unittest import TestCase
from rtreelib import Rect, RTree, RTreeEntry, RTreeNode


def create_simple_tree(test: TestCase, nodes: Optional[Dict[str, RTreeNode]] = None,
                       entries: Optional[Dict[str, RTreeEntry]] = None) -> RTree:
    """
    Creates a simple R-tree with 5 entries split across 3 nodes (1 root, 2 leaves). Asserts that the resulting tree has
    the expected structure, and optionally sets the nodes/entries in the passed in dictionaries for easy access (if
    provided).

    Resulting structure:
    * Root [R]: Rect(0, 0, 10, 10)
        - Leaf node 1 [L1]: Rect(0, 0, 6, 6), Leaf Entries [a, b, c]
        - Leaf node 2 [L2]: Rect(8, 8, 10, 10), Leaf Entries [d, e]
    """
    t = RTree(max_entries=3, min_entries=1)
    t.insert('a', Rect(0, 0, 5, 5))
    t.insert('b', Rect(1, 1, 3, 3))
    t.insert('c', Rect(4, 4, 6, 6))
    t.insert('d', Rect(8, 8, 10, 10))
    t.insert('e', Rect(9, 9, 10, 10))

    # Ensure tree has expected structure
    # Root node bounding rectangle should encompass all entries
    test.assertEqual(Rect(0, 0, 10, 10), t.root.get_bounding_rect())
    # Root node should have 2 child entries
    test.assertEqual(2, len(t.root.entries))
    root_entry_1, root_entry_2 = t.root.entries
    # Root entry 1 bounding rectangle should encompass leaf entries [a, b, c]
    test.assertEqual(Rect(0, 0, 6, 6), root_entry_1.rect)
    # Root entry 2 bounding rectangle should encompass leaf entries [d, e]
    test.assertEqual(Rect(8, 8, 10, 10), root_entry_2.rect)
    # Get the leaf nodes
    leaf_node_1 = root_entry_1.child
    leaf_node_2 = root_entry_2.child
    # Ensure the leaf nodes are properly marked as being leaf nodes
    test.assertTrue(leaf_node_1.is_leaf)
    test.assertTrue(leaf_node_2.is_leaf)
    # Ensure the leaf nodes are not marked as root
    test.assertFalse(leaf_node_1.is_root)
    test.assertFalse(leaf_node_2.is_root)
    # Leaf node 1 should contain entries [a, b, c]
    test.assertEqual(3, len(leaf_node_1.entries))
    entry_a = get_entry(leaf_node_1, 'a')
    entry_b = get_entry(leaf_node_1, 'b')
    entry_c = get_entry(leaf_node_1, 'c')
    # Leaf node 2 should contain entries [d, e]
    test.assertEqual(2, len(leaf_node_2.entries))
    entry_d = get_entry(leaf_node_2, 'd')
    entry_e = get_entry(leaf_node_2, 'e')
    # Ensure leaf node bounding rectangles are correct
    test.assertEqual(Rect(0, 0, 6, 6), leaf_node_1.get_bounding_rect())
    test.assertEqual(Rect(8, 8, 10, 10), leaf_node_2.get_bounding_rect())
    # Ensure leaf entry bounding rectangles are correct
    test.assertEqual(Rect(0, 0, 5, 5), entry_a.rect)
    test.assertEqual(Rect(1, 1, 3, 3), entry_b.rect)
    test.assertEqual(Rect(4, 4, 6, 6), entry_c.rect)
    test.assertEqual(Rect(8, 8, 10, 10), entry_d.rect)
    test.assertEqual(Rect(9, 9, 10, 10), entry_e.rect)

    # Assign nodes and entries to the corresponding dictionary for easy access (if passed in)
    if nodes is not None:
        nodes['R'] = t.root
        nodes['L1'] = leaf_node_1
        nodes['L2'] = leaf_node_2
    if entries is not None:
        entries['a'] = entry_a
        entries['b'] = entry_b
        entries['c'] = entry_c
        entries['d'] = entry_d
        entries['e'] = entry_e

    return t


def create_complex_tree(test: TestCase, nodes: Optional[Dict[str, RTreeNode]] = None,
                        entries: Optional[Dict[str, RTreeEntry]] = None) -> RTree:
    """
    Creates a more complex R-tree with 10 entries split across 7 nodes (1 root, 2 children at level 1, then a total
    of 4 leaf nodes at level 2). Asserts that the resulting tree has the expected structure, and optionally sets the
    nodes/entries in the passed in dictionaries for easy access (if provided).

    Resulting structure:
    * Root [R]: Rect(0, 0, 11, 10)
        - Intermediate child 1 [I1]: Rect(0, 5, 10, 10), Leaf Entries [d, e, f, g, j]
            * Leaf child 1 [L1]: Rect(0, 5, 4, 10), Leaf Entries [f, g, j]
            * Leaf child 2 [L2]: Rect(6, 6, 10, 9), Leaf Entries [d, e]
        - Intermediate child 2 [I2]: Rect(0, 0, 11, 5), Leaf Entries [a, b, c, h, i]
            * Leaf child 3 [L3]: Rect(7, 0, 11, 5), Leaf Entries [h, i]
            * Leaf child 4 [L4]: Rect(0, 0, 6, 4), Leaf Entries [a, b, c]
    """
    t = RTree(max_entries=3, min_entries=1)
    t.insert('a', Rect(0, 0, 5, 2))
    t.insert('b', Rect(1, 1, 2, 3))
    t.insert('c', Rect(2, 2, 6, 4))
    t.insert('d', Rect(6, 6, 9, 8))
    t.insert('e', Rect(8, 7, 10, 9))
    t.insert('f', Rect(1, 5, 3, 9))
    t.insert('g', Rect(2, 8, 4, 10))
    t.insert('h', Rect(7, 2, 10, 5))
    t.insert('i', Rect(9, 0, 11, 3))
    t.insert('j', Rect(0, 5, 2, 7))

    # Ensure tree has expected structure
    # Root node bounding rectangle should encompass all entries
    test.assertEqual(Rect(0, 0, 11, 10), t.root.get_bounding_rect())
    # Root node should have 2 child entries
    test.assertEqual(2, len(t.root.entries))
    root_entry_1, root_entry_2 = t.root.entries
    # Root entry 1 bounding rectangle should encompass leaf entries [d, e, f, g, j]
    test.assertEqual(Rect(0, 5, 10, 10), root_entry_1.rect)
    # Root entry 2 bounding rectangle should encompass leaf entries [a, b, c, h, i]
    test.assertEqual(Rect(0, 0, 11, 5), root_entry_2.rect)
    # Get the children nodes corresponding to the entries in the root node.
    intermediate_node_1 = root_entry_1.child
    intermediate_node_2 = root_entry_2.child
    # Ensure the intermediate nodes are not marked as leaf or root
    test.assertFalse(intermediate_node_1.is_leaf)
    test.assertFalse(intermediate_node_1.is_root)
    test.assertFalse(intermediate_node_2.is_leaf)
    test.assertFalse(intermediate_node_2.is_root)
    # Intermediate node 1 should contain 2 child entries
    test.assertEqual(2, len(intermediate_node_1.entries))
    # Intermediate node 1 bounding rectangle should encompass leaf entries [f, g, j]
    test.assertEqual(Rect(0, 5, 10, 10), intermediate_node_1.get_bounding_rect())
    # Intermediate node 2 should contain 2 child entries
    test.assertEqual(2, len(intermediate_node_2.entries))
    # Intermediate node 2 bounding rectangle should encompass leaf entries [d, e]
    test.assertEqual(Rect(0, 0, 11, 5), intermediate_node_2.get_bounding_rect())
    # Get references to the entries in the intermediate nodes
    intermediate_entry_1 = intermediate_node_1.entries[0]
    intermediate_entry_2 = intermediate_node_1.entries[1]
    intermediate_entry_3 = intermediate_node_2.entries[0]
    intermediate_entry_4 = intermediate_node_2.entries[1]
    # Ensure the bounding rectangles are correct for the entries in the intermediate nodes
    test.assertEqual(Rect(0, 5, 4, 10), intermediate_entry_1.rect)
    test.assertEqual(Rect(6, 6, 10, 9), intermediate_entry_2.rect)
    test.assertEqual(Rect(7, 0, 11, 5), intermediate_entry_3.rect)
    test.assertEqual(Rect(0, 0, 6, 4), intermediate_entry_4.rect)
    # Get the leaf nodes from the child entries of the intermediate nodes
    leaf_node_1 = intermediate_entry_1.child
    leaf_node_2 = intermediate_entry_2.child
    leaf_node_3 = intermediate_entry_3.child
    leaf_node_4 = intermediate_entry_4.child
    # Ensure the leaf nodes are properly marked as being leaf nodes
    test.assertTrue(leaf_node_1.is_leaf)
    test.assertTrue(leaf_node_2.is_leaf)
    test.assertTrue(leaf_node_3.is_leaf)
    test.assertTrue(leaf_node_4.is_leaf)
    # Leaf node 1 should contain entries [f, g, j]
    test.assertEqual(3, len(leaf_node_1.entries))
    entry_f = get_entry(leaf_node_1, 'f')
    entry_g = get_entry(leaf_node_1, 'g')
    entry_j = get_entry(leaf_node_1, 'j')
    # Leaf node 2 should contain entries [d, e]
    test.assertEqual(2, len(leaf_node_2.entries))
    entry_d = get_entry(leaf_node_2, 'd')
    entry_e = get_entry(leaf_node_2, 'e')
    # Leaf node 3 should contain entries [h, i]
    test.assertEqual(2, len(leaf_node_3.entries))
    entry_h = get_entry(leaf_node_3, 'h')
    entry_i = get_entry(leaf_node_3, 'i')
    # Leaf node 4 should contain entries [a, b, c]
    test.assertEqual(3, len(leaf_node_4.entries))
    entry_a = get_entry(leaf_node_4, 'a')
    entry_b = get_entry(leaf_node_4, 'b')
    entry_c = get_entry(leaf_node_4, 'c')
    # Ensure leaf node bounding rectangles are correct
    test.assertEqual(Rect(0, 5, 4, 10), leaf_node_1.get_bounding_rect())
    test.assertEqual(Rect(6, 6, 10, 9), leaf_node_2.get_bounding_rect())
    test.assertEqual(Rect(7, 0, 11, 5), leaf_node_3.get_bounding_rect())
    test.assertEqual(Rect(0, 0, 6, 4), leaf_node_4.get_bounding_rect())
    # Ensure leaf entry bounding rectangles are correct
    test.assertEqual(Rect(0, 0, 5, 2), entry_a.rect)
    test.assertEqual(Rect(1, 1, 2, 3), entry_b.rect)
    test.assertEqual(Rect(2, 2, 6, 4), entry_c.rect)
    test.assertEqual(Rect(6, 6, 9, 8), entry_d.rect)
    test.assertEqual(Rect(8, 7, 10, 9), entry_e.rect)
    test.assertEqual(Rect(1, 5, 3, 9), entry_f.rect)
    test.assertEqual(Rect(2, 8, 4, 10), entry_g.rect)
    test.assertEqual(Rect(7, 2, 10, 5), entry_h.rect)
    test.assertEqual(Rect(9, 0, 11, 3), entry_i.rect)
    test.assertEqual(Rect(0, 5, 2, 7), entry_j.rect)

    # Assign nodes and entries to the corresponding dictionary for easy access (if passed in)
    if nodes is not None:
        nodes['R'] = t.root
        nodes['I1'] = intermediate_node_1
        nodes['I2'] = intermediate_node_2
        nodes['L1'] = leaf_node_1
        nodes['L2'] = leaf_node_2
        nodes['L3'] = leaf_node_3
        nodes['L4'] = leaf_node_4
    if entries is not None:
        entries['a'] = entry_a
        entries['b'] = entry_b
        entries['c'] = entry_c
        entries['d'] = entry_d
        entries['e'] = entry_e
        entries['f'] = entry_f
        entries['g'] = entry_g
        entries['h'] = entry_h
        entries['i'] = entry_i
        entries['j'] = entry_j

    return t


def get_entry(node: RTreeNode, data: str):
    return next((e for e in node.entries if e.data == data))
