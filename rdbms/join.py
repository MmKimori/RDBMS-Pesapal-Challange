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
 
    right_buckets = {}
    for _row_id, row in right._rows.items():  # type: ignore[attr-defined]
        key = row.get(right_col)
        right_buckets.setdefault(key, []).append(row)

    result: List[Dict[str, Any]] = []

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

                    raise ValueError(
                        f"Unknown table alias '{tbl_name}' in join projection; "
                        f"expected '{left.name}' or '{right.name}'"
                    )
                out[f"{tbl_name}.{col_name}"] = value
            result.append(out)
    return result


