import os
import platform
import subprocess
import tempfile
from ..rtree import RTreeBase, RTreeNode, RTreeEntry

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import pydot
    from tqdm import tqdm
except ImportError:
    raise RuntimeError("The following libraries are required to create R-Tree diagrams: matplotlib, pydot, tqdm")


def create_rtree_diagram(tree: RTreeBase, title=None, filename_ps=None, filename_dot=None, include_images=True):
    """
    Creates an R-Tree diagram for visualizing the tree structure using graphviz. Note that the diagram may be large and
    take a while to generate, especially if include_images is set to True.
    :param tree: R-Tree to draw
    :param title: Optional title
    :param filename_ps: Optional filename for the generated diagram. If not provided, a temporary filename will be
        generated.
    :param filename_dot: Optional filename for the 'dot' graphviz file that will be used as an intermediate file for
        creating the diagram. If not provided, a temporary filename will be generated.
    :param include_images: If true, each node and entry in the diagram will contain an embedded plot that helps
        visualize where the node/entry is located in relation to the other nodes/entries. Note this may slow down
        diagram generation significantly.
    """
    graph = pydot.Dot(graph_type='digraph', label=title, labelloc='t')
    graph.set_node_defaults(shape='plaintext')
    _draw_rtree_nodes(graph, tree, include_images)
    _draw_rtree_edges(graph, tree.root)
    filename_ps = filename_ps or tempfile.mkstemp('.ps')[1]
    graph.write(filename_ps, format='ps')
    filename_dot = filename_dot or tempfile.mkstemp('.dot')[1]
    graph.write(filename_dot)
    _invoke_file(filename_ps)


def plot_rtree(tree: RTreeBase, filename=None, show=True, highlight_node=None, highlight_entry=None):
    """
    Create a cartesian plot (using matplotlib) of the R-Tree nodes/entries. Each node's bounding rectangle
    is plotted as a tan rectangle with dashed edges, and each leaf entry's bounding rectangle is plotted in
    blue. A particular node or entry may be highlighted in the plot by passing in highlight_node and/or
    highlight_entry.
    :param tree: R-Tree instance to plot
    :param filename: If passed in, the plot will be saved to a file
    :param show: If True, show the plot
    :param highlight_node: R-Tree node to highlight
    :param highlight_entry: R-Tree leaf entry to highlight
    """
    fig, ax = plt.subplots(1)
    bbox = tree.root.get_bounding_rect()
    padx, pady = (0.1 * bbox.width, 0.1 * bbox.height)
    ax.set_xlim(left=bbox.min_x - padx, right=bbox.max_x + padx)
    ax.set_ylim(bottom=bbox.min_y - pady, top=bbox.max_y + pady)
    _plot_rtree_leaves(ax, tree, highlight_entry)
    _plot_rtree_nodes(ax, tree, highlight_node)
    if filename:
        plt.savefig(filename, bbox_inches='tight')
    if show:
        plt.show()
    plt.close(fig)


def _draw_rtree_nodes(graph, tree: RTreeBase, include_images):
    num_plots = len(list(tree.get_nodes())) + len(list(tree.get_leaf_entries()))
    with tqdm(total=num_plots, desc="Drawing R-Tree", unit="node") as pbar:
        for level, nodes in enumerate(tree.get_levels()):
            subgraph = pydot.Subgraph(rank='same')
            graph.add_subgraph(subgraph)
            for node in nodes:
                img = None
                if include_images:
                    img = tempfile.mkstemp(prefix='node_', suffix='.png')[1]
                    highlight_node = node if not node.is_root else None
                    plot_rtree(tree, filename=img, show=False, highlight_node=highlight_node)
                subgraph.add_node(_rtree_node_to_pydot(node, img))
                pbar.update()
        leaf_subgraph = pydot.Subgraph(rank='same')
        graph.add_subgraph(leaf_subgraph)
        for entry in tree.get_leaf_entries():
            img = None
            if include_images:
                img = tempfile.mkstemp(prefix='entry_', suffix='.png')[1]
                plot_rtree(tree, filename=img, show=False, highlight_entry=entry)
            leaf_subgraph.add_node(_rtree_leaf_entry_to_pydot(entry, img))
            pbar.update()


