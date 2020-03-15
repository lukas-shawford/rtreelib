"""
Module containing utility functions for exporting R-trees to a PostGIS database.

Note that psycopg2 must be installed in order to use the functions in this module. When installing using pip, ensure
that you do *NOT* use the binary distribution to avoid console warnings by passing the --no-binary option as follows:

pip install psycopg2 --no-binary=psycopg2

There are three ways of connecting to the database using this module:

(1) Initialize a connection pool by calling init_db_pool with the connection information. This allows using the other
    functions in this module without having to pass around connection info.
(2) Manually open the connection yourself, and pass in the connection object to the function.
(3) Pass in keyword arguments that can be used to establish the database connection.

Check the documentation for more detailed information and examples.
"""

import string
import pkg_resources
from typing import Union, Type, Dict
from .rtree import RTreeBase, RTreeNode, RTreeEntry

try:
    import psycopg2
    import psycopg2.pool
    from psycopg2.extras import DictCursor
except ImportError:
    raise RuntimeError("The following libraries are required to export R-trees to PostGIS: psycopg2")

pool = None


def init_db_pool(*args, **kwargs):
    """
    Initializes a connection pool for database connections. This allows calling the other methods in this module without
    having to pass in connection info. This function accepts the same arguments as the psycopg2.connect function.
    """
    global pool
    pool = psycopg2.pool.SimpleConnectionPool(1, 20, *args, **kwargs)


def create_rtree_tables(conn=None, schema: str = 'public', srid: int = 0, datatype: Union[Type, str] = None, **kwargs):
    """
    Creates the necessary tables/indexes for storing R-tree data. This must be called prior to exporting an R-tree.
    This method accepts either a connection object or keyword arguments for connecting to the database. Alternatively,
    init_db_pool may be called instead to initialize a connection pool, in which case there is no need to pass in
    database connection information.
    :param conn: psycopg2 connection (Optional).
    :param schema: Database schema (Optional, defaults to "public").
    :param srid: SRID of the geometry data (Optional, defaults to 0, which is no SRID).
    :param datatype: Data type of the R-tree leaf entries. This can either be a string (for example, "VARCHAR(255)"), in
        which case it will be used as the PostgreSQL column type , or a Python type (for example, int or str), in which
        case this function will attempt to choose the appropriate PostgreSQL column type based on the Python type
        (defaulting to "TEXT" if a more appropriate type cannot be determined). When passing a string representing a
        PostgreSQL column type, it is also possible to append modifiers such as NOT NULL, or foreign key constraints
        (for example, "INT REFERENCES my_table (my_id_column)").
    :param kwargs: Keyword arguments for establishing a database connection. These arguments will be passed to the
        psycopg2.connect function. (Optional)
    """
    close = None
    try:
        conn, close = _get_conn(conn, **kwargs)
        sql = _get_sql_from_template('create_rtree_tables', schema=schema, srid=srid, datatype=_get_datatype(datatype))
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(sql)
        conn.commit()
    finally:
        if close is not None:
            close(conn)


def clear_rtree_tables(conn=None, schema: str = 'public', **kwargs):
    """
    Truncates all R-tree tables to ensure they are empty.
    :param conn: psycopg2 connection (Optional).
    :param schema: Database schema (Optional, defaults to "public").
    :param kwargs: Keyword arguments for establishing a database connection. These arguments will be passed to the
        psycopg2.connect function. (Optional)
    """
    close = None
    try:
        conn, close = _get_conn(conn, **kwargs)
        sql = _get_sql_from_template('clear_rtree_tables', schema=schema)
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(sql)
        conn.commit()
    finally:
        if close is not None:
            close(conn)


def drop_rtree_tables(conn=None, schema: str = 'public', **kwargs):
    """
    Drops all R-tree tables created by create_rtree_tables.
    :param conn: psycopg2 connection (Optional).
    :param schema: Database schema (Optional, defaults to "public").
    :param kwargs: Keyword arguments for establishing a database connection. These arguments will be passed to the
        psycopg2.connect function. (Optional)
    """
    close = None
    try:
        conn, close = _get_conn(conn, **kwargs)
        sql = _get_sql_from_template('drop_rtree_tables', schema=schema)
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(sql)
        conn.commit()
    finally:
        if close is not None:
            close(conn)


