## Simple In-Memory RDBMS (Pesapal Junior Developer '26 Challenge)

This repository contains a **minimal but complete relational database management system (RDBMS)** implemented from scratch in Python using **only the standard library**.  
It includes:

- **In-memory RDBMS engine** with tables, constraints, and hash-based indexing
- **SQL-like parser** and an interactive **command-line REPL**
- **HTTP server** built on `http.server` exposing REST-style CRUD endpoints
- **HTML/CSS/JavaScript frontend** that demonstrates CRUD operations against the database

The goal is clarity and correctness rather than performance or full SQL compliance.

---

### Repository structure

```text
repo/
├── rdbms/
│   ├── engine.py        # Core DB engine (tables, rows, constraints)
│   ├── table.py         # Table abstraction
│   ├── index.py         # Hash-based index
│   ├── parser.py        # SQL-like parser
│   ├── join.py          # INNER JOIN implementation
│   └── repl.py          # Interactive SQL REPL
│
├── server/
│   └── server.py        # HTTP server using http.server
│
├── web/
│   ├── index.html       # Frontend UI
│   ├── style.css        # Styling
│   └── app.js           # Browser-side CRUD logic using fetch()
│
├── README.md
└── requirements.txt
```

---

### System architecture

- **Engine (`rdbms/engine.py`)**
  - Manages the collection of tables in memory.
  - Provides methods for:
    - `create_table(name, columns)`
    - `insert(table, values)`
    - `select(table, columns, where)`
    - `update(table, values, where)`
    - `delete(table, where)`
    - `inner_join(left_table, right_table, left_col, right_col, columns)`
  - All operations are performed in Python data structures (primarily dicts and lists).

- **Tables and storage (`rdbms/table.py`)**
  - A `Table` instance holds:
    - `columns`: list of `ColumnDef` describing name, type (`INT` or `TEXT`), and constraints.
    - `_rows`: dict mapping internal `row_id` → row dict (`{column_name: value}`).
    - `_indexes`: map of column name → `HashIndex` for `PRIMARY KEY` and `UNIQUE` constraints.
  - **Insert / Update / Delete** are implemented with constraint enforcement and index maintenance.

- **Hash-based indexing (`rdbms/index.py`)**
  - `HashIndex` wraps a Python `dict` from **key → [row_ids]**.
  - Supports:
    - `insert(key, row_id)` with uniqueness checking
    - `delete(key, row_id)`
    - `update(old_key, new_key, row_id)`
    - `lookup(key)` → iterable of `row_id`s
  - Used automatically by tables for `PRIMARY KEY` and `UNIQUE` columns.

- **JOINs (`rdbms/join.py`)**
  - Implements a simple **INNER JOIN**:
    - `inner_join(left_table, right_table, left_col, right_col, columns)`
  - Performs an equi-join: `left.left_col = right.right_col`.
  - Builds an in-memory hash table for the right side and probes it for each left row.
  - Projects columns as fully qualified names (`table.column`) to avoid collisions.

- **SQL-like parser (`rdbms/parser.py`)**
  - Very small hand-written parser; not a full SQL implementation.
  - Supported statements:
    - `CREATE TABLE`
    - `INSERT INTO ... VALUES (...)`
    - `SELECT ... FROM ... [WHERE col = value]`
    - `SELECT ... FROM t1 INNER JOIN t2 ON t1.col = t2.col`
    - `UPDATE ... SET ... [WHERE col = value]`
    - `DELETE FROM ... [WHERE col = value]`
  - Supports `INT` and `TEXT` types and equality-only `WHERE` conditions.
  - String literals use single quotes: `'text value'`.
  - The parser produces a `ParsedStatement` which is immediately executed via `Engine`.

- **REPL (`rdbms/repl.py`)**
  - Provides a simple interactive console:
    - Multi-line statements terminated by `;`.
    - Meta commands:
      - `.help` – usage help
      - `.tables` – list tables and columns
      - `.quit` / `.exit` – exit the REPL
  - Displays `SELECT` results as a text table with columns and row counts.

---

### HTTP server and web app

- **HTTP server (`server/server.py`)**
  - Uses `http.server.HTTPServer` and `BaseHTTPRequestHandler` from the standard library.
  - On startup, initializes a `users` table:
    ```sql
    CREATE TABLE users (
        id INT PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE
    );
    ```
  - REST-style endpoints (JSON):
    - `GET /api/users`
      - Returns all users as a JSON array.
    - `GET /api/users/<id>`
      - Returns a single user by `id` or `404` if not found.
    - `POST /api/users`
      - Body: `{"id": INT, "name": TEXT, "email": TEXT}`
      - Creates a new user. Enforces primary key and unique email.
    - `PUT /api/users/<id>`
      - Body: `{"name": TEXT?, "email": TEXT?}`
      - Updates the given fields on the specified user.
    - `DELETE /api/users/<id>`
      - Deletes the specified user.
  - Also serves static files from the `web/` directory:
    - `/` → `web/index.html`
    - `/style.css`, `/app.js`, etc.