def _rtree_node_to_pydot(node: RTreeNode, img=None):
    rect = node.get_bounding_rect()
    num_children = len(node.entries)
    children_cells = ''.join([f'<td port="{id(entry)}"><font point-size="8">{entry}</font></td>'
                              for entry in node.entries])
    rect_str = f'({rect.min_x}, {rect.min_y}, {rect.max_x}, {rect.max_y})'
    img_row = f'<tr><td border="0" colspan="{num_children}"><img src="{img}"/></td></tr>' if img else ''
    return pydot.Node(
        id(node),
        label=f'''<<table border="1" cellborder="1" cellspacing="2">
                <tr><td border="0" colspan="{num_children}"><font point-size="8"><b>{node}</b></font></td></tr>
                <tr><td border="0" colspan="{num_children}"><font point-size="8">rect={rect_str}</font></td></tr>
                <tr><td border="0" colspan="{num_children}"><font point-size="8">area={rect.area()}</font></td></tr>
                {img_row}
                <tr>{children_cells}</tr>
            </table>>'''
    )


def _rtree_leaf_entry_to_pydot(entry: RTreeEntry, img=None):
    assert entry.is_leaf
    rect = entry.rect
    rect_str = f'({rect.min_x}, {rect.min_y}, {rect.max_x}, {rect.max_y})'
    img_row = f'<tr><td><img src="{img}"/></td></tr>' if img else ''
    data_str = f'<tr><td><font point-size="8">data={entry.data}</font></td></tr>' if entry.is_leaf else None
    return pydot.Node(
        id(entry),
        label=f'''<<table border="1" cellborder="0" cellspacing="0">
                      <tr><td><font point-size="8"><b>{entry}</b></font></td></tr>
                      <tr><td><font point-size="8">rect={rect_str}</font></td></tr>
                      {data_str}
                      {img_row}
                  </table>>'''
    )


def _draw_rtree_edges(graph, node: RTreeNode):
    for entry in node.entries:
        graph.add_edge(pydot.Edge(id(node), id(entry) if node.is_leaf else id(entry.child), tailport=id(entry)))
    if not node.is_leaf:
        for entry in node.entries:
            _draw_rtree_edges(graph, entry.child)


def _invoke_file(filepath):
    if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':  # Windows
        # noinspection PyUnresolvedReferences
        os.startfile(filepath)
    else:  # linux variants
        subprocess.call(('xdg-open', filepath))


def _plot_rtree_leaves(ax, tree, highlight_entry=None):
    for entry in tree.get_leaf_entries():
        xy = (entry.rect.min_x, entry.rect.min_y)
        w, h = (entry.rect.width, entry.rect.height)
        highlight = entry is highlight_entry
        edgecolor = (0.78, 0.24, 0.52) if highlight else (0.24, 0.52, 0.78)
        facecolor = (0.78, 0.24, 0.52, 0.64) if highlight else (0.24, 0.52, 0.78, 0.5)
        text_color = (0.25, 0.08, 0.17) if highlight else (0.09, 0.19, 0.29)
        text_facecolor = (0.78, 0.24, 0.52, 0.25) if highlight else (0.24, 0.52, 0.78, 0.25)
        patch = patches.Rectangle(xy, w, h, linewidth=1, edgecolor=edgecolor, facecolor=facecolor)
        ax.add_patch(patch)
        plt.annotate(
            s=entry.data,
            color=text_color,
            fontsize=6,
            fontweight='bold',
            xy=xy,
            xytext=(5, 4),
            textcoords='offset pixels',
            bbox=dict(fc=text_facecolor, ec='none', pad=3),
            va='bottom',
            ha='left')


def _plot_rtree_nodes(ax, tree, highlight_node=None):
    for node in tree.get_nodes():
        rect = node.get_bounding_rect()
        xy = (rect.min_x, rect.min_y)
        w, h = (rect.width, rect.height)
        highlight = node is highlight_node
        edgecolor = (0.82, 0.57, 0.55) if highlight else (0.82, 0.71, 0.55, 0.5)
        facecolor = (0.82, 0.57, 0.55, 0.6) if highlight else (0.82, 0.71, 0.55, 0.25)
        patch = patches.Rectangle(xy, w, h, linewidth=2, linestyle='--',
                                  edgecolor=edgecolor, facecolor=facecolor)
        ax.add_patch(patch)