def export_to_postgis(rtree: RTreeBase, conn=None, schema: str = 'public', srid: int = 0, **kwargs) -> int:
    """
    Exports the R-tree to PostGIS, populating the rtree, rtree_node, and rtree_entry tables created by the
    create_rtree_tables function (which must be called first). This function returns the ID of the newly-created
    R-tree in the rtree table (note that multiple R-trees can be exported; they are differentiated by the ID).

    As with the other methods in this module, this method accepts either a connection object or keyword arguments for
    connecting to the database. Alternatively, init_db_pool may be called instead to initialize a connection pool, in
    which case there is no need to pass in database connection information.

    :param rtree: R-tree to export
    :param conn: psycopg2 connection (Optional).
    :param schema: Database schema (Optional, defaults to "public").
    :param srid: SRID of the geometry data (Optional, defaults to 0, which is no SRID).
    :param kwargs: Keyword arguments for establishing a database connection. These arguments will be passed to the
        psycopg2.connect function. (Optional)
    :return: ID of the newly-created R-tree in the rtree table
    """
    close = None
    try:
        conn, close = _get_conn(conn, **kwargs)
        node_ids = {}
        entry_ids = {}
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            rtree_id = _insert_rtree(cursor, schema, rtree)
            for level, nodes in enumerate(rtree.get_levels()):
                for node in nodes:
                    node_id = _insert_rtree_node(cursor, schema, node, rtree_id, level, srid, node_ids, entry_ids)
                    for entry in node.entries:
                        _insert_rtree_entry(cursor, schema, entry, node_id, srid, entry_ids)
        conn.commit()
        return rtree_id
    finally:
        if close is not None:
            close(conn)


def _get_conn(conn=None, **kwargs):
    if conn is not None:
        return conn, None
    if pool is not None:
        return pool.getconn(), _put_conn
    if not kwargs:
        raise RuntimeError("Exporting R-tree to PostGIS requires either passing a connection object, initializing a "
                           "connection pool, or providing keyword arguments that can be used to initalize a "
                           "connection. Please check the documentation for details.")
    return psycopg2.connect(**kwargs), _close_conn


def _put_conn(conn):
    if conn is not None:
        pool.putconn(conn)


def _close_conn(conn):
    if conn is not None:
        conn.close()


def _get_sql_from_template(name, **kwargs):
    s = pkg_resources.resource_string('rtreelib', f'sql/{name}.sql.template').decode('utf-8')
    tpl = string.Template(s)
    return tpl.substitute(**kwargs)


def _get_datatype(datatype: Union[Type, str] = None) -> str:
    if isinstance(datatype, str):
        return datatype
    if datatype == str:
        return 'TEXT'
    if datatype == int:
        return 'INT'
    if datatype == float:
        return 'NUMERIC'
    return 'TEXT'


def _insert_rtree(cursor, schema, tree: RTreeBase) -> int:
    sql = _get_sql_from_template('insert_rtree', schema=schema)
    cursor.execute(sql, {
        "obj_id": id(tree),
        "hex_id": hex(id(tree))
    })
    return cursor.fetchone()['id']


def _insert_rtree_node(cursor, schema: str, node: RTreeNode, rtree_id: int, level: int, srid: int,
                       node_ids: Dict[RTreeNode, int], entry_ids: Dict[RTreeEntry, int]) -> int:
    rect = node.get_bounding_rect()
    sql = _get_sql_from_template('insert_rtree_node', schema=schema)
    cursor.execute(sql, {
        "obj_id": id(node),
        "hex_id": hex(id(node)),
        "rtree_id": rtree_id,
        "level": level,
        "min_x": rect.min_x,
        "min_y": rect.min_y,
        "max_x": rect.max_x,
        "max_y": rect.max_y,
        "srid": srid,
        "parent_entry_id": entry_ids[node.parent_entry] if node.parent_entry is not None else None,
        "leaf": node.is_leaf
    })
    node_id = cursor.fetchone()['id']
    node_ids[node] = node_id
    return node_id


def _insert_rtree_entry(cursor, schema: str, entry: RTreeEntry, node_id: int, srid: int,
                        entry_ids: Dict[RTreeEntry, int]) -> int:
    sql = _get_sql_from_template('insert_rtree_entry', schema=schema)
    cursor.execute(sql, {
        "obj_id": id(entry),
        "hex_id": hex(id(entry)),
        "parent_node_id": node_id,
        "min_x": entry.rect.min_x,
        "min_y": entry.rect.min_y,
        "max_x": entry.rect.max_x,
        "max_y": entry.rect.max_y,
        "srid": srid,
        "leaf": entry.is_leaf,
        "data": entry.data
    })
    entry_id = cursor.fetchone()['id']
    entry_ids[entry] = entry_id
    return entry_id
