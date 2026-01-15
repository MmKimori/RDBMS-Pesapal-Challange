"""
Very small SQL-like parser for the in-memory RDBMS.

Supported statements (simplified, case-insensitive keywords):

    CREATE TABLE table_name (
        col_name TYPE [PRIMARY KEY] [UNIQUE],
        ...
    );

    INSERT INTO table_name (col1, col2, ...) VALUES (val1, val2, ...);

    SELECT col1, col2 FROM table_name [WHERE col = value];

    SELECT t1.col1, t2.col2
      FROM table1
      INNER JOIN table2
        ON table1.colX = table2.colY;

    UPDATE table_name SET col1 = val1, col2 = val2 [WHERE col = value];

    DELETE FROM table_name [WHERE col = value];

Notes:
- Only '=' is supported in WHERE conditions.
- String literals must be wrapped in single quotes; everything else is treated as INT where valid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from .engine import Engine


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _strip_semi(sql: str) -> str:
    sql = sql.strip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    return sql


def _parse_literal(token: str) -> Any:
    token = token.strip()
    if token.startswith("'") and token.endswith("'") and len(token) >= 2:
        return token[1:-1]
    # Try integer
    try:
        return int(token)
    except ValueError:
        return token


@dataclass
class ParsedStatement:
    kind: str
    payload: Dict[str, Any]


class Parser:
    """
    Very small hand-written parser that directly interacts with an Engine instance.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute(self, sql: str) -> Union[List[Dict[str, Any]], int, None]:
        """
        Parse and execute a SQL-like statement.
        Returns:
            - list of rows for SELECT / JOIN
            - affected row count for UPDATE / DELETE / INSERT
            - None for DDL (CREATE TABLE)
        """
        sql = _strip_semi(sql)
        if not sql:
            return None

        parsed = self._parse(sql)
        kind = parsed.kind
        p = parsed.payload

        if kind == "CREATE_TABLE":
            self.engine.create_table(p["name"], p["columns"])
            return None
        if kind == "INSERT":
            return self.engine.insert(p["table"], p["values"])
        if kind == "SELECT":
            return self.engine.select(
                p["table"], columns=p["columns"], where=p.get("where")
            )
        if kind == "UPDATE":
            return self.engine.update(
                p["table"], values=p["values"], where=p.get("where")
            )
        if kind == "DELETE":
            return self.engine.delete(p["table"], where=p.get("where"))
        if kind == "INNER_JOIN":
            return self.engine.inner_join(
                p["left_table"],
                p["right_table"],
                p["left_col"],
                p["right_col"],
                p["columns"],
            )
        raise ValueError(f"Unsupported statement type: {kind}")

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def _parse(self, sql: str) -> ParsedStatement:
        upper = sql.upper()
        if upper.startswith("CREATE TABLE"):
            return self._parse_create_table(sql)
        if upper.startswith("INSERT INTO"):
            return self._parse_insert(sql)
        if upper.startswith("SELECT"):
            if " INNER JOIN " in upper:
                return self._parse_inner_join(sql)
            return self._parse_select(sql)
        if upper.startswith("UPDATE"):
            return self._parse_update(sql)
        if upper.startswith("DELETE FROM"):
            return self._parse_delete(sql)
        raise ValueError(f"Could not parse statement: {sql}")

    # CREATE TABLE ------------------------------------------------------
    def _parse_create_table(self, sql: str) -> ParsedStatement:
        m = re.match(r"CREATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$", sql, re.IGNORECASE | re.DOTALL)
        if not m:
            raise ValueError("Invalid CREATE TABLE syntax")
        table_name = m.group(1)
        cols_part = m.group(2)
        col_defs: List[Tuple[str, str, bool, bool]] = []
        for col_segment in self._split_csv(cols_part):
            col_segment = col_segment.strip()
            if not col_segment:
                continue
            tokens = col_segment.split()
            if len(tokens) < 2:
                raise ValueError(f"Invalid column definition: {col_segment}")
            col_name = tokens[0]
            col_type = tokens[1].upper()
            primary = False
            unique = False
            rest = " ".join(tokens[2:]).upper()
            if "PRIMARY KEY" in rest:
                primary = True
                unique = True
            if "UNIQUE" in rest and not primary:
                unique = True
            col_defs.append((col_name, col_type, primary, unique))

        return ParsedStatement("CREATE_TABLE", {"name": table_name, "columns": col_defs})

    # INSERT ------------------------------------------------------------
    def _parse_insert(self, sql: str) -> ParsedStatement:
        m = re.match(
            r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*VALUES\s*\(([^)]*)\)\s*$",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            raise ValueError("Invalid INSERT syntax")
        table = m.group(1)
        cols_str = m.group(2)
        vals_str = m.group(3)
        col_names = [c.strip() for c in cols_str.split(",") if c.strip()]
        val_tokens = [v.strip() for v in self._split_csv(vals_str) if v.strip()]
        if len(col_names) != len(val_tokens):
            raise ValueError("INSERT column count does not match value count")

        values: Dict[str, Any] = {}
        for name, token in zip(col_names, val_tokens):
            values[name] = _parse_literal(token)

        return ParsedStatement("INSERT", {"table": table, "values": values})

    # SELECT (no join) --------------------------------------------------
    def _parse_select(self, sql: str) -> ParsedStatement:
        # SELECT cols FROM table [WHERE ...]
        m = re.match(
            r"SELECT\s+(.*?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+WHERE\s+(.*))?$",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            raise ValueError("Invalid SELECT syntax")
        cols_str = m.group(1)
        table = m.group(2)
        where_str = m.group(3)

        columns = ["*"]
        if cols_str.strip() != "*":
            columns = [c.strip() for c in cols_str.split(",") if c.strip()]

        where = self._parse_where(where_str) if where_str else None

        return ParsedStatement(
            "SELECT",
            {"table": table, "columns": columns, "where": where},
        )

    # INNER JOIN --------------------------------------------------------
    def _parse_inner_join(self, sql: str) -> ParsedStatement:
        # SELECT cols FROM t1 INNER JOIN t2 ON t1.col = t2.col
        m = re.match(
            r"SELECT\s+(.*?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s+INNER\s+JOIN\s+([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+(.+)$",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            raise ValueError("Invalid INNER JOIN syntax")
        cols_str = m.group(1)
        left_table = m.group(2)
        right_table = m.group(3)
        on_clause = m.group(4).strip()

        # Expect "left_table.col = right_table.col"
        on_m = re.match(
            r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)",
            on_clause,
        )
        if not on_m:
            raise ValueError("Invalid INNER JOIN ON clause")
        left_name, left_col, right_name, right_col = on_m.groups()
        if left_name != left_table or right_name != right_table:
            raise ValueError("JOIN ON clause must reference the tables in the FROM/JOIN")

        # Projection columns - require fully qualified names "table.col"
        columns: List[Tuple[str, str]] = []
        if cols_str.strip() == "*":
            # Expand to all columns from both tables at execution time is complex here,
            # so for simplicity we expect explicit column list in JOIN queries.
            raise ValueError("For INNER JOIN, please specify explicit projection columns")
        for item in cols_str.split(","):
            item = item.strip()
            col_m = re.match(
                r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$", item
            )
            if not col_m:
                raise ValueError(
                    "JOIN projection columns must be fully qualified as table.column"
                )
            tbl, col = col_m.groups()
            columns.append((tbl, col))

        return ParsedStatement(
            "INNER_JOIN",
            {
                "left_table": left_table,
                "right_table": right_table,
                "left_col": left_col,
                "right_col": right_col,
                "columns": columns,
            },
        )

    # UPDATE ------------------------------------------------------------
    def _parse_update(self, sql: str) -> ParsedStatement:
        # UPDATE table SET col1 = val1, col2 = val2 [WHERE ...]
        m = re.match(
            r"UPDATE\s+([A-Za-z_][A-Za-z0-9_]*)\s+SET\s+(.+)$",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            raise ValueError("Invalid UPDATE syntax")
        table = m.group(1)
        rest = m.group(2)

        where_str: Optional[str] = None
        where_pos = re.search(r"\bWHERE\b", rest, re.IGNORECASE)
        if where_pos:
            where_str = rest[where_pos.end() :].strip()
            set_part = rest[: where_pos.start()].strip()
        else:
            set_part = rest.strip()

        values: Dict[str, Any] = {}
        for assignment in self._split_csv(set_part):
            if not assignment.strip():
                continue
            m_assign = re.match(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$",
                assignment.strip(),
            )
            if not m_assign:
                raise ValueError(f"Invalid assignment in UPDATE: {assignment}")
            col, expr = m_assign.groups()
            values[col] = _parse_literal(expr.strip())

        where = self._parse_where(where_str) if where_str else None

        return ParsedStatement(
            "UPDATE",
            {"table": table, "values": values, "where": where},
        )

    # DELETE ------------------------------------------------------------
    def _parse_delete(self, sql: str) -> ParsedStatement:
        # DELETE FROM table [WHERE ...]
        m = re.match(
            r"DELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+WHERE\s+(.*))?$",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            raise ValueError("Invalid DELETE syntax")
        table = m.group(1)
        where_str = m.group(2)
        where = self._parse_where(where_str) if where_str else None
        return ParsedStatement("DELETE", {"table": table, "where": where})

    # Helpers -----------------------------------------------------------
    def _parse_where(self, where_str: str) -> Tuple[str, str, Any]:
        # Only support "col = value"
        m = re.match(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$",
            where_str.strip(),
        )
        if not m:
            raise ValueError("Invalid WHERE clause; only 'col = value' is supported")
        col, expr = m.groups()
        return col, "=", _parse_literal(expr.strip())

    def _split_csv(self, s: str) -> List[str]:
        """
        Split a comma-separated list while respecting single-quoted strings.
        """
        parts: List[str] = []
        current: List[str] = []
        in_quote = False
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == "'" and not in_quote:
                in_quote = True
                current.append(ch)
            elif ch == "'" and in_quote:
                in_quote = False
                current.append(ch)
            elif ch == "," and not in_quote:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
            i += 1
        if current:
            parts.append("".join(current))
        return parts

