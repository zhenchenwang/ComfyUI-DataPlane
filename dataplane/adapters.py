import hashlib
import sqlite3
import time
from pathlib import Path

from .models import QueryResult, WritebackResult


class SQLiteAdapter:
    def __init__(self, profile):
        self.profile = profile

    def connect(self):
        if self.profile.read_only:
            uri = f"file:{Path(self.profile.database).resolve()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=self.profile.timeout_seconds)
        else:
            conn = sqlite3.connect(self.profile.database, timeout=self.profile.timeout_seconds)
        conn.row_factory = sqlite3.Row
        return conn

    def test_connection(self):
        with self.connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True, "SQLite connection successful"

    def execute_query(self, sql, parameters, policy):
        if not policy.allowed:
            raise PermissionError(policy.reason)
        wrapped = f"SELECT * FROM ({sql.rstrip().rstrip(';')}) AS dataplane_query LIMIT :__dp_limit"
        values = dict(parameters.values)
        values["__dp_limit"] = policy.max_rows + 1
        started = time.perf_counter()
        with self.connect() as conn:
            cursor = conn.execute(wrapped, values)
            raw = cursor.fetchall()
            columns = tuple(item[0] for item in cursor.description or ())
        truncated = len(raw) > policy.max_rows
        raw = raw[: policy.max_rows]
        rows = tuple(dict(item) for item in raw)
        query_hash = hashlib.sha256(
            f"{self.profile.name}|{sql}|{sorted(parameters.values.items())}".encode()
        ).hexdigest()
        return QueryResult(
            columns,
            rows,
            len(rows),
            self.profile.name,
            query_hash,
            truncated,
            round((time.perf_counter() - started) * 1000, 3),
        )

    def insert_row(self, table, row, policy, confirmation):
        if not policy.allowed or not policy.allow_writeback:
            raise PermissionError("Writeback is not allowed by policy")
        if confirmation != "CONFIRM_WRITE":
            raise PermissionError("Writeback confirmation token is missing")
        if self.profile.allowed_tables and table not in self.profile.allowed_tables:
            raise PermissionError(f"Table is not allowed: {table}")
        columns = list(row)
        quoted = ", ".join('"' + column + '"' for column in columns)
        placeholders = ", ".join(":" + column for column in columns)
        sql = f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})'
        with self.connect() as conn:
            cursor = conn.execute(sql, row)
            conn.commit()
        return WritebackResult(True, max(cursor.rowcount, 1), table, "insert", "Row inserted")


class PlannedAdapter:
    def __init__(self, profile):
        self.profile = profile

    def __getattr__(self, name):
        raise NotImplementedError(
            f"{self.profile.driver} adapter is planned but not implemented in 0.1.0"
        )


def create_adapter(profile):
    if profile.driver == "sqlite":
        return SQLiteAdapter(profile)
    if profile.driver == "duckdb":
        from .duckdb_adapter import DuckDBAdapter
        return DuckDBAdapter(profile)
    return PlannedAdapter(profile)
