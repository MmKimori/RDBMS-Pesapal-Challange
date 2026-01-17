"""
Simple hash-based index implementation for the in-memory RDBMS.

The index maps a column value to one or more row references (by row id).
Internally this is just a thin wrapper around a Python dict, but having
it separated makes the intent clear and allows extension later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Iterable


@dataclass
class HashIndex:
    column: str
    unique: bool = False
    _index: Dict[Any, List[int]] = field(default_factory=dict)

    def insert(self, key: Any, row_id: int) -> None:
       
        if key is None:
            # For simplicity we do not index NULL / None values.
            return

        if self.unique:
            if key in self._index and self._index[key]:
                raise ValueError(
                    f"Unique constraint violated for column '{self.column}' with value {key!r}"
                )
            self._index[key] = [row_id]
        else:
            self._index.setdefault(key, []).append(row_id)

    def delete(self, key: Any, row_id: int) -> None:
       
        if key is None:
            return

        rows = self._index.get(key)
        if not rows:
            return

        try:
            rows.remove(row_id)
        except ValueError:
            return

        if not rows:
            # Clean up empty bucket
            self._index.pop(key, None)

    def update(self, old_key: Any, new_key: Any, row_id: int) -> None:
      
        if old_key == new_key:
            return
        self.delete(old_key, row_id)
        self.insert(new_key, row_id)

    def lookup(self, key: Any) -> Iterable[int]:
     
        if key is None:
            return []
        return list(self._index.get(key, []))

    def __len__(self) -> int:  # pragma: no cover - trivial
        return sum(len(v) for v in self._index.values())


