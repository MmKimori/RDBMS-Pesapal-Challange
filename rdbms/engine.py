"""
Core in-memory RDBMS engine.

Responsibilities:
- Manage tables
- Execute parsed SQL-like commands
- Coordinate joins
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .join import inner_join
from .table import ColumnDef, Table


@dataclass
class Engine:
    """
    Very small relational engine managing multiple tables in memory.
    """

    tables: Dict[str, Table] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # DDL
    # ------------------------------------------------------------------
    def create_table(
        self,
        name: str,
        columns: List[Tuple[str, str, bool, bool]],
    ) -> None:
        """
        Create a table.

        columns: list of (name, type, primary_key, unique)
        """
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")
        col_defs = [ColumnDef(col_name, col_type, pk, uniq) for col_name, col_type, pk, uniq in columns]
        self.tables[name] = Table(name=name, columns=col_defs)

    def get_table(self, name: str) -> Table:
        try:
            return self.tables[name]
        except KeyError as exc:
            raise ValueError(f"Table '{name}' does not exist") from exc

    # ------------------------------------------------------------------
    # DML helpers called by parser
    # ------------------------------------------------------------------
    def insert(self, table: str, values: Dict[str, Any]) -> int:
        return self.get_table(table).insert(values)

    def select(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        where: Optional[Tuple[str, str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self.get_table(table).select(columns=columns, where=where)

    def update(
        self,
        table: str,
        values: Dict[str, Any],
        where: Optional[Tuple[str, str, Any]] = None,
    ) -> int:
        return self.get_table(table).update(values=values, where=where)

    def delete(
        self,
        table: str,
        where: Optional[Tuple[str, str, Any]] = None,
    ) -> int:
        return self.get_table(table).delete(where=where)

    # ------------------------------------------------------------------
    # JOIN
    # ------------------------------------------------------------------
    def inner_join(
        self,
        left_table: str,
        right_table: str,
        left_col: str,
        right_col: str,
        columns: List[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        left = self.get_table(left_table)
        right = self.get_table(right_table)
        return inner_join(left, right, left_col, right_col, columns)

