"""
Minimal HTTP server exposing REST-like CRUD endpoints backed by the in-memory RDBMS.

Endpoints (all under /api/users):

    GET    /api/users               - list all users
    POST   /api/users               - create user (JSON body)
    PUT    /api/users/<id>          - update user by id
    DELETE /api/users/<id>          - delete user by id

User schema:
    id       INT PRIMARY KEY
    name     TEXT
    email    TEXT UNIQUE

The server also serves the static frontend from the ../web directory.
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rdbms.engine import Engine
from rdbms.parser import Parser


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"


engine = Engine()
parser = Parser(engine)


def _init_schema() -> None:
    """
    Create a simple 'users' table if it does not already exist.
    """
    if "users" in engine.tables:
        return
    parser.execute(
        """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE
        );
        """
    )


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "SimpleRDBMSServer/0.1"

    # Utility helpers
    
    def _send_json(self, status: int, payload: Any) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _parse_json_body(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return None, "Missing request body"
        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # pylint: disable=broad-except
            return None, f"Invalid JSON: {exc}"
        if not isinstance(obj, dict):
            return None, "JSON body must be an object"
        return obj, None

    def _parse_user_id(self) -> Optional[int]:
        parts = self.path.split("/")
        if len(parts) == 4 and parts[1] == "api" and parts[2] == "users":
            try:
                return int(parts[3])
            except ValueError:
                return None
        return None

    # Routing
    
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.startswith("/api/users"):
            if self.path.rstrip("/") == "/api/users":
                # List all users
                rows = parser.execute("SELECT id, name, email FROM users;") or []
                self._send_json(HTTPStatus.OK, rows)
            else:
                user_id = self._parse_user_id()
                if user_id is None:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid user id"})
                    return
                rows = parser.execute(
                    f"SELECT id, name, email FROM users WHERE id = {user_id};"
                ) or []
                if not rows:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "User not found"})
                else:
                    self._send_json(HTTPStatus.OK, rows[0])
            return

        # Static files
        self._serve_static()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/api/users":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
            return
        body, error = self._parse_json_body()
        if error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": error})
            return

        # Expect id, name, email
        try:
            user_id = int(body.get("id"))
        except Exception:  # pylint: disable=broad-except
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Field 'id' must be an integer"})
            return
        name = str(body.get("name", "")).strip()
        email = str(body.get("email", "")).strip()
        if not name or not email:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Fields 'name' and 'email' are required"},
            )
            return

        try:
            parser.execute(
                f"INSERT INTO users (id, name, email) VALUES ({user_id}, '{name}', '{email}');"
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._send_json(
            HTTPStatus.CREATED,
            {"id": user_id, "name": name, "email": email},
        )

    def do_PUT(self) -> None:  # noqa: N802
        user_id = self._parse_user_id()
        if self.path.startswith("/api/users") and user_id is not None:
            body, error = self._parse_json_body()
            if error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": error})
                return
            updates = []
            if "name" in body:
                name = str(body["name"]).replace("'", "''")
                updates.append(f"name = '{name}'")
            if "email" in body:
                email = str(body["email"]).replace("'", "''")
                updates.append(f"email = '{email}'")
            if not updates:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "No fields to update"})
                return
            update_clause = ", ".join(updates)
            try:
                count = parser.execute(
                    f"UPDATE users SET {update_clause} WHERE id = {user_id};"
                )
            except Exception as exc:  # pylint: disable=broad-except
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            if not count:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "User not found"})
                return
            row = parser.execute(
                f"SELECT id, name, email FROM users WHERE id = {user_id};"
            )[0]
            self._send_json(HTTPStatus.OK, row)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})

    def do_DELETE(self) -> None:  # noqa: N802
        user_id = self._parse_user_id()
        if self.path.startswith("/api/users") and user_id is not None:
            try:
                count = parser.execute(
                    f"DELETE FROM users WHERE id = {user_id};"
                )
            except Exception as exc:  # pylint: disable=broad-except
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            if not count:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "User not found"})
            else:
                self._send_json(HTTPStatus.NO_CONTENT, {})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})

    # Static file serving 
    def _serve_static(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/" or path == "":
            path = "/index.html"
        file_path = WEB_DIR / path.lstrip("/")

        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        if str(file_path).startswith(str(WEB_DIR)) is False:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if file_path.suffix == ".html":
            mime = "text/html; charset=utf-8"
        elif file_path.suffix == ".css":
            mime = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            mime = "application/javascript; charset=utf-8"
        else:
            mime = "application/octet-stream"

        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run(host: str = "localhost", port: int = 8000) -> None:
    _init_schema()
    server_address = (host, port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Serving HTTP on {host} port {port} (http://{host}:{port}/) ...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()


