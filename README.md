# Simple In-Memory RDBMS

**Pesapal Junior Developer '26 Challenge Submission**

---

## Overview

This repository contains a simple but complete in-memory relational database management system (RDBMS) implemented from scratch in Python using **only the standard library**.

The project was built to demonstrate a clear understanding of core database concepts—tables, constraints, indexing, joins, and query execution—rather than performance, persistence, or full SQL compatibility.

In addition to the database engine itself, the project includes:

- A small SQL-like command-line REPL
- A lightweight HTTP server exposing CRUD operations
- A minimal HTML/CSS/JavaScript frontend that interacts with the database over HTTP

The focus throughout was correctness, readability, and adherence to the challenge requirements.

---

## Repository Structure

```
repo/
├── rdbms/
│   ├── engine.py        # Core in-memory DB engine
│   ├── table.py         # Table abstraction and row storage
│   ├── index.py         # Hash-based indexing implementation
│   ├── parser.py        # Minimal SQL-like parser
│   ├── join.py          # INNER JOIN logic
│   └── repl.py          # Interactive command-line interface
│
├── server/
│   └── server.py        # HTTP server using Python's standard library
│
├── web/
│   ├── index.html       # Frontend UI
│   ├── style.css        # Styling
│   └── app.js           # Browser-side logic using fetch()
│
├── README.md
└── requirements.txt
```

---

## System Architecture

### Core Engine (`rdbms/engine.py`)

The Engine acts as the central coordinator for all database operations. It maintains an in-memory registry of tables and exposes methods for:

- Creating tables with typed columns and constraints
- Inserting, selecting, updating, and deleting rows
- Performing simple INNER JOIN operations

All data is stored entirely in Python data structures (`dict`, `list`) without relying on any external database.

### Tables and Storage (`rdbms/table.py`)

Each table:

- Defines its schema using `ColumnDef` objects (`INT` or `TEXT`)
- Stores rows internally as dictionaries
- Maintains indexes for constrained columns

Constraints are enforced at insert and update time, ensuring data integrity even in an in-memory setting.

### Hash-Based Indexing (`rdbms/index.py`)

Indexes are implemented using Python dictionaries:

- Each index maps `column_value → row_id(s)`
- Used for `PRIMARY KEY` and `UNIQUE` constraints
- Automatically maintained during insert, update, and delete operations

Where possible, indexed columns are used to optimize equality-based lookups.

### JOIN Implementation (`rdbms/join.py`)

The system supports simple equi-based INNER JOINs:

```sql
SELECT t1.col1, t2.col2
FROM table1
INNER JOIN table2
ON table1.colX = table2.colY;
```

The join logic builds a hash table on the right-hand side and probes it using values from the left-hand table. Projection columns must be fully qualified (`table.column`) to avoid ambiguity.

### SQL-Like Parser (`rdbms/parser.py`)

A small hand-written parser translates SQL-like statements into executable operations.

**Supported statements:**

- `CREATE TABLE`
- `INSERT INTO ... VALUES (...)`
- `SELECT ... FROM ... [WHERE col = value]`
- `SELECT ... FROM ... INNER JOIN ...`
- `UPDATE ... SET ... [WHERE col = value]`
- `DELETE FROM ... [WHERE col = value]`

The parser intentionally supports a very limited SQL subset to keep the focus on execution logic rather than grammar complexity.

### REPL (`rdbms/repl.py`)

The REPL provides an interactive way to work with the database:

- Multi-line statements terminated with `;`
- Helper commands:
  - `.tables` – list defined tables
  - `.help` – usage information
  - `.quit` / `.exit` – exit the session
- Query results are displayed as formatted text tables

---

## HTTP Server and Web Interface

### HTTP Server (`server/server.py`)

The server is implemented using `http.server` and exposes REST-style endpoints for a sample `users` table:

```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE
);
```

**Endpoints:**

- `GET /api/users` – List all users
- `GET /api/users/<id>` – Get user by ID
- `POST /api/users` – Create a new user
- `PUT /api/users/<id>` – Update user by ID
- `DELETE /api/users/<id>` – Delete user by ID

Static frontend files are served directly from the `web/` directory.

### Frontend (`web/`)

The frontend is intentionally minimal and framework-free:

- **HTML**: Form and table layout
- **CSS**: Simple, clean styling
- **JavaScript**:
  - Uses `fetch()` for API calls
  - Supports create, update, delete, and refresh actions
  - Reuses the same form for insert and update operations

The UI exists purely to demonstrate that the database engine works end-to-end.

---

## Design Decisions

### In-Memory Only

No persistence; all data is lost on restart.

### Limited Type System

`INT` and `TEXT` only.

### Constraints

`PRIMARY KEY` and `UNIQUE` enforced via indexes.

### Indexes

Hash-based, created automatically for constrained columns.

### Joins

Only basic `INNER JOIN` with equality predicates.

These constraints were intentional to keep the implementation focused and readable.

---

## How to Run

### Run the REPL

```bash
cd repo
python -m rdbms.repl
```

**Example session:**

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

### Run the HTTP Server

```bash
cd repo
python -m server.server
```

Then open your browser at:

**http://localhost:8000/**

From the UI you can:

- Create users via the form
- Edit an existing user by clicking **Edit**, updating the fields, and clicking **Save User**
- Delete a user with the **Delete** button
- Refresh the table with the **Refresh** button if needed

The frontend communicates with the backend using `fetch()` and JSON.

---

## Limitations and Future Improvements

- **No persistence layer** – Data is lost when the process exits
- **Very small SQL feature set** – Only equality-based `WHERE` conditions are supported
- **Single-threaded HTTP server** – Handles one request at a time
- **Limited join support** – Only basic `INNER JOIN` with explicit `ON` clause
- **Minimal type system** – Only `INT` and `TEXT` are supported

Possible extensions include persistence, additional SQL operators, concurrency, and more join types.

---

## Requirements / Dependencies

This project is intentionally built on **Python standard library only**:

- No external packages are required
- The `requirements.txt` file exists for completeness but is effectively empty

**Recommended Python version:** 3.9+

---

## Using This Project as a Learning Reference

This repository is suitable as a teaching / learning aid for:

- Core RDBMS concepts:
  - Tables, rows, data types
  - Primary keys and unique constraints
  - Indexes and basic join strategies
- How to design clean modules with clear responsibilities in Python
- Building services in Python using **only the standard library**

---

## AI Usage Acknowledgment

An AI coding assistant (Cursor, powered by an OpenAI model) was used as a development aid, primarily for:

- Generating the initial web frontend skeleton
- Assisting with debugging and fixing logic errors in the Python RDBMS code
- Improving code structure and readability during iteration

All architectural decisions, feature selection, constraint handling, and final code review were done manually to ensure the solution aligns with the Pesapal Junior Developer '26 challenge requirements.
