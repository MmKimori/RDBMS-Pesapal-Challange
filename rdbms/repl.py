from __future__ import annotations

import sys
from textwrap import shorten
from typing import Any, Dict, Iterable, List

from .engine import Engine
from .parser import Parser


def _format_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "(no rows)"

    # Determine columns from first row
    columns = list(rows[0].keys())
    col_widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            col_widths[c] = max(col_widths[c], len(str(row.get(c, ""))))

    def fmt_row(row_dict: Dict[str, Any]) -> str:
        return " | ".join(str(row_dict.get(c, "")).ljust(col_widths[c]) for c in columns)

    header = fmt_row({c: c for c in columns})
    sep = "-+-".join("-" * col_widths[c] for c in columns)
    body = "\n".join(fmt_row(r) for r in rows)
    return f"{header}\n{sep}\n{body}"


def _print_result(result: Any) -> None:
    if result is None:
        print("OK")
    elif isinstance(result, list):
        print(_format_table(result))
        print(f"({len(result)} rows)")
    else:
        print(f"{result} rows affected")


def repl() -> None:
    engine = Engine()
    parser = Parser(engine)

    print("Simple in-memory RDBMS REPL")
    print("Type SQL-like statements terminated by ';'.")
    print("Meta-commands: .help  .tables  .quit")

    buffer: List[str] = []

    while True:
        try:
            line = input("rdbms> " if not buffer else "   ...> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        line = line.rstrip()
        if not buffer and line.startswith("."):
            if line in (".quit", ".exit"):
                break
            if line == ".help":
                print(
                    "Supported commands:\n"
                    "  CREATE TABLE, INSERT, SELECT, UPDATE, DELETE, simple INNER JOIN\n"
                    "Meta commands:\n"
                    "  .help   - show this message\n"
                    "  .tables - list tables\n"
                    "  .quit   - exit"
                )
                continue
            if line == ".tables":
                if not engine.tables:
                    print("(no tables)")
                else:
                    for name, table in engine.tables.items():
                        cols = ", ".join(
                            f"{c.name}:{c.col_type}"
                            + (" PK" if c.primary_key else "")
                            + (" UQ" if c.unique and not c.primary_key else "")
                            for c in table.columns
                        )
                        print(f"{name} ({cols})")
                continue
            print(f"Unknown meta-command: {line}")
            continue

        buffer.append(line)
        if ";" not in line:
            continue

        statement = " ".join(buffer)
        buffer = []
        try:
            result = parser.execute(statement)
            _print_result(result)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Error: {exc}")


if __name__ == "__main__":
    repl()


