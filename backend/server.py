#!/usr/bin/env python3
"""Minimal waitlist API server for Inbox Party."""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# Database imports
try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "waitlist.db"
PORT = int(os.environ.get("PORT", 8000))
DATABASE_URL = os.environ.get("DATABASE_URL")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def init_db():
    """Initialize database connection (PostgreSQL pool or SQLite)."""
    if DATABASE_URL and HAS_POSTGRES:
        # Use PostgreSQL connection pool (Supabase)
        connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL
        )
        # Create table using a connection from the pool
        conn = connection_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS waitlist (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            cursor.close()
        finally:
            connection_pool.putconn(conn)
        return connection_pool
    else:
        # Fallback to SQLite
        connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.commit()
        return connection


def waitlist_count() -> int:
    if DATABASE_URL and HAS_POSTGRES:
        conn = DB_CONN.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM waitlist")
            row = cursor.fetchone()
            cursor.close()
            return int(row[0] if row else 0)
        finally:
            DB_CONN.putconn(conn)
    else:
        cursor = DB_CONN.execute("SELECT COUNT(*) FROM waitlist")
        row = cursor.fetchone()
        return int(row[0] if row else 0)


def waitlist_entries(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if DATABASE_URL and HAS_POSTGRES:
        conn = DB_CONN.getconn()
        try:
            sql = "SELECT name, email, created_at FROM waitlist ORDER BY created_at DESC"
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            if limit is not None and limit > 0:
                cursor.execute(sql + " LIMIT %s", (limit,))
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            return [
                {"name": row["name"], "email": row["email"], "created_at": str(row["created_at"])}
                for row in rows
            ]
        finally:
            DB_CONN.putconn(conn)
    else:
        sql = "SELECT name, email, created_at FROM waitlist ORDER BY datetime(created_at) DESC"
        params: tuple[Any, ...] = ()
        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params = (limit,)
        cursor = DB_CONN.execute(sql, params)
        rows = cursor.fetchall()
        return [
            {"name": row[0], "email": row[1], "created_at": row[2]}
            for row in rows
        ]


def insert_waitlist_record(payload: Dict[str, Any]) -> None:
    if DATABASE_URL and HAS_POSTGRES:
        conn = DB_CONN.getconn()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO waitlist (name, email) VALUES (%s, %s)",
                    (payload["name"], payload["email"]),
                )
                conn.commit()
            finally:
                cursor.close()
        finally:
            DB_CONN.putconn(conn)
    else:
        with DB_CONN:
            DB_CONN.execute(
                "INSERT INTO waitlist (name, email) VALUES (:name, :email)",
                payload,
            )


DB_CONN = init_db()


class WaitlistHandler(BaseHTTPRequestHandler):
    server_version = "InboxPartyWaitlist/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Console logging in a concise, structured way.
        message = fmt % args
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {message}")

    # Helper utilities -------------------------------------------------
    def _allowed_origin(self) -> str:
        origin = self.headers.get("Origin")
        if not origin:
            return "*"
        if origin == "null":
            return "*"
        return origin

    def _set_headers(self, status: int = 200, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.end_headers()

    def _json_response(self, body: Dict[str, Any], status: int = 200) -> None:
        self._set_headers(status=status)
        self.wfile.write(json.dumps(body).encode("utf-8"))

    # HTTP methods -----------------------------------------------------
    def do_OPTIONS(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path in {"/health", "/healthz"}:
            self._json_response({"status": "ok"})
            return

        if path == "/api/waitlist":
            self._json_response({"count": waitlist_count()})
            return

        if path == "/api/waitlist/entries":
            limit_value: Optional[int] = None
            if "limit" in query:
                try:
                    limit_value = int(query["limit"][0])
                    if limit_value <= 0:
                        limit_value = None
                except (ValueError, TypeError, IndexError):
                    limit_value = None

            entries = waitlist_entries(limit_value)

            if query.get("format", ["json"])[0].lower() == "csv":
                self._send_csv(entries)
                return

            self._json_response(
                {
                    "entries": entries,
                    "count": waitlist_count(),
                    "limit": limit_value,
                }
            )
            return

        self._json_response({"error": "Not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/api/waitlist":
            self._json_response({"error": "Not found"}, status=404)
            return

        length_header = self.headers.get("Content-Length")
        if not length_header or not length_header.isdigit():
            self._json_response({"error": "Missing Content-Length"}, status=411)
            return

        raw_body = self.rfile.read(int(length_header) or 0)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON payload"}, status=400)
            return

        name = self._sanitize_name(payload.get("name"))
        email = self._sanitize_email(payload.get("email"))

        if not name:
            self._json_response({"error": "Please share your name so we can personalize the rollout."}, status=400)
            return

        if not email:
            self._json_response({"error": "A valid email is required to join the waitlist."}, status=400)
            return

        try:
            insert_waitlist_record({"name": name, "email": email})
        except Exception as e:
            # Rollback handled within insert_waitlist_record for pool connections

            # Handle unique constraint violations for both SQLite and PostgreSQL
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                self._json_response(
                    {
                        "message": "This email is already on the waitlist.",
                        "count": waitlist_count(),
                    },
                    status=409,
                )
                return
            else:
                self.log_error("Database error: %s", e)
                self._json_response({"error": "We hit a snag saving your request."}, status=500)
                return

        self._json_response(
            {
                "message": "You're on the waitlist! We'll reach out as invites roll out.",
                "email": email,
                "count": waitlist_count(),
            },
            status=201,
        )

    # Sanitizers -------------------------------------------------------
    @staticmethod
    def _sanitize_name(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned if len(cleaned) >= 2 else None

    @staticmethod
    def _sanitize_email(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        candidate = str(value).strip().lower()
        return candidate if EMAIL_PATTERN.match(candidate) else None

    def _send_csv(self, entries: List[Dict[str, Any]]) -> None:
        header = ["name", "email", "created_at"]
        lines = [",".join(header)]
        for entry in entries:
            fields = [
                entry.get("name", "").replace('"', '""'),
                entry.get("email", "").replace('"', '""'),
                entry.get("created_at", "").replace('"', '""'),
            ]
            line = ",".join(f'"{value}"' if "," in value or '"' in value else value for value in fields)
            lines.append(line)
        csv_data = "\n".join(lines)

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="inbox-party-waitlist.csv"')
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.end_headers()
        self.wfile.write(csv_data.encode("utf-8"))


def run_server() -> None:
    with HTTPServer(("", PORT), WaitlistHandler) as httpd:
        print(f"Inbox Party waitlist API running on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server…")
        finally:
            httpd.server_close()
            DB_CONN.close()


if __name__ == "__main__":
    run_server()
