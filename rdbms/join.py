"""
INNER JOIN implementation for the in-memory RDBMS.

The join is intentionally simple and supports only equi-joins of the form:

    SELECT ...
    FROM left_table
    INNER JOIN right_table
      ON left_table.left_col = right_table.right_col

This module provides a `inner_join` helper used by the engine.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .table import Table


def inner_join(
    left: Table,
    right: Table,
    left_col: str,
    right_col: str,
    columns: List[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    """
    Perform a basic INNER JOIN between two tables.

    - `left`, `right`: tables
    - `left_col`, `right_col`: column names to join on
    - `columns`: list of (table_alias, column_name) pairs describing which columns to project.
      The table_alias is either 'left' or 'right' for now, but the engine passes user-facing
      table names and we map them accordingly.

    Returns a list of row dicts where keys are "table.column" (fully qualified) to avoid clashes.
    """
    # Build an index on right.join_col for efficient lookup
    # We do not reuse the regular HashIndex to avoid interfering with constraints.
    right_buckets = {}
    for _row_id, row in right._rows.items():  # type: ignore[attr-defined]
        key = row.get(right_col)
        right_buckets.setdefault(key, []).append(row)

    result: List[Dict[str, Any]] = []

    # Iterate over left rows and probe into right side
    for _left_id, left_row in left._rows.items():  # type: ignore[attr-defined]
        key = left_row.get(left_col)
        matches = right_buckets.get(key, [])
        for right_row in matches:
            out: Dict[str, Any] = {}
            for tbl_name, col_name in columns:
                if tbl_name == left.name:
                    value = left_row.get(col_name)
                elif tbl_name == right.name:
                    value = right_row.get(col_name)
                else:
                    # Should not happen with a correct parser
                    raise ValueError(
                        f"Unknown table alias '{tbl_name}' in join projection; "
                        f"expected '{left.name}' or '{right.name}'"
                    )
                out[f"{tbl_name}.{col_name}"] = value
            result.append(out)
    return result

