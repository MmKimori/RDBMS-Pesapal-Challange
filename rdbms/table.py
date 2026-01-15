"""
Table abstraction for the in-memory RDBMS.

Responsibilities:
- Maintain schema (column names, types, constraints)
- Store rows in memory
- Enforce PRIMARY KEY and UNIQUE constraints
- Maintain hash indexes on constrained columns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .index import HashIndex


SUPPORTED_TYPES = {"INT", "TEXT"}


@dataclass
class ColumnDef:
    name: str
    col_type: str
    primary_key: bool = False
    unique: bool = False

    def normalize_value(self, value: Any) -> Any:
        """
        Cast incoming Python value to the declared column type.
        """
        if value is None:
            return None
        if self.col_type == "INT":
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid INT value for column '{self.name}': {value!r}") from exc
        if self.col_type == "TEXT":
            return str(value)
        raise ValueError(f"Unsupported column type: {self.col_type}")


@dataclass
class Table:
    """
    Simple in-memory table.

    Rows are stored as dicts mapping column name -> value.
    Each row has an internal integer id used by indexes.
    """

    name: str
    columns: List[ColumnDef]
    _rows: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    _next_row_id: int = 1
    _indexes: Dict[str, HashIndex] = field(default_factory=dict)

    def __post_init__(self) -> None:
        seen = set()
        for col in self.columns:
            if col.name in seen:
                raise ValueError(f"Duplicate column name '{col.name}' in table '{self.name}'")
            seen.add(col.name)
            if col.col_type not in SUPPORTED_TYPES:
                raise ValueError(
                    f"Unsupported type '{col.col_type}' for column '{col.name}'. "
                    f"Supported types: {sorted(SUPPORTED_TYPES)}"
                )
            if col.primary_key or col.unique:
                self._indexes[col.name] = HashIndex(column=col.name, unique=True)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        col_map = {c.name: c for c in self.columns}
        for col in self.columns:
            if col.name in row:
                normalized[col.name] = col.normalize_value(row[col.name])
            else:
                normalized[col.name] = None
        # Reject unknown columns
        for key in row:
            if key not in col_map:
                raise ValueError(f"Unknown column '{key}' for table '{self.name}'")
        return normalized

    def _get_column(self, name: str) -> ColumnDef:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"Column '{name}' does not exist in table '{self.name}'")

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    def insert(self, values: Dict[str, Any]) -> int:
        """
        Insert a new row and return its internal row id.
        """
        row = self._normalize_row(values)
        row_id = self._next_row_id
        # Check constraints via indexes first
        for col_name, index in self._indexes.items():
            key = row[col_name]
            index.insert(key, row_id)

        self._rows[row_id] = row
        self._next_row_id += 1
        return row_id

    def _iter_matching_rows(
        self, where: Optional[Tuple[str, str, Any]] = None
    ) -> Iterable[Tuple[int, Dict[str, Any]]]:
        """
        Yield (row_id, row_dict) for rows matching a simple predicate.

        where: (column, operator, value); operator currently only supports '='
        """
        if where is None:
            for row_id, row in self._rows.items():
                yield row_id, row
            return

        col_name, op, raw_value = where
        if op != "=":
            raise ValueError(f"Only '=' operator is supported in WHERE, got '{op}'")

        column = self._get_column(col_name)
        value = column.normalize_value(raw_value)

        # If we have an index, use it
        index = self._indexes.get(col_name)
        if index is not None:
            for row_id in index.lookup(value):
                row = self._rows.get(row_id)
                if row is not None:
                    yield row_id, row
            return

        # Fallback: scan
        for row_id, row in self._rows.items():
            if row.get(col_name) == value:
                yield row_id, row

    def select(
        self,
        columns: Optional[List[str]] = None,
        where: Optional[Tuple[str, str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return list of rows (as dicts). If columns is None or ['*'], all columns are returned.
        """
        if columns is None or columns == ["*"]:
            cols = [c.name for c in self.columns]
        else:
            cols = columns

        result: List[Dict[str, Any]] = []
        for _row_id, row in self._iter_matching_rows(where):
            projected = {c: row.get(c) for c in cols}
            result.append(projected)
        return result

    def update(
        self,
        values: Dict[str, Any],
        where: Optional[Tuple[str, str, Any]] = None,
    ) -> int:
        """
        Update rows matching the predicate with new values.
        Returns the count of updated rows.
        """
        if not values:
            return 0

        # Normalize update values
        norm_values: Dict[str, Any] = {}
        for col_name, v in values.items():
            col = self._get_column(col_name)
            norm_values[col_name] = col.normalize_value(v)

        updated = 0
        for row_id, row in list(self._iter_matching_rows(where)):
            old_row = row.copy()
            row.update(norm_values)
            # Re-check constraints via indexes
            try:
                for col_name, index in self._indexes.items():
                    index.update(old_row[col_name], row[col_name], row_id)
            except Exception:
                # Roll back this row if constraint fails
                row.clear()
                row.update(old_row)
                raise
            updated += 1
        return updated

    def delete(self, where: Optional[Tuple[str, str, Any]] = None) -> int:
        """
        Delete rows matching predicate. Returns number of deleted rows.
        """
        to_delete = list(self._iter_matching_rows(where))
        count = 0
        for row_id, row in to_delete:
            for col_name, index in self._indexes.items():
                index.delete(row[col_name], row_id)
            self._rows.pop(row_id, None)
            count += 1
        return count

    def all_rows(self) -> List[Dict[str, Any]]:
        """
        Convenience method, used by demos/tests.
        """
        return list(self.select())