- **Frontend (`web/`)**
  - `index.html`
    - Simple UI with:
      - Form to create or edit a user (ID, name, email).
      - A table listing all current users with Edit/Delete buttons.
  - `style.css`
    - Clean, modern styling for a simple dashboard layout.
  - `app.js`
    - Uses `fetch()` to call the backend endpoints:
      - Load all users on page load and when "Refresh" is clicked.
      - Submit the form to **create or update** a user:
        - Attempts `PUT /api/users/<id>` first.
        - If not found, falls back to `POST /api/users`.
      - Edit button:
        - Populates the form with the existing user data.
      - Delete button:
        - Calls `DELETE /api/users/<id>` and refreshes the table.

---

### Database design decisions

- **In-memory only**
  - All data is stored in Python data structures inside the process.
  - There is **no persistence**; restarting the server or REPL clears all data.

- **Types**
  - The engine supports two basic types:
    - `INT` → stored as Python `int`
    - `TEXT` → stored as Python `str`
  - Type checking is done on insert/update via `ColumnDef.normalize_value`.

- **Constraints**
  - `PRIMARY KEY`:
    - Treated as `UNIQUE` + identifier for the row.
    - Enforced using a `HashIndex` on the column.
  - `UNIQUE`:
    - Also implemented via `HashIndex(unique=True)`.
  - On insert/update:
    - Indexes are updated and uniqueness is enforced.
    - Violations raise `ValueError`.

- **Indexing**
  - Each `PRIMARY KEY` or `UNIQUE` column gets a dedicated `HashIndex`.
  - Lookups in `WHERE col = value` clauses will use the index if available.
  - All other scans fall back to full table iteration.

- **Joins**
  - Only **equi-joins** of the form:
    ```sql
    SELECT t1.col1, t2.col2
    FROM table1
    INNER JOIN table2
      ON table1.colX = table2.colY;
    ```
  - The parser requires **fully qualified** projection columns (`table.column`).
  - Results are returned with keys such as `"table1.col1"` to avoid name clashes.

---

### How to run

All commands assume the current working directory is the `repo/` folder.

#### 1. Run the REPL

```bash
cd repo
python -m rdbms.repl
```

Example session:

```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE
);

INSERT INTO users (id, name, email)
VALUES (1, 'Alice', 'alice@example.com');

SELECT id, name, email FROM users;
```

Use `.tables` to inspect defined tables and `.quit` to exit.

#### 2. Run the HTTP server

```bash
cd repo
python -m server.server
```

Then open a browser at:

- `http://localhost:8000/`

From the UI you can:

- Create users via the form.
- Edit an existing user by clicking **Edit**, updating the fields, and clicking **Save User**.
- Delete a user with the **Delete** button.
- Refresh the table with the **Refresh** button if needed.

The frontend communicates with the backend using `fetch()` and JSON.

---

### Limitations and future improvements

- **No persistence**
  - Data is lost when the process exits.  
  - Future work: add a simple storage layer (e.g., JSON or binary log) to reload tables.

- **Very small SQL subset**
  - Only equality-based `WHERE` conditions are supported.
  - No ordering, grouping, subqueries, or aggregates.
  - Future work: extend the parser and engine to support additional operators and clauses.

- **Single-process, single-threaded**
  - The HTTP server handles one request at a time.
  - Future work: introduce concurrency (e.g., `ThreadingHTTPServer`) and basic locking.

- **Limited type system**
  - Only `INT` and `TEXT` are supported.
  - Future work: add booleans, dates, and custom validation per column.

- **JOINs are basic**
  - Only simple `INNER JOIN` with explicit `ON` clause is supported.
  - Future work: support `LEFT JOIN`, `RIGHT JOIN`, multi-column joins, and projections with `*`.

---

### Requirements / dependencies

This project is intentionally built on **Python standard library only**:

- No external packages are required.
- The `requirements.txt` file exists for completeness but is effectively empty.

Recommended Python version: **3.9+**.

---

### Using this project as a learning reference

This repository is suitable as a teaching / learning aid for:

- Core RDBMS concepts:
  - Tables, rows, data types
  - Primary keys and unique constraints
  - Indexes and basic join strategies
- How to design clean modules with clear responsibilities in Python.
- Building services in Python using **only the standard library**.

---

### AI usage notice

Parts of this implementation, including structure, comments, and documentation, were generated with the assistance of an AI coding assistant (OpenAI model running in Cursor).  
All code has been reviewed and adapted to meet the requirements of the Pesapal Junior Developer '26 challenge.

